{{ config(meta={'requirement': ['ETL-001', 'ETL-002']}) }}
-- Every payment is attributed exactly once: mart totals equal raw payment totals, and no
-- payment is orphaned (no rental/inventory match) or duplicated by the joins.
with src as (
    select count(*) as n, sum(amount) as total from {{ source('raw', 'payment') }}
),
mart as (
    select sum(payment_count) as n, sum(revenue) as total from {{ ref('mart_monthly_store_revenue') }}
),
attributed as (
    select count(*) as n
    from {{ source('raw', 'payment') }} as p
    join {{ source('raw', 'rental') }} as r on r.rental_id = p.rental_id
    join {{ source('raw', 'inventory') }} as i on i.inventory_id = r.inventory_id
)
select src.n as src_n, mart.n as mart_n, attributed.n as attributed_n,
       src.total as src_total, mart.total as mart_total
from src, mart, attributed
where src.n != mart.n or src.total != mart.total or src.n != attributed.n
