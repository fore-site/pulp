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
from django.contrib.auth import views as auth_views
from src.forms import CustomLoginForm
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.IndexView.as_view(), name='home'),
    path('login/', auth_views.LoginView.as_view(template_name="src/login.html", authentication_form=CustomLoginForm), name='login'),
    path('sign-up/', views.signup, name='signup'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('books/<slug:category>/', views.BookListView.as_view(), name='book_list'),
    path('series-index/<str:series_type>', views.SeriesIndexView.as_view(), name='series_index'),
    path('series/<slug:uuid>', views.SeriesDetailView.as_view(), name='series_detail'),
    path('b/<slug:slug>/<slug:uuid>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('books/p/search', views.search_results_view, name='search_results'),
    path('books/deals', views.HotDealsView.as_view(), name='deals'),
    path('cart', views.CartView.as_view(), name='cart'),
    path('cart/update', views.update_and_delete_cart, name='cart_update'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)