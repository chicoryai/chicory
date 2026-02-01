from airflow import DAG
from airflow.providers.google.cloud.hooks.gcs import GCSHook
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from airflow.models import Variable
import csv
import io
import logging
import requests
import json

BUCKET_NAME = "new_vendor_data"
OBJECT_NAME = "demo.csv"

REPO = Variable.get("GITHUB_REPO")  # e.g., "my-org/my-repo"
GH_TOKEN = Variable.get("GITHUB_PAT")

def trigger_github_action(**context):
    """Send repository_dispatch event to GitHub with bucket/object info"""
    url = f"https://api.github.com/repos/{REPO}/dispatches"
    headers = {
        "Authorization": f"token {GH_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    payload = {
        "event_type": "chicory-mapping",
        "client_payload": {
            "bucket": BUCKET_NAME,
            "object": OBJECT_NAME,
            "dag_run_id": context['dag_run'].run_id
        }
    }

    logging.info(f"Sending payload to GitHub: {json.dumps(payload, indent=2)}")
    resp = requests.post(url, headers=headers, data=json.dumps(payload))
    
    if resp.status_code == 204:
        logging.info("✅ Successfully triggered GitHub Action.")
    else:
        logging.error(f"❌ Failed to trigger GitHub Action: {resp.status_code}, {resp.text}")
        raise Exception("GitHub dispatch failed")

def read_gcs_file(**context):
    """Read first 10 rows of a GCS file"""
    hook = GCSHook(gcp_conn_id="google_cloud_default")
    file_bytes = hook.download(bucket_name=BUCKET_NAME, object_name=OBJECT_NAME)
    content = file_bytes.decode("utf-8")
    reader = csv.reader(io.StringIO(content))
    
    rows = []
    for i, row in enumerate(reader):
        if i >= 10:
            break
        rows.append(row)
    
    logging.info(f"First 10 rows:\n{rows}")
    context["ti"].xcom_push(key="sample_rows", value=rows)
    return rows

with DAG(
    dag_id="gcs_read_demo",
    start_date=days_ago(1),
    schedule_interval=None,
    catchup=False,
    tags=["chicory", "gcs"],
) as dag:
    
    read_file = PythonOperator(
        task_id="read_gcs_file",
        python_callable=read_gcs_file,
        provide_context=True
    )

    trigger = PythonOperator(
        task_id="trigger_github_action",
        python_callable=trigger_github,
        provide_context=True
    )

    read_file >> trigger
