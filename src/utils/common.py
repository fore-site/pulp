from django.db.models import Case, When, F, DecimalField, Sum, Subquery, OuterRef, Q
from ..models import Sku, Cart, CartItem, Category, Order, OrderAddress, OrderItem, IdempotencyKey
from django.db import transaction
from django.db.models.manager import BaseManager
from django.utils import timezone
from datetime import timedelta
from django.http import HttpRequest
from ..forms import CartUpdateForm
from decimal import Decimal, InvalidOperation

class FilterSort:
    def __init__(self, books: BaseManager[Sku],
                  sort_by: str | None = None, 
                  price: str | None = None, 
                  genres: list[str] | None = None, 
                  publisher: str | None = None,
                  discount: str | None = None,
                  cat_filter: list[str] | None = None):
        self.books = books
        self.sort_by = sort_by
        self.genres = genres
        self.price = price
        self.publisher = publisher
        self.discount = discount
        self.cat_filter = cat_filter
        self.seven_days = timezone.now().replace(hour=0, minute=0, microsecond=0) - timedelta(days=7)

    def filter_skus(self):
        """Filter sku/books by specified parameter"""
        if self.genres:
            self.books = self.books.filter(book__series__genres__name__in=self.genres)
        if self.publisher:
            self.books = self.books.filter(publisher__name=self.publisher)
        if self.cat_filter:
            self.books = self.books.filter(book__series__category__name__in=self.cat_filter)
        if self.sort_by:
            self.books = self.sort_skus(self.books, self.sort_by)
        if self.discount:
            if self.discount == 'lt50':
                self.books = self.books.filter(discount_percent__lte=50)
            elif self.discount == 'gt50':
                self.books = self.books.filter(discount_percent__gte=50)
            else:
                self.books = []
        if self.price:
            books = self.books.annotate(
                current_price=Case(
                    When(discount_percent__gt=0, then=(F('price') - (F('price') * F('discount_percent') / 100))),
                    default=F('price'),
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
                    When(discount_percent__gt=0, then=(F('price') - (F('price') * F('discount_percent') / 100))),
                    default=F('price'),
                    output_field=DecimalField(max_digits=10, decimal_places=2)
                )
            )
            books = books.order_by('current_price') if sort_by == 'price_asc' else books.order_by('-current_price')
        elif sort_by == 'newest_first':
            books = books.order_by('-published_at')
        elif sort_by == 'reviews':
            books = books.order_by('-book__average_rating')
        elif sort_by == 'discount':
            books = books.order_by('-discount_percent')
        else:
            books = books.order_by('book')
            
        return books

def base_book_queryset(sku: Sku):
    """Function that acts as the base queryset for subsequent queries on the Sku model. Fundamental filters have been applied"""

    return (sku.objects.filter(Q(quantity__gt=0) | Q(quantity__isnull=True), is_discontinued=False, book__is_deleted=False, book__series__is_deleted=False)
                         .select_related('book__series__category')
                         .prefetch_related('book__authors')
                         .only(
                             'book__title',
                             'price',
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


def get_cart_items_and_forms(user, session_id):
    """Find existing cart and return a zip of each item and their corresponding form if exists, else empty list"""
    try:
        # Get cart related to user or session_id, return empty cart if it doesn't exist
        cart = Cart.objects.get(user=user) if user else Cart.objects.get(session_id=session_id)
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
                                When(sku__discount_percent__gt=0, then=(F('sku__price') - (F('sku__price') * F('sku__discount_percent') / 100)) * F('quantity')),
                                default=F('sku__price') * F('quantity'),
                                output_field=DecimalField(max_digits=10, decimal_places=2)
                            )
                        )
                ).get()
        request.session['item_count'] = cart_items['item_count']
        request.session['subtotal_price'] = str(cart_items['subtotal'].quantize(Decimal('0.01')))
    except CartItem.DoesNotExist:
        request.session['item_count'] = 0

def get_related_books(book_sku: Sku, base_queryset: BaseManager[Sku], genre_ids, limit=10):
    """Function to get sku related to a current book/sku"""
    related = []
    used_ids = {book_sku.id}

    
    # Create a distinct queryset, one sku per book
    distinct_skus = (Sku.objects.filter(book__series__category=book_sku.book.series.category)
        .exclude(book=book_sku.book)
        .distinct('book')
        .annotate(distinct_id=Subquery(
            Sku.objects.filter(book=OuterRef('book')).order_by('price')
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

def distinct_sku(sku: Sku, category: Category | None = None):

    """Create a distinct queryset, one sku per book for a category or for any category."""
    if category:    
        distinct_skus_with_category = (sku.objects.filter(book__series__category=category)
            .distinct('book')
            .annotate(distinct_id=Subquery(
                sku.objects.filter(book=OuterRef('book')).order_by('price')
                .values('id')[:1]
            )).values_list('distinct_id', flat=True))
        return distinct_skus_with_category
    
    distinct_skus = (sku.objects
            .distinct('book')
            .annotate(distinct_id=Subquery(
                sku.objects.filter(book=OuterRef('book')).order_by('price')
                .values('id')[:1]
            )).values_list('distinct_id', flat=True))
    return distinct_skus

def create_order_and_related_data(request, user, cart_items, record: IdempotencyKey | None = None, 
                                  key: str | None = None, first_time: bool = False):
    record_in_func = None
    with transaction.atomic():
        if first_time:
            record_in_func = IdempotencyKey.objects.create(key=key)

        user_order = Order.objects.create(
            user = user,
            session_id = request.session.session_key,
            subtotal_amount = request.session.get('subtotal_price'),
            shipping_fee = request.session.get('shipping_fee'),
            total_amount = request.session.get('total_price'),
        )

        for item in cart_items:
            OrderItem.objects.create(
                order = user_order,
                sku = item.sku,
                quantity = item.quantity,
                unit_price = item.unit_price
            )

        OrderAddress.objects.create(
            order = user_order,
            recipient_firstname = request.session.get('firstname'),
            recipient_lastname = request.session.get('lastname'),
            recipient_email = request.session.get('email'),
            recipient_phone_no = request.session.get('phone_no'),
            address_desc = request.session.get('address_desc'),
            address_state = request.session.get('address_state'),
            address_city = request.session.get('address_city')
        )
        if record:
            record.order_id = user_order.id
            record.save()
        elif record_in_func:
            record_in_func.order_id = user_order.id
            record_in_func.save()

    return user_order

def update_db_after_payment(order: Order, 
                            request,
                            payment_status: str,
                            order_items: BaseManager[OrderItem]):
    """Database operations to carry out depending on payment status."""
    if payment_status == 'Paid':
            order.payment_status = 'Paid'
            order.save()
            request.session['is_payment_processing'] = False
            request.session['item_count'] = 0

            # Clear cart items
            user = order.user if order.user else order.session_id
            try:
                cart = Cart.objects.get(user)
            except Cart.DoesNotExist:
                pass
            else:
                item_deleted, _ = CartItem.objects.filter(user=user, cart=cart).delete()
                print(f'{item_deleted} items cleared from cart after successful purchase.')

            # Update stock quantity in database
            sku_to_update = []
            for item in order_items:
                stock_left = item.sku.quantity - item.quantity
                item.sku.quantity = stock_left
                sku_to_update.append(item.sku)

            rows_updated = Sku.objects.bulk_update(sku_to_update, ['quantity'])
            print(f'{rows_updated} stocks updated after successful purchase')

            # Delete corresponding idempotency key
            deleted, _ = IdempotencyKey.objects.filter(order_id=order.id).delete()
            print(f'{deleted} idempotency key(s) deleted after successful purchase')
    elif payment_status == 'Processing':
        order.payment_status = 'Processing'
        order.save()
    else:
        order.payment_status = payment_status
        order.save()