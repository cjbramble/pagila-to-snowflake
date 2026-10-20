-- ETL-001, ETL-002: revenue per store per UTC calendar month.

with payments as (
    select
        p.payment_id,
        p.amount,
        p.payment_date,
        i.store_id
    from {{ ref('stg_payment') }} as p
    inner join {{ ref('stg_rental') }} as r on r.rental_id = p.rental_id
    inner join {{ ref('stg_inventory') }} as i on i.inventory_id = r.inventory_id
)

select
    store_id,
    date_trunc('month', convert_timezone('UTC', payment_date))::date as revenue_month,
    count(*) as payment_count,
    sum(amount) as revenue
from payments
group by store_id, revenue_month
