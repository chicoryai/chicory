# Airflow DAG Configuration

## Overview

This section covers creating the Airflow DAG that monitors S3 for new CSV files, extracts their schemas, and triggers the GitHub Actions workflow for automated schema mapping.

## DAG Structure

Our DAG will consist of:
1. **S3 Key Sensor**: Monitor for new CSV files
2. **Schema Extraction**: Analyze CSV structure and data types
3. **GitHub Trigger**: Start the schema mapping workflow
4. **File Management**: Move processed files to appropriate folders

## DAG Implementation

### 1. Main DAG File

Create `automated_ingestion_dag.py` in your Airflow DAGs folder:

```python
from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.amazon.aws.sensors.s3 import S3KeySensor
from airflow.providers.amazon.aws.operators.s3 import S3MoveObjectOperator
from airflow.operators.python import PythonOperator
from airflow.providers.http.operators.http import SimpleHttpOperator
import pandas as pd
import boto3
import json
import logging

default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5)
}

dag = DAG(
    'automated_csv_ingestion',
    default_args=default_args,
    description='Automated CSV ingestion and schema mapping',
    schedule_interval=None,  # Triggered by file sensor
    catchup=False,
    max_active_runs=1,
    tags=['ingestion', 'schema-mapping', 'chicory']
)

# Configuration
S3_BUCKET = "{{ var.value.AWS_S3_BUCKET }}"
S3_PREFIX = "incoming/"
GITHUB_TOKEN = "{{ var.value.GITHUB_TOKEN }}"
GITHUB_REPO = "{{ var.value.GITHUB_REPO }}"
CHICORY_API_KEY = "{{ var.value.CHICORY_API_KEY }}"
```

### 2. S3 File Sensor

```python
def get_latest_s3_file(**context):
    """Find the latest CSV file in the S3 bucket"""
    s3_client = boto3.client('s3')

    response = s3_client.list_objects_v2(
        Bucket=S3_BUCKET,
        Prefix=S3_PREFIX
    )

    if 'Contents' not in response:
        raise ValueError("No files found in S3 bucket")

    # Filter for CSV files and get the latest
    csv_files = [
        obj for obj in response['Contents']
        if obj['Key'].endswith('.csv')
    ]

    if not csv_files:
        raise ValueError("No CSV files found in S3 bucket")

    latest_file = max(csv_files, key=lambda x: x['LastModified'])

    # Store file info in XCom
    context['task_instance'].xcom_push(
        key='s3_file_key',
        value=latest_file['Key']
    )

    return latest_file['Key']

wait_for_file = PythonOperator(
    task_id='wait_for_s3_file',
    python_callable=get_latest_s3_file,
    dag=dag
)
```

### 3. Schema Extraction

```python
def extract_csv_schema(**context):
    """Extract schema information from the CSV file"""
    s3_client = boto3.client('s3')

    # Get file key from previous task
    file_key = context['task_instance'].xcom_pull(
        task_ids='wait_for_s3_file',
        key='s3_file_key'
    )

    # Parse filename for metadata
    filename = file_key.split('/')[-1]
    parts = filename.replace('.csv', '').split('_')

    source_system = parts[0] if len(parts) > 0 else 'unknown'
    table_name = parts[1] if len(parts) > 1 else 'unknown'

    try:
        # Download and analyze CSV
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=file_key)
        df = pd.read_csv(response['Body'])

        # Extract schema information
        schema_info = {
            'source_system': source_system,
            'table_name': table_name,
            'filename': filename,
            'file_path': file_key,
            'row_count': len(df),
            'columns': []
        }

        for col in df.columns:
            col_info = {
                'name': col,
                'dtype': str(df[col].dtype),
                'null_count': int(df[col].isnull().sum()),
                'null_percentage': float(df[col].isnull().sum() / len(df) * 100),
                'unique_count': int(df[col].nunique()),
                'sample_values': df[col].dropna().head(5).tolist()
            }

            # Infer semantic type
            if 'id' in col.lower():
                col_info['semantic_type'] = 'identifier'
            elif 'email' in col.lower():
                col_info['semantic_type'] = 'email'
            elif 'phone' in col.lower():
                col_info['semantic_type'] = 'phone'
            elif 'date' in col.lower() or 'time' in col.lower():
                col_info['semantic_type'] = 'temporal'
            elif df[col].dtype in ['float64', 'int64']:
                col_info['semantic_type'] = 'numeric'
            else:
                col_info['semantic_type'] = 'text'

            schema_info['columns'].append(col_info)

        # Save schema to S3
        schema_key = f"schemas/{source_system}_{table_name}_schema.json"
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=schema_key,
            Body=json.dumps(schema_info, indent=2),
            ContentType='application/json'
        )

        # Store in XCom for next task
        context['task_instance'].xcom_push(
            key='schema_info',
            value=schema_info
        )

        logging.info(f"Schema extracted for {filename}: {len(schema_info['columns'])} columns")
        return schema_info

    except Exception as e:
        logging.error(f"Failed to extract schema from {filename}: {str(e)}")
        raise

extract_schema = PythonOperator(
    task_id='extract_csv_schema',
    python_callable=extract_csv_schema,
    dag=dag
)
```

### 4. GitHub Actions Trigger

```python
def trigger_github_workflow(**context):
    """Trigger GitHub Actions workflow with schema information"""
    import requests

    schema_info = context['task_instance'].xcom_pull(
        task_ids='extract_csv_schema',
        key='schema_info'
    )

    # GitHub workflow dispatch payload
    payload = {
        'ref': 'main',
        'inputs': {
            'source_system': schema_info['source_system'],
            'table_name': schema_info['table_name'],
            'schema_json': json.dumps(schema_info),
            's3_file_path': schema_info['file_path']
        }
    }

    # Trigger workflow
    url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/schema-mapping.yml/dispatches"
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json'
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 204:
        logging.info(f"Successfully triggered GitHub workflow for {schema_info['filename']}")
        return "SUCCESS"
    else:
        logging.error(f"Failed to trigger GitHub workflow: {response.status_code} - {response.text}")
        raise Exception(f"GitHub workflow trigger failed: {response.status_code}")

trigger_workflow = PythonOperator(
    task_id='trigger_github_workflow',
    python_callable=trigger_github_workflow,
    dag=dag
)
```

### 5. File Management

```python
def move_processed_file(**context):
    """Move processed file to processed folder"""
    file_key = context['task_instance'].xcom_pull(
        task_ids='wait_for_s3_file',
        key='s3_file_key'
    )

    # Generate new key in processed folder
    filename = file_key.split('/')[-1]
    processed_key = f"processed/{filename}"

    s3_client = boto3.client('s3')

    # Copy file to processed folder
    s3_client.copy_object(
        Bucket=S3_BUCKET,
        CopySource={'Bucket': S3_BUCKET, 'Key': file_key},
        Key=processed_key
    )

    # Delete original file
    s3_client.delete_object(Bucket=S3_BUCKET, Key=file_key)

    logging.info(f"Moved {file_key} to {processed_key}")
    return processed_key

move_file = PythonOperator(
    task_id='move_processed_file',
    python_callable=move_processed_file,
    dag=dag
)
```

### 6. Error Handling

```python
def handle_failure(**context):
    """Handle task failures by moving file to failed folder"""
    try:
        file_key = context['task_instance'].xcom_pull(
            task_ids='wait_for_s3_file',
            key='s3_file_key'
        )

        if file_key:
            filename = file_key.split('/')[-1]
            failed_key = f"failed/{filename}"

            s3_client = boto3.client('s3')

            # Copy to failed folder
            s3_client.copy_object(
                Bucket=S3_BUCKET,
                CopySource={'Bucket': S3_BUCKET, 'Key': file_key},
                Key=failed_key
            )

            # Delete original
            s3_client.delete_object(Bucket=S3_BUCKET, Key=file_key)

            logging.info(f"Moved failed file {file_key} to {failed_key}")

    except Exception as e:
        logging.error(f"Failed to handle error cleanup: {str(e)}")

failure_handler = PythonOperator(
    task_id='handle_failure',
    python_callable=handle_failure,
    trigger_rule='one_failed',
    dag=dag
)
```

### 7. Task Dependencies

```python
# Define task dependencies
wait_for_file >> extract_schema >> trigger_workflow >> move_file
[wait_for_file, extract_schema, trigger_workflow] >> failure_handler
```

## DAG Configuration

### 1. Airflow Variables

Set up these Airflow variables in the UI or CLI:

```bash
airflow variables set AWS_S3_BUCKET "your-data-ingestion-bucket"
airflow variables set GITHUB_TOKEN "ghp_your_github_token"
airflow variables set GITHUB_REPO "your-org/your-dbt-repo"
airflow variables set CHICORY_API_KEY "your_chicory_api_key"
```

### 2. Connections

Create AWS connection in Airflow:

```bash
airflow connections add 'aws_default' \
    --conn-type 'aws' \
    --conn-login 'your_access_key' \
    --conn-password 'your_secret_key' \
    --conn-extra '{"region_name": "us-east-1"}'
```

## Testing the DAG

### 1. Manual Testing

```python
# Test functions individually
from airflow.models import DagBag

dag_bag = DagBag()
dag = dag_bag.get_dag('automated_csv_ingestion')

# Test schema extraction
task = dag.get_task('extract_csv_schema')
# ... test execution
```

### 2. Integration Testing

Upload a test file and monitor DAG execution:

```bash
# Upload test file
aws s3 cp test_data.csv s3://your-data-ingestion-bucket/incoming/

# Monitor DAG
airflow dags state automated_csv_ingestion
```

## Monitoring and Alerting

### 1. CloudWatch Integration

```python
# Add CloudWatch metrics
import boto3

def publish_metrics(**context):
    cloudwatch = boto3.client('cloudwatch')

    cloudwatch.put_metric_data(
        Namespace='Airflow/Ingestion',
        MetricData=[
            {
                'MetricName': 'FileProcessed',
                'Value': 1,
                'Unit': 'Count'
            }
        ]
    )

metrics_task = PythonOperator(
    task_id='publish_metrics',
    python_callable=publish_metrics,
    dag=dag
)
```

### 2. Slack Notifications

```python
from airflow.providers.slack.operators.slack_webhook import SlackWebhookOperator

slack_alert = SlackWebhookOperator(
    task_id='slack_notification',
    http_conn_id='slack_default',
    message='New CSV file processed successfully: {{ ti.xcom_pull(key="s3_file_key") }}',
    dag=dag
)
```

---

Next: [Chicory Agent Creation](chicory-agent.md)