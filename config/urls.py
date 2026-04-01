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
from src.views import *
from django.contrib.auth import views as auth_views
from src.forms import CustomLoginForm
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', IndexView.as_view(), name='home'),
    path('login/', auth_views.LoginView.as_view(template_name="src/login.html", authentication_form=CustomLoginForm), name='login'),
    path('sign-up/', signup, name='signup'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('index/<str:series_type>', SeriesIndexView.as_view(), name='series_index'),
    path('series/<uuid:public_id>', SeriesDetailView.as_view(), name='series_detail'),
    path('b/<uuid:public_id>/', ProductDetailView.as_view(), name='product_detail'),
    path('books/p/search', search_results_view, name='search_results'),
    path('books/deals', HotDealsView.as_view(), name='deals'),
    path('cart', CartView.as_view(), name='cart'),
    path('cart/update', update_and_delete_cart_view, name='cart_update'),
    path('bestselling/<slug:category>/', BestsellingView.as_view(), name='bestselling'),
    path('new/<slug:category>/', NewReleaseView.as_view(), name='new_release'),
    path('checkout/shipping/', CheckoutShippingView.as_view(), name='checkout_shipping'),
    path('checkout/review/', CheckoutReviewView.as_view(), name='checkout_review'),
    path('orders/lookup/', order_lookup_view, name='order_lookup'),
    path('orders/', order_detail_view, name='order_detail'),
    path('order/success/<uuid:track_id>', order_confirmed_view, name='order_confirmed'),
    path('order/creation/', handle_payment_and_order_view, name='handle_order_and_payment')
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)