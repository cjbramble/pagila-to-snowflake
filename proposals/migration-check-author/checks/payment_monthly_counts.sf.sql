-- requirement: MIG-003
-- payment: row counts per UTC month of payment_date (detects rows shifted across months or lost within a partition).
SELECT TO_CHAR(DATE_TRUNC('month', CONVERT_TIMEZONE('UTC', PAYMENT_DATE)), 'YYYY-MM') AS month_utc, COUNT(*) AS row_count
FROM PAGILA_MIG.RAW.PAYMENT
GROUP BY 1
ORDER BY 1
