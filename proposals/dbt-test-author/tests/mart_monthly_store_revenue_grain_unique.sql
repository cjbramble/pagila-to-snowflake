{{ config(meta={'requirement': 'ETL-002'}) }}
-- Grain: one row per store and month.
select store_id, revenue_month, count(*) as n
from {{ ref('mart_monthly_store_revenue') }}
group by store_id, revenue_month
having count(*) > 1
