import random
import time

import tqdm

from django.contrib.postgres.search import SearchQuery, SearchVector
from django.core.management import call_command
from django.core.management.base import BaseCommand

from ...models import Item


QUERY_COUNT = 10_000


class Command(BaseCommand):
    def handle(self, **options):
        if Item.objects.count() < 100:
            Item.objects.all().delete()
            call_command("loaddata", "testapp/test_data.json")

        print("Building request terms queue")

        rq = set()
        while len(rq) < 1000:
            item = Item.objects.order_by("?").first()
            try:
                for word in random.sample(item.description.lower().split(), 50):
                    rq.add(word)
            except ValueError:
                pass

        rq = list(rq)[:1000]

        ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ##
        print(f"Running {QUERY_COUNT} queries on Django icontains...")
        t = time.time()
        no_results = []
        for i in tqdm.tqdm(range(QUERY_COUNT)):
            w = rq[i % len(rq)]
            qs = Item.objects.filter(description__icontains=w)
            if qs.count() == 0:
                no_results.append(w)

            if i == 0:
                print(qs.query)

        d = time.time() - t
        print(
            f"Ran {QUERY_COUNT} queries in {d} seconds ({QUERY_COUNT / d} q/s), {len(no_results)} had no results"
        )
        print()

        time.sleep(1)

        ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ##
        print(
            f"Running {QUERY_COUNT} queries on Django's contrib.postgres' ts_vector ..."
        )
        t = time.time()
        no_results = []

        for i in tqdm.tqdm(range(QUERY_COUNT)):
            w = rq[i % len(rq)]
            qs = Item.objects.annotate(
                search=SearchVector("description", config="english")
            ).filter(search=SearchQuery(w))
            if qs.count() == 0:
                no_results.append(w)
            if i == 0:
                print(qs.query)
        d = time.time() - t
        print(
            f"Ran {QUERY_COUNT} queries in {d} seconds ({QUERY_COUNT / d} q/s), {len(no_results)} had no results"
        )
        print()
        time.sleep(1)

        ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ##
        print(f"Running {QUERY_COUNT} queries on ParadeDB's term_search ...")
        t = time.time()
        no_results = []

        for i in tqdm.tqdm(range(QUERY_COUNT)):
            w = rq[i % len(rq)]
            qs = Item.objects.filter(description__term_search=w)
            if qs.count() == 0:
                no_results.append(w)
            if i == 0:
                print(qs.query)
        d = time.time() - t
        print(
            f"Ran {QUERY_COUNT} queries in {d} seconds ({QUERY_COUNT / d} q/s), {len(no_results)} had no results"
        )
