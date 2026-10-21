-- requirement: MIG-004
-- payment: per-column null count, distinct count, min, max, sum (sum of length for text, of epoch microseconds for timestamps, of days for dates, of array sizes for arrays, count of true for booleans).
SELECT 'payment_id' AS column_name, (COUNT(*) - COUNT(payment_id))::bigint AS null_count, COUNT(DISTINCT payment_id::text)::bigint AS distinct_count,
       COALESCE((MIN(payment_id))::text, '') AS min_val, COALESCE((MAX(payment_id))::text, '') AS max_val, COALESCE((SUM(payment_id))::text, '') AS sum_val
FROM public.payment
UNION ALL
SELECT 'customer_id' AS column_name, (COUNT(*) - COUNT(customer_id))::bigint AS null_count, COUNT(DISTINCT customer_id::text)::bigint AS distinct_count,
       COALESCE((MIN(customer_id))::text, '') AS min_val, COALESCE((MAX(customer_id))::text, '') AS max_val, COALESCE((SUM(customer_id))::text, '') AS sum_val
FROM public.payment
UNION ALL
SELECT 'staff_id' AS column_name, (COUNT(*) - COUNT(staff_id))::bigint AS null_count, COUNT(DISTINCT staff_id::text)::bigint AS distinct_count,
       COALESCE((MIN(staff_id))::text, '') AS min_val, COALESCE((MAX(staff_id))::text, '') AS max_val, COALESCE((SUM(staff_id))::text, '') AS sum_val
FROM public.payment
UNION ALL
SELECT 'rental_id' AS column_name, (COUNT(*) - COUNT(rental_id))::bigint AS null_count, COUNT(DISTINCT rental_id::text)::bigint AS distinct_count,
       COALESCE((MIN(rental_id))::text, '') AS min_val, COALESCE((MAX(rental_id))::text, '') AS max_val, COALESCE((SUM(rental_id))::text, '') AS sum_val
FROM public.payment
UNION ALL
SELECT 'amount' AS column_name, (COUNT(*) - COUNT(amount))::bigint AS null_count, COUNT(DISTINCT amount::text)::bigint AS distinct_count,
       COALESCE((MIN(amount))::text, '') AS min_val, COALESCE((MAX(amount))::text, '') AS max_val, COALESCE((SUM(amount))::text, '') AS sum_val
FROM public.payment
UNION ALL
SELECT 'payment_date' AS column_name, (COUNT(*) - COUNT(payment_date))::bigint AS null_count, COUNT(DISTINCT to_char(payment_date AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US'))::bigint AS distinct_count,
       COALESCE(to_char(MIN(payment_date) AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US'), '') AS min_val, COALESCE(to_char(MAX(payment_date) AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US'), '') AS max_val, COALESCE((SUM((extract(epoch from payment_date) * 1000000)::bigint))::text, '') AS sum_val
FROM public.payment
UNION ALL
SELECT 'uuid' AS column_name, (COUNT(*) - COUNT(uuid))::bigint AS null_count, COUNT(DISTINCT lower(uuid::text))::bigint AS distinct_count,
       COALESCE(MIN(lower(uuid::text) COLLATE "C"), '') AS min_val, COALESCE(MAX(lower(uuid::text) COLLATE "C"), '') AS max_val, COALESCE('', '') AS sum_val
FROM public.payment
ORDER BY column_name
