"""Read-only SQL for the dq-triage agent, run with credentials that cannot write.

Usage: python -m triage.query {pg|sf} "SELECT ..."

pg connects as the dq_triage Postgres role (SELECT only, read-only transactions); sf
connects as PAGILA_TRIAGE_SVC with role PAGILA_TRIAGE (SELECT only, no secondary roles).
The statement check below is a second layer, not the guarantee: the credentials are.
"""

import argparse
import os
import re
import sys

import psycopg
import snowflake.connector

READ_ONLY = re.compile(r"^\s*(select|with|show|desc|describe|explain)\b", re.IGNORECASE)
MAX_ROWS = 200
TRIAGE_ROLE = "PAGILA_TRIAGE"


def check_statement(sql: str) -> str:
    """Return the single statement, or exit if it isn't a read."""
    statement = sql.strip().rstrip(";").strip()
    if ";" in statement:
        raise SystemExit("one statement per call")
    if not READ_ONLY.match(statement):
        raise SystemExit("read-only tool: SELECT, WITH, SHOW, DESC, or EXPLAIN only")
    return statement


def fetch(cur, limit: int | None) -> list[tuple]:
    return cur.fetchall() if limit is None else cur.fetchmany(limit)


def query_postgres(sql: str, limit: int | None = MAX_ROWS + 1) -> tuple[list[str], list[tuple]]:
    """Run read-only SQL on the source; limit=None fetches every row."""
    with psycopg.connect(
        host=os.environ["PGHOST"],
        port=os.environ["PGPORT"],
        dbname=os.environ["PGDATABASE"],
        user=os.environ["TRIAGE_PGUSER"],
        password=os.environ["TRIAGE_PGPASSWORD"],
        options="-c TimeZone=UTC",
    ) as conn:
        conn.read_only = True
        cur = conn.execute(sql)
        return [d.name for d in cur.description], fetch(cur, limit)


def query_snowflake(sql: str, limit: int | None = MAX_ROWS + 1) -> tuple[list[str], list[tuple]]:
    """Run read-only SQL on the target as PAGILA_TRIAGE; limit=None fetches every row."""
    name = os.environ.get("TRIAGE_SNOWFLAKE_CONNECTION", "pagila_triage")
    with snowflake.connector.connect(
        connection_name=name,
        session_parameters={"TIMEZONE": "UTC", "QUERY_TAG": "pagila-dq-triage"},
    ) as conn:
        cur = conn.cursor()
        role = cur.execute("SELECT CURRENT_ROLE()").fetchone()[0]
        if role != TRIAGE_ROLE:
            raise SystemExit(f"connection '{name}' uses role {role}, expected {TRIAGE_ROLE}")
        cur.execute(sql)
        return [d[0] for d in cur.description], fetch(cur, limit)


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only SQL for the dq-triage agent")
    parser.add_argument("db", choices=["pg", "sf"], help="pg = source Postgres, sf = Snowflake")
    parser.add_argument("sql")
    args = parser.parse_args()

    statement = check_statement(args.sql)
    run = query_postgres if args.db == "pg" else query_snowflake
    try:
        columns, rows = run(statement)
    except (psycopg.Error, snowflake.connector.errors.Error) as e:
        raise SystemExit(f"query failed: {str(e).strip()}") from e

    print("\t".join(columns))
    for row in rows[:MAX_ROWS]:
        print("\t".join("NULL" if v is None else str(v) for v in row))
    if len(rows) > MAX_ROWS:
        print(f"... truncated at {MAX_ROWS} rows; narrow the query", file=sys.stderr)


if __name__ == "__main__":
    main()
