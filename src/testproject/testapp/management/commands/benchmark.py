import random
import time

from django.contrib.postgres.search import SearchQuery
from django.core.management.base import BaseCommand
from django.db import connection

from ...models import Book


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--queries", type=int, default=100)
        parser.add_argument(
            "--print-sample-queries", action="store_true", default=False
        )
        parser.add_argument("--print-explains", action="store_true", default=False)
        parser.add_argument("--samples", action="store", type=int, default=3)

    def handle(self, **options):
        print_sample_queries = options.get("print_sample_queries", False)
        print_explains = options.get("print_explains", False)
        samples = options.get("samples", 3)

        row_count = Book.objects.count()
        if row_count < 100:
            print(
                "Download and import benchmark data, see `python manage.py import_data`"
            )
            return

        rq = set()
        print("Building request terms queue")
        while len(rq) < 1000:
            books = Book.objects.only("description").order_by("?")[:100]
            try:
                for book in books:
                    for word in random.sample(book.description.lower().split(), 50):
                        if len(word) > 4 and word.isalpha():
                            rq.add(word)

                    if len(rq) >= 1000:
                        break

            except ValueError:
                pass

        rq = list(rq)[:1000]

        queries_count = options.get("queries")

        while Book.objects.count() > 50:
            row_count = Book.objects.count()

            print("#" * 100)
            print(f"Running tests against {row_count} rows")

            print("Pre-warming indexes and vacuuming")
            with connection.cursor() as cursor:
                cursor.execute("vacuum full testapp_book")
                cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_prewarm")
                cursor.execute("SELECT pg_prewarm('testapp_book')")
                cursor.execute("SELECT pg_prewarm('book_idx')")
                cursor.execute("SELECT pg_prewarm('book_search_vector_idx')")

            ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ##

            print(f"Testing TS Vector against {row_count} rows (best of {samples})")
            results = []
            for _ in range(samples):
                t = time.time()
                for i in range(queries_count):
                    w = rq[i % len(rq)]
                    w2 = rq[(i + 11) % len(rq)]

                    qs = (
                        Book.objects.filter(
                            vector_column=SearchQuery(
                                f"('{w}' | '{w2}')", search_type="raw"
                            )
                        )
                        .only("id")
                        .values_list("id", flat=True)[:100]
                    )
                    list(qs)  # force evaluation

                if i == 0 and print_sample_queries:
                    print(qs.query)
                if i == 0 and print_explains:
                    print(qs.explain())

                d = time.time() - t

                query_second = queries_count / d
                results.append(query_second)

            best = max(results)
            print(
                f"TSVector: ran {queries_count} queries in {queries_count / best} seconds ({best} q/s, best of {samples}"
            )
            print(
                f"\tmin: {min(results)}, max: {max(results)}, avg: {sum(results) / len(results)}"
            )

            time.sleep(1)

            ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ##

            print(f"Testing ParadeDB against {row_count} rows (best of {samples})")
            results = []
            for _ in range(samples):
                t = time.time()
                for i in range(queries_count):
                    w = rq[i % len(rq)]
                    w2 = rq[(i + 11) % len(rq)]
                    qs = (
                        Book.objects.filter(description__term_search=f"{w} {w2}")
                        .only("id")
                        .values_list("id", flat=True)[:100]
                    )
                    list(qs)  # force evaluation

                if i == 0 and print_sample_queries:
                    print(qs.query)
                if i == 0 and print_explains:
                    print(qs.explain())

                d = time.time() - t
                query_second = queries_count / d
                results.append(query_second)

            best = max(results)
            print(
                f"ParadeDB: ran {queries_count} queries in {queries_count / best} seconds ({best} q/s, best of {samples})"
            )
            print(
                f"\tmin: {min(results)}, max: {max(results)}, avg: {sum(results) / len(results)}"
            )

            ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ##

            print("Deleting 100'000 rows...")
            with connection.cursor() as cursor:
                cursor.execute(
                    "delete from testapp_book where id in (select id from testapp_book limit 100000)"
                )
