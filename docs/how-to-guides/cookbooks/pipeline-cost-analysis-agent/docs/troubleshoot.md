# Troubleshooting Guide

Common issues and fixes when running the **Pipeline Cost Analysis Agent**.

---

## 1. DAG not appearing in Airflow
- Ensure the DAG file is placed in the `dags/` folder.
- Restart the Airflow webserver/scheduler.

---

## 2. Chicory API connection error
- Verify Airflow **Connection** `chicory_api` exists under **Admin → Connections**.
- Ensure `Host` is set to `https://app.chicory.ai/api/v1`.
- Check the **Extra** field contains:
  ```json
  {"Authorization": "Bearer YOUR_CHICORY_API_TOKEN"}
  ```

---

## 3. Variable not found
- Ensure `CHICORY_AGENT_ID` is set:
  ```bash
  airflow variables set CHICORY_AGENT_ID "your-agent-id"
  ```

---

## 4. BigQuery billing data not found
- Confirm **Billing Export** is enabled in GCP console.
- Check dataset/table (e.g., `Billing`) exists and is populated.
- Verify Airflow service account has `bigquery.jobs.list` and `bigquery.readsessions.*` permissions.

---

## 5. Post-hook times out
- By default, the task polls for 5 minutes.
- Increase wait loop in `run_chicory_agent` if queries take longer.
- Check Chicory run logs for detailed error messages.

---

## 6. Redash dashboard not refreshing
- Verify Redash API key is valid and has correct permissions.
- Ensure the query linked to `analytics.pipeline_cost_history` runs without error.
- Refresh dashboard manually from Redash UI to test.

---

Feel free to reach out to Chicory Team for any issues.

---
