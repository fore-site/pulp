from django.db.models import Case, When, F, DecimalField, Sum, Q, Subquery, OuterRef
from ..models import Sku, Cart, CartItem, Category
from django.db.models.manager import BaseManager
from django.utils import timezone
from datetime import timedelta
from django.http import HttpRequest
from ..forms import CartUpdateForm
from decimal import Decimal, InvalidOperation

class FilterSort:
    def __init__(self, books: Sku, sort_by: str = None, price: str = None, genres: list[str] = None, publishers: list[str] = None):
        self.books = books
        self.sort_by = sort_by
        self.genres = genres
        self.price = price
        self.publishers = publishers
        self.seven_days = timezone.now().replace(hour=0, minute=0, microsecond=0) - timedelta(days=7)

    def filter_skus(self):
        """Filter sku/books by specified parameter"""
        if self.genres:
            self.books = self.books.filter(book__series__genres__id__in=self.genres)
        if self.publishers:
            self.books = self.books.filter(publisher__id__in=self.publishers)
        if self.sort_by:
            self.books = self.sort_skus(self.books, self.sort_by)
        if self.price:
            books = self.books.annotate(
                current_price=Case(
                    When(discount_percent__gt=0, then=(F('price_usd') - (F('price_usd') * F('discount_percent') / 100))),
                    default=F('price_usd'),
                    output_field=DecimalField(max_digits=10, decimal_places=2)
                )
            )
            try:
                self.books = books.filter(current_price__lte=Decimal(self.price))
            except InvalidOperation:
                self.books = []
        return self.books

    def sort_skus(self, books: Sku, sort_by: str) -> BaseManager[Sku]:
        """Sort sku/books by specified parameter"""
        if sort_by == 'price_desc' or sort_by == 'price_asc':
            books = books.annotate(
                current_price=Case(
                    When(discount_percent__gt=0, then=(F('price_usd') - (F('price_usd') * F('discount_percent') / 100))),
                    default=F('price_usd'),
                    output_field=DecimalField(max_digits=10, decimal_places=2)
                )
            )
            books = books.order_by('current_price') if sort_by == 'price_asc' else books.order_by('-current_price')
        elif sort_by == 'newest':
            books = books.order_by('-published_at')
        elif sort_by == 'reviews':
            books = books.order_by('-book__average_rating')
        else:
            books = books.order_by('book')
            
        return books

def base_book_queryset(sku: Sku):
    """Function that acts as the base queryset for subsequent queries on the Sku model. Fundamental filters have been applied"""

    return (sku.objects.filter(is_discontinued=False, quantity__gt=0, book__is_deleted=False, book__series__is_deleted=False)
                         .select_related('book__series')
                         .prefetch_related('book__authors')
                         .only(
                             'book__title',
                             'price_usd',
                             'format',
                             'isbn_number',
                             'book__authors__name',
                             'book__series'
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


def get_cart_items_and_forms(user, session_id, request):
    """Find or create existing cart and return a zip of each item and their corresponding form if exists, else empty list"""
    try:
        # Get cart related to user or session_id, return empty cart if it doesn't exist
        cart = Cart.objects.get(user=user) if user else Cart.objects.get(session_id=session_id)
        # Store cart id in session
        request.session['cart_id'] = str(cart.public_id)
    except Cart.DoesNotExist:
        cart_items_and_forms = []
    else:
        # Get cart items related to cart, return empty cart if it doesn't exist
        cart_items = (CartItem.objects.filter(cart=cart)
            .prefetch_related('sku__book__authors')).order_by('-created_at')
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

def get_related_books(book_sku: Sku, base_queryset: BaseManager[Sku], genre_ids, limit=6):
    """Function to get sku related to a current book/sku"""
    related = []
    used_ids = {book_sku.id}

    
    # Create a distinct queryset, one sku per book
    distinct_skus = (Sku.objects.filter(book__series__category=book_sku.book.series.category)
        .exclude(book=book_sku.book)
        .distinct('book')
        .annotate(distinct_id=Subquery(
            Sku.objects.filter(book=OuterRef('book')).order_by('price_usd')
            .values('id')[:1]
        )).values_list('distinct_id', flat=True))

    # Layer 1: Same Genre
    layer1 = (
        base_queryset
        .filter(book__series__genres__in=genre_ids, id__in=distinct_skus)
        .exclude(id__in=used_ids)
        .order_by('?')[:limit]
    )

    for item in layer1:
        if len(related) >= limit:
            break
        related.append(item)
        used_ids.add(item.id)

    # Layer 2: Same Author
    if len(related) < limit:
        layer2 = (
            base_queryset
            .filter(book__authors__name=book_sku.book.authors.first().name, 
            id__in=distinct_skus)
            .exclude(id__in=used_ids)
            .order_by('?')[:limit]
        )

        for item in layer2:
            if len(related) >= limit:
                break
            related.append(item)
            used_ids.add(item.id)

    # Layer 3: Same Publisher
    if len(related) < limit:
        layer3 = (
            base_queryset
            .filter(publisher__name=book_sku.publisher.name, id__in=distinct_skus)
            .exclude(id__in=used_ids)
            .order_by('?')[:limit]
        )

        for item in layer3:
            if len(related) >= limit:
                break
            related.append(item)
            used_ids.add(item.id)

    # Layer 4: Trending in Category
    if len(related) < limit:
        layer4 = (
            base_queryset
            .filter(book__trending_score__gt=0, id__in=distinct_skus)
            .exclude(id__in=used_ids)[:limit]
        )

        for item in layer4:
            if len(related) >= limit:
                break
            related.append(item)
            used_ids.add(item.id)

    return related

def distinct_sku(sku: Sku, category: Category):
    """Create a distinct queryset, one sku per book for a category."""
    distinct_skus = (sku.objects.filter(book__series__category=category)
        .distinct('book')
        .annotate(distinct_id=Subquery(
            sku.objects.filter(book=OuterRef('book')).order_by('price_usd')
            .values('id')[:1]
        )).values_list('distinct_id', flat=True))
    
    return distinct_skus