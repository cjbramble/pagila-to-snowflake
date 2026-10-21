-- requirement: MIG-003
-- film: total rows and distinct primary keys (detects missing, extra, duplicate rows).
SELECT COUNT(*) AS row_count,
       COUNT(DISTINCT FILM_ID::varchar) AS distinct_pk_count
FROM PAGILA_MIG.RAW.FILM
