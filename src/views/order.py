from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.views.decorators.http import require_POST, require_GET
from django.views import generic
from django.db import transaction
from django.db.models import Case, When, F, DecimalField
from src.models import CartItem, Cart, Order, OrderItem, OrderAddress
from django_htmx.middleware import HtmxDetails
from datetime import timedelta
import time

class HtmxHttpRequest(HttpRequest):
    htmx: HtmxDetails

class OrderHistory(generic.ListView):
    model = Order
    template_name = 'src/order_history.html'
    context_object_name = 'user_orders'

    def get_queryset(self):
        user = self.request.user if self.request.user.is_authenticated else None
        session_id = self.request.session.session_key

        if user:
            orders = Order.objects.filter(user=user)
        else:
            orders = Order.objects.filter(session_id=session_id)

        return orders

@require_GET
def order_lookup_view(request: HtmxHttpRequest) -> HttpResponse:
    """View to retrieve order lookup form"""
    return render(request, 'src/order_lookup.html')

@require_GET
def order_detail_view(request: HtmxHttpRequest) -> HttpResponse:
    """ View to display order details for real-time tracking """
    order_number = request.GET.get('order_number')
    try:
        order = Order.objects.get(order_number__iexact=order_number)
        order_items = OrderItem.objects.filter(order=order)
        order_address = OrderAddress.objects.get(order=order)
    except Order.DoesNotExist:
        order = []
        order_items = []
        order_address = []
    
    return render(request, 'src/order_detail.html',
                   {'order': order, 'order_items': order_items, 'order_address': order_address})

@require_POST
def handle_payment_and_order_view(request: HtmxHttpRequest) -> HttpResponse:
    """ Create order in database and redirect to payment provider"""
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

    if not request.session.get('firstname'):
        return HttpResponseRedirect(reverse('checkout_shipping'))
    
    request.session['is_payment_processing'] = True

    with transaction.atomic():
        user_order = Order.objects.create(
            user = user,
            session_id = request.session.session_key,
            subtotal_amount_usd = request.session.get('subtotal_price'),
            shipping_fee_usd = request.session.get('shipping_fee'),
            total_amount_usd = request.session.get('total_price'),
            order_exchange_rate = 1400,
        )

        for item in cart_items:
            OrderItem.objects.create(
                order = user_order,
                sku = item.sku,
                quantity = item.quantity,
                unit_price_usd = item.unit_price
            )

        OrderAddress.objects.create(
            order = user_order,
            recipient_firstname = request.session.get('firstname'),
            recipient_lastname = request.session.get('lastname'),
            recipient_email = request.session.get('email'),
            recipient_phone_no = request.session.get('phone_no'),
            address_desc = request.session.get('address_desc'),
            address_state = request.session.get('address_state'),
            address_city = request.session.get('address_city')
        )

        time.sleep(10)

    return HttpResponseRedirect(reverse('order_confirmed', kwargs={"track_id": user_order.tracking_id}))

@require_GET
def order_confirmed_view(request: HtmxHttpRequest, track_id) -> HttpResponse:
    try:
        order = Order.objects.get(tracking_id=track_id)
        order_items = OrderItem.objects.filter(order=order)
        order_address = OrderAddress.objects.get(order=order)
    except Order.DoesNotExist:
        return redirect('home')
    except OrderAddress.DoesNotExist:
        return redirect('home')
    
    if not order_items:
        return redirect('home')

    request.session['is_payment_processing'] = False
    request.session['item_count'] = 0
    order_created_at = order.created_at
    estimated_delivery_dates = (order_created_at + timedelta(days=2)).strftime("%b, %d"), (order_created_at + timedelta(days=3)).strftime("%b, %d")

    return render(request, 'src/order_confirmed.html', 
                  {'order': order, 'order_items': order_items, 
                   'order_address': order_address,
                   'delivery_date1': estimated_delivery_dates[0],
                   'delivery_date2': estimated_delivery_dates[1]})