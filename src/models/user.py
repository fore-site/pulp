from django.db import models
from datetime import datetime

class Users(models.Model):

    class UserStatus(models.TextChoices):
        Active = 'Active',
        Suspended = 'Suspended',
        Deleted = 'Deleted'

    class UserRole(models.TextChoices):
        Customer = 'Customer',
        Admin = 'Admin'

    fullname = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, unique=True)
    phone_no = models.CharField(max_length=50, blank=True)
    password_hash = models.CharField(max_length=255, blank=True)
    user_status = models.CharField(max_length=9, choices=UserStatus, default=UserStatus.Active)
    role = models.CharField(max_length=8, choices=UserRole, default=UserRole.Customer)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users'

class Addresses(models.Model):
    user = models.ForeignKey(Users, on_delete=models.RESTRICT)
    city = models.CharField(max_length=255)
    address_state = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    is_default = models.BooleanField(default=False)

    class Meta:
        db_table = 'addresses'