from django.core.management.base import BaseCommand
from src.models import User, Series, Sku
import uuid

class Command(BaseCommand):
    def handle(self, *args, **options):
        all_users = User.objects.all()
        all_series = Series.objects.all()
        all_sku = Sku.objects.all()

        for user in all_users:
            rand_id = uuid.uuid4()
            updated = User.objects.filter(pk=user.id).update(public_id=rand_id)
            self.stdout.write(self.style.SUCCESS(f'{updated} user updated'))
        for series in all_series:
            rand_id = uuid.uuid4()
            updated = Series.objects.filter(pk=series.id).update(public_id=rand_id)
            self.stdout.write(self.style.SUCCESS(f'{updated} series updated'))
        for sku in all_sku:
            rand_id = uuid.uuid4()
            updated = Sku.objects.filter(pk=sku.id).update(public_id=rand_id)
            self.stdout.write(self.style.SUCCESS(f'{updated} sku updated'))