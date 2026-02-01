
```json
{
  "`table_name`": "chicory-`mds.`raw_financial_data``.customer",
  "columns": [
    {
      "`column_name`": "id",
      "`data_type`": "`STRING`",
      "description": "Unique customer identifier in `UUID` format used as primary key for customer records",
      "`policy_tag`": "projects/chicory-mds/locations/us/taxonomies/5701262395035189064/policyTags/3250996656298613505",
      "`policy_tag_display_name`": "`SYSTEM_IDENTIFIERS`",
      "`classification_reasoning`": "`UUID` format system-generated identifier used for technical record linkage, classified as low sensitivity operational data"
    },
    {
      "`column_name`": "name",
      "`data_type`": "`STRING`", 
      "description": "Full legal name of the customer containing first and last name information",
      "`policy_tag`": "projects/chicory-mds/locations/us/taxonomies/5701262395035189064/policyTags/7200905678621418065",
      "`policy_tag_display_name`": "`PII_DIRECT`",
      "`classification_reasoning`": "Customer full name is direct personal identifier that can immediately identify an individual, requiring strict access controls"
    },
    {
      "`column_name`": "email",
      "`data_type`": "`STRING`",
      "description": "Customer email address used for communication and account identification purposes",
      "`policy_tag`": "projects/chicory-mds/locations/us/taxonomies/5701262395035189064/policyTags/7200905678621418065", 
      "`policy_tag_display_name`": "`PII_DIRECT`",
      "`classification_reasoning`": "Email address is direct personal identifier that can immediately identify an individual and is subject to `GDPR`/`CCPA` regulations"
    },
    {
      "`column_name`": "dob",
      "`data_type`": "`DATE`",
      "description": "Customer date of birth used for age verification and demographic analysis",
      "`policy_tag`": "projects/chicory-mds/locations/us/taxonomies/5701262395035189064/policyTags/2566652325851581403",
      "`policy_tag_display_name`": "`PII_BIRTH_DATA`", 
      "`classification_reasoning`": "Date of birth is highly sensitive age-related personal information requiring strict access controls and compliance oversight"
    },
    {
      "`column_name`": "`country_code`",
      "`data_type`": "`STRING`",
      "description": "`ISO` country code representing customer's geographic location or nationality",
      "`policy_tag`": "projects/chicory-mds/locations/us/taxonomies/5701262395035189064/policyTags/7840531813671770804",
      "`policy_tag_display_name`": "`GEOGRAPHIC_DATA`",
      "`classification_reasoning`": "Country code represents geographic location information that could be used for customer profiling, classified as medium sensitivity business data"
    }
  ]
}
```
