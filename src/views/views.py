from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.views import generic
from src.models import User, Series, Book
# Create your views here.

class IndexView(generic.ListView):
    template_name = 'src/index.html'
    context_object_name = 'manga_comic_list'

    def get_queryset(self):
        manga = Book.objects.filter(series__series_type='Manga')
        comic = Book.objects.filter(series__series_type='Comic')
        return manga | comic

class DetailView(generic.DetailView):
    model = Book
    template_name = 'src/detail.html'

def home(request, user_id=None):
    if user_id:
        user = get_object_or_404(User)
        return render(request, 'src/index.html', {"user": user})
    return render(request, 'src/index.html')

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

def manga(request):
    context = {'manga_list': Series.objects.order_by('id')}
    print(context)
    return render(request, "src/listing.html", context)

def comic(request, comic_id):
    response = 'This is comic %s.'
    return HttpResponse(response % comic_id)

def order(request, id):
    return HttpResponse('You have placed an order on %s.' % id)
