"""Normalized row hashes, generated from the mapping spec for both dialects.

Produces the same canonical text as the hand-written pair in sql/reconciliation/
(payment_row_hash_*.sql documents the format); a test proves they agree on payment.
"""

import re
from dataclasses import dataclass
from typing import Any

from reconcile.aggregates import compared_columns

PG_TS = """to_char({} AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"')"""
SF_TS = """TO_VARCHAR(CONVERT_TIMEZONE('UTC', {}), 'YYYY-MM-DD"T"HH24:MI:SS.FF6"Z"')"""
# Vector elements are float32 (about 7 significant digits); both sides round the same
# double value to 9 decimals, which separates any two distinct float32 values in [0, 1].
PG_VECTOR = (
    "(SELECT string_agg(to_char(round(e::float8::numeric, 9), 'FM999990.000000000'), ','"
    " ORDER BY i) FROM unnest({}::real[]) WITH ORDINALITY AS u(e, i))"
)
SF_VECTOR = (
    "ARRAY_TO_STRING(TRANSFORM({}::ARRAY,"
    " x -> TO_VARCHAR(ROUND(x::FLOAT, 9), 'FM999990.000000000')), ',')"
)


def number_format(target_type: str) -> str | None:
    """Fixed-scale format model for NUMBER(p,s) with s > 0, e.g. NUMBER(5,2) -> FM990.00."""
    match = re.fullmatch(r"NUMBER\((\d+),(\d+)\)", target_type)
    if not match or match[2] == "0":
        return None
    precision, scale = int(match[1]), int(match[2])
    return "FM" + "9" * (precision - scale - 1) + "0." + "0" * scale


def postgres_value(column: str, mapping: dict[str, Any]) -> str:
    col, target = f'"{column}"', mapping["target_type"]
    if fmt := number_format(target):
        return f"to_char({col}, '{fmt}')"
    if target.startswith("TIMESTAMP_TZ"):
        return PG_TS.format(col)
    if target == "DATE":
        return f"to_char({col}, 'YYYY-MM-DD')"
    if target == "UUID":
        return f"lower({col}::text)"
    if target == "BOOLEAN":
        return f"CASE WHEN {col} THEN 'true' ELSE 'false' END"
    if target == "ARRAY":
        return f"array_to_json({col})::text"
    if target.startswith("VECTOR"):
        return PG_VECTOR.format(col)
    if target.startswith("BINARY"):
        return f"encode({col}, 'hex')"
    return f"{col}::text"  # integers, text, enums


def snowflake_value(column: str, mapping: dict[str, Any]) -> str:
    col, target = column.upper(), mapping["target_type"]
    if fmt := number_format(target):
        return f"TO_VARCHAR({col}, '{fmt}')"
    if target.startswith("TIMESTAMP_TZ"):
        return SF_TS.format(col)
    if target == "DATE":
        return f"TO_VARCHAR({col}, 'YYYY-MM-DD')"
    if target == "UUID":
        return f"LOWER(TO_VARCHAR({col}))"
    if target == "BOOLEAN":
        return f"CASE WHEN {col} THEN 'true' ELSE 'false' END"
    if target == "ARRAY":
        return f"TO_JSON({col})"
    if target.startswith("VECTOR"):
        return SF_VECTOR.format(col)
    if target.startswith("BINARY"):
        return f"LOWER(HEX_ENCODE({col}))"
    return f"TO_VARCHAR({col})"


def row_hash_sql(dialect: str, table_ref: str, table_spec: dict[str, Any]) -> str:
    """SELECT row_key, row_hash for every row; columns in spec order."""
    if dialect == "postgres":
        value, sep, md5, ident = postgres_value, "chr(31)", "md5", lambda c: f'"{c}"'
    else:
        value, sep, md5, ident = snowflake_value, "CHR(31)", "MD5", str.upper
    columns = compared_columns(table_spec)
    # NULL -> '0', value -> '1' || value: dialect-neutral and collision-free.
    flagged = [
        f"CASE WHEN {ident(c)} IS NULL THEN '0' ELSE '1' || {value(c, m)} END"
        for c, m in columns.items()
    ]
    key = f" || {sep} || ".join(value(c, columns[c]) for c in table_spec["primary_key"])
    return (
        f"SELECT {key} AS row_key,\n"
        f"  {md5}(CONCAT_WS({sep},\n    " + ",\n    ".join(flagged) + "\n  )) AS row_hash\n"
        f"FROM {table_ref}"
    )


@dataclass
class RowDiff:
    missing: list[str]  # in source, not in target
    extra: list[str]  # in target, not in source
    changed: list[str]  # in both, different content
    duplicated_source: list[str]  # key appears more than once in the source
    duplicated_target: list[str]  # key appears more than once in the target

    @property
    def ok(self) -> bool:
        return not (
            self.missing
            or self.extra
            or self.changed
            or self.duplicated_source
            or self.duplicated_target
        )

    def describe(self, limit: int = 20) -> str:
        parts = []
        for name, keys in (
            ("missing", self.missing),
            ("extra", self.extra),
            ("changed", self.changed),
            ("duplicated in source", self.duplicated_source),
            ("duplicated in target", self.duplicated_target),
        ):
            if keys:
                shown = ", ".join(k.replace("\x1f", "|") for k in keys[:limit])
                more = f" (+{len(keys) - limit} more)" if len(keys) > limit else ""
                parts.append(f"{name} {len(keys)}: {shown}{more}")
        return "; ".join(parts)


def _by_key(rows: list[tuple[str, str]]) -> tuple[dict[str, str], list[str]]:
    """First hash per key, plus the keys that occur more than once."""
    hashes: dict[str, str] = {}
    duplicated: set[str] = set()
    for key, row_hash in rows:
        if key in hashes:
            duplicated.add(key)
        else:
            hashes[key] = row_hash
    return hashes, sorted(duplicated)


def diff(source_rows: list[tuple[str, str]], target_rows: list[tuple[str, str]]) -> RowDiff:
    """Compare (row_key, row_hash) rows from both sides, duplicates included."""
    source, duplicated_source = _by_key(source_rows)
    target, duplicated_target = _by_key(target_rows)
    return RowDiff(
        missing=sorted(source.keys() - target.keys()),
        extra=sorted(target.keys() - source.keys()),
        changed=sorted(k for k in source.keys() & target.keys() if source[k] != target[k]),
        duplicated_source=duplicated_source,
        duplicated_target=duplicated_target,
    )
