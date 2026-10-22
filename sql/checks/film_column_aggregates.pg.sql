-- requirement: MIG-004
-- film: per-column null count, distinct count, min, max, sum (sum of length for text, of epoch microseconds for timestamps, of days for dates, of array sizes for arrays, count of true for booleans).
SELECT 'film_id' AS column_name, (COUNT(*) - COUNT(film_id))::bigint AS null_count, COUNT(DISTINCT film_id::text)::bigint AS distinct_count,
       COALESCE((MIN(film_id))::text, '') AS min_val, COALESCE((MAX(film_id))::text, '') AS max_val, COALESCE((SUM(film_id))::text, '') AS sum_val
FROM public.film
UNION ALL
SELECT 'title' AS column_name, (COUNT(*) - COUNT(title))::bigint AS null_count, COUNT(DISTINCT title)::bigint AS distinct_count,
       COALESCE(MIN(title COLLATE "C"), '') AS min_val, COALESCE(MAX(title COLLATE "C"), '') AS max_val, COALESCE((SUM(length(title)))::text, '') AS sum_val
FROM public.film
UNION ALL
SELECT 'description' AS column_name, (COUNT(*) - COUNT(description))::bigint AS null_count, COUNT(DISTINCT description)::bigint AS distinct_count,
       COALESCE(MIN(description COLLATE "C"), '') AS min_val, COALESCE(MAX(description COLLATE "C"), '') AS max_val, COALESCE((SUM(length(description)))::text, '') AS sum_val
FROM public.film
UNION ALL
SELECT 'release_year' AS column_name, (COUNT(*) - COUNT(release_year))::bigint AS null_count, COUNT(DISTINCT release_year::text)::bigint AS distinct_count,
       COALESCE((MIN(release_year))::text, '') AS min_val, COALESCE((MAX(release_year))::text, '') AS max_val, COALESCE((SUM(release_year))::text, '') AS sum_val
FROM public.film
UNION ALL
SELECT 'language_id' AS column_name, (COUNT(*) - COUNT(language_id))::bigint AS null_count, COUNT(DISTINCT language_id::text)::bigint AS distinct_count,
       COALESCE((MIN(language_id))::text, '') AS min_val, COALESCE((MAX(language_id))::text, '') AS max_val, COALESCE((SUM(language_id))::text, '') AS sum_val
FROM public.film
UNION ALL
SELECT 'original_language_id' AS column_name, (COUNT(*) - COUNT(original_language_id))::bigint AS null_count, COUNT(DISTINCT original_language_id::text)::bigint AS distinct_count,
       COALESCE((MIN(original_language_id))::text, '') AS min_val, COALESCE((MAX(original_language_id))::text, '') AS max_val, COALESCE((SUM(original_language_id))::text, '') AS sum_val
FROM public.film
UNION ALL
SELECT 'rental_duration' AS column_name, (COUNT(*) - COUNT(rental_duration))::bigint AS null_count, COUNT(DISTINCT rental_duration::text)::bigint AS distinct_count,
       COALESCE((MIN(rental_duration))::text, '') AS min_val, COALESCE((MAX(rental_duration))::text, '') AS max_val, COALESCE((SUM(rental_duration))::text, '') AS sum_val
FROM public.film
UNION ALL
SELECT 'rental_rate' AS column_name, (COUNT(*) - COUNT(rental_rate))::bigint AS null_count, COUNT(DISTINCT rental_rate::text)::bigint AS distinct_count,
       COALESCE((MIN(rental_rate))::text, '') AS min_val, COALESCE((MAX(rental_rate))::text, '') AS max_val, COALESCE((SUM(rental_rate))::text, '') AS sum_val
FROM public.film
UNION ALL
SELECT 'length' AS column_name, (COUNT(*) - COUNT(length))::bigint AS null_count, COUNT(DISTINCT length::text)::bigint AS distinct_count,
       COALESCE((MIN(length))::text, '') AS min_val, COALESCE((MAX(length))::text, '') AS max_val, COALESCE((SUM(length))::text, '') AS sum_val
FROM public.film
UNION ALL
SELECT 'replacement_cost' AS column_name, (COUNT(*) - COUNT(replacement_cost))::bigint AS null_count, COUNT(DISTINCT replacement_cost::text)::bigint AS distinct_count,
       COALESCE((MIN(replacement_cost))::text, '') AS min_val, COALESCE((MAX(replacement_cost))::text, '') AS max_val, COALESCE((SUM(replacement_cost))::text, '') AS sum_val
FROM public.film
UNION ALL
SELECT 'rating' AS column_name, (COUNT(*) - COUNT(rating))::bigint AS null_count, COUNT(DISTINCT rating::text)::bigint AS distinct_count,
       COALESCE(MIN(rating::text COLLATE "C"), '') AS min_val, COALESCE(MAX(rating::text COLLATE "C"), '') AS max_val, COALESCE('', '') AS sum_val
FROM public.film
UNION ALL
SELECT 'last_update' AS column_name, (COUNT(*) - COUNT(last_update))::bigint AS null_count, COUNT(DISTINCT to_char(last_update AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US'))::bigint AS distinct_count,
       COALESCE(to_char(MIN(last_update) AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US'), '') AS min_val, COALESCE(to_char(MAX(last_update) AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US'), '') AS max_val, COALESCE((SUM((extract(epoch from last_update) * 1000000)::bigint))::text, '') AS sum_val
FROM public.film
UNION ALL
SELECT 'special_features' AS column_name, (COUNT(*) - COUNT(special_features))::bigint AS null_count, COUNT(DISTINCT cardinality(special_features)::text || '#' || array_to_string(special_features, chr(31)))::bigint AS distinct_count,
       COALESCE((MIN(cardinality(special_features)))::text, '') AS min_val, COALESCE((MAX(cardinality(special_features)))::text, '') AS max_val, COALESCE((SUM(cardinality(special_features)))::text, '') AS sum_val
FROM public.film
UNION ALL
SELECT 'length_hours' AS column_name, (COUNT(*) - COUNT(length_hours))::bigint AS null_count, COUNT(DISTINCT length_hours::text)::bigint AS distinct_count,
       COALESCE((MIN(length_hours))::text, '') AS min_val, COALESCE((MAX(length_hours))::text, '') AS max_val, COALESCE((SUM(length_hours))::text, '') AS sum_val
FROM public.film
ORDER BY column_name
