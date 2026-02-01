# Agent-Trigger-Workflow

How to trigger the agent:

{% stepper %}
{% step %}
## Add a new data asset to a table and trigger the schedule via scheduled queries as a job that runs every 5 min.
{% file src="../scripts/new-table-detection.sql" %}
    scripts/sample-user-request.sql
{% endfile %}

{% endstep %}
{% step %}

## Under the Cloud Run Functions deploy a new function and update it with 
{% file src="../scripts/cloud-run-function.py" %}
    scripts/cloud-run-trigger.py
{% endfile %}
{% file src="../scripts/requirements.txt" %}
    [scripts/requirements.txt
{% endfile %}

{% endstep %}
{% step %}

## Create a cloud schedule to run the trigger every 5 min

{% endstep %}
{% step %}

## Click Save and deploy

{% endstep %}
{% step %}

## Once deployed it triggers the agent whenever a new table is detected.

{% endstep %}
{% endstepper %}
