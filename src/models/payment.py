from django.db import models

class TransactionLog(models.Model):
    order = models.ForeignKey('Order', on_delete=models.RESTRICT)
    event = models.CharField(max_length=50)
    details = models.TextField(blank=True)
    time_stamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.event} {self.order}'

    class Meta:
        db_table = 'transaction_logs'