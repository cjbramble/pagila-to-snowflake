-- Normalized row hash for payment, Snowflake side. Pair: payment_row_hash_postgres.sql,
-- which documents the canonical text format. Dialect differences:
--   timestamps   CONVERT_TIMEZONE('UTC', ...) and FF6 instead of AT TIME ZONE and US
--   to text      TO_VARCHAR(x[, format]) instead of x::text / to_char
--   chr(31)      CHR(31); CONCAT_WS and MD5 behave the same (no NULL inputs reach them)

SELECT
    TO_VARCHAR(CONVERT_TIMEZONE('UTC', PAYMENT_DATE), 'YYYY-MM-DD"T"HH24:MI:SS.FF6"Z"')
        || CHR(31) || TO_VARCHAR(PAYMENT_ID) AS ROW_KEY,
    MD5(CONCAT_WS(CHR(31),
        CASE WHEN PAYMENT_ID   IS NULL THEN '0' ELSE '1' || TO_VARCHAR(PAYMENT_ID) END,
        CASE WHEN CUSTOMER_ID  IS NULL THEN '0' ELSE '1' || TO_VARCHAR(CUSTOMER_ID) END,
        CASE WHEN STAFF_ID     IS NULL THEN '0' ELSE '1' || TO_VARCHAR(STAFF_ID) END,
        CASE WHEN RENTAL_ID    IS NULL THEN '0' ELSE '1' || TO_VARCHAR(RENTAL_ID) END,
        CASE WHEN AMOUNT       IS NULL THEN '0' ELSE '1' || TO_VARCHAR(AMOUNT, 'FM990.00') END,
        CASE WHEN PAYMENT_DATE IS NULL THEN '0'
             ELSE '1' || TO_VARCHAR(CONVERT_TIMEZONE('UTC', PAYMENT_DATE),
                                    'YYYY-MM-DD"T"HH24:MI:SS.FF6"Z"') END,
        CASE WHEN UUID         IS NULL THEN '0' ELSE '1' || LOWER(TO_VARCHAR(UUID)) END
    )) AS ROW_HASH
FROM PAGILA_MIG.RAW.PAYMENT
ORDER BY ROW_KEY;
