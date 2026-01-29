from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, Http404
from src.models.product import Series
# Create your views here.


def home(request):
    return HttpResponse('HELLO, You have reached the home page.')

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
