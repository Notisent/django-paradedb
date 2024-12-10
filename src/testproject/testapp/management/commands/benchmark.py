import os
import random
import time

from django.contrib.postgres.search import SearchQuery, SearchVector
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db.models import Q

import tqdm

from ...models import Item


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--queries", type=int, default=10_000)
        parser.add_argument("--dump-sample-queries", action="store_true", default=False)

    def handle(self, **options):
        silent_tqdm = os.environ.get("SILENT_TQDM", False)
        dump_sample_queries = options.get("dump_sample_queries", False)
        queries_count = options.get("queries")
        if Item.objects.count() < 100:
            Item.objects.all().delete()
            call_command("loaddata", "testapp/test_data.json")

        print("Building request terms queue")

        rq = set()
        while len(rq) < 1000:
            item = Item.objects.order_by("?").first()
            try:
                for word in random.sample(item.description.lower().split(), 50):
                    if len(word) > 4 and word.isalpha():
                        rq.add(word)
            except ValueError:
                pass

        rq = list(rq)[:1000]

        ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ##
        print(f"Running {queries_count} queries on Django icontains...")
        t = time.time()
        no_results = []
        for i in tqdm.tqdm(range(queries_count), disable=silent_tqdm):
            w = rq[i % len(rq)]
            w2 = rq[(i + 11) % len(rq)]

            qs = Item.objects.filter(
                Q(description__icontains=w) | Q(description__icontains=w2)
            )

            if qs.count() == 0:
                no_results.append(w)

            if i == 0 and dump_sample_queries:
                print(qs.query)

        d = time.time() - t
        print(
            f"Ran {queries_count} queries in {d} seconds ({queries_count / d} q/s), {len(no_results)} had no results"
        )
        print()

        time.sleep(1)

        ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ##
        print(
            f"Running {queries_count} queries on Django's contrib.postgres' ts_vector ..."
        )
        t = time.time()
        no_results = []

        for i in tqdm.tqdm(range(queries_count), disable=silent_tqdm):
            w = rq[i % len(rq)]
            w2 = rq[(i + 11) % len(rq)]

            qs = Item.objects.annotate(
                search=SearchVector("description", config="english")
            ).filter(search=SearchQuery(f"('{w}' | '{w2}')", search_type="raw"))
            if qs.count() == 0:
                no_results.append(f"{w} {w2}")

            if i == 0 and dump_sample_queries:
                print(qs.query)

        d = time.time() - t
        print(
            f"Ran {queries_count} queries in {d} seconds ({queries_count / d} q/s), {len(no_results)} had no results"
        )
        print()
        time.sleep(1)

        ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ##
        print(f"Running {queries_count} queries on ParadeDB's term_search ...")
        t = time.time()
        no_results = []

        for i in tqdm.tqdm(range(queries_count), disable=silent_tqdm):
            w = rq[i % len(rq)]
            w2 = rq[(i + 11) % len(rq)]
            qs = Item.objects.filter(description__term_search=f"{w} {w2}")
            if qs.count() == 0:
                no_results.append(f"{w} {w2}")

            if i == 0 and dump_sample_queries:
                print(qs.query)

        d = time.time() - t
        print(
            f"Ran {queries_count} queries in {d} seconds ({queries_count / d} q/s), {len(no_results)} had no results"
        )
