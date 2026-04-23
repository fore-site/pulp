import hashlib
import hmac
import json
from urllib.parse import urlencode
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.views import generic
from django.db import IntegrityError
from django.db.models import Case, When, F, DecimalField
from src.models import CartItem, Cart, Order, OrderItem, OrderAddress, IdempotencyKey, Sku
from django_htmx.middleware import HtmxDetails
from datetime import timedelta
from ..forms import OrderLookupForm
from ..utils.common import create_order_and_related_data, update_db_after_payment
from django.conf import settings
import requests

class HtmxHttpRequest(HttpRequest):
    htmx: HtmxDetails

class OrderHistoryView(generic.ListView):
    """ View to display order history for authenticated users and guest users based on session id"""
    model = Order
    template_name = 'src/order_history.html'
    context_object_name = 'user_orders'

    def get_queryset(self):
        user = self.request.user if self.request.user.is_authenticated else None
        session_id = self.request.session.session_key

        if user:
            orders = (Order.objects.filter(user=user)
                      .exclude(payment_status='Pending')
                      .prefetch_related('order_items__sku__book').order_by('-created_at'))
        else:
            orders = (Order.objects
                      .filter(session_id=session_id)
                      .exclude(payment_status='Pending')
                      .prefetch_related('order_items__sku__book').order_by('-created_at'))
        return orders

def order_lookup_view(request: HtmxHttpRequest) -> HttpResponse:
    """View to retrieve order lookup form"""
    if request.POST:
        form = OrderLookupForm(request.POST)
        if form.is_valid():
            order_number = form.cleaned_data['order_number']
            return HttpResponseRedirect(reverse('order_detail', kwargs={'order_number': order_number.strip()}))
        return render(request, 'src/order_lookup.html', {"form": form})
    else:
        form = OrderLookupForm()
        return render(request, 'src/order_lookup.html', {"form": form})

@require_GET
def order_detail_view(request: HtmxHttpRequest, order_number) -> HttpResponse:
    """ View to display order details for real-time tracking or for settled orders"""
    try:
        order = Order.objects.get(order_number__iexact=order_number)
        order_items = OrderItem.objects.filter(order=order)
        order_address = OrderAddress.objects.get(order=order)
        order_created_at = order.created_at
        estimated_delivery_dates = (order_created_at + timedelta(days=2)).strftime("%b, %d"), (order_created_at + timedelta(days=3)).strftime("%b, %d")
        context = {'order': order, 'order_items': order_items, 'order_address': order_address,
                    'delivery_date1': estimated_delivery_dates[0],
                    'delivery_date2': estimated_delivery_dates[1]}
    except Order.DoesNotExist:
        order = []
        order_items = []
        order_address = []
        context = {'order': order, 'order_items': order_items, 'order_address': order_address}
    
    return render(request, 'src/order_detail.html', context)

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
    
    key = request.headers.get('Idempotency-Key')
    
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
            if order.payment_status == 'Pending':
                pass
            elif order.payment_status == 'Failed':
                print('Payment failed for existing order')
                return render(request, 'src/payment_failed.html')
            else:
                print('Order already exists for key, redirecting to payment callback')
                return HttpResponseRedirect(f"{reverse('payment_callback')}?{urlencode({'reference': order.order_number})}")
        else:
        # Key exists but no order
            print('Key exists, but no order')
            try:
                order = create_order_and_related_data(request, user, cart_items, record)
            except:
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
                return HttpResponseRedirect(f"{reverse('payment_callback')}?{urlencode({'reference': order.order_number})}")
            else:
            # If order still does not exist
                try:
                    order = create_order_and_related_data(request, user, cart_items, record)
                except Exception:
                    print('something went wrong while creating order')
                    return render(request, '404.html', 
                            {'exception': Exception("Idempotency key is required")}, 
                            status=500)
        except Exception:
            print('Something went wrong while creating order')
            return render(request, '404.html', 
            {'exception': Exception("Unexpected error occurred while creating order")}, 
            status=500)

    try:
        res = requests.post('https://api.paystack.co/transaction/initialize',
                      json={'email': OrderAddress.objects.get(order=order).recipient_email, 
                            'amount': int(order.total_amount * 100),
                            'reference': order.order_number,
                            'callback_url': request.build_absolute_uri(reverse('payment_callback'))},
                      headers={'Authorization': f'Bearer {settings.PAYSTACK_TEST_SECRET_KEY}'})
    except:
        print('something went wrong while initializing payment')
        return render(request, '404.html', 
            {'exception': Exception("Unexpected error occurred while initializing payment")}, 
            status=500)
    else:
        request.session['is_payment_processing'] = True
        try:
            payload = res.json()
        except Exception:
            payload = {}

        if res.status_code != 200 or not payload.get('data'):
            print(payload)
            return JsonResponse({'error': 'Unable to initialize payment'}, status=502)

        data = payload.get('data', {})
        return JsonResponse(
            {
                'access_code': data.get('access_code', ''),
                'authorization_url': data.get('authorization_url', ''),
                'reference': data.get('reference', order.order_number),
            }
        )

@require_GET
def payment_callback_view(request: HtmxHttpRequest) -> HttpResponse:
    """Callback view after successful payment to display order details and estimated delivery date"""
    
    reference = request.GET.get('reference') or request.GET.get('trxref')
    if not reference:
        return redirect('home')
    
    # Fetch order
    try:
        order = Order.objects.get(order_number=reference)
        order_items = OrderItem.objects.filter(order=order)
        order_address = OrderAddress.objects.get(order=order)
    except Order.DoesNotExist:
        return redirect('home')
    except OrderAddress.DoesNotExist:
        return redirect('home')
    
    if not order_items:
        return redirect('home')
    
    order_created_at = order.created_at
    estimated_delivery_dates = (order_created_at + timedelta(days=2)).strftime("%b, %d"), (order_created_at + timedelta(days=3)).strftime("%b, %d")

    # Check if payment has already been settled
    if order.payment_status == 'Paid':
        pass
    elif order.payment_status == 'Failed':
        return render(request, 'src/payment_failed.html')
    else:
        # Verify payment with Paystack and update payment status accordingly
        res = requests.get(f'https://api.paystack.co/transaction/verify/{reference}',
                        headers={'Authorization': f'Bearer {settings.PAYSTACK_TEST_SECRET_KEY}'})

        if res.status_code != 200 or res.json().get('data', {}).get('status') in ['failed', 'abandoned']:
            print(res.json())
            update_db_after_payment(order, request, 'Failed', order_items)
            return render(request, 'src/payment_failed.html')
        elif res.json().get('data', {}).get('status') == 'pending':
            update_db_after_payment(order, request, 'Processing', order_items)
            return render(request, 'src/payment_processing.html')
        elif res.json().get('data', {}).get('status') == 'success':
            update_db_after_payment(order, request, 'Paid', order_items)
        else:
            print(res.json())
            return redirect('home')
        
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
    hash = hmac.new(settings.PAYSTACK_TEST_SECRET_KEY.encode(), request.body, hashlib.sha256).hexdigest()
    verified = signature == hash
    
    if verified:
        payload = json.loads(request.body)
        event = payload.get('event')
        if event == 'charge.success':
            reference = payload.get('data', {}).get('reference')
            try:
                order = Order.objects.get(order_number=reference)
                order_items = OrderItem.objects.filter(order=order)
                # Check if payment has already been settled
                if order.payment_status == 'Paid':
                    pass
                elif order.payment_status == 'Failed':
                    pass
                else:
                    update_db_after_payment(order, request, 'Paid', order_items)
            except Order.DoesNotExist:
                pass
            finally:
                return HttpResponse(status=200)
    return HttpResponse(status=400)
