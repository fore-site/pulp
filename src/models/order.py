from django.db import models

class Orders(models.Model):
    user_id = models.ForeignKey('Users', on_delete=models.RESTRICT)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    address_city = models.CharField(max_length=255)
    address_state = models.CharField(max_length=255)
    address_description = models.TextField()
    order_status = models.CharField(max_length=255, blank=True, default='Placed')
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'orders'

class OrderItems(models.Model):
    order_id = models.ForeignKey(Orders, on_delete=models.RESTRICT)
    sku_id = models.ForeignKey('Sku', on_delete=models.RESTRICT)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'order_items'