# Introduction

This cookbook shows how to use **Chicory AI agents** to generate a Root Cause Analysis report for a failed DAG

### Tools & Integrations
- **BigQuery MCP** – SQL execution and runtime insights
- **REST API** – Deployment mechanism for Chicory agents
- **Github MCP** – Github code repository for supporting code/documentation
- **DBT MCP** – DBT connection for pipeline runs

---
**Problem**: Developers frequently receive PagerDuty/incident alerts for pipeline failures. Diagnosing root causes requires manually connecting information across multiple systems—logs, data lineage tools, orchestration platforms, and data quality monitors, which is time-consuming and delays incident resolution. 

### Quick Start

1. Build an Airflow Pipeline Dag
2. Set Pager Duty Alerts for incident notifications
3. Build the agent and deploy it


