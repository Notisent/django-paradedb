import os
import random
import time

import tqdm

from django.core.management.base import BaseCommand
from django.db import connection

from ...models import Book


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--queries", type=int, default=10_000)
        parser.add_argument("--dump-sample-queries", action="store_true", default=False)

    def handle(self, **options):
        silent_tqdm = os.environ.get("SILENT_TQDM", False)
        dump_sample_queries = options.get("dump_sample_queries", False)
        queries_count = options.get("queries")
        if Book.objects.count() < 100:
            print(
                "Download and import benchmark data, see `python manage.py import_data`"
            )
            return

        print("Building request terms queue")

        rq = set()
        _wc = 0

        with tqdm.tqdm(total=1000) as bar:
            while len(rq) < 1000:
                book = Book.objects.order_by("?").first()
                _wc = len(rq)
                try:
                    for word in random.sample(book.description.lower().split(), 50):
                        if len(word) > 4 and word.isalpha():
                            rq.add(word)

                except ValueError:
                    pass

                bar.update(len(rq) - _wc)

        rq = list(rq)[:1000]

        print("Prewarming")
        with connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_prewarm")
            cursor.execute("SELECT pg_prewarm('testapp_book')")
            cursor.execute("SELECT pg_prewarm('book_idx')")
            cursor.execute("SELECT pg_prewarm('book_search_vector_idx')")

        ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ##
        # print(f"Running {queries_count} queries on Django icontains...")
        # t = time.time()
        # no_results = []
        # total_results = 0
        # for i in tqdm.tqdm(range(queries_count), disable=silent_tqdm):
        #     w = rq[i % len(rq)]
        #     w2 = rq[(i + 11) % len(rq)]

        #     qs = Book.objects.filter(
        #         Q(description__icontains=w) | Q(description__icontains=w2)
        #     )

        #     result_count = qs.count()
        #     total_results += result_count

        #     if result_count == 0:
        #         no_results.append(w)

        #     if i == 0 and dump_sample_queries:
        #         print(qs.query)

        # d = time.time() - t
        # print(
        #     f"Ran {queries_count} queries in {d} seconds ({queries_count / d} q/s), "
        #     f"{len(no_results)} had no results, average results per query: {total_results / i}"
        # )
        # print()

        # time.sleep(1)

        ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ##
        # print(
        #     f"Running {queries_count} queries on Django's contrib.postgres' ts_vector ..."
        # )
        # t = time.time()
        # no_results = []
        # total_results = 0
        # for i in tqdm.tqdm(range(queries_count), disable=silent_tqdm):
        #     w = rq[i % len(rq)]
        #     w2 = rq[(i + 11) % len(rq)]

        #     qs = Book.objects.annotate(
        #         search=SearchVector("description", config="english")
        #     ).filter(search=SearchQuery(f"('{w}' | '{w2}')", search_type="raw"))

        #     result_count = qs.count()
        #     total_results += result_count

        #     if result_count == 0:
        #         no_results.append(f"{w} {w2}")

        #     if i == 0 and dump_sample_queries:
        #         print(qs.query)

        # d = time.time() - t
        # print(
        #     f"Ran {queries_count} queries in {d} seconds ({queries_count / d} q/s), "
        #     f"{len(no_results)} had no results, average results per query: {total_results / i}"
        # )
        # print()
        # time.sleep(1)

        ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ##
        print(f"Running {queries_count} queries on ParadeDB's term_search ...")
        t = time.time()
        no_results = []
        total_results = 0

        for i in tqdm.tqdm(range(queries_count), disable=silent_tqdm):
            w = rq[i % len(rq)]
            w2 = rq[(i + 11) % len(rq)]
            qs = Book.objects.filter(description__term_search=f"{w} {w2}").only("id")

            result_count = qs.count()
            total_results += result_count

            if result_count == 0:
                no_results.append(f"{w} {w2}")

            if i == 0 and dump_sample_queries:
                print(qs.query)

        d = time.time() - t
        print(
            f"Ran {queries_count} queries in {d} seconds ({queries_count / d} q/s), "
            f"{len(no_results)} had no results, average results per query: {total_results / i}"
        )
