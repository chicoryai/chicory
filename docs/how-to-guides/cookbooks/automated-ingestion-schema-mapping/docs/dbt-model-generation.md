# dbt Model Generation

## Overview

This section covers the automated generation of dbt models and YAML documentation from schema mappings using Chicory AI agents. The system creates production-ready dbt artifacts following best practices.

## Generated Artifacts

### 1. dbt Model SQL

The Chicory agent generates complete dbt model SQL files with:
- Proper source references
- Column transformations
- Data quality logic
- Performance optimizations

**Example Generated Model:**

```sql
{{
  config(
    materialized='table',
    tags=['auto-generated', 'dimension', 'customer'],
    description='Customer dimension table with standardized attributes'
  )
}}

with source_data as (
  select
    customer_id,
    first_name,
    last_name,
    email,
    phone,
    created_date,
    updated_date
  from {{ source('raw_crm', 'customers') }}
),

transformed as (
  select
    -- Surrogate key
    {{ dbt_utils.surrogate_key(['customer_id']) }} as customer_sk,

    -- Business key
    cast(customer_id as string) as customer_bk,

    -- Standardized names
    initcap(trim(first_name)) as first_name,
    initcap(trim(last_name)) as last_name,
    trim(concat(
      initcap(trim(first_name)),
      ' ',
      initcap(trim(last_name))
    )) as full_name,

    -- Contact information
    lower(trim(email)) as email_address,
    regexp_replace(phone, r'[^\d]', '') as phone_number,

    -- Temporal attributes
    cast(created_date as date) as customer_created_date,
    cast(updated_date as timestamp) as last_updated_ts,

    -- Audit columns
    current_timestamp() as created_at,
    current_timestamp() as updated_at,
    true as is_active

  from source_data
)

select * from transformed
```

### 2. YAML Documentation

Comprehensive YAML documentation with tests and metadata:

```yaml
version: 2

sources:
  - name: raw_crm
    description: Raw CRM data from Salesforce integration
    tables:
      - name: customers
        description: Customer master data
        columns:
          - name: customer_id
            description: Unique customer identifier from CRM
            tests:
              - not_null
              - unique

models:
  - name: dim_customer
    description: |
      Customer dimension table containing standardized customer attributes.

      This table is automatically generated from CRM customer data with the following transformations:
      - Name standardization (proper case, trimmed)
      - Email normalization (lowercase, trimmed)
      - Phone number cleaning (digits only)
      - Surrogate key generation

      **Source:** raw_crm.customers
      **Grain:** One row per customer
      **SCD Type:** Type 2 (planned for future implementation)

    columns:
      - name: customer_sk
        description: Surrogate key for the customer dimension
        tests:
          - not_null
          - unique

      - name: customer_bk
        description: Business key - original customer ID from source system
        tests:
          - not_null
          - unique

      - name: first_name
        description: Customer first name (standardized to proper case)
        tests:
          - not_null

      - name: last_name
        description: Customer last name (standardized to proper case)
        tests:
          - not_null

      - name: full_name
        description: Concatenated first and last name
        tests:
          - not_null

      - name: email_address
        description: Customer email address (normalized to lowercase)
        tests:
          - not_null
          - unique
          - relationships:
              to: ref('dim_customer')
              field: email_address

      - name: phone_number
        description: Customer phone number (digits only)

      - name: customer_created_date
        description: Date when customer was first created in source system
        tests:
          - not_null

      - name: last_updated_ts
        description: Timestamp of last update in source system

      - name: created_at
        description: Timestamp when record was created in data warehouse
        tests:
          - not_null

      - name: updated_at
        description: Timestamp when record was last updated in data warehouse
        tests:
          - not_null

      - name: is_active
        description: Flag indicating if customer record is active
        tests:
          - not_null
          - accepted_values:
              values: [true, false]

    tags: ['auto-generated', 'dimension', 'customer', 'pii']
```

## Generated Model Types

### 1. Dimension Tables

For dimension tables, the agent generates:
- Surrogate keys using dbt_utils
- SCD Type 2 structure (when applicable)
- Standardized attribute transformations
- Comprehensive business key mapping

### 2. Fact Tables

For fact tables, the agent includes:
- Foreign key relationships
- Measure calculations
- Grain documentation
- Aggregation logic

### 3. Staging Tables

For staging models, the agent provides:
- Basic data type casting
- Column renaming for consistency
- Initial data quality checks
- Source system documentation

## Customization Options

### 1. Model Configuration

Customize generated models through `dbt_project.yml`:

```yaml
models:
  analytics_dbt:
    auto_generated:
      +materialized: table
      +tags: ['auto-generated']
      +docs:
        node_color: 'lightblue'
    staging:
      +materialized: view
      +tags: ['staging', 'auto-generated']
    marts:
      dimensions:
        +materialized: table
        +tags: ['dimension', 'auto-generated']
      facts:
        +materialized: table
        +tags: ['fact', 'auto-generated']
```

### 2. Transformation Templates

Create custom transformation templates for specific patterns:

```sql
-- macros/standardize_name.sql
{% macro standardize_name(column_name) %}
  initcap(trim({{ column_name }}))
{% endmacro %}

-- macros/clean_phone.sql
{% macro clean_phone(column_name) %}
  regexp_replace({{ column_name }}, r'[^\d]', '')
{% endmacro %}

-- macros/standardize_email.sql
{% macro standardize_email(column_name) %}
  lower(trim({{ column_name }}))
{% endmacro %}
```

### 3. Testing Standards

Define organization-specific testing standards:

```yaml
# models/tests/custom_tests.sql
-- Test for valid email format
select *
from {{ ref('dim_customer') }}
where email_address is not null
  and not regexp_contains(email_address, r'^[^@]+@[^@]+\.[^@]+$')

-- Test for reasonable phone number length
select *
from {{ ref('dim_customer') }}
where phone_number is not null
  and (length(phone_number) < 10 or length(phone_number) > 15)
```

## Advanced Features

### 1. Incremental Models

For large datasets, the agent can generate incremental models:

```sql
{{
  config(
    materialized='incremental',
    unique_key='customer_bk',
    on_schema_change='fail',
    tags=['auto-generated', 'incremental']
  )
}}

select
  customer_sk,
  customer_bk,
  -- ... other columns
  last_updated_ts

from {{ ref('stg_customers') }}

{% if is_incremental() %}
  where last_updated_ts > (select max(last_updated_ts) from {{ this }})
{% endif %}
```

### 2. Slowly Changing Dimensions

Generate SCD Type 2 logic for dimension tables:

```sql
{{
  config(
    materialized='table',
    post_hook=[
      "create unique index if not exists idx_{{ this.identifier }}_current
       on {{ this }} (customer_bk) where is_current = true"
    ]
  )
}}

with source_data as (
  select * from {{ ref('stg_customers') }}
),

scd_logic as (
  select
    *,
    lag(email_address) over (
      partition by customer_bk
      order by last_updated_ts
    ) as prev_email,

    case
      when lag(email_address) over (
        partition by customer_bk
        order by last_updated_ts
      ) != email_address then true
      else false
    end as has_changed

  from source_data
)

select
  customer_sk,
  customer_bk,
  -- ... other columns

  -- SCD Type 2 columns
  last_updated_ts as valid_from,
  lead(last_updated_ts, 1, '9999-12-31') over (
    partition by customer_bk
    order by last_updated_ts
  ) as valid_to,

  case
    when lead(customer_bk) over (
      partition by customer_bk
      order by last_updated_ts
    ) is null then true
    else false
  end as is_current

from scd_logic
```

### 3. Data Quality Monitoring

Generate data quality monitoring models:

```sql
-- models/monitoring/data_quality_customer.sql
select
  'dim_customer' as table_name,
  current_timestamp() as check_timestamp,

  -- Row count checks
  count(*) as total_rows,
  count(distinct customer_bk) as unique_customers,

  -- Null checks
  sum(case when customer_bk is null then 1 else 0 end) as null_customer_bk,
  sum(case when email_address is null then 1 else 0 end) as null_email,

  -- Data quality scores
  round(
    (count(*) - sum(case when email_address is null then 1 else 0 end))
    / count(*) * 100, 2
  ) as email_completeness_pct,

  -- Freshness check
  max(last_updated_ts) as max_last_updated,
  current_timestamp() - max(last_updated_ts) as freshness_hours

from {{ ref('dim_customer') }}
```

## Integration with dbt Packages

### 1. dbt-utils Integration

The generated models leverage dbt-utils for:
- Surrogate key generation
- Cross-database compatibility
- Common transformations

```sql
-- Surrogate keys
{{ dbt_utils.surrogate_key(['customer_id', 'effective_date']) }}

-- Generate series for date dimensions
{{ dbt_utils.date_spine(
    datepart="day",
    start_date="cast('2020-01-01' as date)",
    end_date="cast('2025-12-31' as date)"
) }}

-- Pivot tables
{{ dbt_utils.pivot(
    'metric_type',
    dbt_utils.get_column_values(ref('customer_metrics'), 'metric_type'),
    agg='sum',
    then_value='metric_value'
) }}
```

### 2. dbt-expectations Integration

For advanced data quality testing:

```yaml
# _dim_customer.yml
tests:
  - dbt_expectations.expect_table_row_count_to_be_between:
      min_value: 1000
      max_value: 10000000

  - dbt_expectations.expect_column_values_to_match_regex:
      column_name: email_address
      regex: "^[^@]+@[^@]+\\.[^@]+$"

  - dbt_expectations.expect_column_quantile_values_to_be_between:
      column_name: customer_created_date
      quantile: 0.95
      min_value: "2020-01-01"
      max_value: "{{ var('max_date') }}"
```

## Performance Optimization

### 1. Partitioning and Clustering

For BigQuery targets:

```sql
{{
  config(
    materialized='table',
    partition_by={
      "field": "customer_created_date",
      "data_type": "date"
    },
    cluster_by=["customer_bk", "email_address"]
  )
}}
```

### 2. Query Optimization

The agent applies optimization techniques:

```sql
-- Use appropriate join types
with customers as (
  select * from {{ ref('stg_customers') }}
),

orders as (
  select
    customer_id,
    count(*) as order_count,
    sum(order_amount) as total_spent
  from {{ ref('stg_orders') }}
  group by customer_id
)

select
  c.*,
  coalesce(o.order_count, 0) as order_count,
  coalesce(o.total_spent, 0) as total_spent

from customers c
left join orders o
  on c.customer_bk = cast(o.customer_id as string)
```

## Validation and Testing

### 1. Model Compilation

Test generated models compile correctly:

```bash
# Compile all models
dbt compile

# Parse project structure
dbt parse

# Check for model dependencies
dbt list --models +dim_customer
```

### 2. Data Quality Testing

Run comprehensive tests:

```bash
# Run all tests for generated models
dbt test --select tag:auto-generated

# Run specific model tests
dbt test --select dim_customer

# Run source freshness checks
dbt source freshness
```

### 3. Documentation Generation

Generate and serve documentation:

```bash
# Generate documentation
dbt docs generate

# Serve documentation locally
dbt docs serve --port 8080
```

## Monitoring and Maintenance

### 1. Model Performance Monitoring

```sql
-- models/monitoring/model_performance.sql
select
  model_name,
  run_started_at,
  total_runtime_seconds,
  rows_affected,
  bytes_processed,

  -- Performance flags
  case
    when total_runtime_seconds > 300 then 'SLOW'
    when bytes_processed > 1000000000 then 'HIGH_COST'
    else 'NORMAL'
  end as performance_flag

from {{ ref('dbt_run_results') }}
where model_name like '%auto_generated%'
```

### 2. Automated Alerts

Set up alerts for:
- Model compilation failures
- Test failures
- Performance degradation
- Data freshness issues

### 3. Model Evolution

Track model changes over time:

```sql
-- models/monitoring/model_evolution.sql
select
  model_name,
  column_name,
  data_type,
  is_nullable,
  version_date,
  change_type -- 'ADDED', 'MODIFIED', 'REMOVED'

from {{ ref('schema_evolution_log') }}
where model_name like '%auto_generated%'
order by model_name, version_date desc
```

---

Next: [Testing & Validation](testing-validation.md)