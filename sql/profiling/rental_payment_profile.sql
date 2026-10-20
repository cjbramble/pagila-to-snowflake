-- Source profile for rental and payment (PostgreSQL).
-- Four result sets: null rates, value ranges, key uniqueness, orphaned foreign keys.
-- Read-only; safe to run against the source at any time.

-- Timestamps print in the session time zone; pin it so output is comparable across runs.
SET TIME ZONE 'UTC';

-- 1. Null rates: one scan per table, unpivoted to one row per column.
SELECT 'rental' AS table_name, v.column_name, r.total_rows, v.null_count,
       round(100.0 * v.null_count / nullif(r.total_rows, 0), 2) AS null_pct
FROM (
    SELECT count(*)                       AS total_rows,
           count(*) - count(rental_id)    AS rental_id,
           count(*) - count(rental_date)  AS rental_date,
           count(*) - count(inventory_id) AS inventory_id,
           count(*) - count(customer_id)  AS customer_id,
           count(*) - count(return_date)  AS return_date,
           count(*) - count(staff_id)     AS staff_id,
           count(*) - count(last_update)  AS last_update,
           count(*) - count(uuid)         AS uuid
    FROM rental
) r
CROSS JOIN LATERAL (VALUES
    ('rental_id', r.rental_id), ('rental_date', r.rental_date),
    ('inventory_id', r.inventory_id), ('customer_id', r.customer_id),
    ('return_date', r.return_date), ('staff_id', r.staff_id),
    ('last_update', r.last_update), ('uuid', r.uuid)
) AS v(column_name, null_count)
UNION ALL
SELECT 'payment', v.column_name, p.total_rows, v.null_count,
       round(100.0 * v.null_count / nullif(p.total_rows, 0), 2)
FROM (
    SELECT count(*)                       AS total_rows,
           count(*) - count(payment_id)   AS payment_id,
           count(*) - count(customer_id)  AS customer_id,
           count(*) - count(staff_id)     AS staff_id,
           count(*) - count(rental_id)    AS rental_id,
           count(*) - count(amount)       AS amount,
           count(*) - count(payment_date) AS payment_date,
           count(*) - count(uuid)         AS uuid
    FROM payment
) p
CROSS JOIN LATERAL (VALUES
    ('payment_id', p.payment_id), ('customer_id', p.customer_id),
    ('staff_id', p.staff_id), ('rental_id', p.rental_id),
    ('amount', p.amount), ('payment_date', p.payment_date), ('uuid', p.uuid)
) AS v(column_name, null_count)
ORDER BY table_name DESC, column_name;

-- 2. Value ranges for timestamp and numeric columns. Cast to text so all rows share a type.
SELECT 'rental' AS table_name, 'rental_date' AS column_name,
       min(rental_date)::text AS min_value, max(rental_date)::text AS max_value FROM rental
UNION ALL
SELECT 'rental', 'return_date', min(return_date)::text, max(return_date)::text FROM rental
UNION ALL
SELECT 'rental', 'last_update', min(last_update)::text, max(last_update)::text FROM rental
UNION ALL
SELECT 'payment', 'payment_date', min(payment_date)::text, max(payment_date)::text FROM payment
UNION ALL
SELECT 'payment', 'amount', min(amount)::text, max(amount)::text FROM payment
ORDER BY table_name DESC, column_name;

-- 3. Key uniqueness. duplicate_rows = non-null rows beyond the first per value.
-- payment's PK is (payment_date, payment_id) and its uuid index is (uuid, payment_date),
-- so neither payment_id nor uuid is guaranteed unique on its own.
SELECT 'rental' AS table_name, 'rental_id' AS column_name, count(*) AS total_rows,
       count(rental_id) AS non_null, count(DISTINCT rental_id) AS distinct_values,
       count(rental_id) - count(DISTINCT rental_id) AS duplicate_rows FROM rental
UNION ALL
SELECT 'rental', 'uuid', count(*), count(uuid), count(DISTINCT uuid),
       count(uuid) - count(DISTINCT uuid) FROM rental
UNION ALL
SELECT 'payment', 'payment_id', count(*), count(payment_id), count(DISTINCT payment_id),
       count(payment_id) - count(DISTINCT payment_id) FROM payment
UNION ALL
SELECT 'payment', 'uuid', count(*), count(uuid), count(DISTINCT uuid),
       count(uuid) - count(DISTINCT uuid) FROM payment
ORDER BY table_name DESC, column_name;

-- 4. Orphaned foreign keys: child rows whose non-null key has no parent row.
-- NOT EXISTS counts each child row once even if the parent key were duplicated.
-- The IS NOT NULL guard matters: a null key is "no relationship", not an orphan.
SELECT 'rental' AS child_table, 'inventory_id' AS fk_column, 'inventory' AS parent_table,
       count(*) AS orphan_rows, count(DISTINCT c.inventory_id) AS orphan_keys
FROM rental c
WHERE c.inventory_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM inventory p WHERE p.inventory_id = c.inventory_id)
UNION ALL
SELECT 'rental', 'customer_id', 'customer', count(*), count(DISTINCT c.customer_id)
FROM rental c
WHERE c.customer_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM customer p WHERE p.customer_id = c.customer_id)
UNION ALL
SELECT 'rental', 'staff_id', 'staff', count(*), count(DISTINCT c.staff_id)
FROM rental c
WHERE c.staff_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM staff p WHERE p.staff_id = c.staff_id)
UNION ALL
SELECT 'payment', 'customer_id', 'customer', count(*), count(DISTINCT c.customer_id)
FROM payment c
WHERE c.customer_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM customer p WHERE p.customer_id = c.customer_id)
UNION ALL
SELECT 'payment', 'staff_id', 'staff', count(*), count(DISTINCT c.staff_id)
FROM payment c
WHERE c.staff_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM staff p WHERE p.staff_id = c.staff_id)
UNION ALL
SELECT 'payment', 'rental_id', 'rental', count(*), count(DISTINCT c.rental_id)
FROM payment c
WHERE c.rental_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM rental p WHERE p.rental_id = c.rental_id)
ORDER BY child_table DESC, fk_column;
