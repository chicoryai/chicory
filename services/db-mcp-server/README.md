# DB MCP Server

A Model Context Protocol (MCP) server for database operations using the FastMCP library. Currently supports Databricks and Snowflake with an extensible architecture for additional database providers.

## Features

- **Multi-Database Support**: Databricks and Snowflake with provider auto-detection
- **Project-based Credentials**: Secure credential management with API integration
- **Connection Caching**: TTL-based caching with automatic cleanup
- **Pure Async Architecture**: No threading complexity, fully async operations
- **FastMCP Integration**: Modern MCP server using FastMCP idioms
- **Docker Support**: Production-ready containerization
- **Health Monitoring**: HTTP health endpoint for monitoring and load balancers

## Tools

### Databricks Tools

All tools require a `chicory_project_id` parameter for credential lookup:

- **`databricks_query_tool`**: Execute arbitrary SQL queries with optional row limits
- **`databricks_list_tables_tool`**: List tables in a schema (schema name required)
- **`databricks_describe_table_tool`**: Describe table schema and column information
- **`databricks_sample_table_tool`**: Sample data from tables with configurable limits

### Snowflake Tools

All tools require a `chicory_project_id` parameter for credential lookup:

- **`snowflake_query_tool`**: Execute arbitrary SQL queries with optional row limits
- **`snowflake_list_tables_tool`**: List tables in a database and schema
- **`snowflake_describe_table_tool`**: Describe table schema and column information
- **`snowflake_sample_table_tool`**: Sample data from tables with configurable limits

**Parameters:**
- `chicory_project_id` (required): Project ID for credential lookup
- `table_name` (required): Table name to sample
- `schema_name` (optional): Schema name (if table_name is not fully qualified)
- `limit` (optional): Number of sample rows to return (default: 10)

## Architecture

### Provider-Specific Design

The server uses provider-specific tools rather than generic database tools because:

- **Database Concepts Differ**: Databricks uses `catalog.schema.table`, Snowflake uses `database.schema.table`, BigQuery uses `project.dataset.table`
- **Native Capabilities**: Each database has unique features that generic abstractions would hide
- **Type Safety**: Provider-specific parameters ensure correct usage and better error messages
- **Clear Intent**: Tool names explicitly indicate which database system is being used

### Minimal Base Provider

The `DatabaseProvider` base class provides only essential infrastructure:

- **Common State Management**: Credentials, initialization status, cleanup
- **No Database Abstractions**: No forced abstract methods for database operations
- **Provider Flexibility**: Each provider implements its own natural interface
- **Utility Methods**: Shared logging and metadata functionality

## Installation

### Option 1: Docker (Recommended)

1. **Build the Docker image:**
   ```bash
   docker build -t db-mcp-server .
   ```

2. **Run the container:**
   ```bash
   docker run -p 8080:8080 \
     -e API_BASE_URL=http://localhost:8000 \
     -e CONNECTION_CACHE_TTL=3600 \
     -e CONNECTION_CACHE_MAX_SIZE=100 \
     db-mcp-server
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

- **Build image:** `docker build -t db-mcp-server .`
- **Run container:** `docker run -p 8080:8080 db-mcp-server`
- **View logs:** `docker logs -f <container_id>`
- **Stop container:** `docker stop <container_id>`

## Usage

### Running the Server

**HTTP Transport (Default):**
```bash
python main.py
```
The server will start on `http://localhost:8080` by default.

### HTTP Endpoints

When running in HTTP mode, the server provides the following endpoints:

- `GET /health` - Health check endpoint
- `POST /mcp` - MCP protocol endpoint (JSON-RPC format)
- `POST /tools/list` - List available database tools (simplified format)
- `POST /tools/call` - Execute a database tool (simplified format)

### Example HTTP Usage

**Using MCP Protocol Endpoint:**

List available tools:
```bash
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/list",
    "params": {}
  }'
```

Execute a query:
```bash
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "databricks_query_tool",
      "arguments": {
        "chicory_project_id": "your-project-id",
        "query": "SELECT * FROM your_table LIMIT 10"
      }
    }
  }'
```

**Using Simplified Endpoints:**

List available tools:
```bash
curl -X POST http://localhost:8080/tools/list
```

Execute a query:
```bash
curl -X POST http://localhost:8080/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "databricks_query_tool",
    "arguments": {
      "chicory_project_id": "your-project-id",
      "query": "SELECT * FROM your_table LIMIT 10"
    }
  }'
```

### Using with MCP Client

For stdio transport mode, the server can be used with MCP-compatible clients:

```json
{
  "servers": {
    "db-mcp-server": {
      "command": "python",
      "args": ["/path/to/db-mcp-server/main.py"],
      "env": {
        "MCP_TRANSPORT": "stdio",
        "API_BASE_URL": "http://localhost:8000"
      }
    }
  }
}
```

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

The server fetches database credentials from the backend API endpoint:
```
GET /projects/{chicory_project_id}/data-sources
```

Expected response format:
```json
{
  "data_sources": [
    {
      "type": "databricks",
      "config": {
        "host": "your-databricks-host.cloud.databricks.com",
        "http_path": "/sql/1.0/warehouses/your-warehouse-id",
        "access_token": "your-access-token",
        "catalog": "main",
        "schema": "default"
      }
    }
  ]
}
```

## Architecture

### Provider System

The server uses a provider-based architecture for database support:

- `DatabaseProvider`: Abstract base class defining the interface
- `DatabricksProvider`: Databricks implementation using databricks-sql-connector
- Future providers can be easily added (Snowflake, PostgreSQL, etc.)

### Connection Caching

- LRU/TTL-based caching with configurable limits
- Automatic cleanup of expired connections
- Thread-safe operations with proper resource management
- Background cleanup task runs every 5 minutes

### Error Handling

- Comprehensive error handling with proper logging
- Graceful degradation on connection failures
- Detailed error messages in tool responses

## Development

### Adding New Database Providers

1. Create a new provider class inheriting from `DatabaseProvider`
2. Implement all abstract methods
3. Add the provider to the registry in `server.py`
4. Update credential fetcher to handle new provider credentials

### Testing

Run the server and test with MCP client tools or direct API calls.

## Logging

The server uses Python's standard logging module. Set `LOG_LEVEL` environment variable to control verbosity:
- `DEBUG`: Detailed debugging information
- `INFO`: General operational messages (default)
- `WARNING`: Warning messages only
- `ERROR`: Error messages only

## Security

- Credentials are fetched securely from the backend API
- No credentials are stored in logs or error messages
- Connection cleanup ensures no resource leaks
- Input validation on all tool parameters
