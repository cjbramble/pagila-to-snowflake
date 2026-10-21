{{ config(meta={'requirement': ['ETL-005', 'ETL-006', 'ETL-007']}) }}
-- Column-to-column invariants: status vs return_date/due_at, days_late, fee_basis, late_fee.
select rental_id, return_status, fee_basis, days_late, late_fee, due_at, return_date
from {{ ref('mart_rental_returns') }}
where
    (return_status = 'not_returned') != (return_date is null)
    or (return_status = 'on_time' and not (return_date <= due_at))
    or (return_status = 'late' and not (return_date > due_at))
    or (return_status = 'not_returned' and (days_late is not null or late_fee is not null or fee_basis != 'not_returned'))
    or (return_status = 'on_time' and (days_late != 0 or late_fee != 0 or fee_basis != 'none'))
    or (return_status = 'late' and (days_late < 1 or late_fee is null or fee_basis not in ('daily', 'replacement')))
    or (fee_basis = 'daily' and late_fee != days_late)
    or (fee_basis = 'replacement' and late_fee <= 0)
