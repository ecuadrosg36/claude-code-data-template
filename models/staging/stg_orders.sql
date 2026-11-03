select
    order_id,
    customer_id,
    cast(ordered_at as timestamp) as ordered_at,
    lower(status) as status,
    cast(amount as decimal(12, 2)) as amount
from {{ ref('raw_orders') }}
