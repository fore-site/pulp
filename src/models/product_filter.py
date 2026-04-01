from ..models import Book, Sku, Series
import django_filters

class BookFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='iexact')

    class Meta:
        model = Book
        fields = ['is_featured', 'average_rating', 'bestseller_score']

class SeriesFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='iexact')

    class Meta:
        model = Series
        fields = ['genres']

class SkuFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='iexact')

    class Meta:
        model = Sku
        fields = ['price_usd', 'published_at', 'publisher', 'format']