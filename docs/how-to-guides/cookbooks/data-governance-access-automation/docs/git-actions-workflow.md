# Access Request Workflow

{% stepper %}
{% step %}
Set up github actions worflow in your data-access-requests repository
{% file src="../.github/workflows/bigquery-access.yml" %}
    .github/workflows/bigquery-access.yml
{% endfile %}
{% file src="../.github/workflows/bigquery-deploy.yml" %}
    .github/workflows/bigquery-deploy.yml
{% endfile %}
{% file src="../.github/workflows/pr-closed.yml" %}
    .github/workflows/pr-closed.yml
{% endfile %}

{% endstep %}
{% step %}

Create a service account in Bigquery Data Warehouse for terraform execution with the following permissions : 
- BigQuery Admin
- Logging Admin

{% endstep %}

{% step %}

Download and save the secrets .json file from the terraform service account in Bigquery. Store the secrets in GITHUB actions secrets 

{% endstep %}

{% step %}

Raise a JIRA ticket/task with the summary for access request. The agent analysis, code generation and PR creation flow begins. 

{% endstep %}

{% step %}

Further, if you want to grant access to the user based on the analysis + the terraform code, then go ahead and merge the PR. If not, close the PR. 

{% endstep %}

{% endstepper %}
