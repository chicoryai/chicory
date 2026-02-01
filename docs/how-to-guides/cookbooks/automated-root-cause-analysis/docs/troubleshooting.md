# Troubleshooting

### Common Issues

1. Pager Duty not triggered : Make sure that the Pager Duty Integration key is set correctly on the Airflow connections and GitHub Secrets
2. Github Issue not raised : Make sure the **CHICORY_API_KEY** and **CHICORY_AGENT_ID**** is set correctly in Airflow connections. Also make sure that the necessary permissions are granted access to the GIT PAT token while connecting it with the Agent via MCP. For more information refer to : [Github MCP](https://github.com/github/github-mcp-server)
