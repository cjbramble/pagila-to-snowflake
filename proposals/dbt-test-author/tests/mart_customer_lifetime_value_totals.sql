{{ config(meta={'requirement': 'ETL-003'}) }}
-- Totals tie to source: revenue, payment count, rental count, customer count.
with m as (
    select count(*) as customers, sum(lifetime_revenue) as revenue,
           sum(payment_count) as payments, sum(rental_count) as rentals
    from {{ ref('mart_customer_lifetime_value') }}
)
select m.*
from m
cross join (select count(*) as n from {{ source('raw', 'customer') }}) c
cross join (select count(*) as n, sum(amount) as total from {{ source('raw', 'payment') }}) p
cross join (select count(*) as n from {{ source('raw', 'rental') }}) r
where m.customers != c.n or m.revenue != p.total or m.payments != p.n or m.rentals != r.n
