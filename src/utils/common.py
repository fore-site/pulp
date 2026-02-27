from django.db.models import Case, When, F, DecimalField, Sum
from ..models import Sku, Cart, CartItem
from django.db.models.manager import BaseManager
from django.utils import timezone
from datetime import timedelta
from django.http import HttpRequest
from ..forms import CartUpdateForm
from decimal import Decimal

class FilterSort:
    def __init__(self, books: Sku, sort_by: str, format: str, featured: str, genres: list[str], latest_release: str):
        self.books = books
        self.sort_by = sort_by
        self.format = format
        self.featured = featured
        self.genres = genres
        self.latest_release = latest_release
        self.seven_days = timezone.now().replace(hour=0, minute=0, microsecond=0) - timedelta(days=7)

    def filter_skus(self):
        if self.genres:
            self.books = self.books.filter(book__series__genres__id__in=self.genres)
        if self.featured:
            self.books = self.books.filter(book__is_featured=True)
        if self.format:
            self.books = self.books.filter(format__iexact=self.format)
        if self.latest_release:
            self.books = self.books.filter(published_at__gte=self.seven_days)
        if self.sort_by:
            self.books = self.sort_skus(self.books, self.sort_by)
        return self.books

    def sort_skus(self, books: Sku, sort_by: str) -> BaseManager[Sku]:
        if sort_by == 'price_desc' or sort_by == 'price_asc':
            books = books.annotate(
                current_price=Case(
                    When(discount_percent__gt=0, then=(F('price_usd') - (F('price_usd') * F('discount_percent') / 100))),
                    default=F('price_usd'),
                    output_field=DecimalField(max_digits=10, decimal_places=2)
                )
            )
            books = books.order_by('current_price') if sort_by == 'price_asc' else books.order_by('-current_price')
        elif sort_by == 'bestselling':
            books = books.order_by('-book__bestseller_score')
        elif sort_by == 'reviews':
            books = books.order_by('-book__average_rating')
            
        return books

def base_book_queryset(sku: Sku):
    """Function that acts as the base queryset for subsequent queries on the Sku model. Fundamental filters have been applied"""

    return (sku.objects.filter(is_discontinued=False, quantity__gt=0, book__is_deleted=False, book__series__is_deleted=False)
                         .select_related('book')
                         .prefetch_related('book__authors')
                         .only(
                             'book__title',
                             'price_usd',
                             'format',
                             'isbn_number',
                             'book__authors__name'
                         ))

def get_user_and_session(request: HttpRequest):
    """Get user object and session key from the request object"""

    user = request.user if request.user.is_authenticated else None
    if not request.session.session_key:
        request.session.create()
    session_id = request.session.session_key    
    return user, session_id

def get_cart(user, session_id):
    try:
        cart = Cart.objects.get(user=user) if user else Cart.objects.get(session_id=session_id)
    except Cart.DoesNotExist:
        cart = Cart.objects.create(user=user) if user else Cart.objects.create(session_id=session_id)
    return cart


def get_cart_items_and_forms(user, session_id):
    """Find or create existing cart and return a zip of each item and their corresponding form if exists, else empty list"""
    try:
        # Get cart related to user or session_id, return empty cart if it doesn't exist
        cart = Cart.objects.get(user=user) if user else Cart.objects.get(session_id=session_id)
    except Cart.DoesNotExist:
        cart_items_and_forms = []
    else:
        # Get cart items related to cart, return empty cart if it doesn't exist
        cart_items = (CartItem.objects.filter(cart=cart)
                      .prefetch_related('sku__book__authors')
                      ).order_by('-created_at')
        if not cart_items:
            cart_items_and_forms = []
        else:
            # create django forms for each cart item
            forms = [CartUpdateForm(initial={'quantity': item.quantity}) for item in cart_items]
            cart_items_and_forms = zip(cart_items, forms)
    return cart_items_and_forms

def store_price_and_count(request, cart):
    """Store cart items count and subtotal price in session"""
    try:
        cart_items = CartItem.objects.filter(cart=cart).values('cart').annotate(
                    item_count=Sum(F('quantity')),
                    subtotal=Sum(Case(
                                When(sku__discount_percent__gt=0, then=(F('sku__price_usd') - (F('sku__price_usd') * F('sku__discount_percent') / 100)) * F('quantity')),
                                default=F('sku__price_usd') * F('quantity'),
                                output_field=DecimalField(max_digits=10, decimal_places=2)
                            )
                        )
                ).get()
        request.session['item_count'] = cart_items['item_count']
        request.session['subtotal_price'] = str(cart_items['subtotal'].quantize(Decimal('0.01')))
    except CartItem.DoesNotExist:
        request.session['item_count'] = 0