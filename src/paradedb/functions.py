from django.db.models import CharField, FloatField
from django.db.models.expressions import Func


class Score(Func):
    """
    https://docs.paradedb.com/documentation/full-text/sorting

    SELECT description, rating, category, paradedb.score(id)
    FROM mock_items
    WHERE description @@@ 'shoes'
    ORDER BY score DESC
    LIMIT 5;
    """

    output_field = FloatField()

    def as_sql(self, compiler, connection, **extra_context):
        _field_name = compiler.query.model._meta.pk.name
        return f"paradedb.score({_field_name})", []


class Highlight(Func):
    """
    https://docs.paradedb.com/documentation/full-text/highlighting

    SELECT id, paradedb.snippet(description, start_tag => '<i>', end_tag => '</i>')
    FROM mock_items
    WHERE description @@@ 'shoes'
    LIMIT 5;
    """

    def __init__(
        self, field, start_tag="<em>", end_tag="</em>", max_num_chars=150, **kwargs
    ):
        self._start_tag = start_tag
        self._end_tag = end_tag
        self._max_num_chars = max_num_chars
        self._field = field
        super().__init__(**kwargs, output_field=CharField())

    def as_sql(self, compiler, connection, **extra_context):
        return (
            f"paradedb.snippet({self._field}, "
            f"start_tag => %s, end_tag => %s, "
            f"max_num_chars => %s)"
        ), [self._start_tag, self._end_tag, self._max_num_chars]
