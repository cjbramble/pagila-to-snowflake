-- requirement: MIG-004
-- address: per-column null count, distinct count, min, max, sum (sum of length for text, of epoch microseconds for timestamps, of days for dates, of array sizes for arrays, count of true for booleans).
SELECT 'address_id' AS column_name, (COUNT(*) - COUNT(address_id))::bigint AS null_count, COUNT(DISTINCT address_id::text)::bigint AS distinct_count,
       COALESCE((MIN(address_id))::text, '') AS min_val, COALESCE((MAX(address_id))::text, '') AS max_val, COALESCE((SUM(address_id))::text, '') AS sum_val
FROM public.address
UNION ALL
SELECT 'address' AS column_name, (COUNT(*) - COUNT(address))::bigint AS null_count, COUNT(DISTINCT address)::bigint AS distinct_count,
       COALESCE(MIN(address COLLATE "C"), '') AS min_val, COALESCE(MAX(address COLLATE "C"), '') AS max_val, COALESCE((SUM(length(address)))::text, '') AS sum_val
FROM public.address
UNION ALL
SELECT 'address2' AS column_name, (COUNT(*) - COUNT(address2))::bigint AS null_count, COUNT(DISTINCT address2)::bigint AS distinct_count,
       COALESCE(MIN(address2 COLLATE "C"), '') AS min_val, COALESCE(MAX(address2 COLLATE "C"), '') AS max_val, COALESCE((SUM(length(address2)))::text, '') AS sum_val
FROM public.address
UNION ALL
SELECT 'district' AS column_name, (COUNT(*) - COUNT(district))::bigint AS null_count, COUNT(DISTINCT district)::bigint AS distinct_count,
       COALESCE(MIN(district COLLATE "C"), '') AS min_val, COALESCE(MAX(district COLLATE "C"), '') AS max_val, COALESCE((SUM(length(district)))::text, '') AS sum_val
FROM public.address
UNION ALL
SELECT 'city_id' AS column_name, (COUNT(*) - COUNT(city_id))::bigint AS null_count, COUNT(DISTINCT city_id::text)::bigint AS distinct_count,
       COALESCE((MIN(city_id))::text, '') AS min_val, COALESCE((MAX(city_id))::text, '') AS max_val, COALESCE((SUM(city_id))::text, '') AS sum_val
FROM public.address
UNION ALL
SELECT 'postal_code' AS column_name, (COUNT(*) - COUNT(postal_code))::bigint AS null_count, COUNT(DISTINCT postal_code)::bigint AS distinct_count,
       COALESCE(MIN(postal_code COLLATE "C"), '') AS min_val, COALESCE(MAX(postal_code COLLATE "C"), '') AS max_val, COALESCE((SUM(length(postal_code)))::text, '') AS sum_val
FROM public.address
UNION ALL
SELECT 'phone' AS column_name, (COUNT(*) - COUNT(phone))::bigint AS null_count, COUNT(DISTINCT phone)::bigint AS distinct_count,
       COALESCE(MIN(phone COLLATE "C"), '') AS min_val, COALESCE(MAX(phone COLLATE "C"), '') AS max_val, COALESCE((SUM(length(phone)))::text, '') AS sum_val
FROM public.address
UNION ALL
SELECT 'last_update' AS column_name, (COUNT(*) - COUNT(last_update))::bigint AS null_count, COUNT(DISTINCT to_char(last_update AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US'))::bigint AS distinct_count,
       COALESCE(to_char(MIN(last_update) AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US'), '') AS min_val, COALESCE(to_char(MAX(last_update) AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US'), '') AS max_val, COALESCE((SUM((extract(epoch from last_update) * 1000000)::bigint))::text, '') AS sum_val
FROM public.address
ORDER BY column_name
