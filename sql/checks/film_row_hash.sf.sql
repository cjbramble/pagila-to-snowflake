-- requirement: MIG-005
-- film: md5 of every column of every row, by primary key (detects changed, swapped, truncated or lost-precision values, and names the key).
SELECT FILM_ID,
       md5(CASE WHEN FILM_ID IS NULL THEN '0' ELSE '1' || LENGTH(FILM_ID::varchar)::varchar || ':' || FILM_ID::varchar END
    || '|' || CASE WHEN TITLE IS NULL THEN '0' ELSE '1' || LENGTH(TITLE)::varchar || ':' || TITLE END
    || '|' || CASE WHEN DESCRIPTION IS NULL THEN '0' ELSE '1' || LENGTH(DESCRIPTION)::varchar || ':' || DESCRIPTION END
    || '|' || CASE WHEN RELEASE_YEAR IS NULL THEN '0' ELSE '1' || LENGTH(RELEASE_YEAR::varchar)::varchar || ':' || RELEASE_YEAR::varchar END
    || '|' || CASE WHEN LANGUAGE_ID IS NULL THEN '0' ELSE '1' || LENGTH(LANGUAGE_ID::varchar)::varchar || ':' || LANGUAGE_ID::varchar END
    || '|' || CASE WHEN ORIGINAL_LANGUAGE_ID IS NULL THEN '0' ELSE '1' || LENGTH(ORIGINAL_LANGUAGE_ID::varchar)::varchar || ':' || ORIGINAL_LANGUAGE_ID::varchar END
    || '|' || CASE WHEN RENTAL_DURATION IS NULL THEN '0' ELSE '1' || LENGTH(RENTAL_DURATION::varchar)::varchar || ':' || RENTAL_DURATION::varchar END
    || '|' || CASE WHEN RENTAL_RATE IS NULL THEN '0' ELSE '1' || LENGTH(RENTAL_RATE::varchar)::varchar || ':' || RENTAL_RATE::varchar END
    || '|' || CASE WHEN LENGTH IS NULL THEN '0' ELSE '1' || LENGTH(LENGTH::varchar)::varchar || ':' || LENGTH::varchar END
    || '|' || CASE WHEN REPLACEMENT_COST IS NULL THEN '0' ELSE '1' || LENGTH(REPLACEMENT_COST::varchar)::varchar || ':' || REPLACEMENT_COST::varchar END
    || '|' || CASE WHEN RATING IS NULL THEN '0' ELSE '1' || LENGTH(RATING::varchar)::varchar || ':' || RATING::varchar END
    || '|' || CASE WHEN LAST_UPDATE IS NULL THEN '0' ELSE '1' || LENGTH(TO_CHAR(CONVERT_TIMEZONE('UTC', LAST_UPDATE), 'YYYY-MM-DD"T"HH24:MI:SS.FF6'))::varchar || ':' || TO_CHAR(CONVERT_TIMEZONE('UTC', LAST_UPDATE), 'YYYY-MM-DD"T"HH24:MI:SS.FF6') END
    || '|' || CASE WHEN SPECIAL_FEATURES IS NULL THEN '0' ELSE '1' || LENGTH(ARRAY_SIZE(SPECIAL_FEATURES)::varchar || '#' || ARRAY_TO_STRING(SPECIAL_FEATURES, CHR(31)))::varchar || ':' || ARRAY_SIZE(SPECIAL_FEATURES)::varchar || '#' || ARRAY_TO_STRING(SPECIAL_FEATURES, CHR(31)) END
    || '|' || CASE WHEN LENGTH_HOURS IS NULL THEN '0' ELSE '1' || LENGTH(LENGTH_HOURS::varchar)::varchar || ':' || LENGTH_HOURS::varchar END) AS row_hash
FROM PAGILA_MIG.RAW.FILM
ORDER BY FILM_ID
