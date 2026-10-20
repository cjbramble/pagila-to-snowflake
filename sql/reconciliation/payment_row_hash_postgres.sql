-- Normalized row hash for payment, Postgres side. Pair: payment_row_hash_snowflake.sql.
-- One row per primary key: row_key (normalized PK text) and row_hash (md5 of all columns).
--
-- Canonical text per value, identical in both dialects:
--   NULL            '0'; any non-null value is '1' || value, so NULL never collides with
--                   a real value (Snowflake turns the literal '\N' into 'N', so a
--                   backslash null token would differ between dialects)
--   integer         decimal text
--   numeric(5,2)    fixed two decimals, e.g. 0.00 and 11.99
--   timestamptz     UTC, microseconds, ISO-8601 with Z
--   uuid            lowercase 8-4-4-4-12
--   text            exact, untrimmed (no CHAR(n) columns exist, so trimming would only hide defects)
-- Values are joined with chr(31), the ASCII unit separator, which no Pagila value contains.

SELECT
    to_char(payment_date AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"')
        || chr(31) || payment_id::text AS row_key,
    md5(concat_ws(chr(31),
        CASE WHEN payment_id   IS NULL THEN '0' ELSE '1' || payment_id::text END,
        CASE WHEN customer_id  IS NULL THEN '0' ELSE '1' || customer_id::text END,
        CASE WHEN staff_id     IS NULL THEN '0' ELSE '1' || staff_id::text END,
        CASE WHEN rental_id    IS NULL THEN '0' ELSE '1' || rental_id::text END,
        CASE WHEN amount       IS NULL THEN '0' ELSE '1' || to_char(amount, 'FM990.00') END,
        CASE WHEN payment_date IS NULL THEN '0'
             ELSE '1' || to_char(payment_date AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"') END,
        CASE WHEN uuid         IS NULL THEN '0' ELSE '1' || lower(uuid::text) END
    )) AS row_hash
FROM public.payment
ORDER BY row_key;
