-- requirement: MIG-005
-- rental: md5 of every column of every row, by primary key (detects changed, swapped, truncated or lost-precision values, and names the key).
SELECT rental_id,
       md5(CASE WHEN rental_id IS NULL THEN '0' ELSE '1' || length(rental_id::text)::text || ':' || rental_id::text END
    || '|' || CASE WHEN rental_date IS NULL THEN '0' ELSE '1' || length(to_char(rental_date AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US'))::text || ':' || to_char(rental_date AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US') END
    || '|' || CASE WHEN inventory_id IS NULL THEN '0' ELSE '1' || length(inventory_id::text)::text || ':' || inventory_id::text END
    || '|' || CASE WHEN customer_id IS NULL THEN '0' ELSE '1' || length(customer_id::text)::text || ':' || customer_id::text END
    || '|' || CASE WHEN return_date IS NULL THEN '0' ELSE '1' || length(to_char(return_date AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US'))::text || ':' || to_char(return_date AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US') END
    || '|' || CASE WHEN staff_id IS NULL THEN '0' ELSE '1' || length(staff_id::text)::text || ':' || staff_id::text END
    || '|' || CASE WHEN last_update IS NULL THEN '0' ELSE '1' || length(to_char(last_update AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US'))::text || ':' || to_char(last_update AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US') END
    || '|' || CASE WHEN uuid IS NULL THEN '0' ELSE '1' || length(lower(uuid::text))::text || ':' || lower(uuid::text) END) AS row_hash
FROM public.rental
ORDER BY rental_id
