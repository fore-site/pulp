from django.db import models

class PaymentMethods(models.Model):
    user_id = models.ForeignKey('Users', null=True, blank=True, on_delete=models.CASCADE)
    provider = models.CharField(max_length=255)
    method_type = models.CharField(max_length=255)
    token = models.CharField(max_length=255, blank=True)
    last_four_digits = models.CharField(max_length=4, blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payment_methods'

class Payments(models.Model):
    order_id = models.ForeignKey('Orders', on_delete=models.RESTRICT)
    payment_method_id = models.ForeignKey(PaymentMethods, null=True, on_delete=models.SET_NULL)
    transaction_id = models.CharField(max=255, unique=True, blank=True, null=True)
    provider = models.CharField(max_length=255)
    method_type = models.CharField(max_length=255)
    last_four_digits = models.CharField(max_length=4, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=255, default='Pending')
    payment_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'payments'

class TransactionLogs(models.Model):
    transaction_id = models.ForeignKey(Payments, to_field='transcation_id', on_delete=models.RESTRICT)
    events = models.CharField(max_length=50)
    details = models.TextField(blank=True)
    time_stamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'transaction_logs'