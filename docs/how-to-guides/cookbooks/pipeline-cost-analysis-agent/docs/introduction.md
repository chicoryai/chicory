# Introduction

The **Pipeline Cost Analysis Agent** helps teams track and optimize data pipeline spend.

### Tools & Integrations
- **BigQuery** – SQL execution and runtime insights
- **dbt** – Models and transformations
- **Airflow** – DAG orchestration and pipeline lineage
- **DataHub / Redash** – Metadata and dashboards
- **GitHub** – Source control & pull request workflow
- **ACP API** – Deployment mechanism for Chicory agents

---

**Problem**: Cloud data warehouse queries can be costly. Without attribution, it’s unclear which dbt models or stages drive spend.

### Quick Start

1. **[Set up BigQuery billing export](./docs/bigquery-billing-setup.md)** - Enable detailed cost data export and create the cost history table
2. **[Create the Chicory agent](./docs/chicory-agent.md)** - Build and deploy your cost analysis agent with the provided template
3. **[Configure Airflow integration](./docs/airflow-posthook.md)** - Add the post-hook task to trigger cost analysis after pipeline runs
4. **[Run and visualize](./docs/run-and-dashboard.md)** - Execute your pipeline and view cost analytics in the dashboard

---
