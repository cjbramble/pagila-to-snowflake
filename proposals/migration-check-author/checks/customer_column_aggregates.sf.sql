-- requirement: MIG-004
-- customer: per-column null count, distinct count, min, max, sum (sum of length for text, of epoch microseconds for timestamps, of days for dates, of array sizes for arrays, count of true for booleans).
SELECT 'customer_id' AS column_name, (COUNT(*) - COUNT(CUSTOMER_ID))::bigint AS null_count, COUNT(DISTINCT CUSTOMER_ID::varchar)::bigint AS distinct_count,
       COALESCE((MIN(CUSTOMER_ID))::varchar, '') AS min_val, COALESCE((MAX(CUSTOMER_ID))::varchar, '') AS max_val, COALESCE((SUM(CUSTOMER_ID))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.CUSTOMER
UNION ALL
SELECT 'store_id' AS column_name, (COUNT(*) - COUNT(STORE_ID))::bigint AS null_count, COUNT(DISTINCT STORE_ID::varchar)::bigint AS distinct_count,
       COALESCE((MIN(STORE_ID))::varchar, '') AS min_val, COALESCE((MAX(STORE_ID))::varchar, '') AS max_val, COALESCE((SUM(STORE_ID))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.CUSTOMER
UNION ALL
SELECT 'first_name' AS column_name, (COUNT(*) - COUNT(FIRST_NAME))::bigint AS null_count, COUNT(DISTINCT FIRST_NAME)::bigint AS distinct_count,
       COALESCE(MIN(FIRST_NAME), '') AS min_val, COALESCE(MAX(FIRST_NAME), '') AS max_val, COALESCE((SUM(LENGTH(FIRST_NAME)))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.CUSTOMER
UNION ALL
SELECT 'last_name' AS column_name, (COUNT(*) - COUNT(LAST_NAME))::bigint AS null_count, COUNT(DISTINCT LAST_NAME)::bigint AS distinct_count,
       COALESCE(MIN(LAST_NAME), '') AS min_val, COALESCE(MAX(LAST_NAME), '') AS max_val, COALESCE((SUM(LENGTH(LAST_NAME)))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.CUSTOMER
UNION ALL
SELECT 'email' AS column_name, (COUNT(*) - COUNT(EMAIL))::bigint AS null_count, COUNT(DISTINCT EMAIL)::bigint AS distinct_count,
       COALESCE(MIN(EMAIL), '') AS min_val, COALESCE(MAX(EMAIL), '') AS max_val, COALESCE((SUM(LENGTH(EMAIL)))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.CUSTOMER
UNION ALL
SELECT 'address_id' AS column_name, (COUNT(*) - COUNT(ADDRESS_ID))::bigint AS null_count, COUNT(DISTINCT ADDRESS_ID::varchar)::bigint AS distinct_count,
       COALESCE((MIN(ADDRESS_ID))::varchar, '') AS min_val, COALESCE((MAX(ADDRESS_ID))::varchar, '') AS max_val, COALESCE((SUM(ADDRESS_ID))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.CUSTOMER
UNION ALL
SELECT 'activebool' AS column_name, (COUNT(*) - COUNT(ACTIVEBOOL))::bigint AS null_count, COUNT(DISTINCT (CASE WHEN ACTIVEBOOL THEN '1' ELSE '0' END))::bigint AS distinct_count,
       COALESCE('', '') AS min_val, COALESCE('', '') AS max_val, COALESCE((SUM(CASE WHEN ACTIVEBOOL THEN 1 ELSE 0 END))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.CUSTOMER
UNION ALL
SELECT 'create_date' AS column_name, (COUNT(*) - COUNT(CREATE_DATE))::bigint AS null_count, COUNT(DISTINCT TO_CHAR(CREATE_DATE, 'YYYY-MM-DD'))::bigint AS distinct_count,
       COALESCE(TO_CHAR(MIN(CREATE_DATE), 'YYYY-MM-DD'), '') AS min_val, COALESCE(TO_CHAR(MAX(CREATE_DATE), 'YYYY-MM-DD'), '') AS max_val, COALESCE((SUM(DATEDIFF('day', DATE '1970-01-01', CREATE_DATE)))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.CUSTOMER
UNION ALL
SELECT 'last_update' AS column_name, (COUNT(*) - COUNT(LAST_UPDATE))::bigint AS null_count, COUNT(DISTINCT TO_CHAR(CONVERT_TIMEZONE('UTC', LAST_UPDATE), 'YYYY-MM-DD"T"HH24:MI:SS.FF6'))::bigint AS distinct_count,
       COALESCE(TO_CHAR(CONVERT_TIMEZONE('UTC', MIN(LAST_UPDATE)), 'YYYY-MM-DD"T"HH24:MI:SS.FF6'), '') AS min_val, COALESCE(TO_CHAR(CONVERT_TIMEZONE('UTC', MAX(LAST_UPDATE)), 'YYYY-MM-DD"T"HH24:MI:SS.FF6'), '') AS max_val, COALESCE((SUM(DATE_PART('EPOCH_MICROSECOND', LAST_UPDATE)))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.CUSTOMER
UNION ALL
SELECT 'active' AS column_name, (COUNT(*) - COUNT(ACTIVE))::bigint AS null_count, COUNT(DISTINCT ACTIVE::varchar)::bigint AS distinct_count,
       COALESCE((MIN(ACTIVE))::varchar, '') AS min_val, COALESCE((MAX(ACTIVE))::varchar, '') AS max_val, COALESCE((SUM(ACTIVE))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.CUSTOMER
UNION ALL
SELECT 'uuid' AS column_name, (COUNT(*) - COUNT(UUID))::bigint AS null_count, COUNT(DISTINCT LOWER(UUID::varchar))::bigint AS distinct_count,
       COALESCE(MIN(LOWER(UUID::varchar)), '') AS min_val, COALESCE(MAX(LOWER(UUID::varchar)), '') AS max_val, COALESCE('', '') AS sum_val
FROM PAGILA_MIG.RAW.CUSTOMER
ORDER BY column_name
