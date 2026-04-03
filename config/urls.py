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
    path('order/success/', payment_callback_view, name='payment_callback'),
    path('order/creation/', create_order_and_initialize_payment, name='create_order_and_init_payment')
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)