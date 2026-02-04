from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from ..managers import CustomUserManager

class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(verbose_name=_('email address'),
                               max_length=255,
                                unique=True)
    phone_no = models.CharField(max_length=50, blank=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    class Meta:
        db_table = 'users'

class UserAddress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.RESTRICT)
    recipient_name = models.CharField(max_length=255)
    recipient_phone_no = models.CharField(max_length=255)
    address_state = models.CharField(max_length=255)
    address_city = models.CharField(max_length=255)
    description = models.CharField(max_length=300, help_text='full address details')
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return self.description

    class Meta:
        db_table = 'user_addresses'
        verbose_name_plural = ' User Addresses'