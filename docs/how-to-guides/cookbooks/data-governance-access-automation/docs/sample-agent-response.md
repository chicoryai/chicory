
```
{
  "`validation_status`": "success",
  "`access_decision`": "`DENIED`",
  "dataset": "chicory-`mds.`raw_financial_data``",
  "column": "email",
  "`access_type`": "Read",
  "`requester_role`": "Data Engineer",
  "`policy_analysis`": {
    "`policy_tag_id`": "projects/chicory-mds/locations/us/taxonomies/pii/policyTags/email",
    "`sensitivity_level`": "`HIGH`",
    "`bigquery_query_executed`": "`SELECT` `column_name`, `policy_tags` `FROM` chicory-`mds.`raw_financial_data``.`INFORMATION_SCHEMA`.`COLUMNS` `WHERE` `table_name` = 'customer' `AND` `column_name` = 'email'",
    "`bigquery_query_result`": "Email column has `HIGH` sensitivity policy tag"
  },
  "reasoning": "Role Data Engineer lacks `HIGH` access. Contact `VP` Finance for approval",
  "`approval_contact`": "jessica@`chicory.ai`",
  "`security_notes`": "`PII` data requires `HIGH` access level",
  "recommendations": "Request approval from `VP` Finance",
  "`terraform_config`": "terraform {
  `required_providers` {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }
}

provider "google" {
  project = "chicory-mds"
}

resource "`google_bigquery_dataset_iam_member`" "DAT_13_access" {
  `dataset_id` = "`raw_financial_data`"
  role       = "roles/bigquery.dataViewer"
  member     = "user:sarkar@`chicory.ai`"
}",
  "errors": []
}

```
