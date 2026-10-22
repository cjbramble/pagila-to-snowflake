-- requirement: MIG-005
-- payment: md5 of every column of every row, by primary key (detects changed, swapped, truncated or lost-precision values, and names the key).
SELECT PAYMENT_ID,
       TO_CHAR(CONVERT_TIMEZONE('UTC', PAYMENT_DATE), 'YYYY-MM-DD"T"HH24:MI:SS.FF6') AS PAYMENT_DATE,
       md5(CASE WHEN PAYMENT_ID IS NULL THEN '0' ELSE '1' || LENGTH(PAYMENT_ID::varchar)::varchar || ':' || PAYMENT_ID::varchar END
    || '|' || CASE WHEN CUSTOMER_ID IS NULL THEN '0' ELSE '1' || LENGTH(CUSTOMER_ID::varchar)::varchar || ':' || CUSTOMER_ID::varchar END
    || '|' || CASE WHEN STAFF_ID IS NULL THEN '0' ELSE '1' || LENGTH(STAFF_ID::varchar)::varchar || ':' || STAFF_ID::varchar END
    || '|' || CASE WHEN RENTAL_ID IS NULL THEN '0' ELSE '1' || LENGTH(RENTAL_ID::varchar)::varchar || ':' || RENTAL_ID::varchar END
    || '|' || CASE WHEN AMOUNT IS NULL THEN '0' ELSE '1' || LENGTH(AMOUNT::varchar)::varchar || ':' || AMOUNT::varchar END
    || '|' || CASE WHEN PAYMENT_DATE IS NULL THEN '0' ELSE '1' || LENGTH(TO_CHAR(CONVERT_TIMEZONE('UTC', PAYMENT_DATE), 'YYYY-MM-DD"T"HH24:MI:SS.FF6'))::varchar || ':' || TO_CHAR(CONVERT_TIMEZONE('UTC', PAYMENT_DATE), 'YYYY-MM-DD"T"HH24:MI:SS.FF6') END
    || '|' || CASE WHEN UUID IS NULL THEN '0' ELSE '1' || LENGTH(LOWER(UUID::varchar))::varchar || ':' || LOWER(UUID::varchar) END) AS row_hash
FROM PAGILA_MIG.RAW.PAYMENT
ORDER BY PAYMENT_ID, PAYMENT_DATE
