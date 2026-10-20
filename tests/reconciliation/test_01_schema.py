"""Layer 1: target schema matches the mapping spec (MIG-002)."""

import pytest
from snowflake.connector import DictCursor

from migrate.ddl import target_table
from migrate.mapping import load_spec

pytestmark = pytest.mark.req("MIG-002")

TABLES = list(load_spec()["tables"])


def expected_columns(table_spec: dict) -> list[dict]:
    return [
        {
            "name": column.upper(),
            "type": m["target_type"],
            "nullable": m["nullable"],
            # Snowflake rewrites virtual expressions, so only the kind is compared here;
            # the aggregate and row-hash layers prove the computed values.
            "kind": "VIRTUAL" if "virtual" in m else "COLUMN",
            "check": m.get("check"),
        }
        for column, m in table_spec["columns"].items()
        if not m.get("exclude")
    ]


def test_raw_contains_exactly_the_spec_tables(sf, spec):
    target = spec["target"]
    rows = sf.cursor().execute(
        f"SELECT table_name FROM {target['database']}.information_schema.tables"
        " WHERE table_schema = %s AND table_type = 'BASE TABLE'",
        (target["schema"],),
    )
    actual = {r[0] for r in rows}
    expected = {t.upper() for t in spec["tables"]}
    assert actual == expected, f"extra: {actual - expected}, missing: {expected - actual}"


@pytest.mark.parametrize("table", TABLES)
def test_columns_match_spec(sf, spec, table):
    rows = sf.cursor(DictCursor).execute(f"DESC TABLE {target_table(spec, table)}").fetchall()
    actual = [
        {
            "name": r["name"],
            "type": r["type"],
            "nullable": r["null?"] == "Y",
            "kind": r["kind"],
            "check": r["check"],
        }
        for r in rows
    ]
    assert actual == expected_columns(spec["tables"][table])


@pytest.mark.parametrize("table", TABLES)
def test_primary_key_matches_spec(sf, spec, table):
    rows = sf.cursor(DictCursor).execute(f"SHOW PRIMARY KEYS IN TABLE {target_table(spec, table)}")
    actual = [r["column_name"] for r in sorted(rows, key=lambda r: r["key_sequence"])]
    assert actual == [c.upper() for c in spec["tables"][table]["primary_key"]]
