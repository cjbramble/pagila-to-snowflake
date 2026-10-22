-- requirement: MIG-003
-- rental: row counts per UTC month of rental_date (detects rows shifted across months or lost within a partition).
SELECT TO_CHAR(DATE_TRUNC('month', CONVERT_TIMEZONE('UTC', RENTAL_DATE)), 'YYYY-MM') AS month_utc, COUNT(*) AS row_count
FROM PAGILA_MIG.RAW.RENTAL
GROUP BY 1
ORDER BY 1
