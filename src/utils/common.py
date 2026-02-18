from django.db.models import Case, When, F, DecimalField
from ..models import Sku
from django.db.models.manager import BaseManager
from django.utils import timezone
from datetime import timedelta

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
