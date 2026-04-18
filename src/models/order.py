import random
from django.conf import settings
from django.db import IntegrityError, models, transaction
from django.utils.translation import gettext_lazy as _
import uuid

class Order(models.Model):

    class OrderStatus(models.TextChoices):
        pending = 'Pending'
        processed = 'Processed'
        shipped = 'Shipped'
        delivered = 'Delivered'
        cancelled = 'Cancelled'

    class PaymentStatus(models.TextChoices):
        pending = 'Pending'
        processing = 'Processing'
        failed = 'Failed'
        paid = 'Paid'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, null=True, blank=True)
    session_id = models.CharField(max_length=255, blank=True)
    subtotal_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text='Total amount of the sku prices')
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text='total fee cost')
    public_id = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    order_number = models.CharField(max_length=20, unique=True, editable=False)
    order_status = models.CharField(max_length=255, choices=OrderStatus, default='Pending')
    payment_status = models.CharField(max_length=255, choices=PaymentStatus, default='Pending')
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, * args, **kwargs) -> None:
        if not self.order_number:
            self._save_with_unique_order_number(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def _save_with_unique_order_number(self, *args, **kwargs):
        retries = 5
        while retries > 0:
            try:
                self.order_number = self.generate_code()
                with transaction.atomic():
                    return super().save(*args, **kwargs)
            except IntegrityError:
                retries -= 1
                if retries == 0:
                    raise

    @staticmethod
    def generate_code():
        chars = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
        part1 = ''.join(random.choices(chars, k=4))
        part2 = ''.join(random.choices(chars, k=4))
        return f"PULP-{part1}-{part2}"

    def __str__(self):
        return self.order_number

    class Meta:
        db_table = 'orders'

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.RESTRICT, related_name='order_items')
    sku = models.ForeignKey('Sku', on_delete=models.RESTRICT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.order

    class Meta:
        db_table = 'order_items'

class OrderAddress(models.Model):
    order = models.ForeignKey(Order, on_delete=models.RESTRICT, related_name='address')
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

class IdempotencyKey(models.Model):
    key = models.CharField(max_length=255, unique=True)
    order_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)