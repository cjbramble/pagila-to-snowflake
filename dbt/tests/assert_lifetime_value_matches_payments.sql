-- ETL-003: every customer appears once and lifetime revenue adds up to total payments.
{{ config(meta={'requirement': 'ETL-003'}) }}

with mart as (
    select count(*) as customers, sum(lifetime_revenue) as revenue, sum(payment_count) as payments
    from {{ ref('mart_customer_lifetime_value') }}
),

source as (
    select
        (select count(*) from {{ ref('stg_customer') }}) as customers,
        (select sum(amount) from {{ ref('stg_payment') }}) as revenue,
        (select count(*) from {{ ref('stg_payment') }}) as payments
)

select *
from mart, source
where mart.customers <> source.customers
   or mart.revenue <> source.revenue
   or mart.payments <> source.payments
