-- requirement: MIG-005
-- address: md5 of every column of every row, by primary key (detects changed, swapped, truncated or lost-precision values, and names the key).
SELECT address_id,
       md5(CASE WHEN address_id IS NULL THEN '0' ELSE '1' || length(address_id::text)::text || ':' || address_id::text END
    || '|' || CASE WHEN address IS NULL THEN '0' ELSE '1' || length(address)::text || ':' || address END
    || '|' || CASE WHEN address2 IS NULL THEN '0' ELSE '1' || length(address2)::text || ':' || address2 END
    || '|' || CASE WHEN district IS NULL THEN '0' ELSE '1' || length(district)::text || ':' || district END
    || '|' || CASE WHEN city_id IS NULL THEN '0' ELSE '1' || length(city_id::text)::text || ':' || city_id::text END
    || '|' || CASE WHEN postal_code IS NULL THEN '0' ELSE '1' || length(postal_code)::text || ':' || postal_code END
    || '|' || CASE WHEN phone IS NULL THEN '0' ELSE '1' || length(phone)::text || ':' || phone END
    || '|' || CASE WHEN last_update IS NULL THEN '0' ELSE '1' || length(to_char(last_update AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US'))::text || ':' || to_char(last_update AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US') END) AS row_hash
FROM public.address
ORDER BY address_id
