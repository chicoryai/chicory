# Run Pipeline + Dashboard

1. **Trigger Airflow Pipeline**
   - Run the DAG from the Airflow UI or CLI
   - DAG completes dbt run → triggers cost analysis agent

<img src="../images/airflow-complete.png" alt="Airflow DAG Complete" style="width:25%;"/>


<img src="../images/airflow-logs.png" alt="Airflow DAG Logs" style="width:25%;"/>

2. **Agent Writes Cost Data**
   - Each run inserts rows into `analytics.pipeline_cost_history`

<img src="../images/cost_history.png" alt="Cost History Table" style="width:25%;"/>

3. **Refresh / Create Redash Dashboard/Query**
   - If dashboard exists: agent calls Redash API to refresh
   - If not: agent creates a new dashboard

<img src="../images/budget-threshold.png" alt="Analysis Report" style="width:25%;"/>

<img src="../images/pipeline-code-trends.png" alt="Analysis Report" style="width:25%;"/>

<img src="../images/pipeline-code.png" alt="Analysis Report" style="width:25%;"/>

<img src="../images/pipeline-summary-metrics.png" alt="Analysis Report" style="width:25%;"/>

<img src="../images/expensive-query.png" alt="Analysis Report" style="width:25%;"/>

---
