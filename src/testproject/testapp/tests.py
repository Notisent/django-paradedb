from testapp.models import Item

from django.test import TestCase

from paradedb.functions import Highlight, Score


class ParadeDBCase(TestCase):
    fixtures = ["testapp/test_data.json"]

    def test_has_loaded_data(self):
        self.assertTrue(Item.objects.count() > 100)

    def test_search_lookup(self):
        self.assertTrue(
            Item.objects.filter(
                description__term_search="Colpoys then attempted to isolate his crew"
            ).count()
            > 80
        )

    def test_phrase_search_lookup(self):
        self.assertTrue(
            Item.objects.filter(
                description__phrase_search="Colpoys then attempted to isolate his crew"
            ).count()
            == 1
        )

    def test_fuzzy_lookup(self):
        self.assertTrue(
            Item.objects.filter(description__fuzzy_term_search="atempted crwe").count()
            > 50
        )

    def test_fuzzy_phrase_lookup(self):
        self.assertTrue(
            Item.objects.filter(
                description__fuzzy_phrase_search="Cololys attempte to isoate his crew"
            ).count()
            == 1
        )

    def test_score_sorting(self):
        # annotated but unsorted
        qs = Item.objects.filter(description__term_search="music").annotate(
            score=Score()
        )
        item1, item2, item3 = qs[:3]
        self.assertTrue(item1.score < item2.score)

        # Sorted qs
        item1, item2, item3 = qs.order_by("-score")[:3]
        self.assertTrue(item1.score > item2.score)

    def test_highlighting(self):
        item = (
            Item.objects.filter(description__term_search="Fleischmann")
            .annotate(description_hl=Highlight("description"))
            .first()
        )
        self.assertTrue(
            "The <em>Fleischmann</em> Company in 1905." in item.description_hl
        )
        self.assertFalse(
            "The <em>Fleischmann</em> Company in 1905." in item.description
        )

        item = (
            Item.objects.filter(description__term_search="Fleischmann")
            .annotate(
                description_hl=Highlight(
                    "description", start_tag="<start>", end_tag="<end>"
                )
            )
            .first()
        )
        self.assertTrue(
            "The <start>Fleischmann<end> Company in 1905." in item.description_hl
        )
