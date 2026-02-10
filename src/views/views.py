from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.views import generic
from django.contrib.auth import login
from src.models import Series, Sku, BookAnalyticsDaily
from ..forms import CustomUserCreationForm
from datetime import date, timedelta
from django.db.models import F

# Create your views here.

class IndexView(generic.TemplateView):
    template_name = 'src/index.html'
    yesterday = date.today() - timedelta(days=1)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        manga = Sku.objects.filter(book__series__category__name='Manga', 
                                   book__is_featured=True).order_by('book__series', '-published_at', 'price_usd').distinct('book__series')
        comic = Sku.objects.filter(book__series__category__name='Comic', 
                                   book__is_featured=True).order_by('book__series', '-published_at', 'price_usd').distinct('book__series')
        trending = (BookAnalyticsDaily.objects.filter(created_at=self.yesterday)
                    .select_related('sku__book')
                    .prefetch_related('sku__book__authors')
                    .only(
                        'sku__book__title',
                        'sku__price_usd',
                        'sku__format',
                        'sku__isbn_number',
                        'sku__book__authors__name'
                    )
                    .annotate(
                                    total_metrics=F('view_count') + F('purchase_count') + F('add_to_cart_count')
                                    ).order_by('-total_metrics')[:10]
        )
        context['manga_sku_list'] = manga
        context['comic_sku_list'] = comic
        context['trending'] = trending
        return context

class ComicListView(generic.ListView):
    model = Sku
    template_name = 'src/comic_list.html'
    context_object_name = 'comics'

    def get_queryset(self):
        comics = Sku.objects.filter(book__series__category__name='Comic').order_by('book__title', 'price_usd').distinct('book__title').prefetch_related('book')
        return comics
    
class MangaListView(generic.ListView):
    model = Sku
    template_name = 'src/manga_list.html'
    context_object_name = 'mangas'

    def get_queryset(self):
        mangas = Sku.objects.filter(book__series__category__name='Manga').order_by('book__title', 'price_usd').distinct('book__title').prefetch_related('book')
        return mangas
        
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

class SeriesDetailView(generic.DetailView):
    model = Series
    template_name = 'src/series_detail.html'
    context_object_name = 'series'

    def get_queryset(self):
        return super().get_queryset().prefetch_related('books__sku')

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
