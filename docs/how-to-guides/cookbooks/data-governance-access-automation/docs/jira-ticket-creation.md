# Jira Ticket Creation and automation

Steps: 

{% stepper %}
{% step %}
## Login to Jira 
Refer to the doc to get started: [Get Started with JIRA](https://www.atlassian.com/software/jira). Start a project and name it **Data Access Requests**

{% endstep %}
{% step %}

## Create an automation rule 
Navigate to project settings under **Data Access Requests** and build an automation rule where **when work item is created** push a trigger to our pre built Git Action.  

{% endstep %}

{% step %}

## Create an action
Once the condition is established add **action** to send a web request. Fill in the git link pointing to the repo : https://api.github.com/repos/org-name/data-access-requests/dispatches

- Http Method : Post
- Web Request Body : Custom Data
-  Custom data :
{
  "event_type": "bigquery_access_request",
  "client_payload": {
    "ticket_id": "{{issue.key}}",
    "summary": "{{issue.summary}}",
    "description": "{{issue.description}}",
    "reporter": "{{issue.reporter.emailAddress}}"
  }
}
- Define Headers : Content Type - application/json, Authorization - token GitPAT token, Accept - application/vnd.github.v3+json

{% endstep %}

{% step %}
## Validate the connection by creating a ticket/task with summary if required
For more information on automation rule creation refer to : [Automation Rule Creation](https://support.atlassian.com/cloud-automation/docs/create-and-edit-jira-automation-rules/)   

{% endstep %}

{% step %}

## Sample Summary: 

```
BigQuery Access - chicory-mds.raw_financial_data.customer.email (Read) - Data Engineer Saurabh
```

{% endstep %}
{% endstepper %}

---
