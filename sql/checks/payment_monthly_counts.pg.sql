-- requirement: MIG-003
-- payment: row counts per UTC month of payment_date (detects rows shifted across months or lost within a partition).
SELECT to_char(date_trunc('month', payment_date AT TIME ZONE 'UTC'), 'YYYY-MM') AS month_utc, COUNT(*) AS row_count
FROM public.payment
GROUP BY 1
ORDER BY 1
