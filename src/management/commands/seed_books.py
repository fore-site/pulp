from django.core.management.base import BaseCommand
from django.db.models import Sum
from faker import Faker
import random
from decimal import Decimal, ROUND_HALF_UP
from src.models.product import Series
from ...models import Book, Category, Genre, Author, Publisher, Sku, Rating
from ..test_data import SERIES
from collections import defaultdict
from django.db import transaction
from datetime import datetime

fake = Faker()

CATEGORY = ['Manga', 'Comic']

MANGA_GENRES = ['Action', 'Adventure', 'Biography', 'Comedy', 'Cooking', 'Drama', 
          'Fantasy', 'Harem', 'Historical', 'Horror', 'Josei', 'Music', 'Mystery', 
          'Psychological', 'Romance', 'School', 'Sci-Fi', 'Seinen', 'Shonen', 
          'Shoujo', 'Slice of Life', 'Sports', 'Superhero', 'Supernatural', 'Thriller'
]

COMIC_GENRES = ['Action', 'Adventure', 'Biography', 'Comedy', 'Crime', 'Drama', 'Fantasy', 'Historical', 
                'Horror', 'Mystery', 'Parody', 'Political', 'Romance', 'Sci-Fi', 'Slice of Life', 'Superhero', 
                'Supernatural', 'Thriller', 'Western'
]

GENRES = list(set(MANGA_GENRES + COMIC_GENRES))

FORMATS = ['Hardcover', 'Paperback', 'Digital']

class Command(BaseCommand):
    help = "Seed database with comic/manga data"

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=1000)

    def handle(self, *args, **kwargs):
        with transaction.atomic():
            count = kwargs['count']
            # Prefetch genres, authors, publishers, categories
            genre_objs = {g.name: g for g in Genre.objects.all()}
            author_objs = {a.name: a for a in Author.objects.all()}
            publisher_objs = {p.name: p for p in Publisher.objects.all()}
            category_objs = {c.name: c for c in Category.objects.all()}

            # Create missing genres, authors, publishers, categories
            for genre in GENRES:
                if genre not in genre_objs:
                    genre_objs[genre], _ = Genre.objects.get_or_create(name=genre)
            for category in CATEGORY:
                if category not in category_objs:
                    category_objs[category], _ = Category.objects.get_or_create(name=category)

            # Link categories to their genres
            manga_genres = [genre_objs[g] for g in MANGA_GENRES if g in genre_objs]
            comic_genres = [genre_objs[g] for g in COMIC_GENRES if g in genre_objs]
            for cat_name, cat_obj in category_objs.items():
                if cat_name == 'Manga':
                    cat_obj.genres.set(manga_genres)
                elif cat_name == 'Comic':
                    cat_obj.genres.set(comic_genres)

            # Prepare Series
            series_to_create = []
            for series_data in SERIES:
                cat = category_objs[series_data['category']]
                series_to_create.append(Series(title=series_data['title'], category=cat, description=series_data['description']))
            Series.objects.bulk_create(series_to_create, ignore_conflicts=True)
            series_objs = {s.title: s for s in Series.objects.all()}

            # Many-to-many for genres
            for series_data in SERIES:
                s = series_objs[series_data['title']]
                genre_list = [genre_objs[g] for g in series_data['genres'] if g in genre_objs]
                s.genres.add(*genre_list)

            # Prepare Books
            books_to_create = []
            book_author_map = defaultdict(list)
            for series_data in SERIES:
                s = series_objs[series_data['title']]
                for i in range(1, 21):
                    book_title = f'{s.title} Vol. {i}'
                    b = Book(series=s, title=book_title, trending_score=random.randint(1,100), bestseller_score=random.randint(1,100), page_count=f"{random.randint(150, 400)}")
                    books_to_create.append(b)
                    for author_name in series_data['authors']:
                        if author_name not in author_objs:
                            author_objs[author_name] = Author.objects.create(name=author_name)
                        book_author_map[book_title].append(author_objs[author_name])
            Book.objects.bulk_create(books_to_create, ignore_conflicts=True)
            book_objs = {b.title: b for b in Book.objects.all()}

            # Many-to-many for authors
            for book_title, authors in book_author_map.items():
                b = book_objs[book_title]
                b.authors.add(*authors)

            # Prepare SKUs
            skus_to_create = []
            for series_data in SERIES:
                s = series_objs[series_data['title']]
                for i in range(1, 21):
                    book_title = f'{s.title} Vol. {i}'
                    b = book_objs[book_title]
                    for format in FORMATS:
                        publisher_name = series_data['publisher']
                        if publisher_name not in publisher_objs:
                            publisher_objs[publisher_name] = Publisher.objects.create(name=publisher_name)
                        sku = Sku(
                            book=b,
                            code=f'{s.title[:3].upper()}-{publisher_name[:3].upper().strip()}-{format[:3].upper()}-{i:03d}',
                            publisher=publisher_objs[publisher_name],
                            isbn_number=f'978-{random.randint(1000000000, 9999999999)}',
                            format=format,
                            published_at=fake.date_between(start_date=datetime.fromisoformat(series_data['start_date']), end_date=datetime.fromisoformat(series_data['end_date']))
                        )
                        if format == 'Hardcover':
                            sku.price = Decimal(random.randrange(35000, 50000, 100))
                            sku.discount_percent = random.randrange(0, 10, 5)
                            sku.quantity = random.randrange(0, 500)
                            sku.dimensions = f"{random.randint(15, 25)}x{random.randint(20, 30)} cm"
                        elif format == 'Paperback':
                            sku.price = Decimal(random.randrange(25000, 35000, 100))
                            sku.discount_percent = random.randrange(0, 50, 5)
                            sku.quantity = random.randrange(0, 1000)
                            sku.dimensions = f"{random.randint(10, 20)}x{random.randint(15, 25)} cm"
                        else:
                            sku.quantity = None
                            sku.price = Decimal(random.randrange(20000, 25000))
                            sku.file_size = f'{random.randint(1, 500)} MB'
                        skus_to_create.append(sku)
            Sku.objects.bulk_create(skus_to_create, ignore_conflicts=True)

            # Prepare Ratings
            ratings_to_create = []
            for b in Book.objects.all():
                for _ in range(random.randint(21,51)):
                    ratings_to_create.append(Rating(book=b, user=None, rating_value=random.randint(1,5)))
            Rating.objects.bulk_create(ratings_to_create, ignore_conflicts=True)

            # Calculate reviewer_count and average_rating
            for b in Book.objects.all():
                reviewer_count = Rating.objects.filter(book=b).count()
                total_rating = Rating.objects.filter(book=b).aggregate(total=Sum('rating_value'))['total'] or 0
                average_rating = Decimal(str(total_rating / reviewer_count)).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP) if reviewer_count else Decimal('0.0')
                b.reviewer_count = reviewer_count
                b.average_rating = average_rating
                b.save()

            # Feature flag
            for b in Book.objects.filter(title__endswith='Vol. 20'):
                b.is_featured = random.choice([True, False])
                b.save()
