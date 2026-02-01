from datetime import datetime, timedelta
import time
import json
import requests
from airflow import DAG
from airflow.operators.dummy import DummyOperator
from airflow.operators.python import PythonOperator
from airflow.providers.http.operators.http import SimpleHttpOperator
from airflow.models import Variable
from airflow.hooks.base_hook import BaseHook

default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2024, 8, 1),
}

dag = DAG(
    'dbt_cloud_agent_test',
    default_args=default_args,
    description='Production dbt Cloud job trigger',
    schedule_interval=None,
    catchup=False,
    max_active_runs=1,
    tags=['dbt-cloud', 'production', 'chicory'],
)

start_task = DummyOperator(task_id='start_pipeline', dag=dag)

# Trigger dbt Cloud job
trigger_dbt_job = SimpleHttpOperator(
    task_id='trigger_dbt_cloud_job',
    http_conn_id='dbt_cloud_api',
    endpoint='/api/v2/accounts/{{ var.value.dbt_account_id }}/jobs/{{ var.value.dbt_job_id }}/run/',
    method='POST',
    headers={
        'Authorization': 'Token {{ var.value.dbt_cloud_token }}',
        'Content-Type': 'application/json'
    },
    data=json.dumps({
        'cause': 'Triggered by Airflow Production Pipeline',
        'git_sha': None,
    }),
    dag=dag,
)

# Chicory Post-Hook (PythonOperator)
def run_chicory_agent(ti, dag, run_id, **context):
    # Get connection info from Airflow Connection
    conn = BaseHook.get_connection("chicory_api")
    base_url = conn.host.rstrip("/")
    headers = json.loads(conn.extra or "{}")

    CHICORY_AGENT_ID = Variable.get("CHICORY_AGENT_ID")
    current_time = datetime.utcnow().isoformat() + "Z"

    prompt_context = f"""
    Run cost analysis for pipeline {dag.dag_id}, run_id {run_id}.
    You have default permission to execute all available tools/mcp. Respond with the created resources information/list.

---

### Context:
- **Airflow**: DAG/orchestration structure and lineage insights
- **dbt**: Pipeline and SQL transformation details
- **BigQuery**: Query execution, bytes processed, and billing information
- **Redash**: Visualization and trend tracking

---

### Goal:
Create Dashboard/Query with the cost analysis data for better visualization and understanding.

---

### Your task:
1. Identify all queries associated with the completed pipeline run.
2. Retrieve the compute credits (cost) consumed by each query from usage logs.
3. Attribute query costs to their corresponding dbt models or pipeline stages.
4. Aggregate costs to calculate the total for the pipeline run and for each stage.
5. Persist historical cost data into BigQuery table `analytics.pipeline_cost_history`, view `analytics.query_costs`, and surface insights through Redash dashboards (widgets/viz) for ongoing trend analysis. If the dashboard/queries exist, add on to that.

---

### Dashboard Plan:
Redash dashboards should be designed with both technical (engineers/analysts) and business (leads/execs) users in mind.

#### 1. **Historical Pipeline Cost Trends**
- **Line chart**: Total cost per pipeline run across dates.
- **Multi-line chart**: Compare costs of multiple pipelines over time.
- **Rolling average line**: Smooth out spikes to highlight patterns.
- **Insight**: Detect increasing cost trends and anomalies.

#### 2. **Pipeline Cost Breakdown (per run)**
- **Stacked bar chart**: Cost per dbt model or stage in the pipeline.
- **Tree map**: Contribution of each stage/model to the run cost.
- **Table**: Raw query → model → bytes processed → $ cost.
- **Insight**: Identify cost-heavy models or transformations.

#### 3. **Query-Level Analysis**
- **Bar chart**: Top 10 most expensive queries.
- **Scatter plot**: Bytes processed vs execution time.
- **Insight**: Spot inefficient queries for optimization.

#### 4. **Comparative Cost View**
- **Heatmap**: Pipelines (rows) vs dates (columns) → cost intensity.
- **Box plot**: Distribution of costs per pipeline.
- **Insight**: See stable vs volatile pipelines, prioritize governance.

#### 5. **Cumulative & Forecasting**
- **Cumulative line chart**: Monthly/quarterly cost per pipeline.
- **Forecast line**: Projected spend if trends continue.
- **Insight**: Budget alignment and future spend prediction.

#### 6. **Redash Widgets**
- **Single value tiles**:
  - Total cost for last run
  - % change vs previous run
- **Run comparison widget**: Side-by-side view of two run IDs.
- **Filter controls**: Pipeline ID, Date Range, Run ID.

#### 7. **Appendix / Audit Trail**
- **Table view**: `analytics.query_costs` for transparency.
- **Drill-down links**: Query job IDs → BigQuery console.
- **Notes panel**: Show lineage context from Airflow/dbt.

---

### Note:
- Always use available tools and logs to fetch metrics.
- Use Airflow and dbt metadata for runtime context, pipeline lineage, and job details.
- Use BigQuery job logs to extract bytes processed and compute costs, referencing dataset `Billing` for detailed cost information.
- Include Appendix with all steps/tools/decisions taken for the response.
    """

    payload = {
        "agent_name": CHICORY_AGENT_ID,
        "input": [
            {
                "parts": [
                    {
                        "content_type": "text/plain",
                        "content": prompt_context
                    }
                ],
                "created_at": current_time
            }
        ]
    }

    # Create async run
    resp = requests.post(f"{base_url}/runs", headers=headers, data=json.dumps(payload))
    resp.raise_for_status()
    run_id = resp.json().get("run_id")
    if not run_id:
        raise Exception(f"Failed to create Chicory run: {resp.text}")

    # Poll for completion
    for attempt in range(180):  # 15 minutes max
        status_resp = requests.get(f"{base_url}/runs/{run_id}", headers=headers)
        status_resp.raise_for_status()
        data = status_resp.json()
        status = data.get("status")
        if status == "completed":
            output = data.get("output", [{}])[0].get("parts", [{}])[0].get("content")
            ti.xcom_push(key="chicory_output", value=output)
            print("Chicory run completed:", output)
            return output
        elif status in ("failed", "error"):
            raise Exception(f"Chicory run failed: {data}")
        time.sleep(5)

    raise TimeoutError("Chicory run did not complete in time")

chicory_posthook = PythonOperator(
    task_id="chicory_posthook",
    python_callable=run_chicory_agent,
    provide_context=True,
    dag=dag,
)

end_task = DummyOperator(task_id='end_pipeline', dag=dag)

# Task dependencies
start_task >> trigger_dbt_job >> chicory_posthook >> end_task
