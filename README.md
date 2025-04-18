## Django ParadeDB

This app provides Django lookups and indexes to perform fast full-text search on [ParadeDB](https://paradedb.com) databases using the BM25 index.

Note: this project is in very early alpha stage, currently only supports a limited set of the many features offered by ParadeDB and the API of the lookups and functions might change at any time. Contributions in form of pull requests, suggestions and feedback are most welcome.

## Installation

As soon as the package gains some stability I'll publish it to PyPI, in the meantime install directly from the repo:

```bash
pip install https://github.com/mbi/django-paradedb/archive/main.zip
```


## Getting Started

To get started, please visit ParadeDB's [documentation](https://docs.paradedb.com) to setup and install. The easiest way to play around with the database is via Docker:

```bash
docker run \
  --name paradedb \
  -e POSTGRES_USER=myuser \
  -e POSTGRES_PASSWORD=mypassword \
  -e POSTGRES_DB=mydatabase \
  -v paradedb_data:/var/lib/postgresql/data/ \
  -p 5432:5432 \
  -d \
  paradedb/paradedb:latest
```
... then setup your Django settings to match the same settings (set `HOST` to `localhost`)

Create a `BM25Index` on your Django models, then make and apply migrations.

```python
from django.db import models
from paradedb.indexes import BM25Index

class Item(models.Model):
    name = models.CharField(max_length=127)
    description = models.TextField()
    rating = models.DecimalField(max_digits=3, decimal_places=2)

    class Meta:
        indexes = [
            BM25Index(
                fields=["name", "description", "rating"],
                name="item_idx"
            ),
        ]
```

## Lookups and functions

### Term lookup

This will perform a [term search](https://docs.paradedb.com/documentation/full-text/term), i.e. match any (OR) of the terms in the lookup.

```python
Item.objects.filter(
   description__term_search="keyboard headphones"
)
```


### Phrase lookup

This will perform a [phrase search](https://docs.paradedb.com/documentation/full-text/phrase), i.e. match the exact phrase

```python
Item.objects.filter(
   description__phrase_search="that same year the company began"
)
```

### Phrase prefix lookup

This will perform a [phrase prefix search](https://docs.paradedb.com/documentation/full-text/phrase#phrase-prefix), e.g. "plastic keyb" will match "plastic keyboard"

```python
Item.objects.filter(
   description__phrase_prefix_search="that same year the comp"
)
```


### Fuzzy lookups

Use `fuzzy_term_search` and `fuzzy_phrase_search` to perform [fuzzy term](https://docs.paradedb.com/documentation/guides/autocomplete#fuzzy-term) and [fuzzy phrase](https://docs.paradedb.com/documentation/guides/autocomplete#fuzzy-phrase) lookups, respectively.

This will match any of the provided term(s):

```python
Item.objects.filter(name__fuzzy_term_search="irgin muzik")
```
... will match `Original Music from The TV Show The Untouchables`, `UCLA Bruins men's basketball retired numbers`, `Petroleum Training Institute`

To fuzzily match *all* terms:

```python
Item.objects.filter(name__fuzzy_phrase_search="irgin muzik")
```
This will only match `Original Music from The TV Show The Untouchables`

### JSON Search lookup

For more advanced queries, use the `json_search` lookup which supports ParadeDB's full JSON query syntax. This lookup accepts both JSON strings and Python dictionaries:

```python
# Using JSON string
Item.objects.filter(
    description__json_search='{"term": {"value": "keyboard"}}'
)

# Using Python dictionary
Item.objects.filter(
    description__json_search={"term": {"value": "keyboard"}}
)
```

The JSON syntax gives you access to all ParadeDB query types and options:

```python
# Fuzzy search with custom distance
Item.objects.filter(
    description__json_search={
        "fuzzy": {
            "field": "description", 
            "value": "keyboarrd", 
            "distance": 1
        }
    }
)

# Match with conjunction mode
Item.objects.filter(
    description__json_search={
        "match": {
            "field": "description",
            "value": "wireless keyboard",
            "conjunction_mode": True  # Match all terms
        }
    }
)
```

### Scoring and sorting

ParadeDB calculates a [score](https://docs.paradedb.com/documentation/full-text/sorting) on the resulting rows, which will allow you to sort results by pertinence.

```python
from paradedb.functions import Score

# With term search
Item.objects.filter(description__term_search="music sheets").annotate(score=Score()).order_by('-score')

# With json search
Item.objects.filter(
    description__json_search={"term": {"value": "music sheets"}}
).annotate(score=Score()).order_by('-score')
```

If your query spans multiple tables, you must specify the field used to calculate the
score on, e.g.:

```python
from paradedb.functions import Score
from models import Review, Item

# With term search
Review.objects.filter(item__description__term_search="music sheets")
    .annotate(score=Score('item__description'))
    .order_by('-score')

# With json search
Review.objects.filter(
    item__description__json_search={"term": {"value": "music sheets"}}
).annotate(score=Score('item__description')).order_by('-score')
```



### Highlighting

To highlight the matched terms, use the Highlight function:

```python
from paradedb.functions import Highlight

# With term search
>>> Item.objects.filter(name__term_search="Music").annotate(hl=Highlight('name')).get().hl
'Original <em>Music</em> from The TV Show The Untouchables'

# With json search
>>> Item.objects.filter(
...     name__json_search={"term": {"value": "Music"}}
... ).annotate(hl=Highlight('name')).get().hl
'Original <em>Music</em> from The TV Show The Untouchables'

# You can specify start and end tags
>>> for item in Item.objects.filter(name__term_search="Music yeast").annotate(hl=Highlight('name', start_tag='<i>', end_tag='</i>')):
...   print(item.hl)
...
Fleischmann's <i>Yeast</i>
Original <i>Music</i> from The TV Show The Untouchables
```

## Performance

Above approx 250,000 rows, pg_search performs about 25% to 40% better compared to TSVector with a GIN index. 

![Queries _ sec](https://github.com/user-attachments/assets/69103e9b-ba91-4de2-b7ae-3cab380556be)

See [testproject/testapp/models.py](https://github.com/mbi/django-paradedb/blob/main/src/testproject/testapp/models.py) and [testproject/testapp/management/commands/benchmark.py](https://github.com/mbi/django-paradedb/blob/main/src/testproject/testapp/management/commands/benchmark.py) on how this was measured.

## Testing

To run tests (at the root of the project):
```bash
tox
```
