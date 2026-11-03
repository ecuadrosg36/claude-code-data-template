-- One row per order. LEFT JOIN on purpose: an order whose customer is not loaded yet must stay in
-- the totals (order 1009 in the seed data shows it). tests/dbt/assert_orders_not_lost.sql guards this.
select
    o.order_id,
    o.customer_id,
    coalesce(c.country_code, 'UNKNOWN') as country_code,
    cast(o.ordered_at as date) as order_date,
    o.status,
    o.amount,
    o.status = 'refunded' as is_refunded
from {{ ref('stg_orders') }} as o
left join {{ ref('stg_customers') }} as c using (customer_id)
