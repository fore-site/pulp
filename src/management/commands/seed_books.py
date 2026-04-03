from django.core.management.base import BaseCommand
from django.db.models import Sum
from faker import Faker
import random
from decimal import Decimal, ROUND_HALF_UP
from src.models.product import Series
from ...models import Book, Category, Genre, Author, Publisher, Sku, Rating
from ..test_data import SERIES
from collections import defaultdict

fake = Faker()

CATEGORY = ['Manga', 'Comic']

GENRES = [
    'Action', 'Adventure', 'Comedy', 'Superhero', 'Fantasy', 'Horror', 'Mystery', 'Romance', 'Sci-Fi', 'Thriller', 'Shonen', 'Shoujo', 'Seinen',
    'Slice of Life', 'Drama', 'Sports', 'Martial Arts', 'Psychological', 'Historical', 'School', 'Mecha', 'Josei', 'Shojo Ai', 'Shonen Ai',
    'Ecchi', 'Seinen', 'Isekai', 'Magic', 'Music', 'Parody', 'Samurai', 'Vampire', 'Demons', 'Military', 'Police', 'Game', 'Space', 'Kids',
    'Western', 'Crime', 'Biography', 'Science', 'Detective', 'Family', 'Friendship', 'Tragedy', 'War', 'Medical', 'Cooking', 'Business', 'Romantic Comedy',
    'Supernatural', 'Mystery Thriller', 'Cyberpunk', 'Post-Apocalyptic', 'Steampunk', 'Harem', 'Reverse Harem', 'Yaoi', 'Yuri', 'Sports', 'Magic Girl', 'Adventure Comedy',
    'Dark Fantasy', 'Heroic Fantasy', 'Urban Fantasy', 'Mythology', 'Political', 'Satire', 'Espionage', 'Horror Comedy', 'Zombie', 'Alien', 'Time Travel', 'Survival', 'School Life',
    'Music', 'Game', 'Paranormal', 'Psychological Thriller', 'Romantic Drama', 'Historical Drama', 'Science Fiction', 'Fantasy Adventure', 'Superpower', 'Dystopian', 'Coming of Age', 'Epic', 'Legend', 'Myth', 'Folklore', 'Magic Realism', 'Sports Drama', 'Detective', 'Legal', 'Medical Drama', 'Slice of Life Comedy', 'Family Drama', 'Friendship Drama', 'Tragedy Drama', 'War Drama', 'Cooking Drama', 'Business Drama', 'Romantic Comedy Drama', 'Supernatural Drama', 'Mystery Thriller Drama', 'Cyberpunk Drama', 'Post-Apocalyptic Drama', 'Steampunk Drama', 'Harem Drama', 'Reverse Harem Drama', 'Yaoi Drama', 'Yuri Drama', 'Magic Girl Drama', 'Adventure Comedy Drama', 'Dark Fantasy Drama', 'Heroic Fantasy Drama', 'Urban Fantasy Drama', 'Mythology Drama', 'Political Drama', 'Satire Drama', 'Espionage Drama', 'Horror Comedy Drama', 'Zombie Drama', 'Alien Drama', 'Time Travel Drama', 'Survival Drama', 'School Life Drama', 'Music Drama', 'Game Drama', 'Paranormal Drama', 'Psychological Thriller Drama', 'Romantic Drama Drama', 'Historical Drama Drama', 'Science Fiction Drama', 'Fantasy Adventure Drama', 'Superpower Drama', 'Dystopian Drama', 'Coming of Age Drama', 'Epic Drama', 'Legend Drama', 'Myth Drama', 'Folklore Drama', 'Magic Realism Drama'
]

FORMATS = ['Hardcover', 'Paperback', 'Digital']

class Command(BaseCommand):
    help = "Seed database with comic/manga data"

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=1000)

    def handle(self, *args, **kwargs):
        count = kwargs['count']
        # Prefetch genres, authors, publishers, categories
        genre_objs = {g.name: g for g in Genre.objects.all()}
        author_objs = {a.name: a for a in Author.objects.all()}
        publisher_objs = {p.name: p for p in Publisher.objects.all()}
        category_objs = {c.name: c for c in Category.objects.all()}

        # Create missing genres, authors, publishers, categories
        for genre in GENRES:
            if genre not in genre_objs:
                genre_objs[genre] = Genre.objects.create(name=genre)
        for category in CATEGORY:
            if category not in category_objs:
                category_objs[category] = Category.objects.create(name=category)

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
                        published_at=fake.date_between(start_date=series_data['start_date'], end_date=series_data['end_date'])
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
