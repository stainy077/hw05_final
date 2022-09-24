from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_page

from posts.forms import CommentForm, PostForm
from posts.models import Follow, Group, Post
from posts.utils import get_paginator

CACHE_TIME = 20
User = get_user_model()


@cache_page(CACHE_TIME)
def index(request):
    """Функция отображения главной страницы."""
    posts = Post.objects.select_related('author').all()
    context = {
        'page_obj': get_paginator(request, posts),
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    """Функция отображения постов выбраной группы."""
    group = get_object_or_404(Group, slug=slug)
    posts = Post.objects.filter(group=group)
    page = get_paginator(request, posts)
    context = {
        'group': group,
        'posts': posts,
        'page_obj': page,
    }
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    """Функция отображения страницы пользователя."""
    user = get_object_or_404(User, username=username)
    posts = Post.objects.filter(author=user)
    page = get_paginator(request, posts)
    if request.user.is_authenticated is True:
        following = Follow.objects.filter(user=request.user, author=user)
    else:
        following = None
    context = {
        'page_obj': page,
        'author': user,
        'post': posts,
        'following': following,
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    """Функция отображения одного поста пользователя."""
    post = get_object_or_404(Post, id=post_id)
    author = post.author
    count_posts = author.posts.all().count()
    form_create_comment = CommentForm(request.POST or None)
    comments = post.comments.all()
    context = {
        'post': post,
        'count_posts': count_posts,
        'user': request.user,
        'form': form_create_comment,
        'comments': comments,
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    """Функция создания нового поста пользователя."""
    form = PostForm(request.POST or None, files=request.FILES or None)
    if form.is_valid() and request.method == 'POST':
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('posts:profile', username=request.user.username)
    context = {
        'form': form,
        'is_edit': False,
    }
    return render(request, 'posts/post_create.html', context)


@login_required
def post_edit(request, post_id):
    """Функция редактирования поста пользователя."""
    edit_post = get_object_or_404(Post, id=post_id)
    if request.user != edit_post.author:
        return redirect('posts:post_detail', post_id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=edit_post,
    )
    if form.is_valid() and request.method == 'POST':
        form.save()
        return redirect('posts:post_detail', post_id)
    context = {
        'form': form,
        'post': edit_post,
        'is_edit': True,
    }
    return render(request, 'posts/post_create.html', context)


@login_required
def add_comment(request, post_id):
    """Функция создания комментария к посту."""
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    posts = Post.objects.filter(author__following__user=request.user)
    followers_cnt = request.user.follower.all().count()
    context = {
        'page_obj': get_paginator(request, posts),
        'followers_cnt': followers_cnt,
    }
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if author != request.user:
        Follow.objects.get_or_create(user=request.user, author=author)
    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    Follow.objects.filter(user=request.user, author=author).delete()
    return redirect('posts:profile', username=username)
