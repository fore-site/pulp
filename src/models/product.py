from django.db import models

class Genre(models.Model):
    genre_name = models.CharField(max_length=255)
    image_url = models.TextField(blank=True)

    def __str__(self):
        return self.genre_name

    class Meta:
        db_table = 'genre'

class Series(models.Model):
    title = models.CharField(max_length=255, unique=True)
    image_url = models.TextField(blank=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'series'

class Books(models.Model):
    series = models.ForeignKey(Series, null=True, blank=True, on_delete=models.RESTRICT)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'books'

class Authors(models.Model):
    author_name = models.CharField(max_length=255)
    bio = models.CharField(max_length=255)

    def __str__(self):
        return self.author_name

    class Meta:
        db_table = 'authors'

class Publishers(models.Model):
    publisher_name = models.CharField(max_length=255)
    contact = models.CharField(max_length=255)
    
    def __str__(self):
        return self.publisher_name

    class Meta:
        db_table = 'publishers'

class BooksAuthorsPivot(models.Model):
    book = models.ForeignKey(Books, on_delete=models.DO_NOTHING)
    author = models.ForeignKey(Authors, on_delete=models.RESTRICT)
    author_role = models.CharField(max_length=255)

    class Meta:
        db_table = 'books_authors_pivot'

class BooksPublishersPivot(models.Model):
    book = models.ForeignKey(Books, on_delete=models.DO_NOTHING)
    publisher = models.ForeignKey(Publishers, on_delete=models.RESTRICT)

    class Meta:
        db_table = 'books_publishers_pivot'

class GenreBooksPivot(models.Model):
    genre = models.ForeignKey(Genre, null=True, on_delete=models.SET_NULL)
    book = models.ForeignKey(Books, on_delete=models.DO_NOTHING)

    class Meta:
        db_table = 'genre_books_pivot'
    
class Sku(models.Model):

    class BookFormat(models.TextChoices):
        Hardcover = 'Hardcover',
        Paperback = 'Paperback',
        Digital = 'Digital'

    book = models.ForeignKey(Books, on_delete=models.RESTRICT)
    code = models.CharField(max_length=30, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(null=True, blank=True)
    format = models.CharField(max_length=9, choices=BookFormat)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.code

    class Meta:
        db_table = 'sku'