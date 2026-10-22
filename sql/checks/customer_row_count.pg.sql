-- requirement: MIG-003
-- customer: total rows and distinct primary keys (detects missing, extra, duplicate rows).
SELECT COUNT(*) AS row_count,
       COUNT(DISTINCT customer_id::text) AS distinct_pk_count
FROM public.customer
