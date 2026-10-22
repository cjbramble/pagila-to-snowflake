-- Written by the dbt-test-author agent in a blind run; promoted after human review.
{{ config(meta={'requirement': 'ETL-003'}) }}
-- Per-customer recompute from raw tables via correlated scalar subqueries (different
-- shape from the mart's join). Also covers: one row per customer, total revenue equals
-- total payments. Rows returned are mismatches.
with expected as (
    select
        c.customer_id,
        c.store_id,
        (select coalesce(sum(amount), 0) from {{ source('raw', 'payment') }} p where p.customer_id = c.customer_id) as lifetime_revenue,
        (select count(*) from {{ source('raw', 'payment') }} p where p.customer_id = c.customer_id) as payment_count,
        (select count(*) from {{ source('raw', 'rental') }} r where r.customer_id = c.customer_id) as rental_count,
        (select min(payment_date) from {{ source('raw', 'payment') }} p where p.customer_id = c.customer_id) as first_payment_at,
        (select max(payment_date) from {{ source('raw', 'payment') }} p where p.customer_id = c.customer_id) as last_payment_at
    from {{ source('raw', 'customer') }} as c
)
select coalesce(m.customer_id, e.customer_id) as customer_id
from {{ ref('mart_customer_lifetime_value') }} as m
full outer join expected as e on e.customer_id = m.customer_id
where m.customer_id is null or e.customer_id is null
   or m.store_id != e.store_id
   or m.lifetime_revenue != e.lifetime_revenue
   or m.payment_count != e.payment_count
   or m.rental_count != e.rental_count
   or m.first_payment_at is distinct from e.first_payment_at
   or m.last_payment_at is distinct from e.last_payment_at
