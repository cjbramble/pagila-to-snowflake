-- requirement: MIG-004
-- film: per-column null count, distinct count, min, max, sum (sum of length for text, of epoch microseconds for timestamps, of days for dates, of array sizes for arrays, count of true for booleans).
SELECT 'film_id' AS column_name, (COUNT(*) - COUNT(FILM_ID))::bigint AS null_count, COUNT(DISTINCT FILM_ID::varchar)::bigint AS distinct_count,
       COALESCE((MIN(FILM_ID))::varchar, '') AS min_val, COALESCE((MAX(FILM_ID))::varchar, '') AS max_val, COALESCE((SUM(FILM_ID))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.FILM
UNION ALL
SELECT 'title' AS column_name, (COUNT(*) - COUNT(TITLE))::bigint AS null_count, COUNT(DISTINCT TITLE)::bigint AS distinct_count,
       COALESCE(MIN(TITLE), '') AS min_val, COALESCE(MAX(TITLE), '') AS max_val, COALESCE((SUM(LENGTH(TITLE)))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.FILM
UNION ALL
SELECT 'description' AS column_name, (COUNT(*) - COUNT(DESCRIPTION))::bigint AS null_count, COUNT(DISTINCT DESCRIPTION)::bigint AS distinct_count,
       COALESCE(MIN(DESCRIPTION), '') AS min_val, COALESCE(MAX(DESCRIPTION), '') AS max_val, COALESCE((SUM(LENGTH(DESCRIPTION)))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.FILM
UNION ALL
SELECT 'release_year' AS column_name, (COUNT(*) - COUNT(RELEASE_YEAR))::bigint AS null_count, COUNT(DISTINCT RELEASE_YEAR::varchar)::bigint AS distinct_count,
       COALESCE((MIN(RELEASE_YEAR))::varchar, '') AS min_val, COALESCE((MAX(RELEASE_YEAR))::varchar, '') AS max_val, COALESCE((SUM(RELEASE_YEAR))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.FILM
UNION ALL
SELECT 'language_id' AS column_name, (COUNT(*) - COUNT(LANGUAGE_ID))::bigint AS null_count, COUNT(DISTINCT LANGUAGE_ID::varchar)::bigint AS distinct_count,
       COALESCE((MIN(LANGUAGE_ID))::varchar, '') AS min_val, COALESCE((MAX(LANGUAGE_ID))::varchar, '') AS max_val, COALESCE((SUM(LANGUAGE_ID))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.FILM
UNION ALL
SELECT 'original_language_id' AS column_name, (COUNT(*) - COUNT(ORIGINAL_LANGUAGE_ID))::bigint AS null_count, COUNT(DISTINCT ORIGINAL_LANGUAGE_ID::varchar)::bigint AS distinct_count,
       COALESCE((MIN(ORIGINAL_LANGUAGE_ID))::varchar, '') AS min_val, COALESCE((MAX(ORIGINAL_LANGUAGE_ID))::varchar, '') AS max_val, COALESCE((SUM(ORIGINAL_LANGUAGE_ID))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.FILM
UNION ALL
SELECT 'rental_duration' AS column_name, (COUNT(*) - COUNT(RENTAL_DURATION))::bigint AS null_count, COUNT(DISTINCT RENTAL_DURATION::varchar)::bigint AS distinct_count,
       COALESCE((MIN(RENTAL_DURATION))::varchar, '') AS min_val, COALESCE((MAX(RENTAL_DURATION))::varchar, '') AS max_val, COALESCE((SUM(RENTAL_DURATION))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.FILM
UNION ALL
SELECT 'rental_rate' AS column_name, (COUNT(*) - COUNT(RENTAL_RATE))::bigint AS null_count, COUNT(DISTINCT RENTAL_RATE::varchar)::bigint AS distinct_count,
       COALESCE((MIN(RENTAL_RATE))::varchar, '') AS min_val, COALESCE((MAX(RENTAL_RATE))::varchar, '') AS max_val, COALESCE((SUM(RENTAL_RATE))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.FILM
UNION ALL
SELECT 'length' AS column_name, (COUNT(*) - COUNT(LENGTH))::bigint AS null_count, COUNT(DISTINCT LENGTH::varchar)::bigint AS distinct_count,
       COALESCE((MIN(LENGTH))::varchar, '') AS min_val, COALESCE((MAX(LENGTH))::varchar, '') AS max_val, COALESCE((SUM(LENGTH))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.FILM
UNION ALL
SELECT 'replacement_cost' AS column_name, (COUNT(*) - COUNT(REPLACEMENT_COST))::bigint AS null_count, COUNT(DISTINCT REPLACEMENT_COST::varchar)::bigint AS distinct_count,
       COALESCE((MIN(REPLACEMENT_COST))::varchar, '') AS min_val, COALESCE((MAX(REPLACEMENT_COST))::varchar, '') AS max_val, COALESCE((SUM(REPLACEMENT_COST))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.FILM
UNION ALL
SELECT 'rating' AS column_name, (COUNT(*) - COUNT(RATING))::bigint AS null_count, COUNT(DISTINCT RATING::varchar)::bigint AS distinct_count,
       COALESCE(MIN(RATING::varchar), '') AS min_val, COALESCE(MAX(RATING::varchar), '') AS max_val, COALESCE('', '') AS sum_val
FROM PAGILA_MIG.RAW.FILM
UNION ALL
SELECT 'last_update' AS column_name, (COUNT(*) - COUNT(LAST_UPDATE))::bigint AS null_count, COUNT(DISTINCT TO_CHAR(CONVERT_TIMEZONE('UTC', LAST_UPDATE), 'YYYY-MM-DD"T"HH24:MI:SS.FF6'))::bigint AS distinct_count,
       COALESCE(TO_CHAR(CONVERT_TIMEZONE('UTC', MIN(LAST_UPDATE)), 'YYYY-MM-DD"T"HH24:MI:SS.FF6'), '') AS min_val, COALESCE(TO_CHAR(CONVERT_TIMEZONE('UTC', MAX(LAST_UPDATE)), 'YYYY-MM-DD"T"HH24:MI:SS.FF6'), '') AS max_val, COALESCE((SUM(DATE_PART('EPOCH_MICROSECOND', LAST_UPDATE)))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.FILM
UNION ALL
SELECT 'special_features' AS column_name, (COUNT(*) - COUNT(SPECIAL_FEATURES))::bigint AS null_count, COUNT(DISTINCT ARRAY_SIZE(SPECIAL_FEATURES)::varchar || '#' || ARRAY_TO_STRING(SPECIAL_FEATURES, CHR(31)))::bigint AS distinct_count,
       COALESCE((MIN(ARRAY_SIZE(SPECIAL_FEATURES)))::varchar, '') AS min_val, COALESCE((MAX(ARRAY_SIZE(SPECIAL_FEATURES)))::varchar, '') AS max_val, COALESCE((SUM(ARRAY_SIZE(SPECIAL_FEATURES)))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.FILM
UNION ALL
SELECT 'length_hours' AS column_name, (COUNT(*) - COUNT(LENGTH_HOURS))::bigint AS null_count, COUNT(DISTINCT LENGTH_HOURS::varchar)::bigint AS distinct_count,
       COALESCE((MIN(LENGTH_HOURS))::varchar, '') AS min_val, COALESCE((MAX(LENGTH_HOURS))::varchar, '') AS max_val, COALESCE((SUM(LENGTH_HOURS))::varchar, '') AS sum_val
FROM PAGILA_MIG.RAW.FILM
ORDER BY column_name
