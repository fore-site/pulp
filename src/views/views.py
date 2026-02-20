from django.shortcuts import render, get_object_or_404
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.views import generic
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from django.contrib.auth import login
from src.models import Series, Sku, Book, BookEvent, Genre, Category
from ..forms import CustomUserCreationForm
from django.db.models import Q, Subquery, OuterRef
from django_htmx.middleware import HtmxDetails
from ..utils.common import FilterSort, base_book_queryset
from django.utils import timezone
from datetime import timedelta

class HtmxHttpRequest(HttpRequest):
    htmx: HtmxDetails

# Create your views here.

class IndexView(generic.TemplateView):
    template_name = 'src/index.html'
    seven_days = timezone.now().replace(hour=0, minute=0, microsecond=0) - timedelta(days=7)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        base_queryset = base_book_queryset(Sku)
        
        manga = (base_queryset.filter(book__is_featured=True, book__series__category__name='manga', published_at__gte=self.seven_days)
                 .order_by('book__series', '-published_at', 'price_usd')
                 .distinct('book__series'))
        comic = (base_queryset.filter(book__is_featured=True, book__series__category__name='comic', published_at__gte=self.seven_days)
                 .order_by('book__series', '-published_at', 'price_usd')
                 .distinct('book__series'))
        hot_deals = base_queryset.filter(book__is_featured=True, discount_percent__gt=0).order_by('-discount_percent')[:10]

        trending = (base_queryset.filter(book__trending_score__gt=0).order_by('book', 'book__trending_score').distinct('book')[:10]
                     )
        
        comic_bestselling = (base_queryset
                              .filter(book__series__category__name='comic', book__bestseller_score__gt=0)
                              .order_by('book', 'book__bestseller_score').distinct('book')[:10])

        manga_bestselling = (base_queryset
                              .filter(book__series__category__name='manga', book__bestseller_score__gt=0)
                              .order_by('book', 'book__bestseller_score').distinct('book')[:10])

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

        # Create a distinct queryset, one sku per book
        distinct_skus = (Sku.objects.filter(book__series__category=self.category)
        .distinct('book')
        .annotate(distinct_id=Subquery(
            Sku.objects.filter(book=OuterRef('book')).order_by('price_usd')
            .values('id')[:1]
        )).values_list('distinct_id', flat=True))

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
        genres = Genre.objects.filter(categories__name=self.category.name)

        context['category'] = self.category.name.capitalize()
        context['genres'] = genres
        context['selected_genres'] = [int(g) for g in self.request.GET.getlist('g')]
        context['formats'] = ['hardcover', 'paperback', 'digital']
        context['selected_format'] = self.request.GET.get('f')
        context['selected_sort'] = self.request.GET.get('sort')
        context['latest_release'] = self.request.GET.get('r')

        return context
               
class ProductDetailView(generic.DetailView):
    model = Sku
    template_name = 'src/product_detail.html'
    context_object_name = 'sku'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected_format = self.request.GET.get('f', 'digital')
        pk = self.kwargs.get('pk')

        default_format_sku = Sku.objects.filter(format=selected_format.capitalize(), pk=pk, is_discontinued=False, book__is_deleted=False).select_related('book__series').get()
        BookEvent.objects.create(sku=default_format_sku, event_type='view')

        context['format'] = selected_format
        context['default_sku'] = default_format_sku

        return context

class SeriesIndexView(generic.ListView):
    model = Series
    context_object_name = 'series_list'
    template_name = 'src/series_index.html'

    def get_queryset(self):
        series_type = self.kwargs.get('series_type')
        category = get_object_or_404(Category, name__iexact=series_type)
        series = (Series.objects.filter(category=category))
        return series
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.kwargs.get('series_type').capitalize()
        return context

class SeriesDetailView(generic.TemplateView):
    template_name = 'src/series_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        series = Series.objects.get(pk=self.kwargs.get('pk'))
        sku_list = Sku.objects.filter(book__series=self.kwargs.get('pk'), is_discontinued=False, book__is_deleted=False, book__series__is_deleted=False).order_by('book', 'book__series__title').distinct('book')
        book_count = Book.objects.filter(series=self.kwargs.get('pk'), sku__is_discontinued=False, is_deleted=False, series__is_deleted=False).count()

        context['sku_list'] = sku_list
        context['book_count'] = book_count
        context['series'] = series

        return context

@require_GET
def search_results_view(request):  
    query = request.GET.get('q')
    base_queryset = base_book_queryset(Sku)

    try:
        results = (base_queryset
                   .filter(Q(book__title__icontains=query) | Q(book__authors__name__icontains=query) | Q(isbn_number__icontains=query))
                   .distinct('book'))
    except Sku.DoesNotExist:
        return render(request, 'src/search_results.html', {"results": None, "query": query})
    else:
        return render(request, 'src/search_results.html', {"results": results, "query": query})

@require_http_methods(['GET', 'POST'])
def signup(request):
    if request.POST:
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=True)
            login(request, user)
            return HttpResponseRedirect(reverse('home'))
        else:
            return render(request, 'src/signup.html', {"form": form})
    else:
        form = CustomUserCreationForm()
        return render(request, 'src/signup.html', {"form": form})

class HotDealsView(generic.TemplateView):
    template_name = 'src/deals.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_queryset = base_book_queryset(Sku)

        manga_deals = base_queryset.filter(book__series__category__name='manga', discount_percent__gte=50).order_by('discount_percent')
        comic_deals = base_queryset.filter(book__series__category__name='comic', discount_percent__gte=50).order_by('discount_percent')

        context['manga_deals'] = manga_deals
        context['comic_deals'] = comic_deals
        return context

def order(request, id):
    return HttpResponse('You have placed an order on %s.' % id)
