-- requirement: MIG-005
-- customer: md5 of every column of every row, by primary key (detects changed, swapped, truncated or lost-precision values, and names the key).
SELECT CUSTOMER_ID,
       md5(CASE WHEN CUSTOMER_ID IS NULL THEN '0' ELSE '1' || LENGTH(CUSTOMER_ID::varchar)::varchar || ':' || CUSTOMER_ID::varchar END
    || '|' || CASE WHEN STORE_ID IS NULL THEN '0' ELSE '1' || LENGTH(STORE_ID::varchar)::varchar || ':' || STORE_ID::varchar END
    || '|' || CASE WHEN FIRST_NAME IS NULL THEN '0' ELSE '1' || LENGTH(FIRST_NAME)::varchar || ':' || FIRST_NAME END
    || '|' || CASE WHEN LAST_NAME IS NULL THEN '0' ELSE '1' || LENGTH(LAST_NAME)::varchar || ':' || LAST_NAME END
    || '|' || CASE WHEN EMAIL IS NULL THEN '0' ELSE '1' || LENGTH(EMAIL)::varchar || ':' || EMAIL END
    || '|' || CASE WHEN ADDRESS_ID IS NULL THEN '0' ELSE '1' || LENGTH(ADDRESS_ID::varchar)::varchar || ':' || ADDRESS_ID::varchar END
    || '|' || CASE WHEN ACTIVEBOOL IS NULL THEN '0' ELSE '1' || LENGTH((CASE WHEN ACTIVEBOOL THEN '1' ELSE '0' END))::varchar || ':' || (CASE WHEN ACTIVEBOOL THEN '1' ELSE '0' END) END
    || '|' || CASE WHEN CREATE_DATE IS NULL THEN '0' ELSE '1' || LENGTH(TO_CHAR(CREATE_DATE, 'YYYY-MM-DD'))::varchar || ':' || TO_CHAR(CREATE_DATE, 'YYYY-MM-DD') END
    || '|' || CASE WHEN LAST_UPDATE IS NULL THEN '0' ELSE '1' || LENGTH(TO_CHAR(CONVERT_TIMEZONE('UTC', LAST_UPDATE), 'YYYY-MM-DD"T"HH24:MI:SS.FF6'))::varchar || ':' || TO_CHAR(CONVERT_TIMEZONE('UTC', LAST_UPDATE), 'YYYY-MM-DD"T"HH24:MI:SS.FF6') END
    || '|' || CASE WHEN ACTIVE IS NULL THEN '0' ELSE '1' || LENGTH(ACTIVE::varchar)::varchar || ':' || ACTIVE::varchar END
    || '|' || CASE WHEN UUID IS NULL THEN '0' ELSE '1' || LENGTH(LOWER(UUID::varchar))::varchar || ':' || LOWER(UUID::varchar) END) AS row_hash
FROM PAGILA_MIG.RAW.CUSTOMER
ORDER BY CUSTOMER_ID
