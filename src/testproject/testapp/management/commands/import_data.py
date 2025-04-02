import json
import os

import tqdm
import fileinput
from django.core.management.base import BaseCommand, CommandError

from ...models import Book


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--path", type=str)

    def handle(self, **options):
        if not options.get("path") or not os.path.exists(options.get("path")):
            raise CommandError(
                "Download the Goodreads dataset here "
                "https://mcauleylab.ucsd.edu/public_datasets/gdrive/"
                "goodreads/goodreads_books.json.gz then "
                "gunzip it and point --path to the decompressed json "
                "file"
            )

        Book.objects.all().delete()
        line_count = sum(1 for line in fileinput.input(options.get("path")))

        prog = tqdm.tqdm(total=line_count)
        with open(options.get("path"), "r") as f:
            i = 0
            books = []
            while line := f.readline():
                prog.update(1)
                row = json.loads(line)
                language_code = row.get("language_code")
                if language_code.lower() in ("eng", "en-gb", "en-us", "en-ca", "en-au"):
                    i += 1
                    books.append(
                        Book(
                            title=row.get("title")[:255],
                            isbn=row.get("isbn13", row.get("isbn", "")),
                            average_rating=row.get("average_rating") or None,
                            ratings_count=row.get("ratings_count", 0) or 0,
                            description=row.get("description"),
                            url=row.get("url", row.get("link", "")),
                            image_url=row.get("image_url"),
                            pages=row.get("num_pages") or None,
                            publication_year=row.get("publication_year") or None,
                            ext_id=row.get("book_id"),
                        )
                    )
                    if i >= 10_000:
                        Book.objects.bulk_create(books)
                        books = []
                        i = 0

            if books:
                Book.objects.bulk_create(books)
