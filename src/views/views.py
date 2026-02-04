from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.views import generic
from src.models import User, Series, Book
# Create your views here.

class IndexView(generic.TemplateView):
    template_name = 'src/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        manga = Book.objects.filter(series__series_type='Manga').order_by('series', 'created_at').distinct('series')
        comic = Book.objects.filter(series__series_type='Comic').order_by('series', 'created_at').distinct('series')
        user_id = self.kwargs.get('user_id')
        
        if user_id:
            context['user'] = get_object_or_404(User, pk=user_id)

        context['manga_list'] = manga
        context['comic_list'] = comic
        return context

class BookListView(generic.ListView):
    model = Book

class DetailView(generic.DetailView):
    model = Book
    template_name = 'src/detail.html'

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
