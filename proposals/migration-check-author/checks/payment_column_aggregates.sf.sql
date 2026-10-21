-- requirement: MIG-004
-- payment: per-column null count, distinct count, min, max, sum (sum of length for text, of epoch microseconds for timestamps, of days for dates, of array sizes for arrays, count of true for booleans).
SELECT 'payment_id' AS column_name, (COUNT(*) - COUNT(PAYMENT_ID))::bigint AS null_count, COUNT(DISTINCT PAYMENT_ID::varchar)::bigint AS distinct_count,
       COALESCE((MIN(PAYMENT_ID))::varchar, '') AS min_val, COALESCE((MAX(PAYMENT_ID))::varchar, '') AS max_val, COALESCE((SUM(PAYMENT_ID))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.PAYMENT
UNION ALL
SELECT 'customer_id' AS column_name, (COUNT(*) - COUNT(CUSTOMER_ID))::bigint AS null_count, COUNT(DISTINCT CUSTOMER_ID::varchar)::bigint AS distinct_count,
       COALESCE((MIN(CUSTOMER_ID))::varchar, '') AS min_val, COALESCE((MAX(CUSTOMER_ID))::varchar, '') AS max_val, COALESCE((SUM(CUSTOMER_ID))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.PAYMENT
UNION ALL
SELECT 'staff_id' AS column_name, (COUNT(*) - COUNT(STAFF_ID))::bigint AS null_count, COUNT(DISTINCT STAFF_ID::varchar)::bigint AS distinct_count,
       COALESCE((MIN(STAFF_ID))::varchar, '') AS min_val, COALESCE((MAX(STAFF_ID))::varchar, '') AS max_val, COALESCE((SUM(STAFF_ID))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.PAYMENT
UNION ALL
SELECT 'rental_id' AS column_name, (COUNT(*) - COUNT(RENTAL_ID))::bigint AS null_count, COUNT(DISTINCT RENTAL_ID::varchar)::bigint AS distinct_count,
       COALESCE((MIN(RENTAL_ID))::varchar, '') AS min_val, COALESCE((MAX(RENTAL_ID))::varchar, '') AS max_val, COALESCE((SUM(RENTAL_ID))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.PAYMENT
UNION ALL
SELECT 'amount' AS column_name, (COUNT(*) - COUNT(AMOUNT))::bigint AS null_count, COUNT(DISTINCT AMOUNT::varchar)::bigint AS distinct_count,
       COALESCE((MIN(AMOUNT))::varchar, '') AS min_val, COALESCE((MAX(AMOUNT))::varchar, '') AS max_val, COALESCE((SUM(AMOUNT))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.PAYMENT
UNION ALL
SELECT 'payment_date' AS column_name, (COUNT(*) - COUNT(PAYMENT_DATE))::bigint AS null_count, COUNT(DISTINCT TO_CHAR(CONVERT_TIMEZONE('UTC', PAYMENT_DATE), 'YYYY-MM-DD"T"HH24:MI:SS.FF6'))::bigint AS distinct_count,
       COALESCE(TO_CHAR(CONVERT_TIMEZONE('UTC', MIN(PAYMENT_DATE)), 'YYYY-MM-DD"T"HH24:MI:SS.FF6'), '') AS min_val, COALESCE(TO_CHAR(CONVERT_TIMEZONE('UTC', MAX(PAYMENT_DATE)), 'YYYY-MM-DD"T"HH24:MI:SS.FF6'), '') AS max_val, COALESCE((SUM(DATE_PART('EPOCH_MICROSECOND', PAYMENT_DATE)))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.PAYMENT
UNION ALL
SELECT 'uuid' AS column_name, (COUNT(*) - COUNT(UUID))::bigint AS null_count, COUNT(DISTINCT LOWER(UUID::varchar))::bigint AS distinct_count,
       COALESCE(MIN(LOWER(UUID::varchar)), '') AS min_val, COALESCE(MAX(LOWER(UUID::varchar)), '') AS max_val, COALESCE('', '') AS sum_val
FROM PAGILA_MIG.RAW.PAYMENT
ORDER BY column_name
