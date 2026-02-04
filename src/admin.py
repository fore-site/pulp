from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from src.models import *
from .forms import CustomUserChangeForm, CustomUserCreationForm

class CustomUserAdmin(UserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm

    list_display = ["email", "fullname", "phone_no", "is_active", "is_staff"]
    list_filter = ["email", "is_active", "is_staff"]
    fieldsets = [
        (None, {"fields": ["email", "fullname", "phone_no", "password"]}),
        ("permissions", {"fields": ["is_active", "is_staff", "user_permissions"]}),
    ]

    add_fieldsets = [
        (
            None, {
                "classes": ["wide"],
                "fields": ["email", "fullname", "phone_no", "password1", "password2", "is_active", "is_staff", "user_permissions"]
            }
        )
    ]
    search_fields = ["email"]
    ordering = ["email"]

class SeriesAdmin(admin.ModelAdmin):
    model = Series

class BookAdmin(admin.ModelAdmin):
    model = Book

class SkuAdmin(admin.ModelAdmin):
    model = Sku

class AuthorAdmin(admin.ModelAdmin):
    model = Author

class PublisherAdmin(admin.ModelAdmin):
    model = Publisher


# Register your models here.

admin.site.register(User, CustomUserAdmin)
admin.site.register(Series, SeriesAdmin)
admin.site.register(Book, BookAdmin)
admin.site.register(Sku, SkuAdmin)
admin.site.register(Author, AuthorAdmin)
admin.site.register(Publisher, PublisherAdmin)