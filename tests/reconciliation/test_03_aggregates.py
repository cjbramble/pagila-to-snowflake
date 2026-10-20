"""Layer 3: per-column aggregates match (MIG-004)."""

import pytest

from migrate.ddl import target_table
from migrate.mapping import load_spec
from reconcile import aggregates

pytestmark = pytest.mark.req("MIG-004")

TABLES = list(load_spec()["tables"])


@pytest.mark.parametrize("table", TABLES)
def test_column_aggregates_match(pg, sf, spec, table):
    table_spec = spec["tables"][table]
    source_ref = f'"{spec["source"]["schema"]}"."{table}"'
    source = pg.execute(aggregates.profile_sql("postgres", source_ref, table_spec)).fetchone()
    target_sql = aggregates.profile_sql("snowflake", target_table(spec, table), table_spec)
    target = sf.cursor().execute(target_sql).fetchone()
    differences = aggregates.compare(table_spec, source, target)
    assert not differences, f"{table}:\n  " + "\n  ".join(differences)
