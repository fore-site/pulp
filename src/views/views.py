from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.views import generic
from src.models import User, Series, Book, Sku
# Create your views here.

class IndexView(generic.TemplateView):
    template_name = 'src/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        manga = Sku.objects.filter(book__series__series_type='Manga').order_by('book__series', '-published_at', 'price_usd').distinct('book__series')
        comic = Sku.objects.filter(book__series__series_type='Comic').order_by('book__series', '-published_at', 'price_usd').distinct('book__series')
        user_id = self.kwargs.get('user_id')
        
        if user_id:
            context['user'] = User.objects.filter(pk=user_id)

        context['manga_sku_list'] = manga
        context['comic_sku_list'] = comic
        return context

class BookListView(generic.ListView):
    model = Book
    template_name = 'src/listing.html'

class BookDetailView(generic.DetailView):
    model = Book
    template_name = 'src/product_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected_format = self.request.GET.get('f', 'digital')

        context['format'] = selected_format
        return context
    
class ProductDetailView(generic.DetailView):
    model = Sku
    template_name = 'src/product_detail.html'
    context_object_name = 'sku'

class SeriesIndexView(generic.ListView):
    model = Series
    template_name = 'src/series_index.html'

class SeriesDetailView(generic.DetailView):
    model = Series
    template_name = 'src/series_detail.html'
    context_object_name = 'series'

    def get_queryset(self):
        return super().get_queryset().prefetch_related('book')

def series_list(request, series_type):
    if series_type == 'comic':
        series_list = Series.objects.filter(series_type='comic').order_by('title')
        title = 'Comic'
    elif series_type == 'manga':
        series_list = Series.objects.filter(series_type='manga').order_by('title')
        title = 'Manga'
    context = {
        "series_list": series_list,
        "title": title
    }
    return render(request, 'src/series_list.html', context)

def signin(request):
    return render(request, 'src/login.html')

def signup(request):
    return render(request, 'src/signup.html')

def auth_signup(request, user_id):
    return HttpResponseRedirect(reverse('home', args=[user_id]))

def auth_signin(request, user_id):
    return HttpResponseRedirect(reverse('home', args=[user_id]))

def detail(request, manga_id):
        book = get_object_or_404(Series, pk=manga_id)
        return render(request, 'src/detail.html', {'comic': book})

def order(request, id):
    return HttpResponse('You have placed an order on %s.' % id)
