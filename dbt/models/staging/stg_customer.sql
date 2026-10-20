select
    customer_id,
    store_id,
    first_name,
    last_name,
    email
from {{ source('raw', 'customer') }}
