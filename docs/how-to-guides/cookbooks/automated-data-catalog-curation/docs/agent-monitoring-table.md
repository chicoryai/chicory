# Creating an Agent Monitoring Table

Steps: 

{% stepper %}
{% step %}
## Create a new table to detect new data asset creation
{% file src="../scripts/create-monitoring-table.sql" %}
    scripts/create-monitoring-table.sql
{% endfile %}

{% endstep %}
{% step %}

## Execute a new table detection scheduler for every 5 min under the scheduled queries tab.
Here the "reference_dataset_id" is the "dataset_id" under which a new data asset/file 
is created. Refer to the BigQuery job scheduler details for more info: [BigQuery job scheduler Documentation](https://cloud.google.com/bigquery/docs/scheduling-queries)
{% file src="../scripts/new-table-detection.sql" %}
    scripts/new-table-detection.sql
{% endfile %}

{% endstep %}
{% step %}

## Add a new data asset 

{% endstep %}
{% endstepper %}

---
