from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from src.models import *
from .forms import CustomUserChangeForm, CustomUserCreationForm

class CustomUserAdmin(UserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm

    list_display = ["email", "fullname", "phone_no", "is_active", "is_staff"]
    list_filter = ["is_active", "is_staff"]
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
    list_display = ["title", "category", "description", "cover_image", "is_deleted"]
    list_filter = ["is_deleted", "genres"]

    search_fields = ["title"]
    ordering = ["title"]
    filter_horizontal = ("genres",)

class BookAdmin(admin.ModelAdmin):
    model = Book
    list_display = ["series", "title", "page_count", "cover_image", "trending_score", "bestseller_score", "average_rating", "reviewer_count", "is_featured", "is_deleted", "created_at"]
    list_filter = ["series", "created_at", "is_deleted", "authors"]

    search_fields = ["title"]
    ordering = ["title"]
    filter_horizontal = ["authors"]

class SkuAdmin(admin.ModelAdmin):
    model = Sku
    list_display = ["book", "code", "publisher", "isbn_number", "price", "quantity", "format", "dimensions", "file_size", "published_at", "is_discontinued", "created_at", "updated_at"]
    list_filter = ["publisher", "published_at", "is_discontinued", "created_at", "updated_at"]

    sortable_by = ["price", "book__average_rating"]
    search_fields = ["book", "code"]
    ordering = ["book"]

class AuthorAdmin(admin.ModelAdmin):
    model = Author
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)

class PublisherAdmin(admin.ModelAdmin):
    model = Publisher
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)

class BookEventAdmin(admin.ModelAdmin):
    model = BookEvent
    list_display = ["sku", "created_at", "event_type"]
    list_filter = ("event_type", "created_at")

    search_fields = ("sku",)
    ordering = ("created_at",)

class AdminBookAnalyticsDaily(admin.ModelAdmin):
    model = BookAnalyticsDaily
    list_display = ["sku", "created_at", "view_count", "add_to_cart_count", "purchase_count"]
    list_filter = ["created_at"]

    search_fields = ("sku",)
    ordering = ("created_at",)

class GenreAdmin(admin.ModelAdmin):
    model = Genre
    list_display = ("name",)

class CategoryAdmin(admin.ModelAdmin):
    model = Category
    list_display = ("name",)

class RatingsAdmin(admin.ModelAdmin):
    model = Rating
    list_display = ("book", "user", "rating_value")

class CartAdmin(admin.ModelAdmin):
    model = Cart
    list_display = ("public_id", "user")

class OrderAdmin(admin.ModelAdmin):
    model = Order
    list_display = ("order_number", "user", "session_id", "total_amount", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("order_number", "user__email")
    ordering = ("-created_at",)

# Register your models here.

admin.site.register(User, CustomUserAdmin)
admin.site.register(Series, SeriesAdmin)
admin.site.register(Book, BookAdmin)
admin.site.register(Sku, SkuAdmin)
admin.site.register(Author, AuthorAdmin)
admin.site.register(Publisher, PublisherAdmin)
admin.site.register(BookEvent, BookEventAdmin)
admin.site.register(BookAnalyticsDaily, AdminBookAnalyticsDaily)
admin.site.register(Genre, GenreAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Rating, RatingsAdmin)
admin.site.register(Cart, CartAdmin)

admin.site.site_header = 'Pulp administration'
admin.site.site_title = 'Pulp site admin'
admin.site.index_title = 'Welcome to Pulp admin dashboard'