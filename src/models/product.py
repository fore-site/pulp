from django.db import models
from django.conf import settings
from django.core.validators import MaxValueValidator
from decimal import Decimal

class Genre(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'genre'

class Category(models.Model):
    name = models.CharField(max_length=255)
    genres = models.ManyToManyField(Genre, related_name='categories')

    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'category'
        verbose_name_plural = 'categories'

class Series(models.Model):
    title = models.CharField(max_length=255, unique=True)
    category = models.ForeignKey(Category, on_delete=models.RESTRICT, related_name='series', null=True)
    genres = models.ManyToManyField(Genre, related_name='series')
    description = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to='covers', null=True, blank=True, default=None)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'series'
        verbose_name_plural = 'Series'

class Author(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'authors'

class Publisher(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'publishers'

class Book(models.Model):
    series = models.ForeignKey(Series, null=True, blank=True, on_delete=models.RESTRICT, related_name='books')
    title = models.CharField(max_length=255)
    authors = models.ManyToManyField(Author)
    description = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to='covers', null=True, blank=True, default=None)
    is_featured = models.BooleanField(default=False)
    is_shipping_free = models.BooleanField(default=False)
    trending_score = models.PositiveIntegerField(default=0, blank=True)
    bestseller_score = models.PositiveIntegerField(default=0, blank=True)
    average_rating = models.DecimalField(default=0, blank=True, max_digits=2, decimal_places=1)
    reviewer_count = models.PositiveIntegerField(default=0, blank=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'books'

class Ratings(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='rating')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    rating_value = models.PositiveSmallIntegerField(default=0, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.rating_value}/5 book ID{self.book} rated by user ID {self.user}"

    class Meta:
        db_table = 'ratings'
        unique_together = ('book', 'user')


class Sku(models.Model):

    class BookFormat(models.TextChoices):
        Hardcover = 'Hardcover',
        Paperback = 'Paperback',
        Digital = 'Digital'

    book = models.ForeignKey(Book, on_delete=models.RESTRICT, related_name='sku')
    code = models.CharField(max_length=30, unique=True)
    publisher = models.ForeignKey(Publisher, on_delete=models.RESTRICT, related_name='sku')
    isbn_number = models.CharField(max_length=14, unique=True, help_text='isbn 13 number for the book variant')
    price_usd = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percent = models.PositiveSmallIntegerField(default=0, blank=True, validators=[MaxValueValidator(100)])
    quantity = models.PositiveIntegerField(default=0, blank=True)
    format = models.CharField(max_length=9, choices=BookFormat)
    page_count = models.CharField(max_length=255)
    dimensions = models.CharField(blank=True, max_length=255, help_text='Dimensions of hardcover or paperback formats, otherwise empty')
    file_size = models.CharField(blank=True, max_length=50, help_text='Download size of digital format, otherwise empty')
    published_at = models.DateField()
    is_discontinued = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.code
    
    @property
    def has_discount(self):
        return self.discount_percent > 0

    @property
    def discounted_price(self) -> models.DecimalField:
        """Calculates and returns discounted price"""
        if self.has_discount:
            discount_amount = self.price_usd * (Decimal(self.price_usd) / Decimal(100))
            return (self.price_usd - discount_amount).quantize(Decimal('0.01'))
        return self.price_usd

    class Meta:
        db_table = 'sku'
        verbose_name_plural = 'Sku'

class BookEvent(models.Model):

    class EventTypes(models.TextChoices):
        view = 'view'
        add_to_cart = 'add_to_cart'
        purchase = 'purchase'

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    sku = models.ForeignKey(Sku, on_delete=models.CASCADE)
    event_type = models.CharField(max_length=11, choices=EventTypes)

    def __str__(self):
        return self.event_type

    class Meta:
        db_table = 'book_events'

class BookAnalyticsDaily(models.Model):
    book = models.ForeignKey(Book, null=True, default=None, on_delete=models.CASCADE, related_name = 'book_analytics')
    sku = models.ForeignKey(Sku, on_delete=models.CASCADE, related_name='book_analytics')
    created_at = models.DateField(help_text='indicates the date/day the analytics is collected for, not the date this row is created.')
    view_count = models.PositiveIntegerField()
    add_to_cart_count = models.PositiveIntegerField()
    purchase_count = models.PositiveIntegerField()

    def __str__(self):
        return f'Analytics ID {self.id}'

    class Meta:
        indexes = [
            models.Index(fields=('created_at', 'sku'))
        ]
        db_table = 'book_analytics_daily'
        verbose_name_plural = 'Book Analytics Daily'
        unique_together = ('sku', 'created_at')