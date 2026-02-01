# Setting up your pipeline orchestrator

## Pre-work Before Running the Pipeline

1. **Create an Airflow Connection for Chicory API**

   **Purpose**: This connection securely stores your Chicory API credentials, allowing Airflow tasks to authenticate with the Chicory platform without exposing tokens in your DAG code. The agent will use this connection to receive cost analysis requests from your pipeline.

* In Airflow UI → **Admin** → **Connections** → +
* Fill in the following:
    * Conn Id: `chicory_api`
    * Conn Type: `HTTP`
    * Host: `https://app.chicory.ai/api/v1`
    * Extra (JSON):
    ```
    {
        "Authorization": "Bearer YOUR_CHICORY_API_TOKEN"
    }
    ```
* Save. This will let tasks authenticate without hardcoding the token.

<img src="../images/airflow-connection.png" alt="Airflow Connection" style="width:50%;"/>

2. **Set Chicory Agent ID as Airflow Variable**

   **Purpose**: This variable identifies which specific Chicory agent should handle cost analysis for your pipeline. Each agent is configured with specific tools and context for your infrastructure, ensuring the right agent processes your cost analysis requests with access to your BigQuery, dbt, and dashboard tools.

```
airflow variables set CHICORY_AGENT_ID "YOUR_CHICORY_AGENT_ID"
```

## Airflow Post-hook

Add a task at the end of your DAG to call the agent after a successful pipeline run.

**Purpose**: The post-hook ensures cost analysis happens automatically after every successful pipeline run, providing consistent cost tracking without manual intervention.

{% file src="../scripts/airflow_dag.py" %}
    Complete DAG example with cost analysis integration
{% endfile %}

### What's in the DAG Code

The `airflow_dag.py` file contains a complete example showing:

1. **Standard Pipeline Tasks**:
   - `start_task`: Pipeline initialization
   - `trigger_dbt_job`: Executes dbt transformations via dbt Cloud API
   - Uses Airflow Variables for dbt account/job IDs and authentication tokens

2. **Chicory Integration Function** (`run_chicory_agent`):
   - Retrieves connection details from the Airflow connection you configured
   - Constructs a detailed prompt with pipeline context (run_id, DAG name)
   - Makes API call to trigger the Chicory agent asynchronously
   - Polls for completion and returns results via XCom

3. **Task Dependencies**:
   - `start_task >> trigger_dbt_job >> chicory_posthook >> end_task`
   - Ensures cost analysis only runs after successful dbt execution
   - Maintains clear pipeline lineage for debugging

### Agent Task
- Sample user prompt/context
```
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
```

## Alternative Orchestration Methods

### 1. Event-Driven Approaches
Instead of Airflow post-hooks, consider these reactive methods:

- **Cloud Functions/Lambda Triggers**: Automatically trigger on BigQuery job completion
  - [BigQuery Job State Change Notifications](https://cloud.google.com/bigquery/docs/monitoring#job-state-change-notifications)
  - [Cloud Functions BigQuery Triggers](https://cloud.google.com/run/docs/triggering/storage-triggers)
- **Pub/Sub Messaging**: Real-time cost tracking with message queues
  - [Pub/Sub BigQuery Integration](https://cloud.google.com/pubsub/docs/bigquery)

### 2. Scheduled Approaches
For batch cost analysis:

- **BigQuery Scheduled Queries**: Native cost aggregation without external orchestration
  - [Scheduled Queries Documentation](https://cloud.google.com/bigquery/docs/scheduling-queries)
- **Cloud Scheduler**: Simple cron-based cost analysis triggers
  - [Cloud Scheduler with BigQuery](https://cloud.google.com/scheduler/docs/creating)

### 3. dbt Integration
Embed cost tracking in your transformation layer:

- **dbt Post-hooks**: Add cost tracking directly to model runs
  - [dbt Hooks Documentation](https://docs.getdbt.com/reference/resource-configs/pre-hook-post-hook)
- **dbt Exposures**: Track cost lineage with downstream dependencies
  - [dbt Exposures](https://docs.getdbt.com/docs/build/exposures)

---
