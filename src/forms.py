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

    def __init__(self, request = ..., *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        
        self.fields["username"].error_messages.update({
            'required': _('Enter your email to continue')
        })

        self.fields["password"].error_messages.update({
            'required': _('Enter your password to continue')
        })

    error_messages = {
        'invalid_login': 'Invalid credentials. Enter a valid email and password.',
        'inactive': 'This account is currently disabled',
    }