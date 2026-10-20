-- ETL-006/007: status, days late, and fee agree with the fee basis on every row.
-- Daily fees stop at 2 x rental_duration days; anything later is a replacement.
{{ config(meta={'requirement': ['ETL-006', 'ETL-007']}) }}

select m.*
from {{ ref('mart_rental_returns') }} as m
inner join {{ ref('stg_film') }} as f on f.film_id = m.film_id
where not (
       (m.fee_basis = 'none' and m.return_status = 'on_time'
        and m.days_late = 0 and m.late_fee = 0)
    or (m.fee_basis = 'not_returned' and m.return_status = 'not_returned'
        and m.days_late is null and m.late_fee is null)
    or (m.fee_basis = 'daily' and m.return_status = 'late'
        and m.days_late between 1 and 2 * f.rental_duration
        and m.late_fee = m.days_late * 1.00)
    or (m.fee_basis = 'replacement' and m.return_status = 'late'
        and m.days_late > 2 * f.rental_duration
        and m.late_fee = f.replacement_cost)
)
