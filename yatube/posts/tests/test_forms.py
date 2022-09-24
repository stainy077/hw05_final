import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from posts.models import Comment, Group, Post

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
NEW_POST_TEXT = 'Новое сообщение!!!'


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        User = get_user_model()
        cls.user = User.objects.create(username='NoName')

        cls.test_group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )

        cls.test_post = Post.objects.create(
            text='Тестовое сообщение!!!',
            author=cls.user,
            group=cls.test_group,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        # super().tearDownClass()

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        self.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif',
        )

    def test_post_create(self):
        """Валидная форма создает запись в Post."""
        posts_count = Post.objects.count()
        form_data = {
            'text': NEW_POST_TEXT,
            'group': self.test_group.id,
            'image': self.uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(response, reverse(
            'posts:profile',
            kwargs={'username': 'NoName'},
        ))
        self.assertEqual(Post.objects.count(), posts_count + 1)
        post = Post.objects.filter(
            text=form_data['text'],
            group=self.test_group.id,
            image='posts/small.gif',
        )
        self.assertTrue(post.exists())

    def test_post_edit(self):
        """Валидная форма редактирует существующую запись в Post."""
        posts_count = Post.objects.count()
        edit_post = PostFormTests.test_post
        form_new_data = {
            'text': 'Новый текст',
            'author': self.user,
            'group': self.test_group.id,
        }
        response = self.authorized_client.post(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': edit_post.id},
            ),
            data=form_new_data,
            follow=True,
        )
        self.assertRedirects(response, reverse(
            'posts:post_detail',
            kwargs={'post_id': edit_post.id},
        ))

        self.assertEqual(Post.objects.count(), posts_count)
        edit_post = Post.objects.last()
        self.assertTrue(edit_post)
        self.assertEqual(edit_post.text, form_new_data['text'])
        self.assertEqual(edit_post.author, form_new_data['author'])
        self.assertEqual(edit_post.group.id, form_new_data['group'])

    def test_comment_added(self):
        """После успешной отправки комментарий появляется на странице поста."""
        comments_count = Comment.objects.count()

        form_data = {'text': 'Другой комментарий'}
        self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.test_post.id}),
            # print('!!!{self.test_post.id}!!!!')
            data=form_data,
            follow=True,
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertTrue(Comment.objects.filter(text='Другой комментарий'))
