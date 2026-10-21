{{ config(meta={'requirement': ['ETL-004', 'ETL-005', 'ETL-006', 'ETL-007']}) }}
-- Independent recompute on real data from raw tables, using exact microsecond
-- arithmetic on a different formulation (exact integer day split via MOD, no decimal division).
-- Also proves one row per rental (no drops or fan-out). Rows returned are mismatches.
with base as (
    select
        r.rental_id,
        r.rental_date as rd, r.return_date as ret,
        f.rental_duration as dur, f.replacement_cost as repl
    from {{ source('raw', 'rental') }} as r
    join {{ source('raw', 'inventory') }} as i on i.inventory_id = r.inventory_id
    join {{ source('raw', 'film') }} as f on f.film_id = i.film_id
),
calc as (
    select *,
        timestampadd(day, dur, rd) as due,
        timestampdiff(microsecond, timestampadd(day, dur, rd), ret) as us
    from base
),
expected as (
    select rental_id, due,
        case when ret is null then 'not_returned' when us <= 0 then 'on_time' else 'late' end as st,
        case when ret is null then null when us <= 0 then 0
             else ((us - mod(us, 86400000000)) / 86400000000 + iff(mod(us, 86400000000) > 0, 1, 0)) end as dl,
        case when ret is null then null when us <= 0 then 0.00
             when us > 2 * dur * 86400000000 then repl
             else ((us - mod(us, 86400000000)) / 86400000000 + iff(mod(us, 86400000000) > 0, 1, 0)) * 1.00 end as fee
    from calc
)
select coalesce(m.rental_id, e.rental_id) as rental_id
from {{ ref('mart_rental_returns') }} as m
full outer join expected as e on e.rental_id = m.rental_id
where m.rental_id is null or e.rental_id is null
   or m.due_at != e.due
   or m.return_status != e.st
   or m.days_late is distinct from e.dl
   or m.late_fee is distinct from e.fee
