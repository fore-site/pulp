from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

@receiver(user_logged_in)
def merge_session_data_with_db(sender, request, user, **kwargs):
    """ Signal receiver to update cart data in the database when user logs in"""
    if request.session.get('item_count'):
        old_session_key = request.session.get('old_session_key')
        from .models import Cart, CartItem
        from django.db import transaction
        from django.db.models import Sum, F

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
                    user_cart_items_sku = CartItem.objects.filter(cart=cart).values_list('sku', flat=True)
                    guest_cart_items = CartItem.objects.filter(cart=guest_cart).exclude(sku__in=user_cart_items_sku)
                    
                    if guest_cart_items:
                        for item in guest_cart_items:
                            item.cart = cart
                            items_to_update.append(item)
                        updated = CartItem.objects.bulk_update(items_to_update, ['cart'])
                        updated_cart_items = CartItem.objects.filter(cart=cart).values('cart').annotate(
                                            item_count=Sum(F('quantity'))).get()
                        print(f'{updated} rows updated')
                        request.session['item_count'] = updated_cart_items['item_count']
                        guest_cart.delete()
                    else:
                        pass
            finally:
                del request.session['old_session_key']
    else:
        del request.session['old_session_key']
            
