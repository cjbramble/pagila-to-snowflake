-- requirement: MIG-004
-- customer: per-column null count, distinct count, min, max, sum (sum of length for text, of epoch microseconds for timestamps, of days for dates, of array sizes for arrays, count of true for booleans).
SELECT 'customer_id' AS column_name, (COUNT(*) - COUNT(customer_id))::bigint AS null_count, COUNT(DISTINCT customer_id::text)::bigint AS distinct_count,
       COALESCE((MIN(customer_id))::text, '') AS min_val, COALESCE((MAX(customer_id))::text, '') AS max_val, COALESCE((SUM(customer_id))::text, '') AS sum_val
FROM public.customer
UNION ALL
SELECT 'store_id' AS column_name, (COUNT(*) - COUNT(store_id))::bigint AS null_count, COUNT(DISTINCT store_id::text)::bigint AS distinct_count,
       COALESCE((MIN(store_id))::text, '') AS min_val, COALESCE((MAX(store_id))::text, '') AS max_val, COALESCE((SUM(store_id))::text, '') AS sum_val
FROM public.customer
UNION ALL
SELECT 'first_name' AS column_name, (COUNT(*) - COUNT(first_name))::bigint AS null_count, COUNT(DISTINCT first_name)::bigint AS distinct_count,
       COALESCE(MIN(first_name COLLATE "C"), '') AS min_val, COALESCE(MAX(first_name COLLATE "C"), '') AS max_val, COALESCE((SUM(length(first_name)))::text, '') AS sum_val
FROM public.customer
UNION ALL
SELECT 'last_name' AS column_name, (COUNT(*) - COUNT(last_name))::bigint AS null_count, COUNT(DISTINCT last_name)::bigint AS distinct_count,
       COALESCE(MIN(last_name COLLATE "C"), '') AS min_val, COALESCE(MAX(last_name COLLATE "C"), '') AS max_val, COALESCE((SUM(length(last_name)))::text, '') AS sum_val
FROM public.customer
UNION ALL
SELECT 'email' AS column_name, (COUNT(*) - COUNT(email))::bigint AS null_count, COUNT(DISTINCT email)::bigint AS distinct_count,
       COALESCE(MIN(email COLLATE "C"), '') AS min_val, COALESCE(MAX(email COLLATE "C"), '') AS max_val, COALESCE((SUM(length(email)))::text, '') AS sum_val
FROM public.customer
UNION ALL
SELECT 'address_id' AS column_name, (COUNT(*) - COUNT(address_id))::bigint AS null_count, COUNT(DISTINCT address_id::text)::bigint AS distinct_count,
       COALESCE((MIN(address_id))::text, '') AS min_val, COALESCE((MAX(address_id))::text, '') AS max_val, COALESCE((SUM(address_id))::text, '') AS sum_val
FROM public.customer
UNION ALL
SELECT 'activebool' AS column_name, (COUNT(*) - COUNT(activebool))::bigint AS null_count, COUNT(DISTINCT (CASE WHEN activebool THEN '1' ELSE '0' END))::bigint AS distinct_count,
       COALESCE('', '') AS min_val, COALESCE('', '') AS max_val, COALESCE((SUM(CASE WHEN activebool THEN 1 ELSE 0 END))::text, '') AS sum_val
FROM public.customer
UNION ALL
SELECT 'create_date' AS column_name, (COUNT(*) - COUNT(create_date))::bigint AS null_count, COUNT(DISTINCT to_char(create_date, 'YYYY-MM-DD'))::bigint AS distinct_count,
       COALESCE(to_char(MIN(create_date), 'YYYY-MM-DD'), '') AS min_val, COALESCE(to_char(MAX(create_date), 'YYYY-MM-DD'), '') AS max_val, COALESCE((SUM(create_date - DATE '1970-01-01'))::text, '') AS sum_val
FROM public.customer
UNION ALL
SELECT 'last_update' AS column_name, (COUNT(*) - COUNT(last_update))::bigint AS null_count, COUNT(DISTINCT to_char(last_update AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US'))::bigint AS distinct_count,
       COALESCE(to_char(MIN(last_update) AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US'), '') AS min_val, COALESCE(to_char(MAX(last_update) AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US'), '') AS max_val, COALESCE((SUM((extract(epoch from last_update) * 1000000)::bigint))::text, '') AS sum_val
FROM public.customer
UNION ALL
SELECT 'active' AS column_name, (COUNT(*) - COUNT(active))::bigint AS null_count, COUNT(DISTINCT active::text)::bigint AS distinct_count,
       COALESCE((MIN(active))::text, '') AS min_val, COALESCE((MAX(active))::text, '') AS max_val, COALESCE((SUM(active))::text, '') AS sum_val
FROM public.customer
UNION ALL
SELECT 'uuid' AS column_name, (COUNT(*) - COUNT(uuid))::bigint AS null_count, COUNT(DISTINCT lower(uuid::text))::bigint AS distinct_count,
       COALESCE(MIN(lower(uuid::text) COLLATE "C"), '') AS min_val, COALESCE(MAX(lower(uuid::text) COLLATE "C"), '') AS max_val, COALESCE('', '') AS sum_val
FROM public.customer
ORDER BY column_name
