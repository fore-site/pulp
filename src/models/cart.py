from django.db import models

class Carts(models.Model):
    user_id = models.ForeignKey('Users', on_delete=models.CASCADE)
    session_id = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'carts'

class CartItems(models.Model):
    cart_id = models.ForeignKey(Carts, on_delete=models.CASCADE)
    sku_id = models.ForeignKey('Sku', on_delete=models.RESTRICT)
    quantity = models.PositiveIntegerField()

    class Meta:
        db_table = 'cart_items'