from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid

class Order(models.Model):

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, null=True)
    session_id = models.CharField(max_length=255, blank=True)
    subtotal_amount_usd = models.DecimalField(max_digits=10, decimal_places=2, help_text='Total amount of the sku prices')
    shipping_fee_usd = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount_usd = models.DecimalField(max_digits=10, decimal_places=2, help_text='total fee cost')
    order_exchange_rate = models.DecimalField(max_digits=10, decimal_places=2, help_text='Exchange rate from usd to naira during order placement.')
    tracking_id = models.UUIDField(unique=True, blank=True, default=uuid.uuid4)
    order_status = models.CharField(max_length=255, blank=True, default='Pending')
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user

    class Meta:
        db_table = 'orders'

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.RESTRICT)
    sku = models.ForeignKey('Sku', on_delete=models.RESTRICT)
    quantity = models.PositiveIntegerField()
    unit_price_usd = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.order

    class Meta:
        db_table = 'order_items'

class OrderAddress(models.Model):
    order = models.ForeignKey(Order, on_delete=models.RESTRICT)
    recipient_firstname = models.CharField(max_length=255)
    recipient_lastname = models.CharField(max_length=255)
    recipient_phone_no = models.CharField(max_length=255)
    recipient_email = models.EmailField(verbose_name=_('email address'),
                               max_length=255)
    address_desc = models.CharField(max_length=300)
    address_state = models.CharField(max_length=255)
    address_city = models.CharField(max_length=255)

    def __str__(self):
        return self.address_desc
    
    class Meta:
        db_table = 'order_addresses'
        verbose_name_plural = 'Order Addresses'