from django.db import models

class Carrier(models.Model):
    name = models.CharField(max_length=255, help_text='Name of the logistics provider')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'carriers'

class PickUpLocation(models.Model):
    pickup_state = models.CharField(max_length=255)
    pickup_city = models.CharField(max_length=255)
    description = models.CharField(max_length=300, help_text='full pickup location description')

    def __str__(self):
        return self.description
    
    class Meta:
        db_table = 'pickup_locations'
        verbose_name_plural = 'Pickup locations'