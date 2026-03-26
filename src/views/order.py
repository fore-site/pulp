from django.shortcuts import render
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.views.decorators.http import require_POST, require_GET
from django.db import transaction
from django.db.models import Case, When, F, DecimalField
from src.models import CartItem, Cart, Order, OrderItem
from django_htmx.middleware import HtmxDetails

class HtmxHttpRequest(HttpRequest):
    htmx: HtmxDetails

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
    user = request.user if request.user.is_authenticated else None
    try:
        if user:
            cart = Cart.objects.get(user=user)
        else:
            cart = Cart.objects.get(id = request.session.get('cart_id'))
    except Cart.DoesNotExist:
        return HttpResponseRedirect(reverse('cart'))

    cart_items = CartItem.objects.filter(cart=cart).annotate(unit_price=Case(
                    When(sku__discount_percent__gt=0, then=(F('sku__price_usd') - (F('sku__price_usd') * F('sku__discount_percent') / 100))),
                    default=F('sku__price_usd'),
                    output_field=DecimalField(max_digits=10, decimal_places=2)
                ))
    if not cart_items:
        return HttpResponseRedirect(reverse('cart'))

    with transaction.atomic():
        user_order = Order.objects.create(
            user = user,
            session_id = request.session.session_key,
            subtotal_amount_usd = request.session.get('total_price_before_ship'),
            shipping_fee_usd = request.session.get('shipping_fee'),
            total_amount_usd = request.session.get('total_price_after_ship'),
            order_exchange_rate = 1400,
        )

        for item in cart_items:
            OrderItem.objects.create(
                order = user_order,
                sku = item.sku,
                quantity = item.quantity,
                unit_price_usd = item.unit_price
            )

