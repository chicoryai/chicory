# Introduction

This cookbook shows how to use **Chicory AI agents** to detect any Schema Changes on a raised PR .

### Tools & Integrations
- **BigQuery** – SQL execution and runtime insights
- **dbt** – Models and transformations
- **DataHub / Redash** – Metadata and dashboards
- **GitHub** – Source control & pull request workflow
- **Data Contracts** - Data Contract documentation for the organization
- **REST API** – Deployment mechanism for Chicory agents

---

**Problem**: Schema changes in pull requests frequently cause downstream pipeline failures and report breakages that impact end users. Without proactive schema validation, breaking changes are only discovered after deployment—when it's too late to prevent user disruption.

### Quick Start

1. Copy the GitHub Action into your repo.
{% file src="../.github/workflows/pr-analysis.yml" %}
    Github Action Workflow.
{% endfile %}

2. Add your Chicory API secrets:
   - `CHICORY_API_TOKEN`
   - `CHICORY_AGENT_ID`
3. Establish Github MCP connection with the agent
4. Open a pull request with schema changes to your models or SQL code.
5. Chicory AI will analyze the changes and post an **Analysis and Affected radius review comment**.
