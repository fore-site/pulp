from unicodedata import category
from django.shortcuts import render, get_object_or_404
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.views import generic
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from django.contrib.auth import login
from src.models import Series, Sku, Book, BookEvent, Genre, Category
from ..forms import CustomUserCreationForm
from django.db.models import F, Q
from django_htmx.middleware import HtmxDetails

class HtmxHttpRequest(HttpRequest):
    htmx: HtmxDetails

# Create your views here.

class IndexView(generic.TemplateView):
    template_name = 'src/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_queryset = (Sku.objects.filter(is_discontinued=False, quantity__gt=0)
                         .select_related('book')
                         .prefetch_related('book__authors')
                         .only(
                             'book__title',
                             'price_usd',
                             'format',
                             'isbn_number',
                             'book__authors__name'
                         ))
        manga = (base_queryset.filter(book__is_featured=True, book__series__category__name='manga')
                 .order_by('book__series', '-published_at', 'price_usd')
                 .distinct('book__series'))
        comic = (base_queryset.filter(book__is_featured=True, book__series__category__name='comic' )
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

        context['manga_sku_list'] = manga
        context['comic_sku_list'] = comic
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

        genre_filters = self.request.GET.getlist('genre')
        featured = self.request.GET.get('featured')
        format = self.request.GET.getlist('format')

        books = (Sku.objects.filter(book__series__category=self.category, is_discontinued=False, quantity__gt=0)
                  .select_related('book')
                  .prefetch_related('book__authors')
                  .only(
                      'book__title',
                      'isbn_number',
                      'price_usd',
                      'format',
                      'book__authors__name'
                  )
                  .order_by('book__title').distinct('book__title'))

        if genre_filters:
            books = books.filter(book__series__genres__id__in=genre_filters)
        if featured:
            books = books.filter(book__is_featured=True)
        if format:
            books = books.filter(format=format)

        if self.request.htmx:
                self.template_name = "partials/book_card.html"
    
        return books
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        genres = Genre.objects.filter(categories__name=self.category.name.capitalize())

        context['category'] = self.category
        context['genres'] = genres
        context['selected_genres'] = [int(g) for g in self.request.GET.getlist('genre')]

        return context
               
class ProductDetailView(generic.DetailView):
    model = Sku
    template_name = 'src/product_detail.html'
    context_object_name = 'sku'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected_format = self.request.GET.get('f', 'digital')
        pk = self.kwargs.get('pk')

        default_format_sku = Sku.objects.filter(format=selected_format.capitalize(), pk=pk).prefetch_related('book').get()
        BookEvent.objects.create(sku=default_format_sku, event_type='view')

        context['format'] = selected_format
        context['default_sku'] = default_format_sku

        return context

class SeriesIndexView(generic.ListView):
    model = Series
    template_name = 'src/series_index.html'

class SeriesDetailView(generic.TemplateView):
    template_name = 'src/series_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        series = Series.objects.get(pk=self.kwargs.get('pk'))
        sku_list = Sku.objects.filter(book__series=self.kwargs.get('pk')).order_by('book', 'book__series__title').distinct('book')
        book_count = Book.objects.filter(series=self.kwargs.get('pk')).count()

        context['sku_list'] = sku_list
        context['book_count'] = book_count
        context['series'] = series

        return context

def series_list(request, series_type):
    if series_type == 'comic':
        series_list = Series.objects.filter(category__name='Comic').order_by('title')
        title = 'Comic'
    elif series_type == 'manga':
        series_list = Series.objects.filter(category__name='Manga').order_by('title')
        title = 'Manga'
    context = {
        "series_list": series_list,
        "title": title
    }
    return render(request, 'src/series_index.html', context)

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

def order(request, id):
    return HttpResponse('You have placed an order on %s.' % id)
