from django.test import TestCase
from django.urls import reverse
from ..models import Series, Book, Category, Genre, Sku, Publisher
from django.utils.text import slugify
from django.utils import timezone

def create_sku(series: str, 
               category: str, 
               title: str, 
               genre: str, 
               code: str, 
               publisher_name: str,
               format: str,
               isbn_no: str) -> Sku:
    """
    Create a new issue/volume sku with the given series, title of the book and description of the book
    """
    series_category = Category.objects.create(name=category.capitalize())
    series_genre = Genre.objects.create(name=genre.capitalize())

    series_obj = Series.objects.create(title=series, category=series_category)
    series_obj.genres.add(series_genre)

    book = Book.objects.create(title=title, series=series_obj)
    publisher = Publisher.objects.create(name=publisher_name)

    return Sku.objects.create(book=book, 
                              code=code,
                              publisher=publisher,
                              price_usd=11.20,
                              format=format,
                              quantity=3,
                              isbn_number=isbn_no,
                              language='English',
                              published_at=timezone.datetime(year=1990, month=5, day=20))

class IndexViewTest(TestCase):
    def test_no_comic(self):
        """ If no comic exist, an appropriate message is displayed"""
        manga = create_sku('Bleach', 'Manga', 'Bleach Volume 3', 'Shonen', 'BCHKUBOVOL3', 'Viz Media', 'Hardcover', '974-1233445')
        
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No comic is available')
        self.assertQuerySetEqual(response.context['comic_sku_list'], [])    
        self.assertQuerySetEqual(response.context['manga_sku_list'], [manga])    
        

    def test_no_manga(self):
        """ If no manga exist, an appropriate message is displayed"""
        comic = create_sku('Superman', 'Comic', 'Superman Issue #4', 'Superhero', 'SUPCOMISS4', 'DC Comics', 'Digital', '974-2290394')
        
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No manga is available')
        self.assertQuerySetEqual(response.context['manga_sku_list'], [])
        self.assertQuerySetEqual(response.context['comic_sku_list'], [comic])

    def test_comic_and_manga_displayed(self):
        "Comic issues and manga volumes are displayed on index page"
        manga = create_sku('Bleach', 'Manga', 'Bleach Volume 3', 'Shonen', 'BCHKUBOVOL3', 'Viz Media', 'Hardcover', '974-1233445')
        comic = create_sku('Superman', 'Comic', 'Superman Issue #4', 'Superhero', 'SUPCOMISS4', 'DC Comics', 'Digital', '974-2290394')
        
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['comic_sku_list'], [comic])
        self.assertQuerySetEqual(response.context['manga_sku_list'], [manga])
    
    def test_no_manga_and_comic_displayed(self):
        "No comic and manga are displayed on index page"
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No manga is available')
        self.assertContains(response, 'No comic is available')
        self.assertQuerySetEqual(response.context['manga_sku_list'], [])
        self.assertQuerySetEqual(response.context['comic_sku_list'], [])

class ProductDetailViewTest(TestCase):
    def test_manga_displayed(self):
        "Manga is displayed from detail view"
        manga = create_sku('Bleach', 'Manga', 'Bleach Volume 3', 'Shonen', 'BCHKUBOVOL3', 'Viz Media', 'Hardcover', '974-1233445')
        
        response = self.client.get(reverse('product_detail', args=(slugify(manga.book.series.title), manga.id), query={"f": "Hardcover"}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, manga.book.title)

    def test_comic_displayed(self):
        "Comic is displayed from detail view"
        comic = create_sku('Superman', 'Comic', 'Superman Issue #4', 'Superhero', 'SUPCOMISS4', 'DC Comics', 'Digital', '974-2290394')
        
        url = reverse('product_detail', args=(slugify(comic.book.series.title), comic.id), query={"f": "Digital"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, comic.book.title)