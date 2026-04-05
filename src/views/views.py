from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.views import generic
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth import login
from src.models import Sku, CartItem
from ..forms import CustomUserCreationForm, CartUpdateForm
from django_htmx.middleware import HtmxDetails
from ..utils.common import  base_book_queryset, get_user_and_session, get_cart, get_cart_items_and_forms, store_price_and_count, get_related_books
from django.utils.http import url_has_allowed_host_and_scheme

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

        context['cart_items_and_forms'] = get_cart_items_and_forms(user, session_id)
        
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
        cart = get_cart(user, session_id)

        # Check if item already exists in cart, for idempotency
        try:
            CartItem.objects.get(sku=sku, cart=cart)

        # Create cart item entry if item does not exist in cart        
        except CartItem.DoesNotExist:
            # Ensure user is not currently processing payment in a separate window
            # Ensure sku is not out of stock
            if not request.session.get('is_payment_processing') and (sku.quantity > 0 if sku.format != 'Digital' else sku.quantity == None):
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
    cart = get_cart(user, session_id)

    action = request.POST.get('action')
    sku_id = request.POST.get('sku_id')
    if sku_id:
        sku = get_object_or_404(Sku, public_id=sku_id)
    
    form = CartUpdateForm({'quantity': request.POST.get('quantity')})
    if request.session.get('is_payment_processing') or sku.quantity < 1:
        pass
    elif action == 'clear':
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
    
    if request.htmx and request.session.get('is_payment_processing'):
        response = HttpResponse()
        response['HX-Redirect'] = next_url if next_url and is_safe else reverse('cart')
        return response
    elif request.htmx and action != 'delete':
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
