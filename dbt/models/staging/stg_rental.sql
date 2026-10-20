select
    rental_id,
    rental_date,
    inventory_id,
    customer_id,
    return_date,
    staff_id
from {{ source('raw', 'rental') }}
