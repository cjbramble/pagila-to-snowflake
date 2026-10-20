"""Generate Snowflake DDL for the RAW tables from the mapping spec."""

from typing import Any

from migrate.mapping import load_spec


def target_table(spec: dict[str, Any], table: str) -> str:
    """Fully qualified Snowflake name for a source table."""
    target = spec["target"]
    return f"{target['database']}.{target['schema']}.{table.upper()}"


def create_table_sql(spec: dict[str, Any], table: str) -> str:
    """CREATE OR REPLACE TABLE for one source table; excluded columns are omitted."""
    table_spec = spec["tables"][table]
    columns = {c: m for c, m in table_spec["columns"].items() if not m.get("exclude")}

    lines = []
    for column, m in columns.items():
        if "virtual" in m:
            if not m["nullable"]:
                raise ValueError(f"{table}.{column}: Snowflake virtual columns can't be NOT NULL")
            lines.append(f"{column.upper()} {m['target_type']} AS ({m['virtual']}) VIRTUAL")
        else:
            not_null = "" if m["nullable"] else " NOT NULL"
            lines.append(f"{column.upper()} {m['target_type']}{not_null}")

    primary_key = ", ".join(c.upper() for c in table_spec["primary_key"])
    lines.append(f"CONSTRAINT {table.upper()}_PK PRIMARY KEY ({primary_key})")
    for column, m in columns.items():
        if "check" in m:
            lines.append(f"CONSTRAINT {table.upper()}_{column.upper()}_CHK CHECK ({m['check']})")

    body = ",\n    ".join(lines)
    return f"CREATE OR REPLACE TABLE {target_table(spec, table)} (\n    {body}\n)"


def main() -> None:
    spec = load_spec()
    print(";\n\n".join(create_table_sql(spec, t) for t in spec["tables"]) + ";")


if __name__ == "__main__":
    main()
