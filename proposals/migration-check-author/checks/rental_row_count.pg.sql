-- requirement: MIG-003
-- rental: total rows and distinct primary keys (detects missing, extra, duplicate rows).
SELECT COUNT(*) AS row_count,
       COUNT(DISTINCT rental_id::text) AS distinct_pk_count
FROM public.rental
