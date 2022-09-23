from django.contrib.auth import get_user_model
from django.test import TestCase

from posts.models import Group, Post
from yatube.settings import FIRST_CHARACTERS

User = get_user_model()


class PostModelTest(TestCase):
    """Тестирование модели Post."""

    @classmethod
    def setUpClass(cls):
        """Создание тестовой записи в БД."""
        super().setUpClass()
        cls.user = User.objects.create(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )

    def test_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        post = PostModelTest.post
        expected_object_name = post.text[:FIRST_CHARACTERS]
        self.assertEqual(expected_object_name, post.__str__())


class GroupModelTest(TestCase):
    """Тестирование модели Group."""

    @classmethod
    def setUpClass(cls):
        """Создание тестовой записи в БД."""
        super().setUpClass()
        cls.user = User.objects.create(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )

    def test_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        group = GroupModelTest.group
        expected_object_name = group.title
        self.assertEqual(expected_object_name, group.__str__())
