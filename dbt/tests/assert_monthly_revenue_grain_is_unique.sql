-- ETL-002: one row per store and month.
{{ config(meta={'requirement': 'ETL-002'}) }}

select store_id, revenue_month, count(*) as row_count
from {{ ref('mart_monthly_store_revenue') }}
group by store_id, revenue_month
having count(*) > 1
