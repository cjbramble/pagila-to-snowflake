-- requirement: MIG-005
-- customer: md5 of every column of every row, by primary key (detects changed, swapped, truncated or lost-precision values, and names the key).
SELECT customer_id,
       md5(CASE WHEN customer_id IS NULL THEN '0' ELSE '1' || length(customer_id::text)::text || ':' || customer_id::text END
    || '|' || CASE WHEN store_id IS NULL THEN '0' ELSE '1' || length(store_id::text)::text || ':' || store_id::text END
    || '|' || CASE WHEN first_name IS NULL THEN '0' ELSE '1' || length(first_name)::text || ':' || first_name END
    || '|' || CASE WHEN last_name IS NULL THEN '0' ELSE '1' || length(last_name)::text || ':' || last_name END
    || '|' || CASE WHEN email IS NULL THEN '0' ELSE '1' || length(email)::text || ':' || email END
    || '|' || CASE WHEN address_id IS NULL THEN '0' ELSE '1' || length(address_id::text)::text || ':' || address_id::text END
    || '|' || CASE WHEN activebool IS NULL THEN '0' ELSE '1' || length((CASE WHEN activebool THEN '1' ELSE '0' END))::text || ':' || (CASE WHEN activebool THEN '1' ELSE '0' END) END
    || '|' || CASE WHEN create_date IS NULL THEN '0' ELSE '1' || length(to_char(create_date, 'YYYY-MM-DD'))::text || ':' || to_char(create_date, 'YYYY-MM-DD') END
    || '|' || CASE WHEN last_update IS NULL THEN '0' ELSE '1' || length(to_char(last_update AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US'))::text || ':' || to_char(last_update AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US') END
    || '|' || CASE WHEN active IS NULL THEN '0' ELSE '1' || length(active::text)::text || ':' || active::text END
    || '|' || CASE WHEN uuid IS NULL THEN '0' ELSE '1' || length(lower(uuid::text))::text || ':' || lower(uuid::text) END) AS row_hash
FROM public.customer
ORDER BY customer_id
