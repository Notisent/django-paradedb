from django.db.models import Field, Lookup
from django.db.models.lookups import PostgresOperatorLookup
from django.db.models.sql.compiler import SQLCompiler



@Field.register_lookup
class QuerySearchLookup(Lookup):
    """
    Usage: Q(subject__query_search="AW: Konditionen Beratung^2.0")
    Compiles to: <lhs> @@@ paradedb.parse_with_field('<db_col>', %s)
    - Accepts DSL (^, :, quotes, etc.)
    - Avoids TEXT overload errors and the 'AW:' field-name confusion.
    """
    lookup_name = "query_search"

    def as_sql(self, compiler: SQLCompiler, connection):
        lhs_sql, lhs_params = self.process_lhs(compiler, connection)
        rhs_sql, rhs_params = self.process_rhs(compiler, connection)  # rhs_params[0] = your string

        # Resolve the *DB column name* of the leaf field (works with joins)
        leaf_field = getattr(self.lhs, "target", None) or getattr(self.lhs, "field", None)
        db_col = (leaf_field.column if leaf_field is not None else self.lhs.source.name)

        # Cast LHS to text if the column isn’t already text/char (safe no-op for text)
        lhs_expr = f"({lhs_sql})::text"

        sql = f"{lhs_expr} @@@ paradedb.parse_with_field(%s, %s)"
        params = [db_col, rhs_params[0]]
        # include any params the LHS produced (joins), then our params
        return sql, tuple(lhs_params) + tuple(params)
    
@Field.register_lookup
class BaseParadeDBLookup(PostgresOperatorLookup):
    """
    https://docs.paradedb.com/documentation/full-text/overview#basic-usage

    SELECT description, rating, category
    FROM mock_items
    WHERE description @@@ 'shoes'
    LIMIT 5;
    """

    lookup_name = "term_search"
    postgres_operator = "@@@"
    prepare_rhs = True

    def get_prep_lookup(self):
        rhs = super().get_prep_lookup()
        return (
            rhs.replace(":", r"\:")
            .replace("[", r"\[")
            .replace("]", r"\]")
            .replace("(", r"\(")
            .replace(")", r"\)")
            .replace("'", r"\'")
            .replace('"', r"\"")
            .replace("-", r"\-")
            .replace("+", r"\+")
            .replace("*", r"\*")
            .replace("^", r"\^")
            .replace("`", r"\`")
            .replace("{", r"\{")
            .replace("}", r"\}")
        )


@Field.register_lookup
class PhraseParadeDBLookup(BaseParadeDBLookup):
    """
    https://docs.paradedb.com/documentation/full-text/phrase

    SELECT description, rating, category
    FROM mock_items
    WHERE description @@@ '"plastic keyboard"';
    """

    lookup_name = "phrase_search"

    def process_rhs(self, compiler, connection):
        rhs, rhs_params = super().process_rhs(compiler, connection)
        return f"'\"{rhs_params[0]}\"'", []


@Field.register_lookup
class PhrasePrefixParadeDBLookup(BaseParadeDBLookup):
    """
    https://docs.paradedb.com/documentation/full-text/phrase#phrase-prefix

    The * prefix operator allows for the last term in the phrase query to be
    the prefix of another word. For instance, "plastic keyb"* matches plastic
    keyboard.

    SELECT description, rating, category
    FROM mock_items
    WHERE description @@@ '"plastic keyb"*';
    """

    lookup_name = "phrase_prefix_search"

    def process_rhs(self, compiler, connection):
        rhs, rhs_params = super().process_rhs(compiler, connection)
        return f"'\"{rhs_params[0]}\"*'", []


class BaseFuzzyParadeDBLookup(BaseParadeDBLookup):
    """
    https://docs.paradedb.com/documentation/guides/autocomplete#fuzzy-term
    https://docs.paradedb.com/documentation/guides/autocomplete#fuzzy-phrase

    SELECT description, rating, category FROM mock_items
    WHERE id @@@ paradedb.match(
        field => 'description',
        value => 'ruining shoez'
    ) ORDER BY rating DESC;

    """

    def process_lhs(self, compiler, connection, lhs=None):
        id_field_name = compiler.query.model._meta.pk.name

        # This is so horribly awkward and brittle,
        # there must be a proper way of doing this
        lhs, _ = super().process_lhs(compiler, connection, lhs=lhs)
        tbl = lhs.replace('"', "").rsplit(".", 1)[0]

        return f'"{tbl}"."{id_field_name}"', []

    def process_rhs(self, compiler, connection):
        rhs, rhs_params = super().process_rhs(compiler, connection)
        lhs, _ = super().process_lhs(compiler, connection)
        col = lhs.replace('"', "").rsplit(".", 1)[-1]
        return (
            "paradedb.match(field => %s, value => %s, "
            f"conjunction_mode => {self.match_all_terms}, "
            f"distance => {self.distance})"
        ), [col, rhs_params[0]]


@Field.register_lookup
class FuzzyParadeDBLookup(BaseFuzzyParadeDBLookup):
    lookup_name = "fuzzy_term_search"
    match_all_terms = "false"
    distance = 2


@Field.register_lookup
class FuzzyPhraseParadeDBLookup(BaseFuzzyParadeDBLookup):
    lookup_name = "fuzzy_phrase_search"
    match_all_terms = "true"
    distance = 2
