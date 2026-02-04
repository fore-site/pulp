from django.db import models
from django.conf import settings

class Cart(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    session_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.user:
            return self.user
        return self.session_id

    class Meta:
        db_table = 'carts'

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    sku = models.ForeignKey('Sku', on_delete=models.RESTRICT)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return self.cart

    class Meta:
        db_table = 'cart_items'