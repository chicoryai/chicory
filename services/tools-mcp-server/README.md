# Tools MCP Server

A Model Context Protocol (MCP) server for tools and API operations using the FastMCP library. Supports Looker, Redash, OpenAPI, AWS DataZone, AWS S3, and dbt Cloud services with an extensible architecture for additional tools providers.

## Features

- **Multi-Tools Support**: Looker, Redash, OpenAPI, AWS DataZone, AWS S3, and dbt Cloud with provider auto-detection
- **Project-based Credentials**: Secure credential management with API integration
- **Connection Caching**: TTL-based caching with automatic cleanup
- **Pure Async Architecture**: No threading complexity, fully async operations
- **FastMCP Integration**: Modern MCP server using FastMCP idioms
- **Docker Support**: Production-ready containerization
- **Health Monitoring**: HTTP health endpoint for monitoring and load balancers

## Tools

### Looker Tools

All tools require a `project_id` parameter for credential lookup:

- **`looker_get_models_tool`**: Get all Looker models available in the instance
- **`looker_get_explores_tool`**: Get all explores for a specific model
- **`looker_get_dimensions_tool`**: Get all dimensions for a specific explore
- **`looker_get_measures_tool`**: Get all measures for a specific explore
- **`looker_get_filters_tool`**: Get all filters for a specific explore
- **`looker_get_parameters_tool`**: Get parameters for a specific explore
- **`looker_query_tool`**: Execute a Looker query with dimensions, measures, and filters
- **`looker_query_sql_tool`**: Execute raw SQL against Looker's database connection
- **`looker_get_looks_tool`**: Get all Looks (saved queries) in Looker
- **`looker_run_look_tool`**: Run a specific Look and get its results
- **`looker_query_url_tool`**: Generate a URL for a Looker query

### Redash Tools

All tools require a `project_id` parameter for credential lookup:

- **`redash_list_queries_tool`**: List all queries in Redash with pagination
- **`redash_get_query_tool`**: Get details of a specific Redash query
- **`redash_execute_query_tool`**: Execute a Redash query and get results
- **`redash_get_query_job_status_tool`**: Get the status of a query execution job
- **`redash_get_query_results_tool`**: Get results of a completed query execution
- **`redash_refresh_query_tool`**: Refresh a query (execute with fresh data)
- **`redash_list_dashboards_tool`**: List all dashboards in Redash
- **`redash_get_dashboard_tool`**: Get details of a specific dashboard
- **`redash_list_data_sources_tool`**: List all data sources in Redash

### dbt Cloud Tools

All tools require a `project_id` parameter for credential lookup:

- **`dbt_list_projects_tool`**: List all dbt Cloud projects in the account
- **`dbt_list_environments_tool`**: List all environments in a dbt Cloud project
- **`dbt_list_jobs_tool`**: List all jobs in a dbt Cloud project
- **`dbt_trigger_job_run_tool`**: Trigger a job run with optional parameter overrides
- **`dbt_get_job_run_tool`**: Get details of a specific job run
- **`dbt_list_job_runs_tool`**: List recent job runs with optional filtering
- **`dbt_cancel_job_run_tool`**: Cancel a running job
- **`dbt_list_models_tool`**: List all models using Discovery API
- **`dbt_get_model_details_tool`**: Get detailed information about a specific model
- **`dbt_list_metrics_tool`**: List all metrics using Semantic Layer API
- **`dbt_query_metrics_tool`**: Query metrics with filtering and grouping
- **`dbt_execute_sql_tool`**: Execute SQL using dbt Cloud SQL API

### AWS DataZone Tools

All tools require a `project_id` parameter for credential lookup:

- **`datazone_list_domains_tool`**: List all AWS DataZone domains
- **`datazone_get_domain_tool`**: Get details of a specific DataZone domain
- **`datazone_list_projects_tool`**: List all projects in a DataZone domain
- **`datazone_get_project_tool`**: Get details of a specific DataZone project
- **`datazone_search_listings_tool`**: Search for data assets in DataZone catalog
- **`datazone_get_listing_tool`**: Get details of a specific data listing
- **`datazone_list_environments_tool`**: List environments in a DataZone project
- **`datazone_get_environment_tool`**: Get details of a specific environment
- **`datazone_get_asset_tool`**: Get details of a specific data asset
- **`datazone_list_asset_revisions_tool`**: List revisions of a data asset
- **`datazone_get_glossary_tool`**: Get details of a business glossary
- **`datazone_get_glossary_term_tool`**: Get details of a glossary term
- **`datazone_create_form_type_tool`**: Create a new form type in DataZone
- **`datazone_get_form_type_tool`**: Get details of a specific form type
- **`datazone_create_asset_type_tool`**: Create a new asset type in DataZone
- **`datazone_get_asset_type_tool`**: Get details of a specific asset type
- **`datazone_list_asset_types_tool`**: List all asset types in a DataZone domain

### AWS S3 Tools

All tools require a `project_id` parameter for credential lookup:

- **`s3_list_buckets_tool`**: List all S3 buckets in the account
- **`s3_list_objects_tool`**: List objects in an S3 bucket with optional prefix and delimiter
- **`s3_get_object_tool`**: Get an object from S3 (returns content as text or base64)
- **`s3_get_object_metadata_tool`**: Get metadata for an S3 object without downloading content
- **`s3_create_bucket_tool`**: Create a new S3 bucket in a specified region
- **`s3_put_object_tool`**: Upload an object to S3 with optional metadata and storage class
- **`s3_generate_presigned_url_tool`**: Generate a presigned URL for S3 object operations (get, put, delete)
- **`s3_generate_presigned_post_tool`**: Generate presigned POST data for direct browser uploads to S3

### OpenAPI Tools

All tools require a `project_id` parameter for credential lookup:

- **`openapi_get_spec_tool`**: Get the OpenAPI specification for the configured API
- **`openapi_list_endpoints_tool`**: List all available endpoints in the API
- **`openapi_get_endpoint_schema_tool`**: Get schema definition for a specific endpoint
- **`openapi_call_endpoint_tool`**: Call a specific API endpoint with parameters and data

### Jira Tools

All tools require a `project_id` parameter for credential lookup:

**Issue Management:**
- **`jira_search_issues_tool`**: Search for issues using JQL (Jira Query Language)
- **`jira_get_issue_tool`**: Get details of a specific issue
- **`jira_create_issue_tool`**: Create a new issue with summary, type, and description
- **`jira_update_issue_tool`**: Update fields on an existing issue
- **`jira_transition_issue_tool`**: Transition issue to a new status
- **`jira_get_transitions_tool`**: Get available transitions for an issue
- **`jira_assign_issue_tool`**: Assign issue to a user

**Project Management:**
- **`jira_list_projects_tool`**: List all accessible projects
- **`jira_get_project_tool`**: Get details of a specific project
- **`jira_get_issue_types_tool`**: Get issue types for a project
- **`jira_get_fields_tool`**: Get all system and custom fields

**Comments & Attachments:**
- **`jira_add_comment_tool`**: Add a comment to an issue
- **`jira_get_comments_tool`**: Get all comments for an issue
- **`jira_upload_attachment_tool`**: Upload a file attachment to an issue

**Agile/Boards:**
- **`jira_list_boards_tool`**: List all boards (optionally filtered by project)
- **`jira_list_sprints_tool`**: List sprints for a specific board
- **`jira_get_sprint_tool`**: Get details of a specific sprint
- **`jira_get_backlog_tool`**: Get backlog issues for a board

## Architecture

### Provider-Specific Design

The server uses provider-specific tools rather than generic analytics tools because:

- **Service Concepts Differ**: Looker uses models/explores, Redash uses queries/dashboards, OpenAPI uses endpoints/schemas, dbt Cloud uses projects/jobs/models
- **Native Capabilities**: Each service has unique features that generic abstractions would hide
- **Type Safety**: Provider-specific parameters ensure correct usage and better error messages
- **Clear Intent**: Tool names explicitly indicate which tools service is being used

### Minimal Base Provider

The `ToolsProvider` base class provides only essential infrastructure:

- **Common State Management**: Credentials, initialization status, cleanup
- **No Service Abstractions**: No forced abstract methods for tools operations
- **Provider Flexibility**: Each provider implements its own natural interface
- **Utility Methods**: Shared logging and metadata functionality

## Installation

### Option 1: Docker (Recommended)

1. **Build the Docker image:**
   ```bash
   docker build -t tools-mcp-server .
   ```

2. **Run the container:**
   ```bash
   docker run -p 8080:8080 \
     -e API_BASE_URL=http://localhost:8000 \
     -e CONNECTION_CACHE_TTL=3600 \
     -e CONNECTION_CACHE_MAX_SIZE=100 \
     tools-mcp-server
   ```

### Option 2: Local Development

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables (optional):**
   ```bash
   export API_BASE_URL="http://localhost:8000"
   export CONNECTION_CACHE_TTL=3600
   export CONNECTION_CACHE_MAX_SIZE=100
   ```

3. **Run the server:**
   ```bash
   python server.py
   ```

The server will start on `http://localhost:8080` by default.

### Docker Commands

- **Build image:** `docker build -t tools-mcp-server .`
- **Run container:** `docker run -p 8080:8080 tools-mcp-server`
- **View logs:** `docker logs -f <container_id>`
- **Stop container:** `docker stop <container_id>`

## Configuration

### Environment Variables

- `API_BASE_URL`: Backend API base URL for credential fetching (default: "http://localhost:8000")
- `CONNECTION_CACHE_TTL`: Connection cache TTL in seconds (default: 3600)
- `CONNECTION_CACHE_MAX_SIZE`: Maximum number of cached connections (default: 100)
- `DEFAULT_QUERY_LIMIT`: Default query result limit (default: 100)
- `MAX_QUERY_LIMIT`: Maximum allowed query result limit (default: 1000)
- `DEFAULT_SAMPLE_LIMIT`: Default table sample size (default: 10)
- `LOG_LEVEL`: Logging level (default: "INFO")
- `CACHE_CLEANUP_INTERVAL`: Cache cleanup interval in seconds (default: 300)

### Backend API Integration

The server fetches tools service credentials from the backend API endpoint:
```
GET /projects/{project_id}/tools-sources
```

Expected response format:
```json
{
  "tools_sources": [
    {
      "type": "looker",
      "configuration": {
        "base_url": "https://your-looker-instance.looker.com",
        "client_id": "your-client-id",
        "client_secret": "your-client-secret"
      }
    },
    {
      "type": "redash",
      "configuration": {
        "base_url": "https://your-redash-instance.com",
        "api_key": "your-api-key"
      }
    },
    {
      "type": "openapi",
      "configuration": {
        "base_url": "https://api.example.com",
        "spec_url": "https://api.example.com/openapi.json",
        "api_key": "your-api-key",
        "auth_header": "Authorization"
      }
    },
    {
      "type": "dbt",
      "configuration": {
        "base_url": "https://cloud.getdbt.com",
        "api_token": "your-api-token",
        "account_id": "your-account-id",
        "project_id": "your-project-id",
        "environment_id": "your-environment-id"
      }
    },
    {
      "type": "datazone",
      "configuration": {
        "region": "us-east-1",
        "role_arn": "arn:aws:iam::123456789012:role/DataZoneAccessRole",
        "external_id": "your-external-id"
      }
    },
    {
      "type": "s3",
      "configuration": {
        "region": "us-east-1",
        "role_arn": "arn:aws:iam::123456789012:role/S3AccessRole",
        "external_id": "your-external-id"
      }
    },
    {
      "type": "jira",
      "configuration": {
        "access_token": "your-oauth-access-token",
        "refresh_token": "your-oauth-refresh-token",
        "cloud_id": "your-cloud-id",
        "site_url": "https://your-instance.atlassian.net",
        "account_id": "your-account-id",
        "expires_in": 3600,
        "auth_method": "oauth"
      }
    }
  ]
}
```

## Usage Examples

### HTTP Endpoints

When running in HTTP mode, the server provides the following endpoints:

- `GET /health` - Health check endpoint
- `POST /mcp` - MCP protocol endpoint (JSON-RPC format)
- `POST /tools/list` - List available tools (simplified format)
- `POST /tools/call` - Execute an tool (simplified format)

### Example HTTP Usage

**List Looker models:**
```bash
curl -X POST http://localhost:8080/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "looker_get_models_tool",
    "arguments": {
      "project_id": "your-project-id"
    }
  }'
```

**Execute Looker query:**
```bash
curl -X POST http://localhost:8080/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "looker_query_tool",
    "arguments": {
      "project_id": "your-project-id",
      "model_name": "your_model",
      "explore_name": "your_explore",
      "dimensions": ["users.name", "users.city"],
      "measures": ["users.count"],
      "filters": {"users.created_date": "7 days"},
      "limit": 100
    }
  }'
```

**Execute dbt Cloud job:**
```bash
curl -X POST http://localhost:8080/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "dbt_trigger_job_run_tool",
    "arguments": {
      "project_id": "your-project-id",
      "job_id": "12345",
      "cause": "API test run"
    }
  }'
```

**Call OpenAPI endpoint:**
```bash
curl -X POST http://localhost:8080/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "openapi_call_endpoint_tool",
    "arguments": {
      "project_id": "your-project-id",
      "method": "GET",
      "path": "/users",
      "parameters": {"limit": 10}
    }
  }'
```

**Search Jira issues:**
```bash
curl -X POST http://localhost:8080/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "jira_search_issues_tool",
    "arguments": {
      "project_id": "your-project-id",
      "jql": "project = DEMO AND status = \"In Progress\"",
      "max_results": 20
    }
  }'
```

**Create Jira issue:**
```bash
curl -X POST http://localhost:8080/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "jira_create_issue_tool",
    "arguments": {
      "project_id": "your-project-id",
      "project_key": "DEMO",
      "summary": "Example task from API",
      "issue_type": "Task",
      "description": "This is a test issue created via the API",
      "priority": "Medium"
    }
  }'
```

**Generate S3 presigned URL:**
```bash
curl -X POST http://localhost:8080/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "s3_generate_presigned_url_tool",
    "arguments": {
      "project_id": "your-project-id",
      "bucket_name": "my-bucket",
      "object_key": "path/to/file.pdf",
      "operation": "get_object",
      "expiration": 3600
    }
  }'
```

**Generate S3 presigned POST:**
```bash
curl -X POST http://localhost:8080/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "s3_generate_presigned_post_tool",
    "arguments": {
      "project_id": "your-project-id",
      "bucket_name": "my-bucket",
      "object_key": "uploads/newfile.jpg",
      "expiration": 1800
    }
  }'
```

### Using with MCP Client

For stdio transport mode, the server can be used with MCP-compatible clients:

```json
{
  "servers": {
    "tools-mcp-server": {
      "command": "python",
      "args": ["/path/to/tools-mcp-server/server.py"],
      "env": {
        "MCP_TRANSPORT": "stdio",
        "API_BASE_URL": "http://localhost:8000"
      }
    }
  }
}
```

## Provider Details

### Looker Provider

Supports the full Looker API including:
- Model and explore metadata
- Query execution with dimensions, measures, and filters
- Look management and execution
- SQL query execution
- URL generation for sharing queries

### Redash Provider

Supports core Redash functionality including:
- Query management and execution
- Dashboard access
- Job status monitoring
- Data source listing
- Query result retrieval

### OpenAPI Provider

Supports any REST API with OpenAPI specification:
- Automatic spec discovery
- Endpoint enumeration
- Schema validation
- Authenticated requests
- Flexible authentication methods

## Development

### Adding New Tools Providers

1. Create a new provider class inheriting from `ToolsProvider`
2. Implement the `_initialize_client` method
3. Add provider-specific methods
4. Add the provider to the registry in `server.py`
5. Update credential fetcher to handle new provider credentials
6. Add corresponding MCP tools

### Testing

Run the server and test with MCP client tools or direct API calls.

## Security

- Credentials are fetched securely from the backend API
- No credentials are stored in logs or error messages
- Connection cleanup ensures no resource leaks
- Input validation on all tool parameters
- Authenticated requests to all tools services

## Logging

The server uses Python's standard logging module. Set `LOG_LEVEL` environment variable to control verbosity:
- `DEBUG`: Detailed debugging information
- `INFO`: General operational messages (default)
- `WARNING`: Warning messages only
- `ERROR`: Error messages only
