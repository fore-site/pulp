from django.core.management.base import BaseCommand
from src.models import BookAnalyticsDaily, BookEvent, Sku
from django.db.models import Count, Q, F
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

today = timezone.now().replace(hour=0, second=0, minute=0, microsecond=0)
yesterday = today - timedelta(days=1)

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

        # TRANSFER DATA TO ANALYTICS TABLE
        with transaction.atomic():
            for entry in daily_stats:

                # FETCH EXISTING ROW OR CREATE NEW ROW
                obj, _ = BookAnalyticsDaily.objects.get_or_create(
                    sku=entry['sku'],
                    created_at=yesterday.date(),
                    defaults = {
                        'view_count': 0,
                        'purchase_count': 0,
                        'add_to_cart_count': 0
                    })

                # UPDATE THE FETCHED OR CREATED ROW BY INCREMENTING ITS COUNT VALUES - THIS LOGIC IS INCASE THIS SCRIPT IS RUN MORE THAN ONCE IN A DAY
                BookAnalyticsDaily.objects.filter(
                    pk=obj.pk).update(
                        view_count = F('view_count') + entry['views'],
                        purchase_count = F('purchase_count') + entry['purchases'],
                        add_to_cart_count = F('add_to_cart_count') + entry['carts']
                        )
            
            # DELETE THE RECORDED EVENTS TO KEEP EVENT TABLE CLEAN
            deleted_events_count, _ = BookEvent.objects.filter(
                created_at__gte=yesterday,
                created_at__lt=today
            ).delete()

            self.stdout.write(self.style.SUCCESS(f'Successfully moved events data for {yesterday.date()} into analytics table. {deleted_events_count} recorded and deleted.'))