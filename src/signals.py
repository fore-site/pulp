from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from .models import Cart

@receiver(user_logged_in)
def merge_session_data_with_db(sender, request, user, **kwargs):
    """ Signal receiver to update cart data in the database when user logs in"""
    if request.session.session_key:
        try:
            cart = Cart.objects.get(session_id=request.session.session_key, user__isnull=True)
            cart.user = user
            cart.save()
        except Cart.DoesNotExist:
            pass
