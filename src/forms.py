from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from .models import User
from django import forms

class CustomUserCreationForm(UserCreationForm):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].help_text = mark_safe(
            '<ul><li>Password must be minimum 8 characters</li>'
            '<li>Password cannot consist of only numbers</li></ul>')
        self.fields['password2'].help_text = mark_safe(
            '<ul><li>Enter password again</li></ul>')

    error_messages = {
        'password_mismatch': 'Your passwords do not match'
        }
    
    class Meta:
        model = User
        fields = ["email"]

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
        'invalid_login': _('Invalid credentials. Enter a valid email and password.'),
        'inactive': _('This account is currently disabled'),
    }

class CartUpdateForm(forms.Form):
    quantity = forms.IntegerField(
        max_value=100,
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'w-10 h-8 text-center bg-transparent border-none text-text-main font-medium focus:ring-0 p-0 text-sm quantity-input'})
    )

class ShippingAddressForm():
    pass