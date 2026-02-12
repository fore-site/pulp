from django.core.management.base import BaseCommand
from src.models import BookAnalyticsDaily, BookEvent, Sku, Book
from django.db.models import Count, Q, F
from django.db import transaction
from django.utils import timezone
from datetime import timedelta, date

today = timezone.now().replace(hour=0, second=0, minute=0, microsecond=0)
yesterday = today - timedelta(days=2)
trending_days = (today - timedelta(days=7)).date()
last_thirty_days = (today - timedelta(days=30)).date()

class Command(BaseCommand):
    def handle(self, *args, **options):
        """Aggregate and transfer events data into analytics table"""

        # AGGREGATE EVENTS DATA
        # daily_stats = (BookEvent.objects.filter(
        #     created_at__gte=yesterday,
        #     created_at__lt=today)
        #     .values('sku')
        #     .annotate(
        #         views=Count('id', filter=Q(event_type='view')),
        #         purchases=Count('id', filter=Q(event_type='purchase')),
        #         carts=Count('id', filter=Q(event_type='add_to_cart'))
        #     )
        # )

        # IF SCRIPT IS RUN MORE THAN ONCE A DAY
        # if not daily_stats:
        #     return self.stdout.write(self.style.NOTICE("There are no recorded events for yesterday. This may be due to a successful data transfer to the analytics table"))
        
        # TRANSFER DATA TO ANALYTICS TABLE
        # with transaction.atomic():
        #     for entry in daily_stats:
        #         BookAnalyticsDaily.objects.update_or_create(
        #             sku = Sku.objects.get(pk=entry['sku']),
        #             created_at = yesterday.date(),
        #             defaults= {
        #                 'view_count': entry['views'],
        #                 'purchase_count': entry['purchases'],
        #                 'add_to_cart_count': entry['carts']
        #             }
        #                 )
                
                #GET ROWS OF SKU AND TOTAL METRICS FOR YESTERDAY
        yesterday_trends = BookAnalyticsDaily.objects.filter(created_at=yesterday.date()).annotate(
                total_metrics = F('view_count') + F('purchase_count') + F('add_to_cart_count')
            ).values(
                'sku',
                'created_at',
                'total_metrics'
            )
        for trend in yesterday_trends:
            print(trend['total_metrics'])
            
            # DELETE THE RECORDED EVENTS TO KEEP EVENT TABLE CLEAN
            # deleted_events_count, _ = BookEvent.objects.filter(
            #     created_at__gte=yesterday,
            #     created_at__lt=today
            # ).delete()

            # self.stdout.write(self.style.SUCCESS(f'Successfully moved events data for {yesterday.date()} into analytics table. {deleted_events_count} recorded and deleted.'))