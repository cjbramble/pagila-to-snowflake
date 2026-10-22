-- requirement: MIG-004
-- rental: per-column null count, distinct count, min, max, sum (sum of length for text, of epoch microseconds for timestamps, of days for dates, of array sizes for arrays, count of true for booleans).
SELECT 'rental_id' AS column_name, (COUNT(*) - COUNT(rental_id))::bigint AS null_count, COUNT(DISTINCT rental_id::text)::bigint AS distinct_count,
       COALESCE((MIN(rental_id))::text, '') AS min_val, COALESCE((MAX(rental_id))::text, '') AS max_val, COALESCE((SUM(rental_id))::text, '') AS sum_val
FROM public.rental
UNION ALL
SELECT 'rental_date' AS column_name, (COUNT(*) - COUNT(rental_date))::bigint AS null_count, COUNT(DISTINCT to_char(rental_date AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US'))::bigint AS distinct_count,
       COALESCE(to_char(MIN(rental_date) AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US'), '') AS min_val, COALESCE(to_char(MAX(rental_date) AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US'), '') AS max_val, COALESCE((SUM((extract(epoch from rental_date) * 1000000)::bigint))::text, '') AS sum_val
FROM public.rental
UNION ALL
SELECT 'inventory_id' AS column_name, (COUNT(*) - COUNT(inventory_id))::bigint AS null_count, COUNT(DISTINCT inventory_id::text)::bigint AS distinct_count,
       COALESCE((MIN(inventory_id))::text, '') AS min_val, COALESCE((MAX(inventory_id))::text, '') AS max_val, COALESCE((SUM(inventory_id))::text, '') AS sum_val
FROM public.rental
UNION ALL
SELECT 'customer_id' AS column_name, (COUNT(*) - COUNT(customer_id))::bigint AS null_count, COUNT(DISTINCT customer_id::text)::bigint AS distinct_count,
       COALESCE((MIN(customer_id))::text, '') AS min_val, COALESCE((MAX(customer_id))::text, '') AS max_val, COALESCE((SUM(customer_id))::text, '') AS sum_val
FROM public.rental
UNION ALL
SELECT 'return_date' AS column_name, (COUNT(*) - COUNT(return_date))::bigint AS null_count, COUNT(DISTINCT to_char(return_date AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US'))::bigint AS distinct_count,
       COALESCE(to_char(MIN(return_date) AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US'), '') AS min_val, COALESCE(to_char(MAX(return_date) AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US'), '') AS max_val, COALESCE((SUM((extract(epoch from return_date) * 1000000)::bigint))::text, '') AS sum_val
FROM public.rental
UNION ALL
SELECT 'staff_id' AS column_name, (COUNT(*) - COUNT(staff_id))::bigint AS null_count, COUNT(DISTINCT staff_id::text)::bigint AS distinct_count,
       COALESCE((MIN(staff_id))::text, '') AS min_val, COALESCE((MAX(staff_id))::text, '') AS max_val, COALESCE((SUM(staff_id))::text, '') AS sum_val
FROM public.rental
UNION ALL
SELECT 'last_update' AS column_name, (COUNT(*) - COUNT(last_update))::bigint AS null_count, COUNT(DISTINCT to_char(last_update AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US'))::bigint AS distinct_count,
       COALESCE(to_char(MIN(last_update) AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US'), '') AS min_val, COALESCE(to_char(MAX(last_update) AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US'), '') AS max_val, COALESCE((SUM((extract(epoch from last_update) * 1000000)::bigint))::text, '') AS sum_val
FROM public.rental
UNION ALL
SELECT 'uuid' AS column_name, (COUNT(*) - COUNT(uuid))::bigint AS null_count, COUNT(DISTINCT lower(uuid::text))::bigint AS distinct_count,
       COALESCE(MIN(lower(uuid::text) COLLATE "C"), '') AS min_val, COALESCE(MAX(lower(uuid::text) COLLATE "C"), '') AS max_val, COALESCE('', '') AS sum_val
FROM public.rental
ORDER BY column_name
