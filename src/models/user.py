from django.db import models
from datetime import datetime

class User(models.Model):

    class UserStatus(models.TextChoices):
        Active = 'Active',
        Suspended = 'Suspended',
        Deleted = 'Deleted'

    class UserRole(models.TextChoices):
        Customer = 'Customer',
        Admin = 'Admin'

    fullname = models.CharField(max_length=255, blank=True)
    email = models.EmailField(max_length=255, unique=True)
    phone_no = models.CharField(max_length=50, blank=True)
    password_hash = models.CharField(max_length=255, blank=True)
    user_status = models.CharField(max_length=9, choices=UserStatus, default=UserStatus.Active)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.fullname:
            return self.fullname
        return self.email

    class Meta:
        db_table = 'users'

class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.RESTRICT)
    city = models.CharField(max_length=255)
    address_state = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return self.description

    class Meta:
        db_table = 'addresses'
        verbose_name_plural = 'Addresses'