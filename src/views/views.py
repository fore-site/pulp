from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.views import generic
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.contrib.auth import login
from src.models import Sku, CartItem, Cart, Order, OrderItem
from ..forms import CustomUserCreationForm, CartUpdateForm, ShippingAddressForm
from django_htmx.middleware import HtmxDetails
from ..utils.common import  base_book_queryset, get_user_and_session, get_cart, get_cart_items_and_forms, store_price_and_count, get_related_books
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
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
        
        # Curate trending books for empty cart state
        base_queryset = base_book_queryset(Sku)
        trending = (base_queryset.filter(book__trending_score__gt=0).order_by('book').distinct('book')[:10]
                     )
        context['trending'] = trending
        return context
    
    def post(self, request):
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

        next_url = request.POST.get('next')
        if next_url:
            next_url = next_url.strip()

        # validate the next parameter and ensure user has not tampered with it
        is_safe = url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts=request.get_host(),
            require_https=False
        )
        
        if request.htmx and next_url == reverse('cart'):
            if is_safe:
                response = HttpResponse()
                response['HX-Redirect'] = next_url
                return response

        if request.htmx and next_url != reverse('cart'):
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
    elif action == 'delete':
            CartItem.objects.filter(sku=sku, cart=cart).delete()
    elif form.is_valid():
        quantity = int(form.cleaned_data.get('quantity'))
        if action == 'add':
            new_qty = quantity + 1
            CartItem.objects.filter(sku=sku, cart=cart).update(quantity=new_qty)
        elif action == 'subtract':
            new_qty = quantity - 1
            CartItem.objects.filter(sku=sku, cart=cart).update(quantity=new_qty)
        else:
            CartItem.objects.filter(sku=sku, cart=cart).update(quantity=quantity)
    else:
        pass
    
    # Get total item count in a cart and store it in user session
    store_price_and_count(request, cart)

    next_url = request.POST.get('next')
    if next_url:
        next_url = next_url.strip()
        print(next_url)

    # validate the next parameter and ensure user has not tampered with it
    is_safe = url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts=request.get_host(),
            require_https=False
        )

    if request.htmx and action != 'delete':
        context = {"cart_items_and_forms": get_cart_items_and_forms(user, session_id, request)}
        cart_main_target = render(request, 'src/cart.html#cart_items', context).content.decode()
        cart_count_oob = f'<span id="cart-count" hx-swap-oob="true">{request.session.get('item_count')}</span>'
        return HttpResponse(cart_main_target + cart_count_oob)
        # return render(request, 'src/cart.html#cart_items', context)
    elif request.htmx and action == 'delete':
        response = HttpResponse()
        response['HX-Redirect'] = next_url if next_url and is_safe else reverse('cart')
        return response
    return redirect('cart')

class CheckoutShippingView(generic.TemplateView):
    template_name = 'src/checkout_shipping.html'
    http_method_names = ['get', 'post']

    def get(self, request):
        if request.htmx:
            state = request.GET.get('address_state')
            request.session['address_state'] = state
            subtotal = Decimal(request.session.get('total_price_before_ship'))
            if state == 'Lagos':
                request.session['shipping_fee'] = '3.00'
                total_price_after_ship = (subtotal + Decimal('3.00')).quantize(Decimal('0.01'))
                request.session['total_price_after_ship'] = str(total_price_after_ship)
                total_price_oob = f"<span id='total_price' hx-swap-oob='true' class='text-base font-bold text-primary'>{request.session.get('total_price_after_ship')}</span>"
                return HttpResponse('$3.00' + total_price_oob)
            
            elif state == 'Select State':
                request.session['shipping_fee'] = None
                total_price_oob = f"<span id='total_price' hx-swap-oob='true' class='text-base font-bold text-primary'>{request.session.get('total_price_before_ship')}</span>"
                return HttpResponse('To be calculated' + total_price_oob)
            
            else:
                request.session['shipping_fee'] = '5.00'
                total_price_after_ship = (subtotal + Decimal('5.00')).quantize(Decimal('0.01'))
                request.session['total_price_after_ship'] = str(total_price_after_ship)
                total_price_oob = f"<span id='total_price' hx-swap-oob='true' class='text-base font-bold text-primary'>{request.session.get('total_price_after_ship')}</span>"
                return HttpResponse('$5.00' + total_price_oob)
            
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
        today = timezone.now()
        estimated_delivery_dates = (today + timedelta(days=2)).strftime("%b, %d"), (today + timedelta(days=3)).strftime("%b, %d")
    
        self.request.session["payment_provider_fee"] = random.choice(['3.50', '4.15', '2.80'])
        total_price_before_ship = Decimal(self.request.session.get('subtotal_price')) + Decimal(self.request.session.get('payment_provider_fee'))

        self.request.session["total_price_before_ship"] = str(total_price_before_ship.quantize(Decimal('0.01')))
        
        if self.request.session.get('shipping_fee'):
            self.request.session['total_price_after_ship'] = str((total_price_before_ship + Decimal(self.request.session.get('shipping_fee'))).quantize(Decimal('0.01')))

        if request.session.get('firstname'):
            form = ShippingAddressForm(initial={
                'recipient_firstname': request.session.get('firstname'),
                'recipient_lastname': request.session.get('lastname'),
                'address_desc': request.session.get('address_desc'),
                'address_state': request.session.get('address_state'),
                'address_city': request.session.get('address_city'),
                'phone_no': request.session.get('phone_no'),
                'email': request.session.get('email')})
        else:
            form = ShippingAddressForm()
        context["form"] = form
        context['delivery_date_1'] = estimated_delivery_dates[0]
        context['delivery_date_2'] = estimated_delivery_dates[1]
        
        return context
    
    def post(self, request):
        form = ShippingAddressForm(request.POST)
        if form.is_valid():
            self.request.session['firstname'] = form.cleaned_data['recipient_firstname']
            self.request.session['lastname'] = form.cleaned_data['recipient_lastname']
            self.request.session['address_desc'] = form.cleaned_data['address_desc']
            self.request.session['address_state'] = form.cleaned_data['address_state']
            self.request.session['address_city'] = form.cleaned_data['address_city']
            self.request.session['phone_no'] = form.cleaned_data['phone_no']
            self.request.session['email'] = form.cleaned_data['email']

            return HttpResponseRedirect(reverse('checkout_review'))
        else:
            context = self.get_context_data(request)
            context['form'] = form
            return render(request, self.template_name, context)

class CheckoutReviewView(generic.TemplateView):
    template_name = 'src/checkout_review.html'
    http_method_names = ['get', 'post']

    def get(self, request):
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

        if not request.session.get('firstname'):
            return HttpResponseRedirect(reverse('checkout_shipping'))

        context = self.get_context_data(request)

        return render(request, self.template_name, context)

    def get_context_data(self, request, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now()
        estimated_delivery_dates = (today + timedelta(days=2)).strftime("%b, %d"), (today + timedelta(days=3)).strftime("%b, %d")
        
        if self.user:
            context['user'] = self.user

        # Revalidate total price before/after shipping fee
        total_price_before_ship = Decimal(self.request.session.get('subtotal_price')) + Decimal(self.request.session.get('payment_provider_fee'))

        self.request.session["total_price_before_ship"] = str(total_price_before_ship.quantize(Decimal('0.01')))
        
        if self.request.session.get('shipping_fee'):
            self.request.session['total_price_after_ship'] = str((total_price_before_ship + Decimal(self.request.session.get('shipping_fee'))).quantize(Decimal('0.01')))

        context["cart_items"] = self.cart_items
        context['delivery_date_1'] = estimated_delivery_dates[0]
        context['delivery_date_2'] = estimated_delivery_dates[1]

        return context
    
@require_GET
def order_lookup_view(request: HtmxHttpRequest) -> HttpResponse:
    """View to retrieve order lookup form"""
    return render(request, 'src/order_lookup.html')

@require_GET
def order_detail_view(request: HtmxHttpRequest) -> HttpResponse:
    """ View to display order details for real-time tracking """
    track_id = request.GET.get('track_id')
    try:
        order = Order.objects.get(tracking_number__iexact=track_id)
        order_items = OrderItem.objects.filter(order=order)
    except Order.DoesNotExist:
        order = []
        order_items = []
    
    return render(request, 'src/order_detail.html', {'order': order, 'order_items': order_items})

@require_POST
def order_creation_view(request: HtmxHttpRequest) -> HttpResponse:
    """ Create order in database"""
    with transaction.atomic():
        Order.objects.create(
            user = request.user if request.user.is_authenticated else None,
            session_id = request.session.session_key,
            subtotal_amount_usd = request.session.get('total_price_before_ship'),
            shipping_fee_usd = request.session.get('shipping_fee'),
            total_amount_usd = request.session.get('total_price_after_ship')
        )