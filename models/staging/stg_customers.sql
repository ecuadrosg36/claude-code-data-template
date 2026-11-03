select
    customer_id,
    trim(full_name) as full_name,
    upper(country) as country_code,
    cast(created_at as date) as created_on
from {{ ref('raw_customers') }}
