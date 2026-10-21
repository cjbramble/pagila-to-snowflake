-- requirement: MIG-003
-- payment: total rows and distinct primary keys (detects missing, extra, duplicate rows).
SELECT COUNT(*) AS row_count,
       COUNT(DISTINCT payment_id::text || '|' || to_char(payment_date AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US')) AS distinct_pk_count
FROM public.payment
