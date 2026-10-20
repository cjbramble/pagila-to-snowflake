-- ETL-004 to ETL-007: due date, return status, days late, and late fee per rental.

with rentals as (
    select
        r.rental_id,
        r.customer_id,
        i.store_id,
        i.film_id,
        -- Output timestamps in UTC (rule header); TIMESTAMP_TZ otherwise keeps each
        -- input's own offset, and due_at would inherit it from rental_date.
        convert_timezone('UTC', r.rental_date) as rental_date,
        convert_timezone('UTC', r.return_date) as return_date,
        f.rental_duration,
        f.replacement_cost,
        dateadd(day, f.rental_duration, convert_timezone('UTC', r.rental_date)) as due_at
    from {{ ref('stg_rental') }} as r
    inner join {{ ref('stg_inventory') }} as i on i.inventory_id = r.inventory_id
    inner join {{ ref('stg_film') }} as f on f.film_id = i.film_id
),

measured as (
    select
        *,
        -- DATEDIFF counts unit boundaries crossed, not elapsed time; microseconds match
        -- the stored precision, so this is the exact time after due_at.
        datediff(microsecond, due_at, return_date) as micros_after_due
    from rentals
),

classified as (
    select
        *,
        case
            when return_date is null then 'not_returned'
            when return_date <= due_at then 'on_time'
            else 'late'
        end as return_status,
        case
            when return_date is null then 'not_returned'
            when return_date <= due_at then 'none'
            when micros_after_due > 2 * rental_duration * 86400000000 then 'replacement'
            else 'daily'
        end as fee_basis
    from measured
)

select
    rental_id,
    customer_id,
    store_id,
    film_id,
    rental_date,
    due_at,
    return_date,
    return_status,
    case return_status
        when 'late' then ceil(micros_after_due / 86400000000)
        when 'on_time' then 0
    end::number(10, 0) as days_late,
    fee_basis,
    case fee_basis
        when 'daily' then ceil(micros_after_due / 86400000000) * 1.00
        when 'replacement' then replacement_cost
        when 'none' then 0.00
    end::number(7, 2) as late_fee
from classified
