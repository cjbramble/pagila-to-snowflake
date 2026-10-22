-- requirement: MIG-005
-- address: md5 of every column of every row, by primary key (detects changed, swapped, truncated or lost-precision values, and names the key).
SELECT ADDRESS_ID,
       md5(CASE WHEN ADDRESS_ID IS NULL THEN '0' ELSE '1' || LENGTH(ADDRESS_ID::varchar)::varchar || ':' || ADDRESS_ID::varchar END
    || '|' || CASE WHEN ADDRESS IS NULL THEN '0' ELSE '1' || LENGTH(ADDRESS)::varchar || ':' || ADDRESS END
    || '|' || CASE WHEN ADDRESS2 IS NULL THEN '0' ELSE '1' || LENGTH(ADDRESS2)::varchar || ':' || ADDRESS2 END
    || '|' || CASE WHEN DISTRICT IS NULL THEN '0' ELSE '1' || LENGTH(DISTRICT)::varchar || ':' || DISTRICT END
    || '|' || CASE WHEN CITY_ID IS NULL THEN '0' ELSE '1' || LENGTH(CITY_ID::varchar)::varchar || ':' || CITY_ID::varchar END
    || '|' || CASE WHEN POSTAL_CODE IS NULL THEN '0' ELSE '1' || LENGTH(POSTAL_CODE)::varchar || ':' || POSTAL_CODE END
    || '|' || CASE WHEN PHONE IS NULL THEN '0' ELSE '1' || LENGTH(PHONE)::varchar || ':' || PHONE END
    || '|' || CASE WHEN LAST_UPDATE IS NULL THEN '0' ELSE '1' || LENGTH(TO_CHAR(CONVERT_TIMEZONE('UTC', LAST_UPDATE), 'YYYY-MM-DD"T"HH24:MI:SS.FF6'))::varchar || ':' || TO_CHAR(CONVERT_TIMEZONE('UTC', LAST_UPDATE), 'YYYY-MM-DD"T"HH24:MI:SS.FF6') END) AS row_hash
FROM PAGILA_MIG.RAW.ADDRESS
ORDER BY ADDRESS_ID
