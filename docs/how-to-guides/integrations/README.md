# Chicory Integrations

Chicory integrates with various data platforms, tools, and services to provide comprehensive visibility into your data ecosystem. Our integrations are organized into four main categories based on their capabilities.

## Integration Categories

### Data Sources
Connect to data warehouses, catalogs, and analytics platforms to scan and catalog your data assets.

### Code & Pipelines
Integrate with version control and data pipeline tools to understand data transformations and workflows.

### Documents
Connect to documentation platforms to provide context and knowledge alongside your data assets.

### AI & Tools
Integrate AI platforms for enhanced analysis and intelligent assistance.

---

## Quick Reference

| Integration | Type | Scanning | MCP Tools | Authentication |
|-------------|------|----------|-----------|----------------|
| **Snowflake** | Data |  |  | Password/Key Pair |
| **Databricks** | Data |  |  | Personal Access Token |
| **BigQuery** | Data |  |  | Service Account |
| **Looker** | Data |  |  | OAuth |
| **AWS Glue** | Data |  |  | IAM Role |
| **AWS DataZone** | Tools |  |  | IAM Role |
| **Redash** | Tools |  |  | API Key |
| **DataHub** | Tools |  |  | API Key |
| **dbt Cloud** | Tools |  |  | API Token |
| **Airflow** | Tools |  |  | Basic Auth |
| **GitHub** | Code |  |  | OAuth |
| **Google Drive** | Documents |  |  | Service Account |
| **Anthropic** | AI Tools | - |  | API Key |

---

## Integration Capabilities Explained

### Scanning
Scanning allows Chicory to automatically discover and catalog metadata from your data sources. When enabled:
- Periodic syncs keep metadata up-to-date
- New tables, columns, and assets are automatically discovered
- Schema changes are tracked
- Metadata is indexed for search

### MCP Tool Support
Model Context Protocol (MCP) tools enable programmatic access to integrations for AI agents and applications:
- Query metadata programmatically
- Execute searches across catalogs
- Access lineage and relationships
- Enable AI-powered analysis

---

## Common Setup Patterns

### Service Account Authentication
Used by: BigQuery, Google Drive

1. Create service account in cloud console
2. Generate JSON key file
3. Grant necessary permissions
4. Upload key to Chicory

### OAuth Authentication
Used by: GitHub, Looker

1. Authorize Chicory application
2. Grant requested permissions
3. Redirect back to Chicory
4. Connection established automatically

### API Key Authentication
Used by: Redash, DataHub, dbt Cloud, Anthropic

1. Generate API key in platform settings
2. Copy API key
3. Enter in Chicory connection form
4. Test connection

### IAM Role (AWS)
Used by: AWS Glue, AWS DataZone

1. Create IAM role with trust policy
2. Attach service-specific permissions
3. Configure External ID
4. Enter role ARN in Chicory

---

## Security Best Practices

### Credential Management
- Use read-only credentials whenever possible
- Rotate credentials regularly
- Use service accounts instead of personal credentials
- Store credentials securely (Chicory encrypts at rest)

### Access Control
- Grant minimum required permissions
- Restrict to specific databases/schemas when possible
- Use time-limited tokens where supported
- Monitor access logs regularly

### Network Security
- Use private endpoints when available
- Restrict IP addresses if required
- Enable SSL/TLS for all connections
- Audit connection logs

---

## Troubleshooting

### Connection Issues

**Timeout Errors**
- Check network connectivity
- Verify firewall rules allow Chicory IP addresses
- Confirm service is running and accessible

**Authentication Failures**
- Verify credentials are correct and not expired
- Check permissions are properly configured
- Ensure API keys have required scopes

**Permission Errors**
- Review required permissions for the integration
- Grant necessary access in source platform
- Check role assignments and policies

### Scanning Issues

**No Data Found**
- Verify credentials have read access
- Check if databases/schemas are specified correctly
- Confirm resources exist in source system

**Incomplete Scans**
- Review scan logs for errors
- Check for resource-specific permission issues
- Verify network stability during scan

---

## Getting Started

1. **Choose Your Integration**: Select the platform you want to connect
2. **Prepare Credentials**: Follow the setup guide to create necessary credentials
3. **Configure Connection**: Enter credentials and connection details in Chicory
4. **Test Connection**: Verify connectivity before enabling scanning
5. **Enable Scanning**: Turn on automatic metadata scanning

---

## Support & Documentation

### Platform-Specific Guides
- [AWS Integrations (Glue, DataZone)](aws/README.md)
- More platform guides coming soon

### Need Help?
- Check individual integration setup guides
- Contact Chicory support with connection details
- Review audit logs for error messages

---
