"""Integrity: no orphaned relationships (MIG-007) and source domain rules hold (MIG-008)."""

import pytest
from snowflake.connector import DictCursor

from migrate.ddl import target_table

# (child table, child column, parent table, parent column).
# The source declares these as foreign keys, except store.manager_staff_id, which has no
# declared FK, and payment's, which only 6 of its 55 partitions declare.
RELATIONSHIPS = [
    ("address", "city_id", "city", "city_id"),
    ("city", "country_id", "country", "country_id"),
    ("customer", "address_id", "address", "address_id"),
    ("customer", "store_id", "store", "store_id"),
    ("film", "language_id", "language", "language_id"),
    ("film", "original_language_id", "language", "language_id"),
    ("film_actor", "actor_id", "actor", "actor_id"),
    ("film_actor", "film_id", "film", "film_id"),
    ("film_category", "category_id", "category", "category_id"),
    ("film_category", "film_id", "film", "film_id"),
    ("film_embedding", "film_id", "film", "film_id"),
    ("inventory", "film_id", "film", "film_id"),
    ("inventory", "store_id", "store", "store_id"),
    ("payment", "customer_id", "customer", "customer_id"),
    ("payment", "rental_id", "rental", "rental_id"),
    ("payment", "staff_id", "staff", "staff_id"),
    ("rental", "customer_id", "customer", "customer_id"),
    ("rental", "inventory_id", "inventory", "inventory_id"),
    ("rental", "staff_id", "staff", "staff_id"),
    ("staff", "address_id", "address", "address_id"),
    ("staff", "store_id", "store", "store_id"),
    ("store", "address_id", "address", "address_id"),
    ("store", "manager_staff_id", "staff", "staff_id"),
]


@pytest.mark.req("MIG-007")
@pytest.mark.parametrize(
    "child,child_col,parent,parent_col",
    RELATIONSHIPS,
    ids=[f"{r[0]}.{r[1]}" for r in RELATIONSHIPS],
)
def test_no_orphans_in_target(sf, spec, child, child_col, parent, parent_col):
    # A null key is "no relationship", not an orphan.
    rows = (
        sf.cursor()
        .execute(
            f"""SELECT DISTINCT c.{child_col}
            FROM {target_table(spec, child)} c
            WHERE c.{child_col} IS NOT NULL
              AND NOT EXISTS (SELECT 1 FROM {target_table(spec, parent)} p
                              WHERE p.{parent_col} = c.{child_col})
            ORDER BY 1 LIMIT 20"""
        )
        .fetchall()
    )
    assert not rows, f"orphaned {child}.{child_col} values (first 20): {[r[0] for r in rows]}"


@pytest.mark.req("MIG-008")
def test_film_domain_rules_hold(sf, spec):
    film = target_table(spec, "film")
    columns = spec["tables"]["film"]["columns"]
    violations = {}
    for column in ("rating", "release_year"):
        rule = columns[column]["check"]
        n = sf.cursor().execute(f"SELECT count(*) FROM {film} WHERE NOT ({rule})").fetchone()[0]
        violations[column] = n
    assert violations == {"rating": 0, "release_year": 0}


@pytest.mark.req("MIG-008")
def test_film_check_constraints_exist(sf, spec):
    rows = sf.cursor(DictCursor).execute(f"DESC TABLE {target_table(spec, 'film')}")
    checks = {r["name"]: r["check"] for r in rows if r["check"]}
    columns = spec["tables"]["film"]["columns"]
    assert checks == {
        "RELEASE_YEAR": columns["release_year"]["check"],
        "RATING": columns["rating"]["check"],
    }
