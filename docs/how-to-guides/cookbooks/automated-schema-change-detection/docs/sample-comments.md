Schema Change Analysis

```
Schema Change Analysis

Changes Detected:

Column Rename: standard_cost → s_cost in product_performance.sql
Location: Line 8 of product_performance.sql
Change Type: Column alias modification (breaking change)

Impact Assessment:
DBT Models - ⚠️ HIGH IMPACT
The following files in the chicoryai/adventureworks-modern-data-stack repository reference standard_cost and will FAIL:

models/staging/stg_product_performance.sql - 🔴 CRITICAL

Lines affected: Multiple references throughout the file
Code snippet:
case 
    when standard_cost < 0 then 0.00  -- Handle negative costs
    when standard_cost is null then 0.00
    else round(cast(standard_cost as float64), 2)
end as standard_cost,
Impact: This staging model reads from mapper_enriched.product_performance_mapper and expects a column named standard_cost, not s_cost
models/marts/mart_partner_channel_analysis.sql - 🔴 CRITICAL

Lines affected: Multiple aggregations and calculations
Code snippet:
-- Financial metrics
avg(p.standard_cost) as avg_product_cost_in_territory,
sum(p.standard_cost) as total_inventory_value_potential,
min(p.standard_cost) as lowest_price_point,
max(p.standard_cost) as highest_price_point,
Impact: Joins with stg_product_performance and uses standard_cost in calculations for channel strategy scores and territory analysis
models/marts/mart_sales_perfromance_dashboard.sql - 🔴 CRITICAL

Lines affected: Cost metrics and portfolio positioning
Code snippet:
-- Cost metrics
avg(p.standard_cost) as avg_product_cost,
min(p.standard_cost) as min_product_cost,
max(p.standard_cost) as max_product_cost,
sum(p.standard_cost) as total_inventory_value,
Impact: References stg_product_performance and uses standard_cost for sales performance analysis
BigQuery - ⚠️ MEDIUM IMPACT
The following BigQuery tables/views will be affected:

chicory_analytics.staging.stg_product_performance (view)
chicory_analytics.marts.mart_partner_channel_analysis (table)
chicory_analytics.marts.mart_sales_perfromance_dashboard (table)
All dependent queries and downstream consumers will break when these models fail to build.

Redash - ✅ NO IMPACT
After checking all 48 Redash queries, none directly reference the standard_cost column. The queries primarily use fact tables and dimension tables, not the product performance mapper.

Data Contracts - 👥 AFFECTED USERS
Based on the Data-Contracts repository, the following stakeholders will be impacted:

DC-002: Mapper Enriched Dataset

Owner: Saurabh (saurabh@chicory.ai) - Technical Team Head
Impact: Source table product_performance_mapper schema change
DC-003: dbt Development Staging Models

Owner: Saurabh (saurabh@chicory.ai) - Technical Team Head
Impact: stg_product_performance model will fail to build
Downstream impact: All marts dependent on staging
DC-004: dbt Development Marts

Owner: Jessica James (jessica.james@chicory.ai) - Business Intelligence Head
Impact: Both mart_partner_channel_analysis and mart_sales_perfromance_dashboard will fail
Affected Teams: Business Analysts, Marketing Team, Sales Team, Executive Team
SLA Risk: 99.9% availability target at risk

Action Required:
Option 1: Revert the Change (RECOMMENDED)
Keep the column name as standard_cost to maintain backward compatibility.

Option 2: Coordinated Update (COMPLEX)
If the rename is necessary, coordinate the following updates in order:

Update upstream mapper (this PR)

Change standard_cost to s_cost
Update DBT staging layer (chicoryai/adventureworks-modern-data-stack)

File: models/staging/stg_product_performance.sql
Change: Update all references from standard_cost to s_cost
Add alias: s_cost as standard_cost to maintain downstream compatibility
Update DBT marts layer (chicoryai/adventureworks-modern-data-stack)

Files: models/marts/mart_partner_channel_analysis.sql, models/marts/mart_sales_perfromance_dashboard.sql
Change: Update all references from p.standard_cost to p.s_cost OR rely on staging alias
Test end-to-end

Run full dbt pipeline
Validate all mart tables
Verify Business Intelligence dashboards
Notify stakeholders

Email: Saurabh (saurabh@chicory.ai)
Email: Jessica James (jessica.james@chicory.ai)
Teams: Business Analysts, Marketing, Sales, Executive
Severity: 🔴 HIGH
Rationale: This breaking change affects critical business reporting tables with a 99.9% SLA and impacts executive-level dashboards. The column is used in 3 DBT models across 11 locations for financial calculations and business intelligence.

Recommendation: Do not merge until coordinated fix is in place across all dependent systems.

```