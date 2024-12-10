import json

from django.contrib.postgres.indexes import PostgresIndex


class BM25Index(PostgresIndex):
    suffix = "bm25"

    def __init__(self, *expressions, **kwargs):
        self._key_field = kwargs.pop("key_field", None)
        self._stemmer = kwargs.pop("stemmer", "English")
        super().__init__(*expressions, **kwargs)

    def _get_tokenizer(self):
        return {"type": "default", "stemmer": self._stemmer}

    def create_sql(self, model, schema_editor, using="", **kwargs):
        self.check_supported(schema_editor)
        statement = super().create_sql(
            model, schema_editor, using=" %s " % (using or self.suffix), **kwargs
        )
        if self._key_field:
            _id_field_name = self._key_field
        else:
            _id_field_name = model.pk.fget(model).field.name
        text_fields = {}

        for f in model._meta.fields:
            name, db_type = f.name, f.db_type(schema_editor.connection)
            if db_type == "text" or db_type.startswith("varchar"):
                text_fields[name] = {
                    "fast": True,
                    "tokenizer": self._get_tokenizer(),
                }

        statement.parts["extra"] = " WITH (key_field='%s', text_fields='%s')" % (
            _id_field_name,
            json.dumps(text_fields),
        )
        return statement


class BM25NgramIndex(BM25Index):
    def _get_tokenizer(self):
        return {"type": "ngram", "min_gram": 2, "max_gram": 3, "prefix_only": False}
