"""Run paired source/target validation checks read-only and compare their results.

A check is two files in one directory: <name>.pg.sql (Postgres source) and <name>.sf.sql
(Snowflake target). Each must return the same columns in the same order with an ORDER BY;
the check passes when both sides return identical rows. Values are compared after light
normalization: numbers as Decimal, timestamps in UTC, everything else as-is. Anything
else (case, whitespace, precision, time zones) is the check's job to normalize in SQL.

Usage: python -m triage.check_pair DIR [NAME ...]
"""

import argparse
import datetime as dt
import re
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg
import snowflake.connector

from triage.query import check_statement, query_postgres, query_snowflake

MAX_DIFFS = 10


@dataclass
class PairResult:
    name: str
    requirement: str
    passed: bool
    detail: str


def normalize(value: Any) -> Any:
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int | float | Decimal):
        return Decimal(str(value)).normalize()
    if isinstance(value, dt.datetime):
        return value.astimezone(dt.UTC) if value.tzinfo else value
    return value


def requirement_of(sql: str) -> str:
    match = re.search(r"--\s*requirement:\s*((?:MIG|ETL)-\d{3})", sql)
    return match[1] if match else "untagged"


def compare(source: list[tuple], target: list[tuple]) -> str:
    """Empty string when the result sets are identical, else a short description."""
    src = [tuple(map(normalize, r)) for r in source]
    tgt = [tuple(map(normalize, r)) for r in target]
    if src == tgt:
        return ""
    if src and tgt and len(src[0]) != len(tgt[0]):
        return f"column count differs: source {len(src[0])}, target {len(tgt[0])}"
    diffs = [(i, s, t) for i, (s, t) in enumerate(zip(src, tgt, strict=False)) if s != t]
    lines = [f"rows: source {len(src)}, target {len(tgt)}; first differing positions:"]
    lines += [f"  #{i}: source={s} target={t}" for i, s, t in diffs[:MAX_DIFFS]]
    return "\n".join(lines)


# A string literal, or a line comment. Snowflake treats backslash as an escape inside
# literals; Postgres (standard_conforming_strings) doesn't, so 'C:\' is a whole literal there.
LITERAL_OR_COMMENT = {
    "postgres": re.compile(r"('(?:[^']|'')*')|--[^\n]*"),
    "snowflake": re.compile(r"('(?:[^'\\]|\\.|'')*')|--[^\n]*"),
}


def statement_of(sql: str, dialect: str) -> str:
    """The SQL without line comments, checked to be a single read-only statement.

    `--` inside a string literal is kept, so only real comments are removed.
    """
    stripped = LITERAL_OR_COMMENT[dialect].sub(lambda m: m[1] or "", sql)
    return check_statement(stripped)


def run_pair(directory: Path, name: str) -> PairResult:
    pg_sql = (directory / f"{name}.pg.sql").read_text()
    sf_sql = (directory / f"{name}.sf.sql").read_text()
    requirement = requirement_of(pg_sql)
    try:
        _, source = query_postgres(statement_of(pg_sql, "postgres"), limit=None)
        _, target = query_snowflake(statement_of(sf_sql, "snowflake"), limit=None)
    except (
        SystemExit,
        psycopg.Error,
        snowflake.connector.errors.Error,
    ) as e:  # fail the pair, not the run
        return PairResult(name, requirement, False, f"could not run: {e}")
    detail = compare(source, target)
    return PairResult(name, requirement, not detail, detail or f"{len(source)} rows match")


def pair_names(directory: Path) -> list[str]:
    pg = {p.name.removesuffix(".pg.sql") for p in directory.glob("*.pg.sql")}
    sf = {p.name.removesuffix(".sf.sql") for p in directory.glob("*.sf.sql")}
    if unpaired := pg ^ sf:
        raise SystemExit(f"checks missing one side: {sorted(unpaired)}")
    return sorted(pg)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("directory", type=Path)
    parser.add_argument("names", nargs="*", help="check names (default: all pairs)")
    args = parser.parse_args()
    names = args.names or pair_names(args.directory)

    results = [run_pair(args.directory, n) for n in names]
    for r in results:
        print(f"{'PASS' if r.passed else 'FAIL'}  {r.requirement:8} {r.name}: {r.detail}")
    passed = sum(r.passed for r in results)
    print(f"\n{passed}/{len(results)} checks passed")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
