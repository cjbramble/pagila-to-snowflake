-- ETL-003: one row per customer. Payments and rentals are aggregated separately so a
-- rental with several payments can't multiply either count.

with payments as (
    select
        customer_id,
        count(*) as payment_count,
        sum(amount) as lifetime_revenue,
        convert_timezone('UTC', min(payment_date)) as first_payment_at,
        convert_timezone('UTC', max(payment_date)) as last_payment_at
    from {{ ref('stg_payment') }}
    group by customer_id
),

rentals as (
    select
        customer_id,
        count(*) as rental_count
    from {{ ref('stg_rental') }}
    group by customer_id
)

select
    c.customer_id,
    c.store_id,
    coalesce(p.lifetime_revenue, 0)::number(12, 2) as lifetime_revenue,
    coalesce(p.payment_count, 0) as payment_count,
    coalesce(r.rental_count, 0) as rental_count,
    p.first_payment_at,
    p.last_payment_at
from {{ ref('stg_customer') }} as c
left join payments as p on p.customer_id = c.customer_id
left join rentals as r on r.customer_id = c.customer_id
