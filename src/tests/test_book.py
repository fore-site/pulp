from django.test import TestCase
from django.urls import reverse
from ..models import Series, Book
from django.utils.text import slugify

def create_book(series: str, series_type: str, title: str, description: str):
    """
    Create a new issue/volume with the given series, title of the book and description of the book
    """
    Series.objects.create(title=series, series_type=series_type)
    series = Series.objects.get(title=series)
    return Book.objects.create(series=series, title=title, description=description)

class BookIndexViewTest(TestCase):
    def test_no_comic(self):
        """ If no comic exist, an appropriate message is displayed"""
        manga = create_book('Bleach', 'Manga', 'Bleach Volume 3', 'Adventures of Ichigo')
        
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No comic is available')
        self.assertQuerySetEqual(response.context['comic_list'], [])    
        self.assertQuerySetEqual(response.context['manga_list'], [manga])    
        

    def test_no_manga(self):
        """ If no manga exist, an appropriate message is displayed"""
        comic = create_book('Superman', 'Comic', 'Superman Issue #4', 'Adventures of Superman')
        
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No manga is available')
        self.assertQuerySetEqual(response.context['manga_list'], [])
        self.assertQuerySetEqual(response.context['comic_list'], [comic])

    def test_comic_and_manga_displayed(self):
        "Comic issues and manga volumes are displayed on index page"
        comic = create_book('Batman', 'Comic', 'Batman Issue #2', 'Adventures of Batman')
        manga = create_book('Attack on titan', 'Manga', 'Attack on titan Volume 2', 'Adventures of Eren')
        
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['comic_list'], [comic])
        self.assertQuerySetEqual(response.context['manga_list'], [manga])
    
    def test_no_manga_and_comic_displayed(self):
        "No comic and manga are displayed on index page"
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No manga is available')
        self.assertContains(response, 'No comic is available')
        self.assertQuerySetEqual(response.context['manga_list'], [])
        self.assertQuerySetEqual(response.context['comic_list'], [])

class BookDetailViewTest(TestCase):
    def test_manga_displayed(self):
        "Manga is displayed from detail view"
        manga = create_book('Attack on titan', 'Manga', 'Attack on titan Volume 2', 'Adventures of Eren')
        
        response = self.client.get(reverse('book_detail', args=(slugify(manga.series.title), manga.id)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, manga.title)

    def test_comic_displayed(self):
        "Comic is displayed from detail view"
        comic = create_book('Batman', 'Comic', 'Batman Issue #2', 'Adventures of Batman')
        
        url = reverse('book_detail', args=(slugify(comic.series.title), comic.id))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, comic.title)