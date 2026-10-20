"""Guard the mapping spec: well-formed, decided, and covering every source column."""

import psycopg
import pytest

from migrate.mapping import load_spec
from migrate.profile_source import COLUMNS_SQL, RELATIONS_SQL

SPEC = load_spec()
COLUMN_FIELDS = {
    "source_type",
    "target_type",
    "nullable",
    "decision",
    "exclude",
    "virtual",
    "check",
    "sensitive",
}


def spec_columns() -> dict[tuple[str, str], dict]:
    return {
        (table, column): mapping
        for table, spec in SPEC["tables"].items()
        for column, mapping in spec["columns"].items()
    }


def test_columns_are_well_formed():
    problems = []
    for (table, column), m in spec_columns().items():
        where = f"{table}.{column}"
        if unknown := set(m) - COLUMN_FIELDS:
            problems.append(f"{where}: unknown fields {sorted(unknown)}")
        if "source_type" not in m or not isinstance(m.get("nullable"), bool):
            problems.append(f"{where}: needs source_type and boolean nullable")
        if m.get("exclude") == ("target_type" in m):
            problems.append(f"{where}: needs target_type unless excluded, never both")
        if (d := m.get("decision")) and d not in SPEC["decisions"]:
            problems.append(f"{where}: unknown decision {d}")
    assert not problems, "\n".join(problems)


def test_primary_keys_reference_mapped_columns():
    problems = [
        f"{table}: primary key column {column} not in columns"
        for table, spec in SPEC["tables"].items()
        for column in spec["primary_key"]
        if column not in spec["columns"]
    ]
    assert not problems, "\n".join(problems)


def test_no_open_decisions():
    open_ids = [d for d, spec in SPEC["decisions"].items() if spec["status"] != "decided"]
    assert not open_ids, f"Open mapping decisions need a human call: {open_ids}"


@pytest.fixture(scope="module")
def source():
    with psycopg.connect() as conn:
        yield conn


@pytest.mark.source_db
def test_every_source_column_is_mapped(source):
    params = {"schema": SPEC["source"]["schema"]}
    actual = {(row[0], row[1]): row[2] for row in source.execute(COLUMNS_SQL, params)}
    mapped = spec_columns()

    missing = sorted(f"{t}.{c} ({typ})" for (t, c), typ in actual.items() if (t, c) not in mapped)
    unknown = sorted(f"{t}.{c}" for t, c in mapped if (t, c) not in actual)
    drifted = sorted(
        f"{t}.{c}: spec says {m['source_type']}, source is {actual[(t, c)]}"
        for (t, c), m in mapped.items()
        if (t, c) in actual and m["source_type"] != actual[(t, c)]
    )
    assert not (missing or unknown or drifted), (
        f"missing from spec: {missing}\nnot in source: {unknown}\ntype drift: {drifted}"
    )


@pytest.mark.source_db
def test_every_source_relation_is_mapped_or_excluded(source):
    params = {"schema": SPEC["source"]["schema"]}
    actual = {row[0] for row in source.execute(RELATIONS_SQL, params)}
    covered = set(SPEC["tables"]) | set(SPEC["excluded_relations"])
    assert actual == covered, (
        f"missing from spec: {sorted(actual - covered)}\nnot in source: {sorted(covered - actual)}"
    )
