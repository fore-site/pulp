"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from src.views import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.IndexView.as_view(), name='home'),
    path('<int:user_id>/', views.IndexView.as_view(), name='home'),
    path('sign-in/', views.signin, name='signin'),
    path('sign-up/', views.signup, name='signup'),
    path('auth/sign-in/<int:user_id>/', views.auth_signin, name='auth_signin'),
    path('auth/sign-up/<int:user_id>/', views.auth_signup, name='auth_signup'),
    path('manga/', views.BookListView.as_view(), name='manga_listing'),
    path('books/<slug:slug>/<int:pk>/', views.DetailView.as_view(), name='book_detail'),
    path('comic/', views.BookListView.as_view(), name='comic_listing'),
    path('order/<int:id>/', views.order, name='orders')
]
