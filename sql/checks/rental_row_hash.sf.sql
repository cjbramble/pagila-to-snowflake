-- requirement: MIG-005
-- rental: md5 of every column of every row, by primary key (detects changed, swapped, truncated or lost-precision values, and names the key).
SELECT RENTAL_ID,
       md5(CASE WHEN RENTAL_ID IS NULL THEN '0' ELSE '1' || LENGTH(RENTAL_ID::varchar)::varchar || ':' || RENTAL_ID::varchar END
    || '|' || CASE WHEN RENTAL_DATE IS NULL THEN '0' ELSE '1' || LENGTH(TO_CHAR(CONVERT_TIMEZONE('UTC', RENTAL_DATE), 'YYYY-MM-DD"T"HH24:MI:SS.FF6'))::varchar || ':' || TO_CHAR(CONVERT_TIMEZONE('UTC', RENTAL_DATE), 'YYYY-MM-DD"T"HH24:MI:SS.FF6') END
    || '|' || CASE WHEN INVENTORY_ID IS NULL THEN '0' ELSE '1' || LENGTH(INVENTORY_ID::varchar)::varchar || ':' || INVENTORY_ID::varchar END
    || '|' || CASE WHEN CUSTOMER_ID IS NULL THEN '0' ELSE '1' || LENGTH(CUSTOMER_ID::varchar)::varchar || ':' || CUSTOMER_ID::varchar END
    || '|' || CASE WHEN RETURN_DATE IS NULL THEN '0' ELSE '1' || LENGTH(TO_CHAR(CONVERT_TIMEZONE('UTC', RETURN_DATE), 'YYYY-MM-DD"T"HH24:MI:SS.FF6'))::varchar || ':' || TO_CHAR(CONVERT_TIMEZONE('UTC', RETURN_DATE), 'YYYY-MM-DD"T"HH24:MI:SS.FF6') END
    || '|' || CASE WHEN STAFF_ID IS NULL THEN '0' ELSE '1' || LENGTH(STAFF_ID::varchar)::varchar || ':' || STAFF_ID::varchar END
    || '|' || CASE WHEN LAST_UPDATE IS NULL THEN '0' ELSE '1' || LENGTH(TO_CHAR(CONVERT_TIMEZONE('UTC', LAST_UPDATE), 'YYYY-MM-DD"T"HH24:MI:SS.FF6'))::varchar || ':' || TO_CHAR(CONVERT_TIMEZONE('UTC', LAST_UPDATE), 'YYYY-MM-DD"T"HH24:MI:SS.FF6') END
    || '|' || CASE WHEN UUID IS NULL THEN '0' ELSE '1' || LENGTH(LOWER(UUID::varchar))::varchar || ':' || LOWER(UUID::varchar) END) AS row_hash
FROM PAGILA_MIG.RAW.RENTAL
ORDER BY RENTAL_ID
