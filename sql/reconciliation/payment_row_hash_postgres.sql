-- Normalized row hash for payment, Postgres side. Pair: payment_row_hash_snowflake.sql.
-- One row per primary key: row_key (normalized PK text) and row_hash (md5 of all columns).
--
-- Canonical text per value, identical in both dialects:
--   NULL            '0'; any non-null value v is '1' || length(v) || ':' || v. The flag
--                   keeps NULL apart from every real value (Snowflake turns the literal '\N'
--                   into 'N', so a backslash null token would differ between dialects), and
--                   the length prefix makes the encoding unambiguous: without it, values
--                   containing the separator can make two different rows hash the same.
--   integer         decimal text
--   numeric(5,2)    fixed two decimals, e.g. 0.00 and 11.99
--   timestamptz     UTC, microseconds, ISO-8601 with Z
--   uuid            lowercase 8-4-4-4-12
--   text            exact, untrimmed (no CHAR(n) columns exist, so trimming would only hide defects)
-- Encoded values are joined with chr(31), the ASCII unit separator.

SELECT
    to_char(payment_date AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"')
        || chr(31) || payment_id::text AS row_key,
    md5(concat_ws(chr(31),
        CASE WHEN payment_id IS NULL THEN '0'
             ELSE '1' || length(payment_id::text)::text || ':' || payment_id::text END,
        CASE WHEN customer_id IS NULL THEN '0'
             ELSE '1' || length(customer_id::text)::text || ':' || customer_id::text END,
        CASE WHEN staff_id IS NULL THEN '0'
             ELSE '1' || length(staff_id::text)::text || ':' || staff_id::text END,
        CASE WHEN rental_id IS NULL THEN '0'
             ELSE '1' || length(rental_id::text)::text || ':' || rental_id::text END,
        CASE WHEN amount IS NULL THEN '0'
             ELSE '1' || length(to_char(amount, 'FM990.00'))::text || ':'
                  || to_char(amount, 'FM990.00') END,
        CASE WHEN payment_date IS NULL THEN '0'
             ELSE '1' || length(to_char(payment_date AT TIME ZONE 'UTC',
                                        'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'))::text || ':'
                  || to_char(payment_date AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"') END,
        CASE WHEN uuid IS NULL THEN '0'
             ELSE '1' || length(lower(uuid::text))::text || ':' || lower(uuid::text) END
    )) AS row_hash
FROM public.payment
ORDER BY row_key;
