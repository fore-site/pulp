from django.utils import timezone
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from datetime import timedelta
from src.models import Series, Sku, Book, BookEvent, Genre, Category, Publisher
from django.views.decorators.http import require_GET
from ..utils.common import FilterSort, base_book_queryset, get_related_books, distinct_sku
from django.db.models import Q, Count
from django.views import generic
from datetime import timedelta

def partial_rendering(request):
    # Standard Django pagination
    page_num = request.GET.get("page", "1")
    page = Paginator(object_list='', per_page=10).get_page(page_num)

    # The htmx magic - render just the `#table-section` partial for htmx
    # requests, allowing us to skip rendering the unchanging parts of the
    # template.
    template_name = "partial-rendering.html"
    if request.htmx:
        template_name += "#table-section"

    return render(
        request,
        template_name,
        {
            "page": page,
        },
    )

class IndexView(generic.TemplateView):
    template_name = 'src/index.html'
    seven_days = timezone.now().replace(hour=0, minute=0, microsecond=0) - timedelta(days=7)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        base_queryset = base_book_queryset(Sku)
        
        comic_category = Category.objects.get(name='comic')
        manga_category = Category.objects.get(name='manga')
        
        manga_distinct_skus = distinct_sku(Sku, manga_category)
        comic_distinct_skus = distinct_sku(Sku, comic_category)

        manga = (base_queryset.filter(book__is_featured=True, book__series__category__name='manga', published_at__gte=self.seven_days)
                 .order_by('book')
                 .distinct('book'))
        comic = (base_queryset.filter(book__is_featured=True, book__series__category__name='comic', published_at__gte=self.seven_days)
                 .order_by('book')
                 .distinct('book'))
        hot_deals = base_queryset.filter(book__is_featured=True, discount_percent__gt=0).order_by('-discount_percent')[:10]

        trending = (base_queryset.filter(book__trending_score__gt=0).order_by('book').distinct('book')[:10]
                     )
        
        comic_bestselling = (base_queryset
                              .filter(book__series__category__name='comic', book__bestseller_score__gt=0, id__in=comic_distinct_skus)
                              .order_by('book__bestseller_score')[:10])

        manga_bestselling = (base_queryset
                              .filter(book__series__category__name='manga', book__bestseller_score__gt=0, id__in=manga_distinct_skus)
                              .order_by('book__bestseller_score')[:10])

        context['new_manga_release'] = manga
        context['new_comic_release'] = comic
        context['trending'] = trending
        context['hot_deals'] = hot_deals
        context['comic_bestselling'] = comic_bestselling
        context['manga_bestselling'] = manga_bestselling

        return context

class BookListView(generic.ListView):
    model = Sku
    template_name = 'src/book_list.html'
    context_object_name = 'books'

    def get_queryset(self):
        self.category = get_object_or_404(Category, name__iexact=self.kwargs.get('category'))

        # Fetch filters and sort params 
        genre_filters = self.request.GET.getlist('g')
        featured = self.request.GET.get('featured')
        format = self.request.GET.get('f')
        sort_by = self.request.GET.get('sort')
        latest_release = self.request.GET.get('r')

        distinct_skus = distinct_sku(Sku, self.category)

        # Create a base queryset
        books = base_book_queryset(Sku).filter(id__in=distinct_skus).order_by('book__title')
        
        # Filter and sort Skus if params exist
        filter_sort = FilterSort(books, sort_by, format, featured, genre_filters, latest_release)
        books = filter_sort.filter_skus()

        if self.request.htmx:
            self.template_name = "partials/book_card.html"

        return books
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        genres = Genre.objects.filter(categories__name__icontains=self.category.name)

        context['category'] = self.category.name.capitalize()
        context['genres'] = genres
        context['formats'] = ['hardcover', 'paperback', 'digital']
        context['selected_format'] = self.request.GET.get('f')
        context['selected_sort'] = self.request.GET.get('sort')
        context['latest_release'] = self.request.GET.get('r')

        return context
               
class ProductDetailView(generic.TemplateView):
    model = Sku
    template_name = 'src/product_detail.html'
    context_object_name = 'sku'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected_format = self.request.GET.get('f', 'digital')
        public_id = self.kwargs.get('public_id')

        default_format_sku = base_book_queryset(Sku).filter(format=selected_format.capitalize(), public_id=public_id).get()
        BookEvent.objects.create(sku=default_format_sku, event_type='view')
        
        # More books in the series
        books_in_series = Book.objects.filter(series=default_format_sku.book.series, is_deleted=False).exclude(sku=default_format_sku)[:5]

        # Related books/sku - Filter by category        
        base_queryset = (base_book_queryset(Sku).filter(
            book__series__category=default_format_sku.book.series.category
            ).exclude(id=default_format_sku.id, book=default_format_sku.book, book__series=default_format_sku.book.series))

        genre_ids = default_format_sku.book.series.genres.values_list('id', flat=True)
        
        related_titles_sku = get_related_books(default_format_sku, base_queryset, genre_ids=genre_ids) 

        context['format'] = selected_format
        context['default_sku'] = default_format_sku
        context['books_in_series'] = books_in_series
        context['related_sku'] = related_titles_sku

        return context

class SeriesIndexView(generic.ListView):
    model = Series
    context_object_name = 'series_list'
    template_name = 'src/series_index.html'

    def get_queryset(self):
        series_type = self.kwargs.get('series_type')
        category = get_object_or_404(Category, name__iexact=series_type)
        series = (Series.objects.filter(category=category).annotate(
            book_count=Count('books')
        ))
        return series
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.kwargs.get('series_type').capitalize()
        return context

class SeriesDetailView(generic.TemplateView):
    template_name = 'src/series_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        series = get_object_or_404(Series, public_id=self.kwargs.get('public_id'), is_deleted=False)
        sku_list = Sku.objects.filter(book__series=series, is_discontinued=False, book__is_deleted=False).order_by('book', 'book__series__title').distinct('book')
        book_count = Book.objects.filter(series=series, sku__in=sku_list, is_deleted=False).count()
        context['sku_list'] = sku_list
        context['book_count'] = book_count
        context['series'] = series

        return context

@require_GET
def search_results_view(request):  
    query = request.GET.get('q')
    if len(query) > 20:
        query = query[:20] + "..."
    base_queryset = base_book_queryset(Sku)

    try:
        results = (base_queryset
                   .filter(Q(book__title__icontains=query) | Q(book__authors__name__icontains=query) | Q(isbn_number__icontains=query))
                   .distinct('book'))
    except Sku.DoesNotExist:
        return render(request, 'src/search_results.html', {"results": None, "query": query})
    else:
        return render(request, 'src/search_results.html', {"results": results, "query": query})

class BestsellingView(generic.ListView):
    model = Sku
    template_name = 'src/bestseller.html'
    context_object_name = 'bestselling_books'

    def get_queryset(self):
        # Get query parameters for filter/sort
        genre_filters = self.request.GET.getlist('genre')
        publisher_filters = self.request.GET.getlist('publisher')
        price_range = self.request.GET.get('price')
        sort_by = self.request.GET.get('sort')

        self.category = get_object_or_404(Category, name__iexact = self.kwargs.get('category'))

        # Get a list of all distinct Sku in a category 
        distinct = distinct_sku(Sku, self.category)

        base_queryset = base_book_queryset(Sku)

        base_bestselling = (base_queryset
                        .filter(book__series__category=self.category, id__in=distinct, book__bestseller_score__gt=0))
        
        # Apply filters and sort if they exist
        filter_sort = FilterSort(base_bestselling, sort_by, price=price_range, genres=genre_filters, publishers=publisher_filters)
        bestselling = filter_sort.filter_skus()

        if self.request.htmx:
            self.template_name = 'src/bestseller.html#book_display'

        return bestselling

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        genres = Genre.objects.filter(categories__name__icontains=self.category.name)
        publishers = Publisher.objects.filter(sku__book__series__category=self.category).distinct('name')

        context['category'] = self.category.name.capitalize()
        context['genres'] = genres
        context['publishers'] = publishers
        context['price_range'] = ['10', '20', '50', '100']
        context['selected_genres'] = [int(g) for g in self.request.GET.getlist('genre')]
        context['selected_publishers'] = [int(pub) for pub in self.request.GET.getlist('publisher')]
        context['selected_price'] = self.request.GET.get('price')
        context['selected_sort'] = self.request.GET.get('sort')

        return context

class NewReleaseView(generic.ListView):
    model = Sku
    template_name = 'src/new_release.html'
    context_object_name = 'new_releases'

    def get_queryset(self):
        # Get current date and date from two weeks ago
        today = timezone.now().replace(hour=0, second=0, minute=0, microsecond=0)
        two_weeks = (today - timedelta(days=14)).date()

        # Get query parameters for filter/sort
        genre_filters = self.request.GET.getlist('genre')
        publisher_filters = self.request.GET.getlist('publisher')
        price_range = self.request.GET.get('price')
        sort_by = self.request.GET.get('sort')

        self.category = get_object_or_404(Category, name__iexact=self.kwargs.get('category'))
        
        # Get a list of all distinct Sku in a category 
        distinct = distinct_sku(Sku, self.category)
        
        base_queryset = base_book_queryset(Sku)
        
        base_new_releases = (base_queryset.filter(published_at__gte=two_weeks,
        book__series__category=self.category, id__in=distinct))

        # Apply filters and sort if they exist
        filter_sort = FilterSort(base_new_releases, sort_by, price=price_range, genres=genre_filters, publishers=publisher_filters)
        new_releases = filter_sort.filter_skus()

        if self.request.htmx:
            self.template_name = 'src/new_release.html#book_display'

        return new_releases

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        genres = Genre.objects.filter(categories__name__icontains=self.category.name)
        publishers = Publisher.objects.filter(sku__book__series__category=self.category).distinct('name')
        
        context['category'] = self.category.name.capitalize()
        context['genres'] = genres
        context['publishers'] = publishers
        context['price_range'] = ['10', '20', '50', '100']
        context['selected_genres'] = [int(g) for g in self.request.GET.getlist('genre')]
        context['selected_publishers'] = [int(pub) for pub in self.request.GET.getlist('publisher')]
        context['selected_price'] = self.request.GET.get('price')
        context['selected_sort'] = self.request.GET.get('sort')
        
        return context