{{ config(meta={'requirement': 'ETL-004'}) }}
-- Timestamp outputs are normalised to UTC (zero offset), not left at the input's offset.
select rental_id, rental_date, due_at, return_date
from {{ ref('mart_rental_returns') }}
where extract(timezone_hour from rental_date) != 0 or extract(timezone_minute from rental_date) != 0
   or extract(timezone_hour from due_at) != 0 or extract(timezone_minute from due_at) != 0
   or extract(timezone_hour from return_date) != 0 or extract(timezone_minute from return_date) != 0
