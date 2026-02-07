from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm
from django import forms
from django.forms import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import User

class CustomUserCreationForm(UserCreationForm):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].help_text = 'Password must be minimum 8 characters'
        self.fields['password2'].help_text = 'Enter password again'

    class Meta:
        model = User
        fields = ["email"]
        error_messages = {
            'email': {
                'unique': 'This email already exists'
            },
            'password2': {
                'password_mismatch': 'Your passwords do not match'
            }
        }

class CustomUserChangeForm(UserChangeForm):

    class Meta:
        model = User
        fields = ["email"]

class CustomLoginForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise ValidationError(
            ("This account is inactive."),
            code="inactive",
        )

    error_messages = {
        'invalid_login': 'Invalid credentials. Enter a valid email and password.',
        'inactive': 'This account is currently disabled',
    }