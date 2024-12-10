## Django ParadeDB

This app provides Django lookups and indexes to perform fast full-text search on [ParadeDB](https://paradedb.com) databases using the BM25 index.

Note: this project is in very early alpha phase, currently only supports a limited set of the many features offered by ParadeDB and the API of the lookups and functions might change at any time. Contributions in form of pull requests, suggestions and feedback are most welcome.

## Installation

As soon as the package gains some stability I'll publish it to PyPI, in the meantime install directly from the repo:

```bash
pip install https://github.com/mbi/django-paradedb/archive/main.zip
```


## Getting Started

To get started, please visit our [documentation](https://docs.paradedb.com) to setup and install ParadeDB. The easiest way to play around with the database is via Docker:

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
   description__search="keyboard headphones"
)
```


### Phrase lookup

This will perform a [phrase search](https://docs.paradedb.com/documentation/full-text/phrase), i.e. match the exact phrase 

```python
Item.objects.filter(
   description__phrase_search="that same year the company began"
)
```


### Fuzzy lookups

Use `fuzzy_search` and `fuzzy_phrase_search` to perform [fuzzy term](https://docs.paradedb.com/documentation/guides/autocomplete#fuzzy-term) and [fuzzy phrase](https://docs.paradedb.com/documentation/guides/autocomplete#fuzzy-phrase) lookups, respectively.

This will match any of the provided term(s):

```python
Item.objects.filter(name__fuzzy_search="irgin muzik")
```
... will match `Original Music from The TV Show The Untouchables`, `UCLA Bruins men's basketball retired numbers`, `Petroleum Training Institute`

To fuzzily match *all* terms:

```python
Item.objects.filter(name__fuzzy_phrase_search="irgin muzik")
```
This will only match `Original Music from The TV Show The Untouchables`


### Scoring and sorting

ParadeDB calculates a [score](https://docs.paradedb.com/documentation/full-text/sorting) on the resulting rows, which will allow you to sort results by pertinence.

```python
from paradedb.functions import Score

Item.objects.filter(description__search="music sheets").annotate(score=Score()).order_by('-score')
```

### Highlighting

To highlight the matched terms, use the Highlight function:

```python
from paradedb.functions import Highlight

>>> Item.objects.filter(name__search="Music").annotate(hl=Highlight('name')).get().hl
'Original <em>Music</em> from The TV Show The Untouchables'

# You can specifiy start and end tags
>>> for item in Item.objects.filter(name__search="Music yeast").annotate(hl=Highlight('name', start_tag='<i>', end_tag='</i>')):
...   print(item.hl)
... 
Fleischmann's <i>Yeast</i>
Original <i>Music</i> from The TV Show The Untouchables
```

## Testing

To run tests (at the root of the project):
```bash
tox
```


