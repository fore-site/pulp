from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.views import generic
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth import login
from src.models import Sku, CartItem, Cart
from ..forms import CustomUserCreationForm, CartUpdateForm
from django.db.models import F
from django_htmx.middleware import HtmxDetails
from ..utils.common import  base_book_queryset, get_user_and_session, get_cart, get_cart_items_and_forms, store_price_and_count, get_related_books
from django.utils.http import url_has_allowed_host_and_scheme
from decimal import Decimal
import random

class HtmxHttpRequest(HttpRequest):
    htmx: HtmxDetails

@require_http_methods(['GET', 'POST'])
def signup(request: HtmxHttpRequest) -> HttpResponse:
    if request.POST:
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=True)
            login(request, user)
            return HttpResponseRedirect(reverse('home'))
        else:
            return render(request, 'src/signup.html', {"form": form})
    else:
        form = CustomUserCreationForm()
        return render(request, 'src/signup.html', {"form": form})

class HotDealsView(generic.TemplateView):
    template_name = 'src/deals.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_queryset = base_book_queryset(Sku)

        manga_deals = base_queryset.filter(book__series__category__name='manga', discount_percent__gte=50).order_by('discount_percent')
        comic_deals = base_queryset.filter(book__series__category__name='comic', discount_percent__gte=50).order_by('discount_percent')

        context['manga_deals'] = manga_deals
        context['comic_deals'] = comic_deals
        return context

class CartView(generic.TemplateView):
    template_name = 'src/cart.html'
    http_method_names = ['get', 'post']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get user object if authenticated, create session instance as well
        user = self.request.user if self.request.user.is_authenticated else None
        if not self.request.session.session_key:
            self.request.session.create()
        session_id = self.request.session.session_key

        context['cart_items_and_forms'] = get_cart_items_and_forms(user, session_id, self.request)
        return context
    
    def post(self, request, **kwargs):
        # Get user object if authenticated, create session instance as well
        user, session_id = get_user_and_session(request)

        # Get and validate form data
        sku_id = request.POST.get('sku_id')
        sku = get_object_or_404(Sku, public_id=sku_id)
        
        # Get cart related to user or session_id, create cart if it doesn't exist
        cart = get_cart(user, session_id, request)

        # Check if item already exists in cart, for idempotency
        try:
            CartItem.objects.get(sku=sku, cart=cart)

        # Create cart item entry if item does not exist in cart        
        except CartItem.DoesNotExist:
            CartItem.objects.create(sku=sku, cart=cart, quantity=1)

        # Get total item count in a cart and store it in user session
        store_price_and_count(request, cart)

        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
        if next_url:
            next_url = next_url.strip()

        # validate the next parameter and ensure user has not tampered with it
        is_safe = url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts=request.get_host(),
            require_https=False
        )
        if request.htmx:
            return HttpResponse(request.session['item_count'])

        if next_url and is_safe:
            return redirect(next_url)
        return redirect('home')

@require_POST
def update_and_delete_cart_view(request: HtmxHttpRequest) -> HttpResponse:
    """View to update cart contents or clear cart"""

    user, session_id = get_user_and_session(request)
    cart = get_cart(user, session_id, request)

    action = request.POST.get('action')
    sku_id = request.POST.get('sku_id')
    if sku_id:
        sku = get_object_or_404(Sku, public_id=sku_id)
    
    form = CartUpdateForm({'quantity': request.POST.get('quantity')})
    if action == 'clear':
        CartItem.objects.filter(cart=cart).delete()
    elif form.is_valid():
        quantity = int(form.cleaned_data.get('quantity'))
        if action == 'add':
            new_qty = quantity + 1
            CartItem.objects.filter(sku=sku, cart=cart).update(quantity=new_qty)
        elif action == 'subtract':
            new_qty = quantity - 1
            CartItem.objects.filter(sku=sku, cart=cart).update(quantity=new_qty)
        elif action == 'delete':
            CartItem.objects.filter(sku=sku, cart=cart).delete()
        else:
            CartItem.objects.filter(sku=sku, cart=cart).update(quantity=quantity)
    else:
        pass
    
    # Get total item count in a cart and store it in user session
    store_price_and_count(request, cart)

    if request.htmx and action != 'delete':
        context = {"cart_items_and_forms": get_cart_items_and_forms(user, session_id, request)}
        cart_main_target = render(request, 'src/cart.html#cart_items', context).content.decode()
        cart_count_oob = f'<span id="cart-count" hx-swap-oob="true">{request.session['item_count']}</span>'
        return HttpResponse(cart_main_target + cart_count_oob)
        # return render(request, 'src/cart.html#cart_items', context)
    elif request.htmx and action == 'delete':
        response = HttpResponse()
        response['HX-Redirect'] = reverse('cart')
        return response
    return redirect('cart')

class CheckoutShippingView(generic.TemplateView):
    template_name = 'src/checkout_shipping.html'
    http_method_names = ['get', 'post']

    def get(self, request, *args, **kwargs):
        self.user = request.user if request.user.is_authenticated else None
        try:
            if self.user:
                cart = Cart.objects.get(user=self.user)
            else:
                cart = Cart.objects.get(id = request.session.get('cart_id'))
        except Cart.DoesNotExist:
            return HttpResponseRedirect(reverse('cart'))
        
        self.cart_items = CartItem.objects.filter(cart=cart)
        if not self.cart_items:
            return HttpResponseRedirect(reverse('cart'))
        
        context = self.get_context_data(request)

        return render(request, self.template_name, context)

    def get_context_data(self, request, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if self.user:
            context['user'] = self.user

        context["cart_items"] = self.cart_items
        
        request.session["shipping_fee"] = random.choice(['4.00', '5.00'])
        request.session["payment_provider_fee"] = random.choice(['3.50', '4.15', '2.80'])
        total_price_before_ship = Decimal(request.session.get('subtotal_price')) + Decimal(self.request.session.get('payment_provider_fee'))

        context["total_price"] = total_price_before_ship.quantize(Decimal('0.01'))
        return context

class CheckoutReviewView(generic.TemplateView):
    template_name = 'src/checkout_review.html'
    http_method_names = ['get', 'post']

    def get(self, request, *args, **kwargs):
        self.user = request.user if request.user.is_authenticated else None
        try:
            if self.user:
                cart = Cart.objects.get(user=self.user)
            else:
                cart = Cart.objects.get(id = request.session.get('cart_id'))
        except Cart.DoesNotExist:
            return HttpResponseRedirect(reverse('cart'))
        
        self.cart_items = CartItem.objects.filter(cart=cart)
        if not self.cart_items:
            return HttpResponseRedirect(reverse('cart'))

        context = self.get_context_data(request)

        return render(request, self.template_name, context)

    def get_context_data(self, request, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if self.user:
            context['user'] = self.user

        context["cart_items"] = self.cart_items
        
        return context

class CheckoutPaymentView(generic.TemplateView):
    template_name = 'src/checkout_payment.html'

    def get(self, request, *args, **kwargs):
        self.user = request.user if request.user.is_authenticated else None
        try:
            if self.user:
                cart = Cart.objects.get(user=self.user)
            else:
                cart = Cart.objects.get(id = request.session.get('cart_id'))
        except Cart.DoesNotExist:
            return HttpResponseRedirect(reverse('cart'))
        
        self.cart_items = CartItem.objects.filter(cart=cart)
        if not self.cart_items:
            return HttpResponseRedirect(reverse('cart'))   

        context = self.get_context_data(request)

        return render(request, self.template_name, context)   

    def get_context_data(self, request, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if self.user:
            context['user'] = self.user

        context["cart_items"] = self.cart_items

        return context
    
class UserProfileView(generic.DetailView):
    pass