"""Layer 2: row counts match per table (MIG-003), and the load log is complete (MIG-006)."""

import pytest
from psycopg import sql

from migrate.ddl import target_table
from migrate.load import LOAD_LOG
from migrate.mapping import load_spec

TABLES = list(load_spec()["tables"])


@pytest.mark.req("MIG-003")
@pytest.mark.parametrize("table", TABLES)
def test_row_counts_match(pg, sf, spec, table):
    query = sql.SQL("SELECT count(*) FROM {}.{}").format(
        sql.Identifier(spec["source"]["schema"]), sql.Identifier(table)
    )
    source = pg.execute(query).fetchone()[0]
    target = sf.cursor().execute(f"SELECT count(*) FROM {target_table(spec, table)}").fetchone()[0]
    assert target == source, f"{table}: source {source}, target {target}, diff {target - source}"


@pytest.mark.req("MIG-006")
def test_latest_load_of_every_table_succeeded(sf, spec):
    rows = (
        sf.cursor()
        .execute(
            f"""SELECT table_name, run_id, status, rows_extracted, rows_loaded
            FROM {LOAD_LOG}
            QUALIFY ROW_NUMBER() OVER (PARTITION BY table_name ORDER BY started_at DESC) = 1"""
        )
        .fetchall()
    )
    latest = {r[0]: r[1:] for r in rows}
    never_loaded = sorted(set(spec["tables"]) - set(latest))
    bad = {t: v for t, v in latest.items() if v[1] != "SUCCESS" or v[2] != v[3]}
    assert not never_loaded and not bad, f"never loaded: {never_loaded}; latest not OK: {bad}"
