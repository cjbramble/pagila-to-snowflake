-- requirement: MIG-003
-- payment: total rows and distinct primary keys (detects missing, extra, duplicate rows).
SELECT COUNT(*) AS row_count,
       COUNT(DISTINCT PAYMENT_ID::varchar || '|' || TO_CHAR(CONVERT_TIMEZONE('UTC', PAYMENT_DATE), 'YYYY-MM-DD"T"HH24:MI:SS.FF6')) AS distinct_pk_count
FROM PAGILA_MIG.RAW.PAYMENT
