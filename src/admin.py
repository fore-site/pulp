from django.contrib import admin
from src.models import *

# Register your models here.
admin.site.register([Series, 
                     Book, 
                     Address, 
                     Sku, 
                     Author, 
                     Payment, 
                     PaymentMethod, 
                     Publisher, 
                     BookAuthorPivot, 
                     BookPublisherPivot, 
                     Genre, 
                     GenreBookPivot,
                     Cart,
                     CartItem,
                     Order,
                     OrderItem, 
                     TransactionLog])