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
    path('', views.home, {"user_id": None}, name='home'),
    path('/<int:user_id>/', views.home, name='home'),
    path('manga/', views.manga, name='manga_listing'),
    path('manga/<int:manga_id>/', views.detail, name='manga_detail'),
    path('comic/<int:comic_id>/', views.comic, name='comic_detail'),
    path('order/<int:id>/', views.order, name='orders')
]
