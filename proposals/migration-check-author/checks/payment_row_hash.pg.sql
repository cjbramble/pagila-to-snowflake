-- requirement: MIG-005
-- payment: md5 of every column of every row, by primary key (detects changed, swapped, truncated or lost-precision values, and names the key).
SELECT payment_id,
       to_char(payment_date AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US') AS payment_date,
       md5(CASE WHEN payment_id IS NULL THEN '0' ELSE '1' || length(payment_id::text)::text || ':' || payment_id::text END
    || '|' || CASE WHEN customer_id IS NULL THEN '0' ELSE '1' || length(customer_id::text)::text || ':' || customer_id::text END
    || '|' || CASE WHEN staff_id IS NULL THEN '0' ELSE '1' || length(staff_id::text)::text || ':' || staff_id::text END
    || '|' || CASE WHEN rental_id IS NULL THEN '0' ELSE '1' || length(rental_id::text)::text || ':' || rental_id::text END
    || '|' || CASE WHEN amount IS NULL THEN '0' ELSE '1' || length(amount::text)::text || ':' || amount::text END
    || '|' || CASE WHEN payment_date IS NULL THEN '0' ELSE '1' || length(to_char(payment_date AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US'))::text || ':' || to_char(payment_date AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US') END
    || '|' || CASE WHEN uuid IS NULL THEN '0' ELSE '1' || length(lower(uuid::text))::text || ':' || lower(uuid::text) END) AS row_hash
FROM public.payment
ORDER BY payment_id, payment_date
