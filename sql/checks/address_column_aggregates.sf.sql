-- requirement: MIG-004
-- address: per-column null count, distinct count, min, max, sum (sum of length for text, of epoch microseconds for timestamps, of days for dates, of array sizes for arrays, count of true for booleans).
SELECT 'address_id' AS column_name, (COUNT(*) - COUNT(ADDRESS_ID))::bigint AS null_count, COUNT(DISTINCT ADDRESS_ID::varchar)::bigint AS distinct_count,
       COALESCE((MIN(ADDRESS_ID))::varchar, '') AS min_val, COALESCE((MAX(ADDRESS_ID))::varchar, '') AS max_val, COALESCE((SUM(ADDRESS_ID))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.ADDRESS
UNION ALL
SELECT 'address' AS column_name, (COUNT(*) - COUNT(ADDRESS))::bigint AS null_count, COUNT(DISTINCT ADDRESS)::bigint AS distinct_count,
       COALESCE(MIN(ADDRESS), '') AS min_val, COALESCE(MAX(ADDRESS), '') AS max_val, COALESCE((SUM(LENGTH(ADDRESS)))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.ADDRESS
UNION ALL
SELECT 'address2' AS column_name, (COUNT(*) - COUNT(ADDRESS2))::bigint AS null_count, COUNT(DISTINCT ADDRESS2)::bigint AS distinct_count,
       COALESCE(MIN(ADDRESS2), '') AS min_val, COALESCE(MAX(ADDRESS2), '') AS max_val, COALESCE((SUM(LENGTH(ADDRESS2)))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.ADDRESS
UNION ALL
SELECT 'district' AS column_name, (COUNT(*) - COUNT(DISTRICT))::bigint AS null_count, COUNT(DISTINCT DISTRICT)::bigint AS distinct_count,
       COALESCE(MIN(DISTRICT), '') AS min_val, COALESCE(MAX(DISTRICT), '') AS max_val, COALESCE((SUM(LENGTH(DISTRICT)))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.ADDRESS
UNION ALL
SELECT 'city_id' AS column_name, (COUNT(*) - COUNT(CITY_ID))::bigint AS null_count, COUNT(DISTINCT CITY_ID::varchar)::bigint AS distinct_count,
       COALESCE((MIN(CITY_ID))::varchar, '') AS min_val, COALESCE((MAX(CITY_ID))::varchar, '') AS max_val, COALESCE((SUM(CITY_ID))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.ADDRESS
UNION ALL
SELECT 'postal_code' AS column_name, (COUNT(*) - COUNT(POSTAL_CODE))::bigint AS null_count, COUNT(DISTINCT POSTAL_CODE)::bigint AS distinct_count,
       COALESCE(MIN(POSTAL_CODE), '') AS min_val, COALESCE(MAX(POSTAL_CODE), '') AS max_val, COALESCE((SUM(LENGTH(POSTAL_CODE)))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.ADDRESS
UNION ALL
SELECT 'phone' AS column_name, (COUNT(*) - COUNT(PHONE))::bigint AS null_count, COUNT(DISTINCT PHONE)::bigint AS distinct_count,
       COALESCE(MIN(PHONE), '') AS min_val, COALESCE(MAX(PHONE), '') AS max_val, COALESCE((SUM(LENGTH(PHONE)))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.ADDRESS
UNION ALL
SELECT 'last_update' AS column_name, (COUNT(*) - COUNT(LAST_UPDATE))::bigint AS null_count, COUNT(DISTINCT TO_CHAR(CONVERT_TIMEZONE('UTC', LAST_UPDATE), 'YYYY-MM-DD"T"HH24:MI:SS.FF6'))::bigint AS distinct_count,
       COALESCE(TO_CHAR(CONVERT_TIMEZONE('UTC', MIN(LAST_UPDATE)), 'YYYY-MM-DD"T"HH24:MI:SS.FF6'), '') AS min_val, COALESCE(TO_CHAR(CONVERT_TIMEZONE('UTC', MAX(LAST_UPDATE)), 'YYYY-MM-DD"T"HH24:MI:SS.FF6'), '') AS max_val, COALESCE((SUM(DATE_PART('EPOCH_MICROSECOND', LAST_UPDATE)))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.ADDRESS
ORDER BY column_name
