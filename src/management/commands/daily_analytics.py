from django.core.management.base import BaseCommand
from src.models.product import BookAnalyticsDaily, BookEvent
from datetime import datetime, timedelta, time

today = datetime.combine(datetime.now(), time.min)
yesterday = today - timedelta(days=1)

class CustomCommand(BaseCommand):

    def handle(self, *args, **options):
        events = BookEvent.objects.filter()