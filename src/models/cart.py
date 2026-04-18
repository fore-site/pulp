from django.db import models
from django.conf import settings
from django.core.validators import MaxValueValidator
import uuid

class Cart(models.Model):
    public_id = models.UUIDField(unique=True, blank=True, default=uuid.uuid4, null=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __repr__(self):
        return self.public_id

    class Meta:
        db_table = 'carts'

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="cart_items")
    sku = models.ForeignKey('Sku', on_delete=models.RESTRICT)
    quantity = models.PositiveIntegerField(validators=[MaxValueValidator(100)])
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        db_table = 'cart_items'