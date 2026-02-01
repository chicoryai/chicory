# Workflow 

Steps: 

{% stepper %}
{% step %}
## Create a new/modify an existing DAG in Airflow 
For more information on how to create your first DAG, Refer : [About DAGs](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dags.html)

Below is an attached sample Airflow DAG, that is connected to BigQuery, DBT, PagerDuty and the Chicory AI Agent built for RCA. 
{% file src="../scripts/dag.py" %}
    scripts/dag.py
{% endfile %}
You can add the following parts to your existing DAG's to implement Root Cause Analysis:

- PagerDuty Invocation
```
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
```
- Chicory AI Agent Invocation via API 

```
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
```


{% endstep %}
{% step %}

## Connect Airflow to Pager Duty 
Establish connection from Airflow to Pager Duty by storing the Pager Duty Integration Key in Airflow connections. For more information on API generation on Pager Duty Refer: [PagerDuty Documentation](https://developer.pagerduty.com/docs/introduction)

{% endstep %}
{% step %}

## Build Chicory AI Agent with connection to Github MCP 
Build the prompt and connections within the agent. 

{% endstep %}

{% step %}

## Build Github Actions workflow
Build the Github Actions workflow in order to update the Pager Duty Incident with status
{% file src="../.github/workflows/close-pager.yml" %}
    .github/workflows/close-pager.yml
{% endfile %}

{% endstep %}


{% endstepper %}

---
