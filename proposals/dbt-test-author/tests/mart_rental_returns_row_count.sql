{{ config(meta={'requirement': ['ETL-004', 'ETL-005']}) }}
-- Every rental has exactly one row (joins must not drop or multiply rentals).
select m.n_mart, s.n_src
from (select count(*) as n_mart from {{ ref('mart_rental_returns') }}) as m
cross join (select count(*) as n_src from {{ source('raw', 'rental') }}) as s
where m.n_mart != s.n_src
