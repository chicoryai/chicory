# Troubleshooting

### Common Issues

1. Connection Errors: Make sure the Jira -> GitAction connection works, you can validate and test it while building the automation rule. 
2. GIT PR creation error : Make sure the GIT PAT token has the following permissions
-  Read access to metadata
-  Read and Write access to actions, code, issues, and pull requests
3. Terraform Execution Error : Make sure the service account details are stored in GIT Action secrets. Make sure the terraform service account in Bigquery has the following permissions
- BigQuery Admin
- Logging Admin
4. Jira Ticket Status Updation Error: Make sure the JIRA API, Email and the URL is accurate and present in the GIT actions secrets. 
5. Agent Analysis Issue : Make sure the CHICORY_API_KEY and CHICORY_AGENT_ID are stored in GIT Actions secrets, corresponding to the Agent you have built and deployed for this use case. 


