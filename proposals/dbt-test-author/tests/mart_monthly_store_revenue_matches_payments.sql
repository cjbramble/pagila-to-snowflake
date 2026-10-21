{{ config(meta={'requirement': ['ETL-001', 'ETL-002']}) }}
-- Independent recompute from raw tables: every raw payment lands in exactly one
-- (store, UTC month) and the mart equals the recompute exactly. Rows returned are mismatches.
with expected as (
    select
        i.store_id,
        date_trunc('month', convert_timezone('UTC', p.payment_date))::date as revenue_month,
        count(*) as payment_count,
        sum(p.amount) as revenue
    from {{ source('raw', 'payment') }} as p
    join {{ source('raw', 'rental') }} as r on r.rental_id = p.rental_id
    join {{ source('raw', 'inventory') }} as i on i.inventory_id = r.inventory_id
    group by 1, 2
)
select coalesce(m.store_id, e.store_id) as store_id,
       coalesce(m.revenue_month, e.revenue_month) as revenue_month,
       m.payment_count, e.payment_count as expected_count,
       m.revenue, e.revenue as expected_revenue
from {{ ref('mart_monthly_store_revenue') }} as m
full outer join expected as e
    on e.store_id = m.store_id and e.revenue_month = m.revenue_month
where m.store_id is null or e.store_id is null
   or m.payment_count != e.payment_count or m.revenue != e.revenue
