-- requirement: MIG-004
-- rental: per-column null count, distinct count, min, max, sum (sum of length for text, of epoch microseconds for timestamps, of days for dates, of array sizes for arrays, count of true for booleans).
SELECT 'rental_id' AS column_name, (COUNT(*) - COUNT(RENTAL_ID))::bigint AS null_count, COUNT(DISTINCT RENTAL_ID::varchar)::bigint AS distinct_count,
       COALESCE((MIN(RENTAL_ID))::varchar, '') AS min_val, COALESCE((MAX(RENTAL_ID))::varchar, '') AS max_val, COALESCE((SUM(RENTAL_ID))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.RENTAL
UNION ALL
SELECT 'rental_date' AS column_name, (COUNT(*) - COUNT(RENTAL_DATE))::bigint AS null_count, COUNT(DISTINCT TO_CHAR(CONVERT_TIMEZONE('UTC', RENTAL_DATE), 'YYYY-MM-DD"T"HH24:MI:SS.FF6'))::bigint AS distinct_count,
       COALESCE(TO_CHAR(CONVERT_TIMEZONE('UTC', MIN(RENTAL_DATE)), 'YYYY-MM-DD"T"HH24:MI:SS.FF6'), '') AS min_val, COALESCE(TO_CHAR(CONVERT_TIMEZONE('UTC', MAX(RENTAL_DATE)), 'YYYY-MM-DD"T"HH24:MI:SS.FF6'), '') AS max_val, COALESCE((SUM(DATE_PART('EPOCH_MICROSECOND', RENTAL_DATE)))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.RENTAL
UNION ALL
SELECT 'inventory_id' AS column_name, (COUNT(*) - COUNT(INVENTORY_ID))::bigint AS null_count, COUNT(DISTINCT INVENTORY_ID::varchar)::bigint AS distinct_count,
       COALESCE((MIN(INVENTORY_ID))::varchar, '') AS min_val, COALESCE((MAX(INVENTORY_ID))::varchar, '') AS max_val, COALESCE((SUM(INVENTORY_ID))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.RENTAL
UNION ALL
SELECT 'customer_id' AS column_name, (COUNT(*) - COUNT(CUSTOMER_ID))::bigint AS null_count, COUNT(DISTINCT CUSTOMER_ID::varchar)::bigint AS distinct_count,
       COALESCE((MIN(CUSTOMER_ID))::varchar, '') AS min_val, COALESCE((MAX(CUSTOMER_ID))::varchar, '') AS max_val, COALESCE((SUM(CUSTOMER_ID))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.RENTAL
UNION ALL
SELECT 'return_date' AS column_name, (COUNT(*) - COUNT(RETURN_DATE))::bigint AS null_count, COUNT(DISTINCT TO_CHAR(CONVERT_TIMEZONE('UTC', RETURN_DATE), 'YYYY-MM-DD"T"HH24:MI:SS.FF6'))::bigint AS distinct_count,
       COALESCE(TO_CHAR(CONVERT_TIMEZONE('UTC', MIN(RETURN_DATE)), 'YYYY-MM-DD"T"HH24:MI:SS.FF6'), '') AS min_val, COALESCE(TO_CHAR(CONVERT_TIMEZONE('UTC', MAX(RETURN_DATE)), 'YYYY-MM-DD"T"HH24:MI:SS.FF6'), '') AS max_val, COALESCE((SUM(DATE_PART('EPOCH_MICROSECOND', RETURN_DATE)))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.RENTAL
UNION ALL
SELECT 'staff_id' AS column_name, (COUNT(*) - COUNT(STAFF_ID))::bigint AS null_count, COUNT(DISTINCT STAFF_ID::varchar)::bigint AS distinct_count,
       COALESCE((MIN(STAFF_ID))::varchar, '') AS min_val, COALESCE((MAX(STAFF_ID))::varchar, '') AS max_val, COALESCE((SUM(STAFF_ID))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.RENTAL
UNION ALL
SELECT 'last_update' AS column_name, (COUNT(*) - COUNT(LAST_UPDATE))::bigint AS null_count, COUNT(DISTINCT TO_CHAR(CONVERT_TIMEZONE('UTC', LAST_UPDATE), 'YYYY-MM-DD"T"HH24:MI:SS.FF6'))::bigint AS distinct_count,
       COALESCE(TO_CHAR(CONVERT_TIMEZONE('UTC', MIN(LAST_UPDATE)), 'YYYY-MM-DD"T"HH24:MI:SS.FF6'), '') AS min_val, COALESCE(TO_CHAR(CONVERT_TIMEZONE('UTC', MAX(LAST_UPDATE)), 'YYYY-MM-DD"T"HH24:MI:SS.FF6'), '') AS max_val, COALESCE((SUM(DATE_PART('EPOCH_MICROSECOND', LAST_UPDATE)))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.RENTAL
UNION ALL
SELECT 'uuid' AS column_name, (COUNT(*) - COUNT(UUID))::bigint AS null_count, COUNT(DISTINCT LOWER(UUID::varchar))::bigint AS distinct_count,
       COALESCE(MIN(LOWER(UUID::varchar)), '') AS min_val, COALESCE(MAX(LOWER(UUID::varchar)), '') AS max_val, COALESCE('', '') AS sum_val
FROM PAGILA_MIG.RAW.RENTAL
ORDER BY column_name
