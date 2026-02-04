from django.conf import settings
from django.db import models

class PaymentMethod(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE)
    provider = models.CharField(max_length=255)
    method_type = models.CharField(max_length=255)
    token = models.CharField(max_length=255, blank=True)
    last_four_digits = models.CharField(max_length=4, blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payment_methods'

class Payment(models.Model):
    order = models.ForeignKey('Order', on_delete=models.RESTRICT)
    payment_method_id = models.ForeignKey(PaymentMethod, null=True, on_delete=models.SET_NULL)
    transaction_id = models.CharField(max_length=255, unique=True, blank=True, null=True)
    provider = models.CharField(max_length=255)
    method_type = models.CharField(max_length=255)
    last_four_digits = models.CharField(max_length=4, blank=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=5, help_text='Currency the customer paid in')
    payment_exchange_rate = models.DecimalField(max_digits=10, decimal_places=2, help_text='Exchange rate from usd to naira during payment.')
    payment_status = models.CharField(max_length=255, default='Pending')
    payment_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.transaction_id

    class Meta:
        db_table = 'payments'

class TransactionLog(models.Model):
    transaction = models.ForeignKey(Payment, to_field='transaction_id', on_delete=models.RESTRICT)
    events = models.CharField(max_length=50)
    details = models.TextField(blank=True)
    time_stamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.transaction

    class Meta:
        db_table = 'transaction_logs'