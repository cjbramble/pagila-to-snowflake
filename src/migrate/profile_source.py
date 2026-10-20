"""Profile the source Postgres schema: tables, row counts, and columns with non-trivial types.

Connects with the standard PG* environment variables and prints Markdown to stdout.
"""

import psycopg
from psycopg import sql

SCHEMA = "public"

# Types that migrate to Snowflake with no decision to make. Everything else is listed.
TRIVIAL_TYPES = {"smallint", "integer", "bigint", "text", "boolean", "date"}

RELKIND_LABELS = {"r": "table", "p": "partitioned table", "v": "view", "m": "materialized view"}

RELATIONS_SQL = """
select c.relname, c.relkind, c.relispopulated,
       (select count(*) from pg_inherits i where i.inhparent = c.oid) as partitions
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = %(schema)s
  and c.relkind in ('r', 'p', 'v', 'm')
  and not c.relispartition
order by c.relkind, c.relname
"""

COLUMNS_SQL = """
select c.relname,
       a.attname,
       format_type(a.atttypid, a.atttypmod) as declared_type,
       t.typtype,
       t.typcategory,
       case when t.typtype = 'd' then format_type(t.typbasetype, t.typtypmod) end as domain_base,
       a.attnotnull,
       a.attgenerated,
       a.attidentity,
       pg_get_expr(d.adbin, d.adrelid) as default_expr
from pg_attribute a
join pg_class c on c.oid = a.attrelid
join pg_namespace n on n.oid = c.relnamespace
join pg_type t on t.oid = a.atttypid
left join pg_attrdef d on d.adrelid = a.attrelid and d.adnum = a.attnum
where n.nspname = %(schema)s
  and c.relkind in ('r', 'p')
  and not c.relispartition
  and a.attnum > 0
  and not a.attisdropped
order by c.relname, a.attnum
"""

ENUMS_SQL = """
select t.typname, string_agg(e.enumlabel, ', ' order by e.enumsortorder)
from pg_type t
join pg_namespace n on n.oid = t.typnamespace
join pg_enum e on e.enumtypid = t.oid
where n.nspname = %(schema)s
group by t.typname
order by t.typname
"""

DOMAINS_SQL = """
select t.typname,
       format_type(t.typbasetype, t.typtypmod),
       t.typnotnull,
       coalesce(string_agg(pg_get_constraintdef(con.oid), ' AND '), '')
from pg_type t
join pg_namespace n on n.oid = t.typnamespace
left join pg_constraint con on con.contypid = t.oid
where n.nspname = %(schema)s and t.typtype = 'd'
group by t.typname, t.typbasetype, t.typtypmod, t.typnotnull
order by t.typname
"""


def md_table(headers: list[str], rows: list[list[object]]) -> str:
    """Render rows as a Markdown table; pipes in values are escaped."""
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for row in rows:
        cells = ["" if v is None else str(v).replace("|", "\\|") for v in row]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def column_notes(
    typtype: str,
    typcategory: str,
    domain_base: str | None,
    generated: str,
    identity: str,
    default_expr: str | None,
) -> list[str]:
    """Describe what makes a column non-trivial to migrate."""
    notes = []
    if typtype == "d":
        notes.append(f"domain over {domain_base}")
    if typtype == "e":
        notes.append("enum")
    if typcategory == "A":
        notes.append("array")
    if generated:
        kind = {"s": "stored", "v": "virtual"}[generated]
        notes.append(f"generated {kind}: {default_expr}")
    elif default_expr and not default_expr.startswith("nextval("):
        notes.append(f"default {default_expr}")
    if identity:
        notes.append("identity")
    return notes


def main() -> None:
    params = {"schema": SCHEMA}
    with psycopg.connect() as conn:
        version = conn.execute("show server_version").fetchone()[0]
        timezone = conn.execute("show timezone").fetchone()[0]
        relations = conn.execute(RELATIONS_SQL, params).fetchall()
        columns = conn.execute(COLUMNS_SQL, params).fetchall()
        enums = conn.execute(ENUMS_SQL, params).fetchall()
        domains = conn.execute(DOMAINS_SQL, params).fetchall()

        relation_rows = []
        for name, relkind, populated, partitions in relations:
            # Reading an unpopulated materialized view errors, and refreshing it would
            # modify the source, so report it instead.
            if not populated:
                relation_rows.append([name, RELKIND_LABELS[relkind], "", "not populated"])
                continue
            query = sql.SQL("select count(*) from {}.{}").format(
                sql.Identifier(SCHEMA), sql.Identifier(name)
            )
            count = conn.execute(query).fetchone()[0]
            relation_rows.append([name, RELKIND_LABELS[relkind], partitions or "", count])

    hazard_rows = []
    for table, column, declared, typtype, typcat, base, notnull, gen, ident, default in columns:
        notes = column_notes(typtype, typcat, base, gen, ident, default)
        if declared in TRIVIAL_TYPES and not notes:
            continue
        hazard_rows.append([table, column, declared, "yes" if notnull else "", "; ".join(notes)])

    print(f"# Source profile: schema `{SCHEMA}`\n")
    print(f"PostgreSQL {version}, server timezone `{timezone}`.\n")
    tables = sum(1 for r in relation_rows if r[1] != "view" and r[1] != "materialized view")
    print(f"## Relations ({tables} tables, partitions folded into their parent)\n")
    print(md_table(["relation", "kind", "partitions", "rows"], relation_rows))
    print(f"\n## Non-trivial columns ({len(hazard_rows)} of {len(columns)})\n")
    print(f"Trivial and omitted: {', '.join(sorted(TRIVIAL_TYPES))} with no special default.\n")
    print(md_table(["table", "column", "type", "not null", "notes"], hazard_rows))
    print("\n## Enums\n")
    print(md_table(["type", "labels"], enums))
    print("\n## Domains\n")
    print(md_table(["domain", "base type", "not null", "constraints"], domains))


if __name__ == "__main__":
    main()
