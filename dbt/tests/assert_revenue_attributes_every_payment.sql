-- ETL-001/002: every payment lands in exactly one store-month, so counts and totals
-- match the payments table. Returns a row on mismatch.
{{ config(meta={'requirement': ['ETL-001', 'ETL-002']}) }}

with mart as (
    select sum(payment_count) as payments, sum(revenue) as revenue
    from {{ ref('mart_monthly_store_revenue') }}
),

source as (
    select count(*) as payments, sum(amount) as revenue
    from {{ ref('stg_payment') }}
)

select *
from mart, source
where mart.payments <> source.payments or mart.revenue <> source.revenue
