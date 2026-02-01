# Introduction

This cookbook shows how to use **Chicory AI agents** to generate data catalog for a new onboarding data asset.

### Tools & Integrations
- **BigQuery** – SQL execution and runtime insights
- **REST API** – Deployment mechanism for Chicory agents

---
**Problem**: Data teams spend significant time manually documenting tables, columns, and relationships across multiple data platforms. Creating and maintaining accurate data catalogs with metadata, lineage, business definitions, and ownership information is time-consuming and often becomes outdated quickly as schemas evolve.

### Quick Start

1. Build the monitoring table and policies for your sample data
2. Build the agent and deploy it
3. Build the cloud run function
4. Create a new data asset
5. Trigger the cloud run - This triggers the agent with the new table schema info and gets back the column level desciptions back to the BigQuery table

