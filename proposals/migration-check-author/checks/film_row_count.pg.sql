-- requirement: MIG-003
-- film: total rows and distinct primary keys (detects missing, extra, duplicate rows).
SELECT COUNT(*) AS row_count,
       COUNT(DISTINCT film_id::text) AS distinct_pk_count
FROM public.film
