"""Unit tests for DDL generation and loader helpers; no database needed."""

import copy

import pyarrow as pa
import pytest

from migrate import load
from migrate.ddl import create_table_sql
from migrate.load import arrow_type, copy_sql, loaded_columns
from migrate.mapping import load_spec

SPEC = load_spec()


def test_every_mapped_column_has_a_parquet_type():
    for table, table_spec in SPEC["tables"].items():
        for column, mapping in loaded_columns(table_spec).items():
            assert arrow_type(mapping), f"{table}.{column}"


def test_loaded_columns_skip_excluded_and_virtual():
    columns = loaded_columns(SPEC["tables"]["film"])
    assert "fulltext" not in columns
    assert "length_hours" not in columns
    assert "title" in columns


def test_film_ddl_has_virtual_column_checks_and_no_excluded_column():
    ddl = create_table_sql(SPEC, "film")
    assert "FULLTEXT" not in ddl
    assert "LENGTH_HOURS NUMBER(4,2) AS (ROUND(LENGTH / 60.0, 2)::NUMBER(4,2)) VIRTUAL" in ddl
    assert "CONSTRAINT FILM_RATING_CHK CHECK (RATING IN" in ddl
    assert "CONSTRAINT FILM_PK PRIMARY KEY (FILM_ID)" in ddl
    assert "TITLE VARCHAR(16777216) NOT NULL" in ddl
    assert "DESCRIPTION VARCHAR(16777216)," in ddl


def test_composite_primary_key_keeps_spec_order():
    assert "PRIMARY KEY (PAYMENT_DATE, PAYMENT_ID)" in create_table_sql(SPEC, "payment")


def test_virtual_column_cannot_be_not_null():
    spec = copy.deepcopy(SPEC)
    spec["tables"]["film"]["columns"]["length_hours"]["nullable"] = False
    with pytest.raises(ValueError, match="virtual"):
        create_table_sql(spec, "film")


def test_copy_casts_vector_through_array():
    columns = loaded_columns(SPEC["tables"]["film_embedding"])
    sql = copy_sql("T", columns, "@S/run/film_embedding/")
    assert '$1:"embedding"::ARRAY::VECTOR(FLOAT, 20)' in sql
    assert '$1:"last_update"::TIMESTAMP_TZ(6)' in sql
    assert "ON_ERROR = ABORT_STATEMENT" in sql


@pytest.mark.parametrize(
    "error",
    [pa.ArrowInvalid("Could not convert 'x' with type str"), OSError("No space left on device")],
    ids=["arrow", "os"],
)
def test_extract_failure_is_reported_as_failed(monkeypatch, tmp_path, error):
    def failing_extract(*args, **kwargs):
        raise error

    monkeypatch.setattr(load, "extract_to_parquet", failing_extract)
    # Connections are never touched: the extract fails before anything reaches Snowflake.
    result = load.migrate_table(None, None, SPEC, "payment", tmp_path, "run-1")
    assert result["status"] == "FAILED"
    assert result["loaded"] is None
    assert type(error).__name__ in result["error"]
