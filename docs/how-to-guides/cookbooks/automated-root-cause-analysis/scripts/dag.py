from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.http.operators.http import SimpleHttpOperator
from airflow.providers.google.cloud.hooks.bigquery import BigQueryHook
from airflow.models import Variable
import json
import requests

def send_pagerduty_alert(error_details):
    """Send alert to PagerDuty Events API v1"""
    
    pagerduty_key = Variable.get("pagerduty_integration_key")
    
    payload = {
        "service_key": pagerduty_key,
        "event_type": "trigger",
        "description": f"Airflow Pipeline Validation Failed: {error_details['task']}",
        "client": "Airflow Data Pipeline",
        "details": {
            "pipeline_name": error_details['pipeline'],
            "failed_task": error_details['task'],
            "error_message": error_details['error'],
            "failed_validations": error_details.get('failed_validations', []),
            "timestamp": error_details['timestamp']
        }
    }
    
    try:
        response = requests.post(
            "https://events.pagerduty.com/generic/2010-04-15/create_event.json",
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            print("PagerDuty alert sent successfully")
            return response.json()
        else:
            print(f"Failed to send PagerDuty alert: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Error sending PagerDuty alert: {str(e)}")
        return None
    
def send_alert_and_notify_agent(error_details):
    """Send PagerDuty alert AND notify Chicory agent directly"""
    
    # Step 1: Send to PagerDuty first and get incident key
    pagerduty_response = send_pagerduty_alert(error_details)
    
    incident_key = None
    if pagerduty_response:
        incident_key = pagerduty_response.get('incident_key')
        print(f"PagerDuty incident created with key: {incident_key}")
    else:
        print("PagerDuty alert failed, but continuing with agent notification")
    
    # Step 2: Send directly to Chicory agent
    try:
        agent_token = Variable.get("chicory_agent_token")
        agent_name = Variable.get("chicory_agent_name")
        
        # Create the message with all failure details
        agent_message = f"Pipeline failure in {error_details['pipeline']} - Task: {error_details['task']} - Error: {error_details['error']} - Failed validations: {error_details.get('failed_validations', [])} - Timestamp: {error_details['timestamp']} - PagerDuty incident: {incident_key}"
        
        agent_payload = {
            "agent_name": agent_name,
            "input": [
                {
                    "parts": [
                        {
                            "content_type": "text/plain",
                            "content": agent_message
                        }
                    ],
                    "created_at": datetime.now().isoformat() + "Z"
                }
            ]
        }
        
        response = requests.post(
            "https://app.chicory.ai/api/v1/runs",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {agent_token}"
            },
            json=agent_payload,
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            print("Successfully sent failure details to Chicory agent")
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            print(f"Raw response text: {response.text}")
            
            try:
                response_data = response.json()
                print(f"Parsed JSON keys: {list(response_data.keys())}")
                run_id = response_data.get('run_id')
                if run_id:
                    print(f"Chicory agent run ID: {run_id}")
                else:
                    print("No run ID found in response")
            except Exception as e:
                print(f"JSON parsing error: {str(e)}")
        else:
            print(f"Failed to send to Chicory agent: {response.status_code}")
            
    except Exception as e:
        print(f"Error sending to Chicory agent: {str(e)}")
    
    return incident_key

def validate_raw_tables():
    """Validate raw AdventureWorks tables before transformation"""
    
    hook = BigQueryHook(gcp_conn_id='bigquery_default')
    client = hook.get_client()
    
    print("=== Pre-dbt Raw Data Validation ===")
    
    # Test region table
    region_count = int(client.query("SELECT COUNT(*) as count FROM `chicory-mds.raw_adventureworks.dim_region`").to_dataframe().iloc[0]['count'])
    region_nulls = int(client.query("SELECT COUNT(*) as count FROM `chicory-mds.raw_adventureworks.dim_region` WHERE SalesTerritoryKey IS NULL").to_dataframe().iloc[0]['count'])
    
    print(f"Region table: {region_count} rows, {region_nulls} null keys")
    region_passed = region_count > 0 and region_nulls == 0
    
    # Test salesperson table
    salesperson_count = int(client.query("SELECT COUNT(*) as count FROM `chicory-mds.raw_adventureworks.dim_salesperson`").to_dataframe().iloc[0]['count'])
    salesperson_nulls = int(client.query("SELECT COUNT(*) as count FROM `chicory-mds.raw_adventureworks.dim_salesperson` WHERE EmployeeKey IS NULL").to_dataframe().iloc[0]['count'])
    
    print(f"Salesperson table: {salesperson_count} rows, {salesperson_nulls} null keys")
    salesperson_passed = salesperson_count > 0 and salesperson_nulls == 0
    
    if region_passed and salesperson_passed:
        print("Raw data validation PASSED - proceeding to dbt")
        return "Pre-dbt validation successful"
    else:
        raise ValueError("Raw data validation failed")

def validate_transformed_tables(**context):
    """Validate transformed tables after dbt runs - with region validation that will fail"""
    
    hook = BigQueryHook(gcp_conn_id='bigquery_default')
    client = hook.get_client()
    
    print("=== Post-dbt Transformed Data Validation ===")
    
    validation_results = []
    failed_validations = []
    
    # Test 1: stg_territory table
    print("\n--- stg_territory validation ---")
    try:
        stg_territory_count = int(client.query("SELECT COUNT(*) as count FROM `chicory-mds.chicory_mds_staging.stg_territory`").to_dataframe().iloc[0]['count'])
        print(f"stg_territory: {stg_territory_count} rows")
        territory_passed = stg_territory_count > 0
        validation_results.append(("stg_territory", territory_passed))
        if not territory_passed:
            failed_validations.append("stg_territory: No data found")
        
    except Exception as e:
        print(f"stg_territory validation failed: {e}")
        validation_results.append(("stg_territory", False))
        failed_validations.append(f"stg_territory: {str(e)}")
    
    # Test 2: stg_salesperson table
    print("\n--- stg_salesperson validation ---")
    try:
        stg_salesperson_count = int(client.query("SELECT COUNT(*) as count FROM `chicory-mds.chicory_mds_staging.stg_salesperson`").to_dataframe().iloc[0]['count'])
        print(f"stg_salesperson: {stg_salesperson_count} rows")
        salesperson_passed = stg_salesperson_count > 0
        validation_results.append(("stg_salesperson", salesperson_passed))
        if not salesperson_passed:
            failed_validations.append("stg_salesperson: No data found")
        
    except Exception as e:
        print(f"stg_salesperson validation failed: {e}")
        validation_results.append(("stg_salesperson", False))
        failed_validations.append(f"stg_salesperson: {str(e)}")
    
    # Test 3: sales_performance marts table
    print("\n--- sales_performance validation ---")
    try:
        sales_performance_count = int(client.query("SELECT COUNT(*) as count FROM `chicory-mds.chicory_mds_marts.mart_sales_perfromance_dashboard`").to_dataframe().iloc[0]['count'])
        print(f"sales_performance: {sales_performance_count} rows")
        performance_passed = sales_performance_count > 0
        validation_results.append(("sales_performance", performance_passed))
        if not performance_passed:
            failed_validations.append("sales_performance: No data found")
        
    except Exception as e:
        print(f"sales_performance validation failed: {e}")
        validation_results.append(("sales_performance", False))
        failed_validations.append(f"sales_performance: {str(e)}")
    
    # NEW Test 4: Region whitelist validation (this will fail because South America/Brazil is excluded)
    print("\n--- region_whitelist validation ---")
    try:
        # Define allowed regions (excluding South America to create failure)
        allowed_regions = [
            'Northwest', 'Northeast', 'Central', 'Southwest', 'Southeast',
            'Canada', 'France', 'Germany', 'Australia', 'United Kingdom'
            # Note: 'South America' is intentionally excluded to trigger failure
        ]
        
        # Check if any regions in staging are not in the allowed list
        region_query = f"""
        SELECT DISTINCT region_name
        FROM `chicory-mds.chicory_mds_staging.stg_territory`
        WHERE region_name NOT IN ({','.join([f"'{r}'" for r in allowed_regions])})
        """

        invalid_regions_df = client.query(region_query).to_dataframe()

        if len(invalid_regions_df) > 0:
            invalid_region_names = invalid_regions_df['region_name'].tolist()
            print(f"VALIDATION FAILURE: Found {len(invalid_regions_df)} unauthorized regions: {invalid_region_names}")
            print(f"Allowed regions: {allowed_regions}")
            validation_results.append(("region_whitelist", False))
            failed_validations.append(f"region_whitelist: Unauthorized regions - {invalid_region_names}")
        else:
            print(f"All regions are authorized")
            validation_results.append(("region_whitelist", True))

    except Exception as e:
        print(f"region_whitelist validation failed: {e}")
        validation_results.append(("region_whitelist", False))
        failed_validations.append(f"region_whitelist: {str(e)}")
    
    # Overall results
    print(f"\n=== Validation Summary ===")
    passed_count = 0
    for table_name, passed in validation_results:
        status = "PASSED" if passed else "FAILED"
        print(f"{table_name}: {status}")
        if passed:
            passed_count += 1
    
    overall_passed = passed_count == len(validation_results)
    print(f"\nOverall: {passed_count}/{len(validation_results)} tests passed")
    
    if overall_passed:
        print("All post-dbt validations PASSED - pipeline complete!")
        return "Post-dbt validation successful"
    else:
        # Send PagerDuty alert 
        error_details = {
            'pipeline': 'BQ_DBT_Validation_Pipeline',
            'task': 'validate_transformed_data',
            'error': f"Validation failed: {len(validation_results) - passed_count} out of {len(validation_results)} tests failed",
            'failed_validations': failed_validations,
            'timestamp': datetime.now().isoformat(),
            'dag_run_id': context.get('dag_run').run_id if context.get('dag_run') else 'unknown'
        }
        
        # This now sends the PagerDuty alert and notifies the agent
        incident_key = send_alert_and_notify_agent(error_details)
        
        if incident_key:
            print(f"Alert sent and GitHub triggered with incident key: {incident_key}")
        
        raise ValueError(f"Post-dbt validation failed - only {passed_count}/{len(validation_results)} tests passed")

# DAG definition
dag = DAG(
    'pager-workflow-1',
    default_args={
        'owner': 'data-team',
        'start_date': datetime(2024, 1, 1),
        'retries': 1,
        'retry_delay': timedelta(minutes=5)
    },
    description='Working BQ validation → dbt Cloud → post-dbt validation pipeline',
    schedule_interval=None,
    catchup=False,
    tags=['working', 'dbt-cloud', 'validation', 'complete']
)

# Task 1: Validate raw data
validate_raw = PythonOperator(
    task_id='validate_raw_data',
    python_callable=validate_raw_tables,
    dag=dag
)

# Task 2: Trigger dbt job 
trigger_dbt = SimpleHttpOperator(
    task_id='trigger_dbt_cloud_job',
    http_conn_id='dbt_cloud_api',
    endpoint='/api/v2/accounts/{{ var.value.dbt_account_id }}/jobs/{{ var.value.dbt_job_id }}/run/',
    method='POST',
    headers={
        'Authorization': 'Token {{ var.value.dbt_cloud_token }}',
        'Content-Type': 'application/json'
    },
    data=json.dumps({
        'cause': 'Triggered by Airflow BQ Validation Pipeline',
        'git_sha': None,
    }),
    dag=dag
)

# Task 3: Wait for dbt completion 
wait_dbt = PythonOperator(
    task_id='wait_for_dbt',
    python_callable=lambda: __import__('time').sleep(120),  # Wait 2 minutes
    dag=dag
)

# Task 4: Validate transformed data 
validate_transformed = PythonOperator(
    task_id='validate_transformed_data',
    python_callable=validate_transformed_tables,
    provide_context=True,
    retries=0,  
    dag=dag
)

# Pipeline flow
validate_raw >> trigger_dbt >> wait_dbt >> validate_transformed