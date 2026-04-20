from typing import Any
from django.db.models import Subquery, OuterRef, F
from django.http import HttpRequest
from django.http.response import HttpResponse as HttpResponse
from django.utils import timezone
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render, redirect
from datetime import timedelta
from src.models import Series, Sku, Book, BookEvent, Genre, Category, Publisher
from django.views.decorators.http import require_GET
from ..utils.common import FilterSort, base_book_queryset, get_related_books, distinct_sku
from django.db.models import Q, Count
from django.views import generic
from datetime import timedelta
from ..forms import SearchBarForm

class IndexView(generic.TemplateView):
    template_name = 'src/index.html'
    seven_days = timezone.now().replace(hour=0, minute=0, microsecond=0) - timedelta(days=7)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get current date and date from one year ago
        today = timezone.now().replace(hour=0, second=0, minute=0, microsecond=0)
        one_year = (today - timedelta(weeks=52)).date()

        base_queryset = base_book_queryset(Sku)
        
        comic_category = Category.objects.get(name__iexact='comic')
        manga_category = Category.objects.get(name__iexact='manga')
        
        manga_distinct_skus = distinct_sku(Sku, manga_category)
        comic_distinct_skus = distinct_sku(Sku, comic_category)
        combined_distinct_skus = manga_distinct_skus | comic_distinct_skus

        manga = (base_queryset.filter(published_at__gte=one_year, book__series__category__name__iexact='manga', id__in=manga_distinct_skus)
                 .order_by('-published_at'))[:10]
        comic = (base_queryset.filter(published_at__gte=one_year, book__series__category__name__iexact='comic', id__in=comic_distinct_skus)
                 .order_by('-published_at'))[:10]
        hot_deals = base_queryset.filter(book__is_featured=True, discount_percent__gt=0).order_by('-discount_percent')[:10]

        trending = (base_queryset.filter(book__trending_score__gt=0, id__in=combined_distinct_skus).order_by('-book__trending_score')[:10]
                     )
        
        comic_bestselling = (base_queryset
                              .filter(book__series__category__name__iexact='comic', book__bestseller_score__gt=0, id__in=comic_distinct_skus)
                              .order_by('-book__bestseller_score')[:10])

        manga_bestselling = (base_queryset
                              .filter(book__series__category__name__iexact='manga', book__bestseller_score__gt=0, id__in=manga_distinct_skus)
                              .order_by('-book__bestseller_score')[:10])

        context['new_manga_release'] = manga
        context['new_comic_release'] = comic
        context['trending'] = trending
        context['hot_deals'] = hot_deals
        context['comic_bestselling'] = comic_bestselling
        context['manga_bestselling'] = manga_bestselling

        return context
               
class ProductDetailView(generic.TemplateView):
    model = Sku
    template_name = 'src/product_detail.html'
    context_object_name = 'sku'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        public_id = self.kwargs.get('public_id')

        default_format_sku = base_book_queryset(Sku).filter(public_id=public_id).get()
        BookEvent.objects.create(sku=default_format_sku, event_type='view')
        
        # More books in the series
        books_in_series = Book.objects.filter(series=default_format_sku.book.series, is_deleted=False).exclude(sku=default_format_sku)[:10]

        # Related books/sku - Filter by category        
        base_queryset = (base_book_queryset(Sku).filter(
            book__series__category=default_format_sku.book.series.category
            ).exclude(id=default_format_sku.id, book=default_format_sku.book, book__series=default_format_sku.book.series))

        genre_ids = default_format_sku.book.series.genres.values_list('id', flat=True)
        
        related_titles_sku = get_related_books(default_format_sku, base_queryset, genre_ids=genre_ids) 

        context['format'] = default_format_sku.format
        context['default_sku'] = default_format_sku
        context['books_in_series'] = books_in_series
        context['related_sku'] = related_titles_sku

        return context

class SeriesIndexView(generic.ListView):
    model = Series
    context_object_name = 'series_list'
    template_name = 'src/series_index.html'
    paginate_by = 10

    def get_queryset(self):
        series_type = self.kwargs.get('series_type')
        letter = self.request.GET.get('letter')
        category = get_object_or_404(Category, name__iexact=series_type)
        series = (Series.objects.filter(category=category).annotate(
            book_count=Count('books')
        ).order_by('title'))

        if letter:
            if len(letter) > 1:
                return series
            else:
                series = series.filter(title__istartswith=letter)

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
        sku_list = Sku.objects.filter(book__series=series, is_discontinued=False, book__is_deleted=False).order_by('book').distinct('book')
        book_count = Book.objects.filter(series=series, sku__in=sku_list, is_deleted=False).count()
        
        page_num = self.request.GET.get('page', '1')
        page = Paginator(object_list=sku_list, per_page=10).get_page(page_num)
        
        context['page'] = page
        context['book_count'] = book_count
        context['series'] = series

        return context

@require_GET
def search_results_view(request):  
    price_range = ['10000', '20000', '50000', '100000']
    selected_price = request.GET.get('price')
    selected_sort = request.GET.get('sort')
    template_name = 'src/search_results.html'

    form = SearchBarForm({'q': request.GET.get('q')})

    if request.htmx:
        template_name = 'partials/book_grid.html'
    
    base_queryset = base_book_queryset(Sku)

    # Get a list of all distinct Sku
    distinct = distinct_sku(Sku)
    
    if form.is_valid():
        query = form.cleaned_data.get('q')
        public_query = query[:20] + "..." if len(query) > 20 else query
        try:
            results = (base_queryset
                    .filter(Q(book__title__icontains=query) | Q(book__authors__name__icontains=query) | Q(isbn_number__icontains=query), id__in=distinct))
            result_count = results.count()
        except Sku.DoesNotExist:
            return render(request, template_name, {"page": None, "query": public_query})
        else:
            # Apply filters and sort if they exist
            filter_sort = FilterSort(results, sort_by=selected_sort, price=selected_price)
            search_results = filter_sort.filter_skus()
            
            page_num = request.GET.get("page", "1")
            page = Paginator(object_list=search_results, per_page=10).get_page(page_num)
            response = render(request, template_name, 
                        {"page_obj": page, "query": public_query, 
                        "result_count": result_count, "selected_price": selected_price, 
                        "selected_sort": selected_sort, "price_range": price_range,
                        'search_bar_form': form})
        
            # Add response header to indicate that the content varies based on the presence of the HX-Request header
            response['Vary'] = 'HX-Request'

            #   Add headers to prevent caching of the response, ensuring that users always see the most up-to-date search results
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'

            return response
    return render(request, template_name, {"page": None, "query": None,
                                           'search_bar_form': form})

class BestsellingView(generic.ListView):
    model = Sku
    template_name = 'src/bestseller.html'
    context_object_name = 'bestselling_books'
    paginate_by = 10

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        response = super().dispatch(request, *args, **kwargs)
        # Add response header to indicate that the content varies based on the presence of the HX-Request header
        response['Vary'] = 'HX-Request'

        #   Add headers to prevent caching of the response, ensuring that users always see the most up-to-date bestseller listings
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response

    def get_queryset(self):
        # Get query parameters for filter/sort]
        genre_filters = self.request.GET.getlist('genre')
        publisher_filter = self.request.GET.get('publisher')
        price_range = self.request.GET.get('price')
        sort_by = self.request.GET.get('sort')

        self.category = get_object_or_404(Category, name__iexact = self.kwargs.get('category'))

        # Get a list of all distinct Sku in a category 
        distinct = distinct_sku(Sku, self.category)

        base_queryset = base_book_queryset(Sku)

        base_bestselling = (base_queryset
                        .filter(book__series__category=self.category, id__in=distinct, book__bestseller_score__gt=0))
        # Apply filters and sort if they exist
        filter_sort = FilterSort(base_bestselling, sort_by, price=price_range, genres=genre_filters, publisher=publisher_filter)
        bestselling = filter_sort.filter_skus()

        if self.request.htmx:
            self.template_name = 'partials/book_grid.html'

        return bestselling

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        genres = Genre.objects.filter(categories__name__iexact=self.category.name).order_by('name')
        publishers = Publisher.objects.filter(sku__book__series__category=self.category).order_by('name').distinct('name')

        context['category'] = self.category.name.capitalize()
        context['page_title'] = 'Bestseller'
        context['genres'] = genres
        context['publishers'] = publishers
        context['price_range'] = ['10000', '20000', '50000', '100000']
        context['selected_genres'] = [g for g in self.request.GET.getlist('genre')]
        context['selected_publisher'] = self.request.GET.get('publisher')
        context['selected_price'] = self.request.GET.get('price')
        context['selected_sort'] = self.request.GET.get('sort')

        return context

class NewReleaseView(generic.ListView):
    model = Sku
    template_name = 'src/new_release.html'
    context_object_name = 'new_releases'
    paginate_by = 10

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        response = super().dispatch(request, *args, **kwargs)
        # Add response header to indicate that the content varies based on the presence of the HX-Request header
        response['Vary'] = 'HX-Request'

        #   Add headers to prevent caching of the response, ensuring that users always see the most up-to-date new releases
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        
        return response

    def get_queryset(self):
        # Get current date and date from one year ago
        today = timezone.now().replace(hour=0, second=0, minute=0, microsecond=0)
        one_year = (today - timedelta(weeks=52)).date()

        # Get query parameters for filter/sort
        genre_filters = self.request.GET.getlist('genre')
        publisher_filter = self.request.GET.get('publisher')
        price_range = self.request.GET.get('price')
        sort_by = self.request.GET.get('sort')

        print(genre_filters)

        self.category = get_object_or_404(Category, name__iexact=self.kwargs.get('category'))
        
        # Get a list of all distinct Sku in a category 
        distinct = distinct_sku(Sku, self.category)
        
        base_queryset = base_book_queryset(Sku)
        
        base_new_releases = (base_queryset.filter(published_at__gte=one_year,
        book__series__category=self.category, id__in=distinct))

        # Apply filters and sort if they exist
        filter_sort = FilterSort(base_new_releases, sort_by, price=price_range, genres=genre_filters, publisher=publisher_filter)
        new_releases = filter_sort.filter_skus()

        if self.request.htmx:
            self.template_name = 'partials/book_grid.html'

        return new_releases

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        genres = Genre.objects.filter(categories__name__iexact=self.category.name).order_by('name')
        publishers = Publisher.objects.filter(sku__book__series__category=self.category).order_by('name').distinct('name')
        
        context['category'] = self.category.name.capitalize()
        context['page_title'] = 'New Releases'
        context['genres'] = genres
        context['publishers'] = publishers
        context['price_range'] = ['10000', '20000', '50000', '100000']
        context['selected_genres'] = [g for g in self.request.GET.getlist('genre')]
        context['selected_publisher'] = self.request.GET.getlist('publisher')
        context['selected_price'] = self.request.GET.get('price')
        context['selected_sort'] = self.request.GET.get('sort')
        
        return context
    
class HotDealsView(generic.ListView):
    model = Sku
    template_name = 'src/deals.html'
    context_object_name = 'hot_deals'
    paginate_by = 10
    
    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        response = super().dispatch(request, *args, **kwargs)
        # Add response header to indicate that the content varies based on the presence of the HX-Request header
        response['Vary'] = 'HX-Request'

        #   Add headers to prevent caching of the response, ensuring that users always see the most up-to-date new releases
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response

    def get_queryset(self):
        sort_by = self.request.GET.get('sort')
        price_range = self.request.GET.get('price')
        discount = self.request.GET.get('disct')
        category_filter = self.request.GET.getlist('cat')

        base_queryset = base_book_queryset(Sku)
        
        distinct_sku_func = (Sku.objects.filter(discount_percent__gt=0)
            .distinct('book')
            .annotate(distinct_id=Subquery(
                Sku.objects.filter(book=OuterRef('book'))
                .annotate(discounted_price=(F('price') - (F('price') * F('discount_percent') / 100)))
                .order_by('discounted_price')
                .values('id')[:1]
            )).values_list('distinct_id', flat=True))

        base_hot_deals = base_queryset.filter(discount_percent__gt=0, id__in=distinct_sku_func)

        # Apply filter and sort if they exist
        filter_sort = FilterSort(base_hot_deals, sort_by=sort_by, price=price_range, discount=discount, cat_filter=category_filter)
        hot_deals = filter_sort.filter_skus()
         
        if self.request.htmx:
            self.template_name = 'partials/book_grid.html'

        return hot_deals
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        categories = Category.objects.all()

        context['selected_sort'] = self.request.GET.get('sort')
        context['categories'] = categories
        context['page_title'] = 'Hot Deals'
        context['price_range'] = ['10000', '20000', '50000', '100000']
        context['discounts'] = ['lt50', 'gt50']
        context['selected_categories'] = [c for c in self.request.GET.getlist('cat')]
        context['selected_price'] = self.request.GET.get('price')
        context['selected_discount'] = self.request.GET.get('disct')
        
        return context