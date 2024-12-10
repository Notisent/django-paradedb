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
