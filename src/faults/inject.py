"""Apply a named fault to a RAW table, and restore it from a zero-copy clone.

Usage:
    python -m faults.inject list
    python -m faults.inject apply FAULT
    python -m faults.inject restore TABLE
"""

import argparse
import hashlib

from snowflake.connector import SnowflakeConnection

from faults.catalog import FAULTS, Fault
from migrate.ddl import target_table
from migrate.mapping import load_spec
from migrate.snowflake_conn import connect

# Kept out of QA on purpose: the read-only triage role can see QA, and a pre-fault copy
# would hand it the answer during blind diagnosis tests.
BACKUP_SCHEMA = "PAGILA_MIG.FAULTS"


def backup_table(table: str) -> str:
    return f"{BACKUP_SCHEMA}.FAULT_BACKUP_{table.upper()}"


def fingerprint(sf: SnowflakeConnection, table: str) -> str:
    """Hash of a table's data and structure; changes if either does.

    Structure comes from DESC TABLE and SHOW PRIMARY KEYS rather than GET_DDL, because
    cloning reorders constraints in GET_DDL output without changing the table.
    """
    ref = target_table(load_spec(), table)
    cur = sf.cursor()
    data = cur.execute(f"SELECT COUNT(*), HASH_AGG(*) FROM {ref}").fetchone()
    columns = cur.execute(f"DESC TABLE {ref}").fetchall()
    keys = cur.execute(f"SHOW PRIMARY KEYS IN TABLE {ref}").fetchall()
    key_columns = sorted((r[5], r[4]) for r in keys)  # (key_sequence, column_name)
    return hashlib.sha256(f"{data}|{columns}|{key_columns}".encode()).hexdigest()


def backup_exists(sf: SnowflakeConnection, table: str) -> bool:
    name = backup_table(table).split(".")[-1]
    return bool(
        sf.cursor().execute(f"SHOW TABLES LIKE '{name}' IN SCHEMA {BACKUP_SCHEMA}").fetchall()
    )


def apply(sf: SnowflakeConnection, fault: Fault) -> None:
    """Back up the table, then run the fault's statements against RAW.

    If a statement fails, the table is restored before the error propagates, so a
    half-applied fault never stays in RAW.
    """
    cur = sf.cursor()
    cur.execute(f"CREATE SCHEMA IF NOT EXISTS {BACKUP_SCHEMA}")
    backup = backup_table(fault.table)
    if backup_exists(sf, fault.table):
        raise SystemExit(f"{backup} exists: restore {fault.table} before applying another fault")
    ref = target_table(load_spec(), fault.table)
    cur.execute(f"CREATE TABLE {backup} CLONE {ref}")
    try:
        for statement in fault.statements:
            cur.execute(statement.format(t=ref))
    except BaseException:
        restore(sf, fault.table)
        raise


def restore(sf: SnowflakeConnection, table: str) -> None:
    """Replace the RAW table with its backup clone, then drop the backup."""
    sf.cursor().execute(f"CREATE SCHEMA IF NOT EXISTS {BACKUP_SCHEMA}")
    if not backup_exists(sf, table):
        raise SystemExit(f"no fault backup for {table}: nothing to restore")
    cur = sf.cursor()
    backup = backup_table(table)
    cur.execute(f"CREATE OR REPLACE TABLE {target_table(load_spec(), table)} CLONE {backup}")
    cur.execute(f"DROP TABLE {backup}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inject migration faults into RAW tables")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")
    sub.add_parser("apply").add_argument("fault", choices=sorted(FAULTS))
    sub.add_parser("restore").add_argument("table")
    args = parser.parse_args()

    if args.command == "list":
        for f in FAULTS.values():
            print(f"{f.name:24} {f.table:15} {f.description}")
        return
    with connect() as sf:
        if args.command == "apply":
            fault = FAULTS[args.fault]
            apply(sf, fault)
            print(f"applied {fault.name}; undo with: python -m faults.inject restore {fault.table}")
        else:
            restore(sf, args.table)
            print(f"restored {args.table}")


if __name__ == "__main__":
    main()
