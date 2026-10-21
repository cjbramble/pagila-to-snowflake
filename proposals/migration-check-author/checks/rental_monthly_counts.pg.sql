-- requirement: MIG-003
-- rental: row counts per UTC month of rental_date (detects rows shifted across months or lost within a partition).
SELECT to_char(date_trunc('month', rental_date AT TIME ZONE 'UTC'), 'YYYY-MM') AS month_utc, COUNT(*) AS row_count
FROM public.rental
GROUP BY 1
ORDER BY 1
