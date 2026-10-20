"""Business-rule reconciliation: dbt marts vs an independent Postgres implementation.

The legacy rule (get_customer_balance) can't run, so each ETL rule is re-implemented here
in Postgres, differently on purpose (epoch arithmetic instead of DATEDIFF), against the
untouched source. Both implementations of the written rule must agree row for row.
"""

from decimal import Decimal

import pytest

MARTS = "PAGILA_MIG.MARTS"

pytestmark = [pytest.mark.source_db, pytest.mark.target_db]


def normalize(row: tuple) -> tuple:
    return tuple(Decimal(str(v)) if isinstance(v, int | float | Decimal) else v for v in row)


def keyed(rows) -> dict:
    return {normalize(r)[0]: normalize(r)[1:] for r in rows}


def mismatches(source: dict, target: dict, limit: int = 10) -> str:
    keys = sorted(set(source) | set(target), key=str)
    bad = [k for k in keys if source.get(k) != target.get(k)]
    shown = "\n  ".join(f"{k}: source={source.get(k)} mart={target.get(k)}" for k in bad[:limit])
    return f"{len(bad)} of {len(keys)} keys differ:\n  {shown}" if bad else ""


@pytest.mark.req("ETL-001", "ETL-002")
def test_monthly_store_revenue_matches_source(pg, sf):
    source = pg.execute(
        """SELECT i.store_id || '|' || date_trunc('month', p.payment_date AT TIME ZONE 'UTC')::date,
                  count(*), sum(p.amount)
           FROM payment p
           JOIN rental r USING (rental_id)
           JOIN inventory i USING (inventory_id)
           GROUP BY 1"""
    ).fetchall()
    target = (
        sf.cursor()
        .execute(
            f"""SELECT store_id || '|' || TO_VARCHAR(revenue_month, 'YYYY-MM-DD'),
                   payment_count, revenue
            FROM {MARTS}.MART_MONTHLY_STORE_REVENUE"""
        )
        .fetchall()
    )
    assert not (diff := mismatches(keyed(source), keyed(target))), diff


@pytest.mark.req("ETL-001")
def test_store_totals_match_legacy_sales_by_store_view(pg, sf):
    legacy = sorted(Decimal(r[0]) for r in pg.execute("SELECT total_sales FROM sales_by_store"))
    mart = sorted(
        Decimal(r[0])
        for r in sf.cursor().execute(
            f"SELECT SUM(revenue) FROM {MARTS}.MART_MONTHLY_STORE_REVENUE GROUP BY store_id"
        )
    )
    assert mart == legacy


@pytest.mark.req("ETL-003")
def test_customer_lifetime_value_matches_source(pg, sf):
    source = pg.execute(
        """SELECT c.customer_id, coalesce(p.revenue, 0), coalesce(p.n, 0), coalesce(r.n, 0),
                  p.first_at, p.last_at
           FROM customer c
           LEFT JOIN (SELECT customer_id, sum(amount) AS revenue, count(*) AS n,
                             min(payment_date) AS first_at, max(payment_date) AS last_at
                      FROM payment GROUP BY 1) p USING (customer_id)
           LEFT JOIN (SELECT customer_id, count(*) AS n FROM rental GROUP BY 1) r
                  USING (customer_id)"""
    ).fetchall()
    target = (
        sf.cursor()
        .execute(
            f"""SELECT customer_id, lifetime_revenue, payment_count, rental_count,
                   first_payment_at, last_payment_at
            FROM {MARTS}.MART_CUSTOMER_LIFETIME_VALUE"""
        )
        .fetchall()
    )
    assert not (diff := mismatches(keyed(source), keyed(target))), diff


@pytest.mark.req("ETL-004", "ETL-005", "ETL-006", "ETL-007")
def test_rental_returns_match_source(pg, sf):
    source = pg.execute(
        """WITH x AS (
               SELECT r.rental_id, r.return_date, f.rental_duration, f.replacement_cost,
                      r.rental_date + f.rental_duration * interval '1 day' AS due_at
               FROM rental r JOIN inventory i USING (inventory_id) JOIN film f USING (film_id)
           ), y AS (
               SELECT *, extract(epoch FROM return_date - due_at) AS secs_after_due FROM x
           )
           SELECT rental_id, due_at,
                  CASE WHEN return_date IS NULL THEN 'not_returned'
                       WHEN secs_after_due <= 0 THEN 'on_time' ELSE 'late' END,
                  CASE WHEN return_date IS NULL THEN NULL
                       WHEN secs_after_due <= 0 THEN 0 ELSE ceil(secs_after_due / 86400) END,
                  CASE WHEN return_date IS NULL THEN 'not_returned'
                       WHEN secs_after_due <= 0 THEN 'none'
                       WHEN secs_after_due > 2 * rental_duration * 86400 THEN 'replacement'
                       ELSE 'daily' END,
                  CASE WHEN return_date IS NULL THEN NULL
                       WHEN secs_after_due <= 0 THEN 0.00
                       WHEN secs_after_due > 2 * rental_duration * 86400 THEN replacement_cost
                       ELSE ceil(secs_after_due / 86400) * 1.00 END
           FROM y"""
    ).fetchall()
    target = (
        sf.cursor()
        .execute(
            f"""SELECT rental_id, due_at, return_status, days_late, fee_basis, late_fee
            FROM {MARTS}.MART_RENTAL_RETURNS"""
        )
        .fetchall()
    )
    assert not (diff := mismatches(keyed(source), keyed(target))), diff
