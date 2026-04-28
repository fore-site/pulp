from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.views import generic
from django.contrib.humanize.templatetags.humanize import intcomma
from django.utils import timezone
from src.models import CartItem, Cart
from ..forms import ShippingAddressForm
from datetime import timedelta
from decimal import Decimal
from dal import autocomplete
from nigerian_states.models import LocalGovernment, State
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
import json

class LGAAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = LocalGovernment.objects.all()

        # Get the selected state's ID from the forwarded data
        state_id = self.forwarded.get('address_state', None) 

        # Filter LGAs by the selected state
        if state_id:
            qs = qs.filter(state=state_id)

        # If the user is typing in the autocomplete, filter by the query text
        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs
    
    def get_result_label(self, result):
        return result.name
    
    def get_selected_result_label(self, result):
        return result.name

class CheckoutShippingView(generic.TemplateView):
    template_name = 'src/checkout_shipping.html'
    http_method_names = ['get', 'post']

    def get(self, request):
        if request.htmx:
            state_id = request.GET.get('address_state')
            try:
                state = State.objects.get(id=state_id).name if state_id else None
            except State.DoesNotExist:
                state = None

            subtotal = Decimal(request.session.get('subtotal_price'))
            if state == 'Lagos':
                request.session['shipping_fee'] = '3000.00'
                total_price = (subtotal + Decimal('3000.00')).quantize(Decimal('0.01'))
                request.session['total_price'] = str(total_price)
                total_price_oob = f"<span id='total_price' hx-swap-oob='true' class='text-base font-bold text-primary'>₦{intcomma(request.session.get('total_price'))}</span>"
                return HttpResponse('₦3,000.00' + total_price_oob)
            elif state:
                request.session['shipping_fee'] = '5000.00'
                total_price = (subtotal + Decimal('5000.00')).quantize(Decimal('0.01'))
                request.session['total_price'] = str(total_price)
                total_price_oob = f"<span id='total_price' hx-swap-oob='true' class='text-base font-bold text-primary'>₦{intcomma(request.session.get('total_price'))}</span>"
                return HttpResponse('₦5,000.00' + total_price_oob)
            else:
                request.session['shipping_fee'] = None
                request.session['total_price'] = str(subtotal)
                total_price_oob = f"<span id='total_price' hx-swap-oob='true' class='text-base font-bold text-primary'>₦{intcomma(request.session.get('total_price'))}</span>"
                return HttpResponse('pending' + total_price_oob)
            
        self.user = request.user if request.user.is_authenticated else None
        try:
            if self.user:
                cart = Cart.objects.get(user=self.user)
            else:
                cart = Cart.objects.get(session_id = request.session.session_key)
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
                'address_state': State.objects.get(name=request.session.get('address_state')).id,
                'address_city': request.session.get('address_city'),
                'phone_no': request.session.get('phone_no'),
                'email': request.session.get('email')})
        else:
            form = ShippingAddressForm()
        context["form"] = form
        context['delivery_date_1'] = estimated_delivery_dates[0]
        context['delivery_date_2'] = estimated_delivery_dates[1]
        
        return context
    
    @method_decorator(ratelimit(key='ip', rate='3/m', method='POST'))
    def post(self, request):
        form = ShippingAddressForm(request.POST)
        if form.is_valid():
            self.request.session['firstname'] = form.cleaned_data['recipient_firstname']
            self.request.session['lastname'] = form.cleaned_data['recipient_lastname']
            self.request.session['address_desc'] = form.cleaned_data['address_desc']
            self.request.session['address_state'] = State.objects.get(id=form.cleaned_data['address_state']).name
            self.request.session['address_city'] = form.cleaned_data['address_city'].name
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
                cart = Cart.objects.get(session_id = request.session.session_key)
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
