from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.views import generic
from django.utils import timezone
from src.models import CartItem, Cart
from ..forms import ShippingAddressForm
from datetime import timedelta
from decimal import Decimal
import json

class CheckoutShippingView(generic.TemplateView):
    template_name = 'src/checkout_shipping.html'
    http_method_names = ['get', 'post']

    def get(self, request):
        if request.htmx:
            state = request.GET.get('address_state')
            request.session['address_state'] = state
            subtotal = Decimal(request.session.get('subtotal_price'))
            if state == 'Lagos':
                request.session['shipping_fee'] = '3.00'
                total_price = (subtotal + Decimal('3.00')).quantize(Decimal('0.01'))
                request.session['total_price'] = str(total_price)
                total_price_oob = f"<span id='total_price' hx-swap-oob='true' class='text-base font-bold text-primary'>{request.session.get('total_price')}</span>"
                return HttpResponse('$3.00' + total_price_oob)
            else:
                request.session['shipping_fee'] = '5.00'
                total_price = (subtotal + Decimal('5.00')).quantize(Decimal('0.01'))
                request.session['total_price'] = str(total_price)
                total_price_oob = f"<span id='total_price' hx-swap-oob='true' class='text-base font-bold text-primary'>{request.session.get('total_price')}</span>"
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
            
        if self.request.session.get('shipping_fee'):
            self.request.session['total_price'] = str((Decimal(self.request.session.get('subtotal_price')) + Decimal(self.request.session.get('shipping_fee'))).quantize(Decimal('0.01')))
        else:
            self.request.session['total_price'] = self.request.session.get('subtotal_price')

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
        self.request.session['total_price'] = str((Decimal(self.request.session.get('subtotal_price')) + Decimal(self.request.session.get('shipping_fee'))).quantize(Decimal('0.01')))

        # Generate checkout state to use in javascript
        checkout_state = {
            'subtotal_amount_usd': request.session.get('subtotal_price'),
            'shipping_fee_usd': request.session.get('shipping_fee'),
            'total_amount_usd': request.session.get('total_price'),
            'recipient_firstname': request.session.get('firstname'),
            'recipient_lastname': request.session.get('lastname'),
            'recipient_email': request.session.get('email'),
            'recipient_phone_no': request.session.get('phone_no'),
            'address_desc': request.session.get('address_desc'),
            'address_state': request.session.get('address_state'),
            'address_city': request.session.get('address_city')
        }

        context["cart_items"] = self.cart_items
        context['delivery_date_1'] = estimated_delivery_dates[0]
        context['delivery_date_2'] = estimated_delivery_dates[1]
        context['checkout_state_json'] = json.dumps(checkout_state)

        return context
