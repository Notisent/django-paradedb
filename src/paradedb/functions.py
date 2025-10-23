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

    def __init__(self, field=None, *args, **kwargs):
        self._field = field
        super().__init__(*args, **kwargs)

    output_field = FloatField()

    def as_sql(self, compiler, connection, **extra_context):
        # This is mighty nasty.
        _table_name = compiler.query.model._meta.db_table
        _field_name = compiler.query.model._meta.pk.name
        if self._field is not None and "__" in self._field:
            for table_name, ds in compiler.query.alias_map.items():
                if hasattr(ds, "join_field") and self._field.startswith(
                    f"{ds.join_field.name}__"
                ):
                    _table_name = table_name
                    break

        return f"pdb.score({_table_name}.{_field_name})", []


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
