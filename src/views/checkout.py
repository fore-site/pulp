from django.shortcuts import get_object_or_404
from src.models import Cart
from django.views import generic

class CheckoutShippingView(generic.TemplateView):
    template_name = 'src/checkout_shipping.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart = get_object_or_404(Cart, public_id = self.kwargs.get('public_id'))
        user = self.request.user if self.request.user.is_authenticated else None
        if user:
            context['user'] = user
        return context

class CheckoutReviewView(generic.TemplateView):
    template_name = 'src/checkout_review.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart = get_object_or_404(Cart, public_id = self.kwargs.get('public_id'))
        user = self.request.user if self.request.user.is_authenticated else None
        if user:
            context['user'] = user
        return context

class CheckoutPaymentView(generic.TemplateView):
    template_name = 'src/checkout_payment.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart = get_object_or_404(Cart, public_id = self.kwargs.get('public_id'))
        user = self.request.user if self.request.user.is_authenticated else None
        if user:
            context['user'] = user
        return context