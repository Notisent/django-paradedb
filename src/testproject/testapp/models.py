from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVector
from django.db import models

from paradedb.indexes import BM25Index


class Item(models.Model):
    name = models.CharField(max_length=127)
    description = models.TextField()
    alt_name = models.CharField(max_length=64, blank=True, null=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2)

    class Meta:
        ordering = ("-pk",)
        verbose_name = "Item"
        verbose_name_plural = "Items"

        indexes = [
            BM25Index(
                fields=["name", "alt_name", "description", "rating"],
                name="item_idx",
                stemmer="English",
            ),
            # The GinIndex is only here to run benchmarks against
            GinIndex(
                SearchVector("description", config="english"),
                name="search_vector_idx",
            ),
        ]

    def __str__(self):
        return self.name


class Review(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    added = models.DateTimeField(auto_now_add=True)
    review = models.TextField()

    class Meta:
        verbose_name = "Review"
        verbose_name_plural = "Reviews"
        ordering = ["-added"]

        indexes = [
            BM25Index(
                fields=["review"],
                name="review_idx",
            )
        ]

    def __str__(self):
        return self.item.__str__()


class Book(models.Model):
    title = models.CharField(max_length=512, blank=True)
    isbn = models.CharField(max_length=20, blank=True)
    average_rating = models.DecimalField(
        max_digits=3, decimal_places=2, blank=True, null=True
    )
    ratings_count = models.IntegerField()
    description = models.TextField(blank=True)
    url = models.URLField(max_length=1024)
    image_url = models.URLField(max_length=1024)
    pages = models.IntegerField(blank=True, null=True)
    publication_year = models.IntegerField(blank=True, null=True)
    ext_id = models.IntegerField()

    class Meta:
        ordering = ("-pk",)
        verbose_name = "Book"
        verbose_name_plural = "Books"

        indexes = [
            BM25Index(
                fields=["title", "isbn", "description", "publication_year"],
                name="book_idx",
                stemmer="English",
            ),
            # The GinIndex is only here to run benchmarks against
            GinIndex(
                SearchVector("title", "isbn", "description", config="english"),
                name="book_search_vector_idx",
            ),
        ]

    def __str__(self):
        return self.title


class BookReview(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    added = models.DateTimeField(auto_now_add=True)
    review = models.TextField()

    class Meta:
        verbose_name = "Book Review"
        verbose_name_plural = "Book Reviews"
        ordering = ["-added"]

        indexes = [
            BM25Index(
                fields=["review"],
                name="book_review_idx",
            )
        ]

    def __str__(self):
        return self.book.__str__()
