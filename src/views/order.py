import hashlib
import hmac
import json

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.views import generic
from django.db import IntegrityError
from django.db.models import Case, When, F, DecimalField
from src.models import CartItem, Cart, Order, OrderItem, OrderAddress, IdempotencyKey
from django_htmx.middleware import HtmxDetails
from datetime import timedelta
from ..utils.common import create_order_and_related_data
from django.conf import settings
import requests

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
def create_order_and_initialize_payment(request: HtmxHttpRequest) -> HttpResponse:
    """ Create order in database and redirect to payment provider"""
    user = request.user if request.user.is_authenticated else None
    try:
        if user:
            cart = Cart.objects.get(user=user)
        else:
            cart = Cart.objects.get(session_id = request.session.session_key)
    except Cart.DoesNotExist:
        return HttpResponseRedirect(reverse('cart'))

    cart_items = CartItem.objects.filter(cart=cart).annotate(unit_price=Case(
                    When(sku__discount_percent__gt=0, then=(F('sku__price') - (F('sku__price') * F('sku__discount_percent') / 100))),
                    default=F('sku__price'),
                    output_field=DecimalField(max_digits=10, decimal_places=2)
                ))
    if not cart_items:
        return HttpResponseRedirect(reverse('cart'))

    if not request.session.get('firstname'):
        return HttpResponseRedirect(reverse('checkout_shipping'))
    
    request.session['is_payment_processing'] = True
    key = request.POST.get('idempotency_key')

    if not key:
        return render(request, '404.html', 
        {'exception': Exception("Idempotency key is required")}, 
        status=500)

    # Check if key exists in db
    record = IdempotencyKey.objects.filter(key=key).first()

    if record:
        # If order exists:
        if record.order_id:
            order = get_object_or_404(Order, id=record.order_id)
            return HttpResponseRedirect(reverse('payment_callback', query={'reference': order.order_number}))
        
        # Key exists but no order
        try:
            order = create_order_and_related_data(request, user, cart_items, record)
        except Exception:
            return render(request, '404.html', 
                            {'exception': Exception("Unexpected error occurred while creating order")}, 
                            status=500)
    else:
        # If key does not exist. First time request.
        try:
            order = create_order_and_related_data(request, user, cart_items, key=key, first_time=True)
        except IntegrityError:
            # Another request already created the key
            record = IdempotencyKey.objects.get(key=key)
            if record.order_id:
                order = get_object_or_404(Order, id=record.order_id)
                return HttpResponseRedirect(reverse('payment_callback', query={'reference': order.order_number}))
            else:
            # If order still does not exist
                try:
                    order = create_order_and_related_data(request, user, cart_items, record)
                except Exception:
                    return render(request, '404.html', 
                            {'exception': Exception("Idempotency key is required")}, 
                            status=500)
        except Exception:
            return render(request, '404.html', 
            {'exception': Exception("Unexpected error occurred while creating order")}, 
            status=500)
        
    try:
        res = requests.post('https://api.paystack.co/transaction/initialize',
                      json={'email': order.address.recipient_email, 
                            'amount': int(order.total_amount * 100),
                            'reference': order.order_number,
                            'callback_url': request.build_absolute_uri(reverse('payment_callback'))},
                      headers={'Authorization': f'Bearer {settings.paystack_test_secret_key}'})
    except Exception:
        return render(request, 'src/payment_failed.html')
    else:
        return JsonResponse({'access_code': res.json().get('data', {}).get('access_code', '')})

@require_GET
def payment_callback_view(request: HtmxHttpRequest) -> HttpResponse:
    """Callback view after successful payment to display order details and estimated delivery date"""
    
    reference = request.GET.get('reference')

    # Verify payment with Paystack
    res = requests.get(f'https://api.paystack.co/transaction/verify/{reference}',
                      headers={'Authorization': f'Bearer {settings.paystack_test_secret_key}'})

    if res.status_code != 200 or res.json().get('data', {}).get('status') in ['failed', 'abandoned']:
        return render(request, 'src/payment_failed.html')
    elif res.json().get('data', {}).get('status') == 'pending':
        return render(request, 'src/payment_processing.html')
    
    try:
        order = Order.objects.get(order_number=reference)
        order_items = OrderItem.objects.filter(order=order)
        order_address = OrderAddress.objects.get(order=order)
        if order.order_status != 'Paid':
            order.order_status = 'Paid'
            order.save()
            request.session['is_payment_processing'] = False
            request.session['item_count'] = 0
    except Order.DoesNotExist:
        return redirect('home')
    except OrderAddress.DoesNotExist:
        return redirect('home')
    
    if not order_items:
        return redirect('home')
    
    order_created_at = order.created_at
    estimated_delivery_dates = (order_created_at + timedelta(days=2)).strftime("%b, %d"), (order_created_at + timedelta(days=3)).strftime("%b, %d")

    return render(request, 'src/order_confirmed.html', 
                  {'order': order, 'order_items': order_items, 
                   'order_address': order_address,
                   'delivery_date1': estimated_delivery_dates[0],
                   'delivery_date2': estimated_delivery_dates[1]})

@csrf_exempt
def paystack_webhook_view(request: HtmxHttpRequest) -> HttpResponse:
    """Webhook view to handle Paystack events such as payment verification and update order status accordingly"""
    # Verify webhook signature
    signature = request.headers.get('x-Paystack-Signature')
    hash = hmac.new(settings.paystack_test_secret_key.encode(), request.body, hashlib.sha256).hexdigest()
    verified = signature == hash
    
    if verified:
        payload = json.loads(request.body)
        event = payload.get('event')
        if event == 'charge.success':
            reference = payload.get('data', {}).get('reference')
            try:
                order = Order.objects.get(order_number=reference)
                if order.order_status != 'Paid':
                    order.order_status = 'Paid'
                    order.save()
            except Order.DoesNotExist:
                pass
            finally:
                return HttpResponse(status=200)
    return HttpResponse(status=400)