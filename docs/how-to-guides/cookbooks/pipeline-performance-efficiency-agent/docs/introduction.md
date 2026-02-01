# Introduction

This cookbook shows how to use **Chicory AI agents** to improve pipeline efficiency.

### Tools & Integrations
- **BigQuery** – SQL execution and runtime insights
- **dbt** – Models and transformations
- **Airflow** – DAG orchestration and pipeline lineage
- **DataHub / Redash** – Metadata and dashboards
- **GitHub** – Source control & pull request workflow
- **REST API** – Deployment mechanism for Chicory agents

---

**Problem**: Cloud data warehouse queries and models often create inefficiencies. Without a comprehensive review of the entire data lakehouse environment, it becomes difficult to understand the broader impact that a proposed change may have on the system.

### Quick Start

1. Copy the GitHub Action into your repo.
{% file src="../.github/workflows/pr-analysis.yml" %}
    Github Action Workflow.
{% endfile %}

2. Add your Chicory API secrets:
   - `CHICORY_API_TOKEN`
   - `CHICORY_AGENT_ID`
3. Open a pull request with changes to your models or SQL code.
4. Chicory AI will analyze the changes and post a **performance review comment**.
