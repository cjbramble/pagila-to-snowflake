"""Layer 4: row-level content matches by normalized row hash (MIG-005)."""

from pathlib import Path

import pytest

from migrate.ddl import target_table
from migrate.mapping import load_spec
from reconcile import rowhash

pytestmark = pytest.mark.req("MIG-005")

TABLES = list(load_spec()["tables"])
SQL_DIR = Path(__file__).resolve().parents[2] / "sql" / "reconciliation"


def source_ref(spec, table):
    return f'"{spec["source"]["schema"]}"."{table}"'


@pytest.mark.parametrize("table", TABLES)
def test_row_hashes_match(pg, sf, spec, table):
    table_spec = spec["tables"][table]
    source_sql = rowhash.row_hash_sql("postgres", source_ref(spec, table), table_spec)
    target_sql = rowhash.row_hash_sql("snowflake", target_table(spec, table), table_spec)
    source = pg.execute(source_sql).fetchall()
    target = sf.cursor().execute(target_sql).fetchall()
    result = rowhash.diff(source, target)
    assert result.ok, f"{table}: {result.describe()}"


def test_generator_reproduces_handwritten_payment_hashes(pg, sf, spec):
    """The generated SQL must agree row-for-row with the reviewed hand-written pair."""
    table_spec = spec["tables"]["payment"]
    handwritten_pg = dict(pg.execute((SQL_DIR / "payment_row_hash_postgres.sql").read_text()))
    generated_pg = dict(
        pg.execute(rowhash.row_hash_sql("postgres", source_ref(spec, "payment"), table_spec))
    )
    cur = sf.cursor()
    handwritten_sf = dict(cur.execute((SQL_DIR / "payment_row_hash_snowflake.sql").read_text()))
    generated_sf = dict(
        cur.execute(rowhash.row_hash_sql("snowflake", target_table(spec, "payment"), table_spec))
    )
    assert generated_pg == handwritten_pg
    assert generated_sf == handwritten_sf
