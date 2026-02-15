from django.shortcuts import render
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.views import generic
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from django.contrib.auth import login
from src.models import Series, Sku, Book, BookEvent, Genre
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
        manga = (base_queryset.filter(book__is_featured=True, book__series__category__name='Manga')
                 .order_by('book__series', '-published_at', 'price_usd')
                 .distinct('book__series'))
        comic = (base_queryset.filter(book__is_featured=True, book__series__category__name='Comic' )
                 .order_by('book__series', '-published_at', 'price_usd')
                 .distinct('book__series'))
        hot_deals = base_queryset.filter(book__is_featured=True, discount_percent__gt=0).order_by('-discount_percent')[:10]

        trending = (base_queryset.filter(book__trending_score__gt=0).order_by('book', 'book__trending_score').distinct('book')[:10]
                     )
        
        comic_bestselling = (base_queryset
                              .filter(book__series__category__name='Comic', book__bestseller_score__gt=0)
                              .order_by('book', 'book__bestseller_score').distinct('book')[:10])

        manga_bestselling = (base_queryset
                              .filter(book__series__category__name='Manga', book__bestseller_score__gt=0)
                              .order_by('book', 'book__bestseller_score').distinct('book')[:10])

        context['manga_sku_list'] = manga
        context['comic_sku_list'] = comic
        context['trending'] = trending
        context['hot_deals'] = hot_deals
        context['comic_bestselling'] = comic_bestselling
        context['manga_bestselling'] = manga_bestselling

        return context

class ComicListView(generic.TemplateView):
    template_name = 'src/comic_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        genre_filters = self.request.GET.get('filter')
        is_featured_list = self.request.GET.get('is_featured')
        format_list = self.request.GET.get('format')

        comics = (Sku.objects.filter(book__series__category__name='Comic', is_discontinued=False, quantity__gt=0)
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

        genres = Genre.objects.filter(categories__name='Comic')

        if genre_filters:
            if self.request.htmx:
                self.template_name = "partials/book_card.html"
                for genre in genre_filters:
                    comics = comics.filter(book__series__genres__name=genre.capitalize())
            else:
                for genre in genre_filters:
                    comics = comics.filter(book__series__genres__name=genre.capitalize())
        if is_featured_list:
            if self.request.htmx:
                self.template_name = "partials/book_card.html"
                for is_featured in is_featured_list:
                    comics = comics.filter(book__series__genres__name=bool(is_featured))
            else:
                for genre in genre_filters:
                    comics = comics.filter(book__series__genres__name=bool(is_featured))
        if format_list:
            if self.request.htmx:
                self.template_name = "partials/book_card.html"
                for format in format_list:
                    comics = comics.filter(book__series__genres__name=format.capitalize())
            else:
                for genre in genre_filters:
                    comics = comics.filter(book__series__genres__name=format.capitalize())

        context['books'] = comics
        context['genres'] = genres
        return context
       
class MangaListView(generic.TemplateView):
    template_name = 'src/manga_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        genre_filters = self.request.GET.getlist("filter")
        format_list = self.request.GET.getlist("format")
        is_featured_list = self.request.GET.getlist("is_featured")

        mangas = (Sku.objects.filter(book__series__category__name='Manga', is_discontinued=False, quantity__gt=0)
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

        genres = Genre.objects.filter(categories__name='Manga')
        
        if genre_filters:
            if self.request.htmx:
                self.template_name = "partials/book_card.html"
                for genre in genre_filters:
                    mangas = mangas.filter(book__series__genres__name=genre.capitalize())
            else:
                for genre in genre_filters:
                    mangas = mangas.filter(book__series__genres__name=genre.capitalize())
        if is_featured_list:
            if self.request.htmx:
                self.template_name = "partials/book_card.html"
                for is_featured in is_featured_list:
                    mangas = mangas.filter(book__series__genres__name=bool(is_featured))
            else:
                for genre in genre_filters:
                    mangas = mangas.filter(book__series__genres__name=bool(is_featured))
        if format_list:
            if self.request.htmx:
                self.template_name = "partials/book_card.html"
                for format in format_list:
                    mangas = mangas.filter(book__series__genres__name=format.capitalize())
            else:
                for genre in genre_filters:
                    mangas = mangas.filter(book__series__genres__name=format.capitalize())
        
        context['books'] = mangas
        context['genres'] = genres
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
