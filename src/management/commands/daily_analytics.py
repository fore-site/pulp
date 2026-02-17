from django.core.management.base import BaseCommand
from src.models import BookAnalyticsDaily, BookEvent, Sku, Book
from django.db.models import Count, Q, F, Sum
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

today = timezone.now().replace(hour=0, second=0, minute=0, microsecond=0)
yesterday = today - timedelta(days=1)
last_thirty_days = (today - timedelta(days=30)).date()

class Command(BaseCommand):
    def handle(self, *args, **options):
        """Aggregate and transfer events data into analytics table"""

        # AGGREGATE EVENTS DATA
        daily_stats = (BookEvent.objects.filter(
            created_at__gte=yesterday,
            created_at__lt=today)
            .values('sku')
            .annotate(
                views=Count('id', filter=Q(event_type='view')),
                purchases=Count('id', filter=Q(event_type='purchase')),
                carts=Count('id', filter=Q(event_type='add_to_cart'))
            )
        )

        # IF SCRIPT IS RUN MORE THAN ONCE A DAY
        if not daily_stats:
            return self.stdout.write(self.style.NOTICE("There are no recorded events for yesterday. This may be due to a successful data transfer to the analytics table"))
        
        # TRANSFER DATA TO ANALYTICS TABLE
        with transaction.atomic():
            for entry in daily_stats:
                BookAnalyticsDaily.objects.update_or_create(
                    sku = Sku.objects.get(pk=entry['sku']),
                    created_at = yesterday.date(),
                    book = Book.objects.get(sku__id=entry['sku']),
                    defaults= {
                        'view_count': entry['views'],
                        'purchase_count': entry['purchases'],
                        'add_to_cart_count': entry['carts']
                    }
                        )
                
        # UPDATE THE TRENDING_SCORE COLUMN OF EACH BOOK WITH THE TOTAL METRICS STAT FROM THE ANALYTICS TABLE
            yesterday_trends = BookAnalyticsDaily.objects.filter(created_at=yesterday.date()).values('book').annotate(
                    total_metrics = Sum(F('view_count') + F('purchase_count') + F('add_to_cart_count'))
                ).order_by('-total_metrics')

            books_to_update = [] 
            books = Book.objects.filter(is_deleted=False)
            for book in books:
                for book_trend in yesterday_trends:
                    if book.id == book_trend['book']:
                        book.trending_score = book_trend['total_metrics']
                        books_to_update.append(book)
                        break
                    else:
                        pass

            rows_updated = Book.objects.bulk_update(books_to_update, ['trending_score'])
            self.stdout.write(self.style.SUCCESS(f'Updated trending_score on {rows_updated} rows in Book table'))

            # DELETE THE RECORDED EVENTS TO KEEP EVENT TABLE CLEAN
            deleted_events_count, _ = BookEvent.objects.filter(
                created_at__gte=yesterday,
                created_at__lt=today
            ).delete()

            self.stdout.write(self.style.SUCCESS(f'Successfully moved events data for {yesterday.date()} into analytics table. {deleted_events_count} recorded and deleted.'))

def update_bestseller():
    """Function that calculates aggregated purchase count on analytics table and updates as each book's bestseller_score. Returns total rows updated."""

    bestsellers = BookAnalyticsDaily.objects.filter(created_at__gte=last_thirty_days).values('book').annotate(
        bestseller_score=Sum('purchase_count')
    ).order_by('-bestseller_score')

    books_to_update = []
    books = Book.objects.filter(is_deleted=False)

    for book in books:
        for bestseller_book in bestsellers:
            if book.id == bestseller_book['book']:
                book.bestseller_score = bestseller_book['bestseller_score']
                books_to_update.append(book)
                break
    
    updated_rows = Book.objects.bulk_update(books_to_update, ['bestseller_score'])
    return updated_rows