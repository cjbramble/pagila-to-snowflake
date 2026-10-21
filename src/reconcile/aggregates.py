"""Per-column aggregate profiles, generated from the mapping spec for both dialects.

Each column gets the metrics that are comparable across Postgres and Snowflake for its
type. Text also gets the sum of value lengths, which catches truncation and added or lost
whitespace even when distinct counts and min/max don't move. Content of ARRAY, VECTOR, and
BINARY columns is compared by the row-hash layer.
"""

import datetime as dt
from decimal import Decimal
from typing import Any

METRICS_BY_KIND = {
    "number": ["nulls", "distinct", "min", "max", "sum"],
    "temporal": ["nulls", "distinct", "min", "max"],
    "text": ["nulls", "distinct", "min", "max", "length_sum"],
    "uuid": ["nulls", "distinct", "min", "max"],  # fixed length, so no length_sum
    "boolean": ["nulls", "true_count"],
    "other": ["nulls"],
}


def column_kind(target_type: str) -> str:
    if target_type.startswith("NUMBER"):
        return "number"
    if target_type.startswith("TIMESTAMP") or target_type == "DATE":
        return "temporal"
    if target_type.startswith("VARCHAR"):
        return "text"
    if target_type == "UUID":
        return "uuid"
    if target_type == "BOOLEAN":
        return "boolean"
    return "other"


def compared_columns(table_spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Every column present in the target, including virtual ones."""
    return {c: m for c, m in table_spec["columns"].items() if not m.get("exclude")}


def postgres_expr(metric: str, column: str, mapping: dict[str, Any]) -> str:
    col = f'"{column}"'
    # Snowflake compares strings by code point; Postgres uses the database locale unless
    # told otherwise, so COLLATE "C" makes min/max agree. Non-text sources that land as
    # text (uuid, and enums, which order by declaration) compare as their text form.
    if column_kind(mapping["target_type"]) in ("text", "uuid"):
        cast = "" if mapping["source_type"] == "text" else "::text"
        col = f'{col}{cast} COLLATE "C"'
    return {
        "nulls": f'count(*) - count("{column}")',
        "distinct": f"count(DISTINCT {col})",
        "min": f"min({col})",
        "max": f"max({col})",
        "sum": f"sum({col})",
        "true_count": f"count(*) FILTER (WHERE {col})",
        "length_sum": f"sum(length({col}))",
    }[metric]


def snowflake_expr(metric: str, column: str, mapping: dict[str, Any]) -> str:
    col = column.upper()
    if mapping["target_type"] == "UUID":
        col = f"TO_VARCHAR({col})"
    return {
        "nulls": f"COUNT(*) - COUNT({column.upper()})",
        "distinct": f"COUNT(DISTINCT {col})",
        "min": f"MIN({col})",
        "max": f"MAX({col})",
        "sum": f"SUM({col})",
        "true_count": f"COUNT_IF({col})",
        "length_sum": f"SUM(LENGTH({col}))",
    }[metric]


def metric_names(table_spec: dict[str, Any]) -> list[tuple[str, str]]:
    """(column, metric) pairs, in a stable order shared by both dialects."""
    return [
        (column, metric)
        for column, m in compared_columns(table_spec).items()
        for metric in METRICS_BY_KIND[column_kind(m["target_type"])]
    ]


def profile_sql(dialect: str, table_ref: str, table_spec: dict[str, Any]) -> str:
    expr = postgres_expr if dialect == "postgres" else snowflake_expr
    columns = compared_columns(table_spec)
    exprs = [expr(metric, c, columns[c]) for c, metric in metric_names(table_spec)]
    return f"SELECT {', '.join(exprs)} FROM {table_ref}"


def normalize(value: Any) -> Any:
    """Make driver values comparable: numbers as Decimal, timestamps in UTC."""
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int | float | Decimal):
        return Decimal(str(value))
    if isinstance(value, dt.datetime):
        return value.astimezone(dt.UTC)
    return value


def compare(table_spec: dict[str, Any], source_row: tuple, target_row: tuple) -> list[str]:
    """Describe every metric that differs; empty when the profiles match."""
    return [
        f"{column}.{metric}: source={s!r} target={t!r}"
        for (column, metric), s, t in zip(
            metric_names(table_spec),
            map(normalize, source_row),
            map(normalize, target_row),
            strict=True,
        )
        if s != t
    ]
