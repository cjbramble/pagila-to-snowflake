"""Migrate Pagila tables: Postgres → Parquet → internal stage → COPY INTO RAW.

Full refresh per table, so re-running is safe: each table is recreated from the spec
and reloaded. All tables are extracted from one Postgres snapshot. Every table's
outcome is written to QA.LOAD_LOG.

Usage: python -m migrate.load [TABLE ...]
"""

import argparse
import datetime as dt
import re
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

import psycopg
import pyarrow as pa
import pyarrow.parquet as pq
from psycopg import sql
from snowflake.connector import SnowflakeConnection
from snowflake.connector.cursor import SnowflakeCursor
from snowflake.connector.errors import Error as SnowflakeError

from migrate.ddl import create_table_sql, target_table
from migrate.mapping import load_spec
from migrate.snowflake_conn import connect

STAGE = "PAGILA_MIG.RAW.PAGILA_STAGE"
FILE_FORMAT = "PAGILA_MIG.RAW.PARQUET_FMT"
LOAD_LOG = "PAGILA_MIG.QA.LOAD_LOG"
BATCH_ROWS = 10_000

SETUP_SQL = [
    f"CREATE STAGE IF NOT EXISTS {STAGE}",
    # The vectorized scanner reads Parquet binary as BINARY; the default scanner tries
    # to decode it as UTF-8 and fails on non-text bytes.
    f"CREATE OR REPLACE FILE FORMAT {FILE_FORMAT} TYPE = PARQUET USE_VECTORIZED_SCANNER = TRUE",
    f"""CREATE TABLE IF NOT EXISTS {LOAD_LOG} (
        RUN_ID VARCHAR NOT NULL,
        TABLE_NAME VARCHAR NOT NULL,
        STATUS VARCHAR NOT NULL,
        ROWS_EXTRACTED NUMBER(38,0),
        ROWS_LOADED NUMBER(38,0),
        STARTED_AT TIMESTAMP_TZ(6) NOT NULL,
        FINISHED_AT TIMESTAMP_TZ(6) NOT NULL,
        DURATION_S NUMBER(10,3) NOT NULL,
        ERROR VARCHAR
    )""",
]


def loaded_columns(table_spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Columns that are physically loaded: not excluded and not computed by Snowflake."""
    return {
        c: m
        for c, m in table_spec["columns"].items()
        if not m.get("exclude") and "virtual" not in m
    }


def arrow_type(mapping: dict[str, Any]) -> pa.DataType:
    """Parquet column type for a mapped column."""
    target = mapping["target_type"]
    if target == "NUMBER(38,0)":
        return pa.int64()
    if match := re.fullmatch(r"NUMBER\((\d+),(\d+)\)", target):
        return pa.decimal128(int(match[1]), int(match[2]))
    if target.startswith("VARCHAR") or target == "UUID":
        return pa.string()
    if target.startswith("TIMESTAMP_TZ"):
        return pa.timestamp("us", tz="UTC")
    if target.startswith("VECTOR(FLOAT"):
        return pa.list_(pa.float32())
    if target.startswith("BINARY"):
        return pa.binary()
    if target == "ARRAY" and mapping["source_type"] == "text[]":
        return pa.list_(pa.string())
    if target == "BOOLEAN":
        return pa.bool_()
    if target == "DATE":
        return pa.date32()
    raise ValueError(f"no Parquet type for {mapping['source_type']} -> {target}")


def extract_query(schema: str, table: str, columns: dict[str, dict[str, Any]]) -> sql.Composed:
    """SELECT with casts for types psycopg can't hand to pyarrow directly."""
    exprs = []
    for column, m in columns.items():
        ident = sql.Identifier(column)
        if m["target_type"] == "UUID":
            exprs.append(sql.SQL("{}::text").format(ident))
        elif m["target_type"].startswith("VECTOR"):
            # pgvector stores float4; real[] keeps the exact values.
            exprs.append(sql.SQL("{}::real[]").format(ident))
        else:
            exprs.append(ident)
    return sql.SQL("SELECT {} FROM {}.{}").format(
        sql.SQL(", ").join(exprs), sql.Identifier(schema), sql.Identifier(table)
    )


def extract_to_parquet(
    pg: psycopg.Connection, schema: str, table: str, columns: dict[str, dict[str, Any]], path: Path
) -> int:
    """Stream a table into a Parquet file; returns rows written."""
    arrow_schema = pa.schema([(c, arrow_type(m)) for c, m in columns.items()])
    names = list(columns)
    rows_written = 0
    with (
        pg.cursor(name=f"extract_{table}") as cur,
        pq.ParquetWriter(path, arrow_schema) as writer,
    ):
        cur.execute(extract_query(schema, table, columns))
        while rows := cur.fetchmany(BATCH_ROWS):
            batch = [dict(zip(names, row, strict=True)) for row in rows]
            writer.write_table(pa.Table.from_pylist(batch, schema=arrow_schema))
            rows_written += len(rows)
    return rows_written


def copy_sql(target: str, columns: dict[str, dict[str, Any]], stage_path: str) -> str:
    """COPY INTO with an explicit cast per column, so types come from the spec."""
    casts = []
    for column, m in columns.items():
        # Parquet lists can't cast straight to VECTOR; go through ARRAY.
        via = "::ARRAY" if m["target_type"].startswith("VECTOR") else ""
        casts.append(f'$1:"{column}"{via}::{m["target_type"]}')
    return (
        f"COPY INTO {target} ({', '.join(c.upper() for c in columns)})\n"
        f"FROM (SELECT {', '.join(casts)} FROM {stage_path})\n"
        f"FILE_FORMAT = (FORMAT_NAME = '{FILE_FORMAT}')\n"
        "ON_ERROR = ABORT_STATEMENT\n"
        "PURGE = TRUE"
    )


def rows_loaded(cur: SnowflakeCursor) -> int:
    """Sum rows_loaded across the files in a COPY result."""
    names = [d[0].lower() for d in cur.description]
    if "rows_loaded" not in names:  # "Copy executed with 0 files processed."
        return 0
    index = names.index("rows_loaded")
    return sum(row[index] for row in cur.fetchall())


def load_table(
    sf: SnowflakeConnection, spec: dict[str, Any], table: str, parquet: Path, run_id: str
) -> int:
    """Recreate the target table, stage the file, and COPY it in; returns rows loaded."""
    table_spec = spec["tables"][table]
    columns = loaded_columns(table_spec)
    target = target_table(spec, table)
    stage_path = f"@{STAGE}/{run_id}/{table}/"
    cur = sf.cursor()
    cur.execute(create_table_sql(spec, table))
    cur.execute(f"PUT 'file://{parquet}' {stage_path} AUTO_COMPRESS = FALSE OVERWRITE = TRUE")

    # COPY INTO isn't allowed on tables with CHECK constraints, so those tables load
    # through an unconstrained landing table; the INSERT then enforces the CHECKs.
    if not any("check" in m for m in table_spec["columns"].values()):
        cur.execute(copy_sql(target, columns, stage_path))
        return rows_loaded(cur)

    landing = f"{target}_LANDING"
    names = ", ".join(c.upper() for c in columns)
    landing_columns = ", ".join(f"{c.upper()} {m['target_type']}" for c, m in columns.items())
    cur.execute(f"CREATE OR REPLACE TEMPORARY TABLE {landing} ({landing_columns})")
    try:
        cur.execute(copy_sql(landing, columns, stage_path))
        cur.execute(f"INSERT INTO {target} ({names}) SELECT {names} FROM {landing}")
        return cur.fetchone()[0]
    finally:
        cur.execute(f"DROP TABLE IF EXISTS {landing}")


def log_result(sf: SnowflakeConnection, run_id: str, table: str, result: dict[str, Any]) -> None:
    sf.cursor().execute(
        f"INSERT INTO {LOAD_LOG} (RUN_ID, TABLE_NAME, STATUS, ROWS_EXTRACTED, ROWS_LOADED,"
        " STARTED_AT, FINISHED_AT, DURATION_S, ERROR)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            run_id,
            table,
            result["status"],
            result["extracted"],
            result["loaded"],
            result["started_at"],
            result["finished_at"],
            round(result["duration_s"], 3),
            result["error"],
        ),
    )


def migrate_table(
    pg: psycopg.Connection,
    sf: SnowflakeConnection,
    spec: dict[str, Any],
    table: str,
    workdir: Path,
    run_id: str,
) -> dict[str, Any]:
    """Extract and load one table, returning its LOAD_LOG fields."""
    started_at, t0 = dt.datetime.now(dt.UTC), time.perf_counter()
    result: dict[str, Any] = {"extracted": None, "loaded": None, "error": None}
    try:
        parquet = workdir / f"{table}.parquet"
        columns = loaded_columns(spec["tables"][table])
        result["extracted"] = extract_to_parquet(
            pg, spec["source"]["schema"], table, columns, parquet
        )
        result["loaded"] = load_table(sf, spec, table, parquet, run_id)
        result["status"] = "SUCCESS" if result["loaded"] == result["extracted"] else "MISMATCH"
    # Arrow and file errors come from building the Parquet extract. Logging them as FAILED
    # matters: an unlogged attempt would leave the previous SUCCESS as the latest entry.
    except (psycopg.Error, SnowflakeError, pa.ArrowException, OSError) as e:
        result["status"], result["error"] = "FAILED", f"{type(e).__name__}: {e}"
    result["started_at"] = started_at
    result["finished_at"] = dt.datetime.now(dt.UTC)
    result["duration_s"] = time.perf_counter() - t0
    return result


def run(tables: list[str]) -> bool:
    """Load the given tables; returns True if every table succeeded."""
    spec = load_spec()
    run_id = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]
    print(f"run {run_id}")
    all_ok = True

    with (
        psycopg.connect() as pg,
        connect() as sf,
        tempfile.TemporaryDirectory() as tmp,
    ):
        # One read-only snapshot, so tables are consistent with each other.
        pg.read_only = True
        pg.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
        for statement in SETUP_SQL:
            sf.cursor().execute(statement)

        with pg.transaction():
            for table in tables:
                result = migrate_table(pg, sf, spec, table, Path(tmp), run_id)
                log_result(sf, run_id, table, result)
                all_ok &= result["status"] == "SUCCESS"
                print(
                    f"  {table:16} {result['status']:9} extracted={result['extracted']} "
                    f"loaded={result['loaded']} {result['duration_s']:.1f}s"
                    + (f"\n    {result['error']}" if result["error"] else "")
                )
                if pg.info.transaction_status == psycopg.pq.TransactionStatus.INERROR:
                    # A source error aborts the snapshot; later tables can't be extracted.
                    raise SystemExit("source snapshot aborted; stopping run")

    return all_ok


def main() -> None:
    spec_tables = list(load_spec()["tables"])
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("tables", nargs="*", help="tables to load (default: all)")
    args = parser.parse_args()
    if unknown := set(args.tables) - set(spec_tables):
        parser.error(f"not in the mapping spec: {sorted(unknown)}")
    sys.exit(0 if run(args.tables or spec_tables) else 1)


if __name__ == "__main__":
    main()
