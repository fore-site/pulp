from django.db import models

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
    cover_image = models.ImageField(upload_to='src/images', null=True, default=None)
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
    cover_image = models.ImageField(upload_to='src/images', null=True, default=None)
    is_featured = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'books'

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
    quantity = models.PositiveIntegerField()
    format = models.CharField(max_length=9, choices=BookFormat)
    page_count = models.CharField(max_length=255)
    dimensions = models.CharField(blank=True, max_length=255, help_text='Dimensions of hardcover or paperback formats, otherwise empty')
    file_size = models.CharField(blank=True, max_length=50, help_text='Download size of digital format, otherwise empty')
    language = models.CharField(max_length=255, help_text='Language edition of the book')
    published_at = models.DateField()
    is_shipping_free = models.BooleanField(default=False)
    is_discontinued = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.code

    class Meta:
        db_table = 'sku'
        verbose_name_plural = 'Sku'

class BookEvent(models.Model):

    class EventTypes(models.TextChoices):
        view = 'view'
        add_to_cart = 'add_to_cart'
        purchase = 'purchase'

    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    sku = models.ForeignKey(Sku, on_delete=models.CASCADE)
    event_type = models.CharField(max_length=11, choices=EventTypes)

    def __str__(self):
        return self.event_type

    class Meta:
        db_table = 'book_events'

class BookAnalyticsDaily(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    sku = models.ForeignKey(Sku, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    view_count = models.PositiveBigIntegerField()
    add_to_cart_count = models.PositiveBigIntegerField()
    purchase_count = models.PositiveBigIntegerField()

    def __str__(self):
        return f'view_count: {self.view_count}, add_to_cart_count: {self.add_to_cart_count}, purchase_count: {self.purchase_count}'

    class Meta:
        db_table = 'book_analytics_daily'
        verbose_name_plural = 'Book Analytics Daily'