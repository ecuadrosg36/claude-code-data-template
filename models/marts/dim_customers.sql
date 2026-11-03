select
    c.customer_id,
    c.full_name,
    c.country_code,
    count(o.order_id) as orders,
    coalesce(sum(o.amount) filter (where not o.is_refunded), 0) as lifetime_value
from {{ ref('stg_customers') }} as c
left join {{ ref('fct_orders') }} as o using (customer_id)
group by c.customer_id, c.full_name, c.country_code
