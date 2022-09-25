import shutil
import tempfile
import time

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Comment, Follow, Group, Post
from yatube.settings import POSTS_COUNT, POSTS_TEST_COUNT

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
COUNT_FOR_POSTS = 14


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTest(TestCase):
    """Тестрование страниц приложения posts на корректную
    работу views-функций."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        User = get_user_model()
        cls.test_user1 = User.objects.create(username='NoName')
        cls.ok_group = Group.objects.create(
            title='Правильная тестовая группа',
            slug='ok-slug',
            description='Описание правильной группы',
        )
        cls.wrong_group = Group.objects.create(
            title='Другая тестовая группа',
            slug='wrong-slug',
            description='Описание другой группы',
        )
        cls.test_post = Post.objects.create(
            text='Тестовое сообщение!!!',
            author=cls.test_user1,
            group=cls.ok_group,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        """ Создание неавторизованного клиента и
        клиента с авторизованным пользователем. Очистка кэша."""
        self.guest_client = Client()

        user1 = get_user_model()
        self.user1 = user1.objects.get(username='NoName')
        self.authorized_client1 = Client()
        self.authorized_client1.force_login(self.user1)

        user2 = get_user_model()
        self.user2 = user2.objects.create(username='TestUser2')
        self.authorized_client2 = Client()
        self.authorized_client2.force_login(self.user2)

        self.follow2 = self.authorized_client2.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.user1},
        ))
        self.test_comment = Comment.objects.create(
            post=self.test_post,
            author=self.user2,
            text='Тест комментарий',
        )

        cache.clear()

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        page_templates_dict = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list',
                kwargs={'slug': self.ok_group.slug},
            ): 'posts/group_list.html',
            reverse(
                'posts:profile',
                kwargs={'username': self.test_post.author},
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.test_post.id},
            ): 'posts/post_detail.html',
            reverse(
                'posts:post_edit',
                kwargs={'post_id': self.test_post.id},
            ): 'posts/post_create.html',
            reverse('posts:post_create'): 'posts/post_create.html',
        }

        for reverse_name, template in page_templates_dict.items():
            with self.subTest(template=template):
                response = self.authorized_client1.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_page_show_correct_context(self):
        """View-функция страницы index передает правильный контекст."""
        response = self.authorized_client1.get(reverse('posts:index'))
        first_post = response.context['page_obj'][0]
        self.assertEqual(first_post, self.test_post)

    def test_group_list_page_show_correct_context(self):
        """View-функция страницы group_list передает правильный контекст."""
        response = self.authorized_client1.get(reverse(
            'posts:group_list',
            kwargs={'slug': self.ok_group.slug},
        ))
        test_group_field = response.context.get('group')
        test_posts_field = response.context.get('posts')[0]
        test_page_obj_field = response.context.get('page_obj')[0]
        test_group_title = response.context.get('group').title
        test_group_slug = response.context.get('group').slug
        test_group_description = response.context.get('group').description

        self.assertEqual(test_group_field, self.ok_group)
        self.assertEqual(test_posts_field, self.test_post)
        self.assertEqual(test_page_obj_field, self.test_post)
        self.assertEqual(test_group_title, self.ok_group.title)
        self.assertEqual(test_group_slug, self.ok_group.slug)
        self.assertEqual(test_group_description, self.ok_group.description)

    def test_post_create_page_show_correct_context(self):
        """View-функция страницы post_create передает правильный контекст."""
        response = self.authorized_client1.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for field_name, field_format in form_fields.items():
            with self.subTest(value=field_name):
                form_field = (
                    response.context.get('form').fields.get(field_name)
                )
                is_edit = response.context.get('is_edit')
                self.assertIsInstance(form_field, field_format)
                self.assertEqual(is_edit, False)

    def test_profile_page_show_correct_context(self):
        """View-функция страницы профайла передает правильный контекст."""
        response = self.authorized_client2.get(reverse(
            'posts:profile',
            kwargs={'username': self.test_post.author},
        ))
        test_profile_page_obj = response.context.get('page_obj')[0]
        test_profile_author = response.context.get('author')
        test_profile_post = response.context.get('post')[0]
        test_profile_following = response.context.get('following')[0]

        self.assertEqual(test_profile_page_obj, self.test_post)
        self.assertEqual(test_profile_author, self.test_post.author)
        self.assertEqual(test_profile_post, self.test_post)
        self.assertEqual(test_profile_following.author, self.user1)

    def test_post_detail_show_correct_context(self):
        """View-функция страницы поста передает правильный контекст."""
        response = self.authorized_client2.get(reverse(
            'posts:post_detail',
            kwargs={'post_id': self.test_post.id},
        ))
        post_detail_post = response.context.get('post')
        post_detail_count_posts = response.context.get('count_posts')
        post_detail_user = response.context.get('user')
        post_detail_comments = response.context.get('comments')[0]
        author_posts = self.user1.posts.count()
        correct_comment = Comment.objects.filter(text='Тест комментарий')[0]

        self.assertEqual(post_detail_post, self.test_post)
        self.assertEqual(post_detail_count_posts, author_posts)
        self.assertEqual(post_detail_user, self.user2)
        self.assertTrue(correct_comment)
        self.assertEqual(post_detail_comments, correct_comment)

        form_dict = {'text': forms.fields.CharField}
        form_field = (response.context.get('form').fields.get('text'))
        self.assertIsInstance(form_field, form_dict['text'])

    def test_post_edit_page_show_correct_context(self):
        """View-функция редактирования поста передает правильный контекст."""
        response = self.authorized_client1.get(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': self.test_post.id},
            ),
        )
        post_edit_post = response.context.get('post')
        self.assertEqual(post_edit_post, self.test_post)
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for field_name, field_format in form_fields.items():
            with self.subTest(value=field_name):
                form_field = (
                    response.context.get('form').fields.get(field_name)
                )
                is_edit = response.context.get('is_edit')
                self.assertIsInstance(form_field, field_format)
                self.assertEqual(is_edit, True)

    def test_post_image_exists_in_context(self):
        """При выводе поста картинка передается в словаре context."""
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif',
        )
        tim_group = Group.objects.create(
            title='Группа с картинками',
            slug='image-slug',
            description='Тут посты с картинками',
        )
        tim_post = Post.objects.create(
            text='Сообщение с картинкой',
            author=self.test_user1,
            group=tim_group,
            image=uploaded,
        )
        page_dict = {
            reverse('posts:index'): 'page_obj',
            reverse(
                'posts:group_list',
                kwargs={'slug': tim_group.slug},
            ): 'page_obj',
            reverse(
                'posts:profile',
                kwargs={'username': tim_post.author},
            ): 'page_obj',
        }
        for reverse_name, context_item in page_dict.items():
            with self.subTest():
                response = self.authorized_client1.get(reverse_name)
                test_page_image = response.context.get(context_item)[0].image
                self.assertEqual(test_page_image, tim_post.image)

        response = self.authorized_client1.get(reverse(
            'posts:post_detail',
            kwargs={'post_id': tim_post.id},
        ))
        test_page_image = response.context.get('post').image
        self.assertEqual(test_page_image, tim_post.image)

    def test_post_in_right_group(self):
        """Пост попал в нужную группу"""
        groups_list = {
            'ok_group': reverse(
                'posts:group_list',
                kwargs={'slug': self.ok_group.slug},
            ),
            'wrong_group': reverse(
                'posts:group_list',
                kwargs={'slug': self.wrong_group.slug}
            )
        }
        for some_group, reverse_name in groups_list.items():
            with self.subTest():
                response = self.authorized_client1.get(reverse_name)
                posts_in_group = response.context.get('page_obj')
                if some_group == 'ok_group':
                    self.assertIn(self.test_post, posts_in_group)
                else:
                    self.assertNotIn(self.test_post, posts_in_group)

    def test_main_page_display_post(self):
        """Пост видно на главной странице"""
        response = self.authorized_client1.get(reverse('posts:index'))
        main_page_view = response.context.get('page_obj')
        self.assertIn(self.test_post, main_page_view)

    def test_profile_page_display_post(self):
        """Пост видно на странице автора"""
        response = self.authorized_client1.get(reverse(
            'posts:profile',
            kwargs={'username': self.test_post.author},
        ))
        profile_page_view = response.context.get('page_obj')
        self.assertIn(self.test_post, profile_page_view)

    # Проверка кэширования стартовой страницы
    def test_cached_index_page(self):
        """Стартовая страница сохранена в кэше."""
        cached_response1 = self.authorized_client1.get(reverse('posts:index'))
        Post.objects.filter(id=self.test_post.id).delete()
        cached_response2 = self.authorized_client1.get(reverse('posts:index'))
        self.assertEqual(cached_response1.content, cached_response2.content)

        time.sleep(20)
        cached_response3 = self.authorized_client1.get(reverse('posts:index'))
        self.assertNotEqual(
            cached_response1.content,
            cached_response3.content,
        )

    # Проверка работоcпособности подписки/отписки
    def test_follow(self):
        """При подписке создается соответствующая запись в БД."""
        self.authorized_client1.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.user2},
        ))
        follow_exists = Follow.objects.filter(
            user=self.user1,
            author=self.user2,
        ).exists()
        self.assertTrue(follow_exists)

    def test_unfollow(self):
        """При отписке удаляется соответствующая запись в БД."""
        self.authorized_client1.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.user2},
        ))
        self.authorized_client1.get(reverse(
            'posts:profile_unfollow',
            kwargs={'username': self.user2},
        ))
        follow_exists = Follow.objects.filter(
            user=self.user1,
            author=self.user2,
        ).exists()
        self.assertFalse(follow_exists)

    def test_follow_index_page_display_followed_author_post(self):
        """В ленте подписок появляются посты соответствующих авторов"""
        kat_post = Post.objects.create(
            text='Сообщение TestUser2',
            author=self.user2,
            group=self.ok_group,
        )
        # 'TestUser2' подписан на 'NoName'
        Follow.objects.get_or_create(user=self.user2, author=self.user1)

        # Пост автора 'NoName' появляется в ленте подписок у 'TestUser2'
        response = self.authorized_client2.get(reverse('posts:follow_index'))
        follow_index_page_view1 = response.context.get('page_obj')
        self.assertIn(self.test_post, follow_index_page_view1)

        # 'NoName' НЕ подписан на 'TestUser2'
        # Пост автора 'TestUser2' НЕ появится в ленте подписок у 'NoName'
        response = self.authorized_client1.get(reverse('posts:follow_index'))
        follow_index_page_view2 = response.context.get('page_obj')
        self.assertNotIn(kat_post, follow_index_page_view2)


class PaginatorViewsTest(TestCase):
    """Тестирование страниц на корректную работу паджинатора."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        User = get_user_model()
        cls.test_user1 = User.objects.create(username='TestUser1')
        cls.group = Group.objects.create(
            title='Tестовая группа',
            slug='ok-slug',
            description='Описание группы',
        )
        cls.test_posts = []
        for post in range(1, COUNT_FOR_POSTS):
            cls.test_posts.append(Post(
                text=f'Тестовое сообщение - {post}',
                author=cls.test_user1,
                group=cls.group,
            ))
        Post.objects.bulk_create(cls.test_posts)

    def setUp(self):
        self.index_reverse = reverse('posts:index')
        self.group_list_reverse = reverse(
            'posts:group_list',
            kwargs={'slug': self.group.slug},
        )
        self.profile_reverse = reverse(
            'posts:profile',
            kwargs={'username': self.test_user1},
        )
        cache.clear()

    def test_first_page_urls_contains_ten_records(self):
        """Проверка: количество постов на странице равно 10."""
        url_reverse_list = [
            self.index_reverse,
            self.group_list_reverse,
            self.profile_reverse,
        ]
        for url_reverse in url_reverse_list:
            with self.subTest(url_reverse=url_reverse):
                response = self.client.get(url_reverse)
                self.assertEqual(
                    len(response.context['page_obj']),
                    POSTS_COUNT,
                )

    def test_second_page_urls_contains_three_records(self):
        """Проверка: на второй странице должно быть три поста."""
        url_reverse_list = [
            self.index_reverse,
            self.group_list_reverse,
            self.profile_reverse,
        ]
        for url_reverse in url_reverse_list:
            with self.subTest(url_reverse=url_reverse):
                response = self.client.get(url_reverse + '?page=2')
                self.assertEqual(
                    len(response.context['page_obj']),
                    POSTS_TEST_COUNT,
                )
