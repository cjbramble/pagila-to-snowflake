-- requirement: MIG-003
-- rental: total rows and distinct primary keys (detects missing, extra, duplicate rows).
SELECT COUNT(*) AS row_count,
       COUNT(DISTINCT RENTAL_ID::varchar) AS distinct_pk_count
FROM PAGILA_MIG.RAW.RENTAL
