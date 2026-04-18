from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from .models import Cart, CartItem
from django.db import transaction

@receiver(user_logged_in)
def merge_session_data_with_db(sender, request, user, **kwargs):
    """ Signal receiver to update cart data in the database when user logs in"""
    if request.session.get('item_count'):
        old_session_key = request.session.get('old_session_key')
        with transaction.atomic():
            try:
                cart = Cart.objects.get(user=user)
            except Cart.DoesNotExist:
                cart = Cart.objects.get(session_id=old_session_key, user__isnull=True)
                cart.user = user
                cart.session_id = ''
                cart.save()
            else:
                try:
                    guest_cart = Cart.objects.get(session_id=old_session_key, user__isnull=True)
                except Cart.DoesNotExist:
                    pass
                else:
                    items_to_update = []
                    guest_cart_items = CartItem.objects.filter(cart=guest_cart)
                    if guest_cart_items:
                        for item in guest_cart_items:
                            item.cart = cart
                            items_to_update.append(item)
                        updated = CartItem.objects.bulk_update(items_to_update, ['cart'])
                        print(f'{updated} rows updated')
                        guest_cart.delete()
                    else:
                        pass
            finally:
                del request.session['old_session_key']
    else:
        del request.session['old_session_key']
            
