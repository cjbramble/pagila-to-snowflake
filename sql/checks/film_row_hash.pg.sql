-- requirement: MIG-005
-- film: md5 of every column of every row, by primary key (detects changed, swapped, truncated or lost-precision values, and names the key).
SELECT film_id,
       md5(CASE WHEN film_id IS NULL THEN '0' ELSE '1' || length(film_id::text)::text || ':' || film_id::text END
    || '|' || CASE WHEN title IS NULL THEN '0' ELSE '1' || length(title)::text || ':' || title END
    || '|' || CASE WHEN description IS NULL THEN '0' ELSE '1' || length(description)::text || ':' || description END
    || '|' || CASE WHEN release_year IS NULL THEN '0' ELSE '1' || length(release_year::text)::text || ':' || release_year::text END
    || '|' || CASE WHEN language_id IS NULL THEN '0' ELSE '1' || length(language_id::text)::text || ':' || language_id::text END
    || '|' || CASE WHEN original_language_id IS NULL THEN '0' ELSE '1' || length(original_language_id::text)::text || ':' || original_language_id::text END
    || '|' || CASE WHEN rental_duration IS NULL THEN '0' ELSE '1' || length(rental_duration::text)::text || ':' || rental_duration::text END
    || '|' || CASE WHEN rental_rate IS NULL THEN '0' ELSE '1' || length(rental_rate::text)::text || ':' || rental_rate::text END
    || '|' || CASE WHEN length IS NULL THEN '0' ELSE '1' || length(length::text)::text || ':' || length::text END
    || '|' || CASE WHEN replacement_cost IS NULL THEN '0' ELSE '1' || length(replacement_cost::text)::text || ':' || replacement_cost::text END
    || '|' || CASE WHEN rating IS NULL THEN '0' ELSE '1' || length(rating::text)::text || ':' || rating::text END
    || '|' || CASE WHEN last_update IS NULL THEN '0' ELSE '1' || length(to_char(last_update AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US'))::text || ':' || to_char(last_update AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US') END
    || '|' || CASE WHEN special_features IS NULL THEN '0' ELSE '1' || length(cardinality(special_features)::text || '#' || array_to_string(special_features, chr(31)))::text || ':' || cardinality(special_features)::text || '#' || array_to_string(special_features, chr(31)) END
    || '|' || CASE WHEN length_hours IS NULL THEN '0' ELSE '1' || length(length_hours::text)::text || ':' || length_hours::text END) AS row_hash
FROM public.film
ORDER BY film_id
