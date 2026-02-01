# Troubleshooting

## Overview

This section provides solutions for common issues encountered when implementing and running the automated ingestion and schema mapping pipeline.

## Common Issues

### 1. S3 and Airflow Issues

#### **Issue: S3 Sensor Not Triggering**

**Symptoms:**
- DAG not starting when files are uploaded
- S3KeySensor task stuck in running state
- No detection of new files

**Solutions:**

```python
# Check S3 connection in Airflow
from airflow.providers.amazon.aws.hooks.s3 import S3Hook

def test_s3_connection():
    hook = S3Hook(aws_conn_id='aws_default')
    try:
        # Test bucket access
        hook.list_keys(bucket_name='your-bucket', prefix='incoming/')
        print("S3 connection successful")
    except Exception as e:
        print(f"S3 connection failed: {e}")

# Add to your DAG for debugging
test_connection = PythonOperator(
    task_id='test_s3_connection',
    python_callable=test_s3_connection,
    dag=dag
)
```

**Checklist:**
- [ ] Verify AWS credentials are configured correctly
- [ ] Check S3 bucket permissions
- [ ] Confirm bucket name and prefix are correct
- [ ] Validate IAM role has necessary S3 permissions
- [ ] Check Airflow connection configuration

#### **Issue: Schema Extraction Fails**

**Symptoms:**
- Task fails with pandas or CSV parsing errors
- Memory issues with large files
- Encoding problems

**Solutions:**

```python
def robust_schema_extraction(**context):
    """Enhanced schema extraction with error handling"""
    import pandas as pd
    import chardet

    s3_client = boto3.client('s3')
    file_key = context['task_instance'].xcom_pull(
        task_ids='wait_for_s3_file',
        key='s3_file_key'
    )

    try:
        # Download file with streaming for large files
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=file_key)

        # Detect encoding
        raw_data = response['Body'].read()
        encoding = chardet.detect(raw_data)['encoding']

        # Parse CSV with robust options
        df = pd.read_csv(
            io.BytesIO(raw_data),
            encoding=encoding,
            encoding_errors='replace',
            dtype=str,  # Read all as strings initially
            nrows=1000,  # Sample first 1000 rows for schema
            na_values=['', 'NULL', 'null', 'N/A', 'n/a']
        )

        # Continue with schema extraction...

    except pd.errors.EmptyDataError:
        logging.error(f"File {file_key} is empty")
        raise
    except pd.errors.ParserError as e:
        logging.error(f"CSV parsing error: {e}")
        # Try alternative parsing
        df = pd.read_csv(
            io.BytesIO(raw_data),
            sep=None,  # Auto-detect separator
            engine='python',
            encoding=encoding
        )
    except MemoryError:
        logging.error("Memory error - file too large")
        # Use chunked processing
        df = pd.read_csv(
            io.BytesIO(raw_data),
            chunksize=1000,
            encoding=encoding
        )
        df = next(df)  # Get first chunk for schema

    return extract_schema_info(df, file_key)
```

### 2. Chicory Agent Issues

#### **Issue: Agent API Timeouts**

**Symptoms:**
- Requests timeout after 60 seconds
- Agent responses are slow
- Intermittent connectivity issues

**Solutions:**

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def create_resilient_session():
    """Create HTTP session with retry logic"""
    session = requests.Session()

    # Retry strategy
    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        method_whitelist=["HEAD", "GET", "POST"],
        backoff_factor=1
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session

def call_chicory_agent_with_retry(schema_data, target_standards):
    """Call Chicory agent with retry logic"""
    session = create_resilient_session()

    headers = {
        "Authorization": f"Bearer {CHICORY_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "messages": [{"role": "user", "content": create_prompt(schema_data, target_standards)}],
        "temperature": 0.1,
        "max_tokens": 2000
    }

    try:
        response = session.post(
            "https://api.chicory.ai/v1/agents/schema_mapper_agent/chat",
            headers=headers,
            json=payload,
            timeout=120  # Increased timeout
        )

        response.raise_for_status()
        return response.json()

    except requests.exceptions.Timeout:
        logging.error("Request timed out - try breaking down the schema")
        raise
    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed: {e}")
        raise
```

#### **Issue: Poor Quality Agent Responses**

**Symptoms:**
- Inconsistent mapping quality
- Missing required fields in responses
- Incorrect data type mappings

**Solutions:**

```python
def validate_and_enhance_mapping(mapping, source_schema):
    """Validate and enhance agent-generated mapping"""

    # Ensure all source columns are mapped
    source_columns = {col['name'] for col in source_schema['columns']}
    mapped_columns = {cm['source_column'] for cm in mapping['column_mappings']}

    missing_columns = source_columns - mapped_columns
    if missing_columns:
        logging.warning(f"Missing mappings for columns: {missing_columns}")

        # Add basic mappings for missing columns
        for col_name in missing_columns:
            source_col = next(col for col in source_schema['columns'] if col['name'] == col_name)

            basic_mapping = {
                'source_column': col_name,
                'target_column': col_name.lower().replace(' ', '_'),
                'source_type': source_col['dtype'],
                'target_type': infer_target_type(source_col['dtype']),
                'transformation': f'CAST({{{col_name}}} AS STRING)',
                'confidence': 0.5
            }

            mapping['column_mappings'].append(basic_mapping)

    # Validate data types
    for col_mapping in mapping['column_mappings']:
        if col_mapping['target_type'] not in VALID_TARGET_TYPES:
            logging.warning(f"Invalid target type: {col_mapping['target_type']}")
            col_mapping['target_type'] = 'STRING'  # Default fallback

    return mapping

def infer_target_type(source_type):
    """Infer target type from source type"""
    type_mapping = {
        'int64': 'INTEGER',
        'float64': 'FLOAT',
        'bool': 'BOOLEAN',
        'datetime64[ns]': 'TIMESTAMP',
        'object': 'STRING'
    }
    return type_mapping.get(source_type, 'STRING')
```

### 3. GitHub Actions Issues

#### **Issue: Workflow Not Triggering**

**Symptoms:**
- GitHub Actions workflow doesn't start
- No workflow runs showing in GitHub
- API calls fail with 404

**Solutions:**

1. **Check Workflow File Location:**
```bash
# Ensure workflow files are in correct location
ls -la .github/workflows/
# Should show: schema-mapping.yml, dbt-generation.yml
```

2. **Validate Workflow Syntax:**
```bash
# Use GitHub CLI to validate
gh workflow list
gh workflow view schema-mapping.yml
```

3. **Test API Trigger:**
```python
import requests

def test_workflow_trigger():
    """Test GitHub workflow trigger API"""

    url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/schema-mapping.yml/dispatches"
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json'
    }

    payload = {
        'ref': 'main',
        'inputs': {
            'source_system': 'test',
            'table_name': 'test',
            'schema_json': '{}',
            's3_file_path': 'test'
        }
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 204:
        print("Workflow triggered successfully")
    else:
        print(f"Failed: {response.status_code} - {response.text}")

        # Common issues and solutions
        if response.status_code == 404:
            print("Check: Repo name, workflow file name, branch name")
        elif response.status_code == 422:
            print("Check: Workflow inputs, branch exists")
        elif response.status_code == 401:
            print("Check: GitHub token permissions")

test_workflow_trigger()
```

#### **Issue: dbt Model Generation Fails**

**Symptoms:**
- dbt compilation errors
- Invalid SQL syntax in generated models
- Missing source references

**Solutions:**

```python
def validate_generated_sql(sql_content, table_name):
    """Validate generated SQL syntax"""
    import sqlparse

    try:
        # Parse SQL to check syntax
        parsed = sqlparse.parse(sql_content)

        if not parsed:
            raise ValueError("Empty or invalid SQL")

        # Check for required elements
        sql_lower = sql_content.lower()

        required_elements = [
            'select',
            'from',
            '{{',  # dbt syntax
            table_name.lower()
        ]

        missing_elements = [elem for elem in required_elements if elem not in sql_lower]

        if missing_elements:
            raise ValueError(f"Missing required elements: {missing_elements}")

        return True

    except Exception as e:
        logging.error(f"SQL validation failed: {e}")
        return False

def fix_common_sql_issues(sql_content):
    """Fix common SQL generation issues"""

    fixes = [
        # Fix missing spaces
        (r'{{source\(', '{{ source('),
        (r'\)}}', ') }}'),

        # Fix column references
        (r'{([^}]+)}', r'{{ \1 }}'),

        # Fix data types
        ('VARCHAR', 'STRING'),
        ('INTEGER', 'INT64'),

        # Fix common syntax errors
        (',,', ','),
        (',\n)', '\n)'),
    ]

    for pattern, replacement in fixes:
        sql_content = re.sub(pattern, replacement, sql_content)

    return sql_content
```

### 4. dbt Issues

#### **Issue: dbt Models Don't Compile**

**Symptoms:**
- `dbt compile` fails
- Missing dependencies
- Invalid references

**Solutions:**

```yaml
# dbt_project.yml - ensure proper configuration
name: 'analytics_dbt'
version: '1.0.0'

model-paths: ["models"]
analysis-paths: ["analysis"]
test-paths: ["tests"]
seed-paths: ["data"]
macro-paths: ["macros"]
snapshot-paths: ["snapshots"]

target-path: "target"
clean-targets:
  - "target"
  - "dbt_packages"

models:
  analytics_dbt:
    auto_generated:
      +materialized: table
      +tags: ['auto-generated']

# Add to models/_sources.yml
sources:
  - name: raw_data
    description: Raw data from various source systems
    tables:
      - name: customers
        description: Customer data from CRM
      - name: orders
        description: Order data from e-commerce platform
```

**Debugging Steps:**

```bash
# Check dbt configuration
dbt debug

# Parse project without running
dbt parse

# Compile specific model
dbt compile --select dim_customer

# Check dependencies
dbt list --models +dim_customer

# Run with verbose output
dbt run --select dim_customer --full-refresh --debug
```

#### **Issue: Test Failures**

**Symptoms:**
- Data quality tests fail
- Relationship tests fail
- Custom tests error out

**Solutions:**

```sql
-- Create more robust tests
-- tests/generic/test_email_format.sql
{% test valid_email_format(model, column_name) %}

select {{ column_name }}
from {{ model }}
where {{ column_name }} is not null
  and not regexp_contains({{ column_name }}, r'^[^@]+@[^@]+\.[^@]+$')

{% endtest %}

-- tests/generic/test_reasonable_date.sql
{% test reasonable_date_range(model, column_name, start_date='1900-01-01', end_date=None) %}

{% if end_date is none %}
  {% set end_date = modules.datetime.date.today() %}
{% endif %}

select {{ column_name }}
from {{ model }}
where {{ column_name }} < '{{ start_date }}'
   or {{ column_name }} > '{{ end_date }}'

{% endtest %}
```

### 5. Performance Issues

#### **Issue: Slow Pipeline Execution**

**Symptoms:**
- Long processing times
- Memory issues
- Timeout errors

**Solutions:**

1. **Optimize Airflow Configuration:**
```python
# In airflow.cfg
[core]
executor = CeleryExecutor  # For parallel processing
parallelism = 32
dag_concurrency = 16
max_active_runs_per_dag = 16

[celery]
worker_concurrency = 16
```

2. **Implement Parallel Processing:**
```python
from concurrent.futures import ThreadPoolExecutor
import asyncio

async def process_multiple_files(file_list):
    """Process multiple files concurrently"""

    async def process_single_file(file_path):
        # Process individual file
        return await extract_and_map_schema(file_path)

    # Process files in parallel
    tasks = [process_single_file(file_path) for file_path in file_list]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return results
```

3. **Optimize Large File Processing:**
```python
def process_large_csv_in_chunks(file_path, chunk_size=10000):
    """Process large CSV files in chunks"""

    chunk_schemas = []

    for chunk_df in pd.read_csv(file_path, chunksize=chunk_size):
        chunk_schema = extract_chunk_schema(chunk_df)
        chunk_schemas.append(chunk_schema)

    # Merge chunk schemas
    consolidated_schema = merge_schemas(chunk_schemas)
    return consolidated_schema
```

## Monitoring and Alerting

### 1. Set Up Comprehensive Monitoring

```python
# monitoring/pipeline_monitor.py
import logging
import boto3
from datetime import datetime, timedelta

def monitor_pipeline_health():
    """Monitor pipeline health and send alerts"""

    checks = {
        's3_file_processing': check_s3_processing_rate(),
        'airflow_dag_success': check_airflow_dag_health(),
        'github_actions': check_github_actions_health(),
        'dbt_model_freshness': check_dbt_model_freshness(),
        'chicory_agent_performance': check_agent_response_times()
    }

    failed_checks = {k: v for k, v in checks.items() if not v['status']}

    if failed_checks:
        send_alert(failed_checks)

    return checks

def check_s3_processing_rate():
    """Check S3 file processing rate"""
    s3_client = boto3.client('s3')

    # Check for files older than 1 hour in incoming/
    response = s3_client.list_objects_v2(
        Bucket=S3_BUCKET,
        Prefix='incoming/'
    )

    old_files = []
    cutoff_time = datetime.now() - timedelta(hours=1)

    for obj in response.get('Contents', []):
        if obj['LastModified'].replace(tzinfo=None) < cutoff_time:
            old_files.append(obj['Key'])

    return {
        'status': len(old_files) == 0,
        'message': f'{len(old_files)} files stuck in processing',
        'details': old_files
    }

def send_alert(failed_checks):
    """Send alert for failed checks"""
    import json

    # Send to Slack, email, or monitoring system
    alert_message = {
        'timestamp': datetime.now().isoformat(),
        'alert_type': 'pipeline_health_check',
        'failed_checks': failed_checks,
        'runbook': 'https://docs.example.com/runbook/pipeline-troubleshooting'
    }

    # Example: Send to CloudWatch
    cloudwatch = boto3.client('cloudwatch')
    cloudwatch.put_metric_data(
        Namespace='Pipeline/Health',
        MetricData=[
            {
                'MetricName': 'FailedChecks',
                'Value': len(failed_checks),
                'Unit': 'Count'
            }
        ]
    )
```

### 2. Create Debugging Scripts

```python
# debug/pipeline_debugger.py
def debug_pipeline_step(step_name, **kwargs):
    """Debug specific pipeline steps"""

    debuggers = {
        's3_detection': debug_s3_file_detection,
        'schema_extraction': debug_schema_extraction,
        'mapping_generation': debug_mapping_generation,
        'dbt_generation': debug_dbt_generation
    }

    if step_name in debuggers:
        return debuggers[step_name](**kwargs)
    else:
        raise ValueError(f"Unknown debug step: {step_name}")

def debug_s3_file_detection(bucket_name, prefix):
    """Debug S3 file detection issues"""
    import boto3

    s3_client = boto3.client('s3')

    print(f"Debugging S3 detection for bucket: {bucket_name}, prefix: {prefix}")

    try:
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=prefix
        )

        if 'Contents' in response:
            print(f"Found {len(response['Contents'])} objects")
            for obj in response['Contents'][:10]:  # Show first 10
                print(f"  - {obj['Key']} (Modified: {obj['LastModified']})")
        else:
            print("No objects found")

    except Exception as e:
        print(f"Error accessing S3: {e}")
        print("Check: AWS credentials, bucket name, permissions")

# Usage: python debug/pipeline_debugger.py s3_detection --bucket=my-bucket --prefix=incoming/
```

## Emergency Procedures

### 1. Pipeline Failure Recovery

```bash
#!/bin/bash
# emergency/recover_pipeline.sh

echo "Starting pipeline recovery procedure..."

# 1. Stop all running workflows
echo "Stopping active workflows..."
gh workflow disable schema-mapping.yml
gh workflow disable dbt-generation.yml

# 2. Clear stuck files
echo "Moving stuck files..."
aws s3 mv s3://your-bucket/incoming/ s3://your-bucket/recovery/ --recursive

# 3. Reset Airflow DAG state
echo "Resetting Airflow DAG..."
airflow dags state-set automated_csv_ingestion SUCCESS $(date -d "1 hour ago" '+%Y-%m-%dT%H:%M:%S')

# 4. Validate system health
echo "Validating system health..."
python monitoring/pipeline_monitor.py

# 5. Re-enable workflows
echo "Re-enabling workflows..."
gh workflow enable schema-mapping.yml
gh workflow enable dbt-generation.yml

echo "Recovery complete. Monitor logs for issues."
```

### 2. Data Quality Issues

```python
# emergency/data_quality_fix.py
def fix_data_quality_issues(table_name):
    """Fix common data quality issues"""

    fixes = [
        fix_null_values,
        fix_duplicate_records,
        fix_data_type_issues,
        fix_constraint_violations
    ]

    for fix_function in fixes:
        try:
            fix_function(table_name)
            print(f"Applied {fix_function.__name__} to {table_name}")
        except Exception as e:
            print(f"Failed to apply {fix_function.__name__}: {e}")

def fix_null_values(table_name):
    """Fix null values in critical columns"""
    # Implementation depends on your data warehouse
    pass

def fix_duplicate_records(table_name):
    """Remove duplicate records"""
    # Implementation depends on your data warehouse
    pass
```

## Getting Help

### 1. Log Analysis

```bash
# Check Airflow logs
airflow logs list
airflow logs get automated_csv_ingestion extract_csv_schema 2024-01-15

# Check GitHub Actions logs
gh run list --workflow=schema-mapping.yml
gh run view <run_id>

# Check dbt logs
cat logs/dbt.log | grep ERROR
```

### 2. Support Channels

- **Chicory AI Support**: support@chicory.ai
- **GitHub Issues**: Create issue in your repository
- **Internal Documentation**: Update troubleshooting docs with new solutions

### 3. Escalation Process

1. **Level 1**: Check common issues in this guide
2. **Level 2**: Run debugging scripts and check logs
3. **Level 3**: Contact system administrators
4. **Level 4**: Engage vendor support (Chicory, cloud providers)

---

This concludes the Automated Ingestion & Schema Mapping cookbook. For additional support, refer to the [Chicory AI documentation](https://docs.chicory.ai) or contact your system administrator.