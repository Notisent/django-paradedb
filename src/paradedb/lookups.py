from django.db.models import Field, Lookup
from django.db.models.lookups import PostgresOperatorLookup
import ast

def _db_col_from_lhs(lhs):
    leaf = getattr(lhs, "target", None) or getattr(lhs, "field", None)
    return (leaf.column if leaf is not None else lhs.source.name)

def _model_from_lhs(lhs):
    # try to get the concrete Django model behind this LHS
    leaf = getattr(lhs, "target", None) or getattr(lhs, "field", None)
    return getattr(leaf, "model", None)

def _bm25_index_name_for_model(model):
    # default convention: <table_name>_bm25_idx
    tbl = model._meta.db_table  # may be "schema.table" or just "table"
    base = tbl.split(".")[-1]
    return f"{base}_bm25_idx".strip().strip('"').strip("'")

@Field.register_lookup
class QuerySearchLookup(Lookup):
    lookup_name = "query_search"
    def as_sql(self, compiler, connection):
        lhs_sql, lhs_params = self.process_lhs(compiler, connection)
        text = getattr(self.rhs, "value", self.rhs)       # <<< read raw, no process_rhs
        db_col = _db_col_from_lhs(self.lhs)
        sql = (
            f"({lhs_sql}) @@@ "
            f"paradedb.parse_with_field(paradedb.text_to_fieldname(%s), %s)"
        )
        params = tuple(lhs_params) + (db_col, text)
        return sql, params

@Field.register_lookup
class BoostSearchLookup(Lookup):
    lookup_name = "boost_search"
    def as_sql(self, compiler, connection):
        lhs_sql, lhs_params = self.process_lhs(compiler, connection)
        rhs = getattr(self.rhs, "value", self.rhs)        # <<< read raw, no process_rhs
        # Expect (text, factor); tolerate mis-shapes
        if not isinstance(rhs, (list, tuple)):
            rhs = ast.literal_eval(rhs)
        text = rhs[0]
        factor = float(rhs[1]) if len(rhs) > 1 else 1.0

        if isinstance(text, (list, tuple)):              # guard nested tuple
            text = text[0]
        db_col = _db_col_from_lhs(self.lhs)
        model = _model_from_lhs(self.lhs)
        index_name = _bm25_index_name_for_model(model)
        sql = (
            f"{lhs_sql} @@@ "
            f"paradedb.with_index(%s, paradedb.boost(%s, paradedb.term(paradedb.text_to_fieldname(%s), %s)))"
        )
        params = tuple(lhs_params) + (index_name, factor, db_col, text)
        return sql, params
    
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
