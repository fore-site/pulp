from django.contrib import admin
from src.models import Series, Book, Address

# Register your models here.
admin.site.register([Series, Book, Address])