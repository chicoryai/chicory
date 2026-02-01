import logging
import httpx
from pydantic_settings import BaseSettings
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# Chicory MCP tool names (prefixed for Claude SDK)
CHICORY_MCP_TOOLS: List[str] = [
    # Project management
    "mcp__chicory__chicory_list_projects",
    "mcp__chicory__chicory_get_context",
    # Agent management
    "mcp__chicory__chicory_create_agent",
    "mcp__chicory__chicory_list_agents",
    "mcp__chicory__chicory_get_agent",
    "mcp__chicory__chicory_update_agent",
    "mcp__chicory__chicory_deploy_agent",
    "mcp__chicory__chicory_execute_agent",
    "mcp__chicory__chicory_list_agent_tasks",
    "mcp__chicory__chicory_get_agent_task",
    # Evaluation management
    "mcp__chicory__chicory_create_evaluation",
    "mcp__chicory__chicory_list_evaluations",
    "mcp__chicory__chicory_get_evaluation",
    "mcp__chicory__chicory_execute_evaluation",
    "mcp__chicory__chicory_get_evaluation_result",
    "mcp__chicory__chicory_list_evaluation_runs",
    "mcp__chicory__chicory_add_evaluation_test_cases",
    "mcp__chicory__chicory_delete_evaluation",
    # Data source / Integration management
    "mcp__chicory__chicory_list_data_source_types",
    "mcp__chicory__chicory_list_data_sources",
    "mcp__chicory__chicory_get_data_source",
    "mcp__chicory__chicory_create_data_source",
    "mcp__chicory__chicory_update_data_source",
    "mcp__chicory__chicory_delete_data_source",
    "mcp__chicory__chicory_validate_credentials",
    "mcp__chicory__chicory_test_connection",
    # Folder/File management
    "mcp__chicory__chicory_list_folder_files",
    "mcp__chicory__chicory_get_folder_file",
    "mcp__chicory__chicory_delete_folder_file",
]

# DB MCP tool names - dynamically discovered from server
# These are populated at runtime based on available tools
DB_MCP_TOOLS: List[str] = [
    "mcp__db_mcp_server__*",  # Wildcard pattern - actual tools discovered at runtime
]

# Tools MCP tool names - dynamically discovered from server
TOOLS_MCP_TOOLS: List[str] = [
    "mcp__tools_mcp_server__*",  # Wildcard pattern - actual tools discovered at runtime
]

# Active descriptions for MCP tools (present continuous form for UI display)
MCP_TOOL_DESCRIPTIONS: Dict[str, str] = {
    # Chicory Platform Tools
    "mcp__chicory__chicory_list_projects": "Listing projects...",
    "mcp__chicory__chicory_get_context": "Getting project context...",
    "mcp__chicory__chicory_create_agent": "Creating agent...",
    "mcp__chicory__chicory_list_agents": "Listing agents...",
    "mcp__chicory__chicory_get_agent": "Getting agent details...",
    "mcp__chicory__chicory_update_agent": "Updating agent...",
    "mcp__chicory__chicory_deploy_agent": "Deploying agent...",
    "mcp__chicory__chicory_execute_agent": "Executing agent...",
    "mcp__chicory__chicory_list_agent_tasks": "Listing agent tasks...",
    "mcp__chicory__chicory_get_agent_task": "Getting task details...",
    "mcp__chicory__chicory_create_evaluation": "Creating evaluation...",
    "mcp__chicory__chicory_list_evaluations": "Listing evaluations...",
    "mcp__chicory__chicory_get_evaluation": "Getting evaluation details...",
    "mcp__chicory__chicory_execute_evaluation": "Running evaluation...",
    "mcp__chicory__chicory_get_evaluation_result": "Getting evaluation results...",
    "mcp__chicory__chicory_list_evaluation_runs": "Listing evaluation runs...",
    "mcp__chicory__chicory_add_evaluation_test_cases": "Adding test cases...",
    "mcp__chicory__chicory_delete_evaluation": "Deleting evaluation...",
    # Data source / Integration management
    "mcp__chicory__chicory_list_data_source_types": "Listing data source types...",
    "mcp__chicory__chicory_list_data_sources": "Listing data sources...",
    "mcp__chicory__chicory_get_data_source": "Getting data source details...",
    "mcp__chicory__chicory_create_data_source": "Creating data source...",
    "mcp__chicory__chicory_update_data_source": "Updating data source...",
    "mcp__chicory__chicory_delete_data_source": "Deleting data source...",
    "mcp__chicory__chicory_validate_credentials": "Validating credentials...",
    "mcp__chicory__chicory_test_connection": "Testing connection...",
    # Folder/File management
    "mcp__chicory__chicory_list_folder_files": "Listing folder files...",
    "mcp__chicory__chicory_get_folder_file": "Getting file details...",
    "mcp__chicory__chicory_delete_folder_file": "Deleting file...",
}


def get_tool_active_description(tool_name: str, tool_input: Optional[dict] = None) -> str:
    """Generate active description for a tool.

    Priority:
    1. Claude-provided description in tool_input (like Bash's 'description' param)
    2. Static mapping for known tools
    3. Auto-generate from tool name

    Args:
        tool_name: Full tool name (e.g., "mcp__chicory__chicory_list_agents")
        tool_input: Optional tool input dict that may contain a 'description' field

    Returns:
        Human-readable active description (e.g., "Listing agents...")
    """
    # 1. Check if Claude provided a description in the input
    if tool_input and tool_input.get("description"):
        return tool_input["description"]

    # 2. Check static mapping
    if tool_name in MCP_TOOL_DESCRIPTIONS:
        return MCP_TOOL_DESCRIPTIONS[tool_name]

    # 3. Fallback: generate from tool name
    # mcp__chicory__chicory_list_agents -> "Listing agents..."
    # mcp__db_mcp_server__query_table -> "Querying table..."
    parts = tool_name.split("__")
    if len(parts) >= 3:
        action = parts[-1].replace("chicory_", "").replace("_", " ")
        words = action.split()
        if words:
            # Simple present continuous: "list" -> "Listing"
            verb = words[0]
            if verb.endswith("e"):
                verb = verb[:-1] + "ing"
            else:
                verb = verb + "ing"
            words[0] = verb.capitalize()
            return " ".join(words) + "..."

    return f"Executing {tool_name}..."


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Service configuration
    SERVICE_NAME: str = "agent-service"
    DEBUG: bool = False

    # Anthropic API
    ANTHROPIC_API_KEY: str

    # Redis configuration (for streaming updates)
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_CLUSTER_MODE: bool = False  # Set True for AWS MemoryDB

    # Backend API URL (for callbacks)
    BACKEND_API_URL: str = "http://localhost:8000"

    # MCP Server URLs for DB and Tools
    # These use project-specific endpoints: {URL}/mcp/{project_id}
    DB_MCP_SERVER_URL: Optional[str] = None  # e.g., http://localhost:8080
    TOOLS_MCP_SERVER_URL: Optional[str] = None  # e.g., http://localhost:8081

    # Chicory MCP Configuration
    # Local: http://localhost:3000
    # Prod:  https://app.chicory.ai
    CHICORY_MCP_BASE_URL: str = "http://localhost:3000"
    CHICORY_MCP_API_KEY: Optional[str] = None

    # MCP Timeout Configuration (in milliseconds)
    # Applied to all MCP server connections to prevent initialization timeouts
    MCP_TIMEOUT: int = 300000  # 5 minutes default - sufficient for slow MCP server startups
    CHICORY_MCP_TIMEOUT: int = 300000  # Legacy: kept for backwards compatibility

    # Agent defaults
    DEFAULT_MAX_TURNS: int = 15
    DEFAULT_MODEL: str = "claude-sonnet-4-20250514"

    # Sandbox defaults
    SANDBOX_ENABLED: bool = True
    SANDBOX_AUTO_ALLOW_BASH: bool = True

    # Workspace defaults
    WORKSPACE_BASE_PATH: str = "/data/workspaces"

    @property
    def chicory_mcp_url(self) -> str:
        """Build full MCP URL from base URL."""
        logger.info(f"[CONFIG] Chicory MCP Base URL: {self.CHICORY_MCP_BASE_URL}")
        return f"{self.CHICORY_MCP_BASE_URL}/mcp/platform"

    def get_chicory_mcp_config(self) -> Dict[str, Any]:
        """
        Build Chicory MCP server configuration.

        Returns:
            MCP server config dict, or empty dict if API key not set
        """
        if not self.CHICORY_MCP_API_KEY:
            logger.warning("[CONFIG] CHICORY_MCP_API_KEY not set, MCP server disabled")
            return {}

        # Log config values (mask API key for security)
        api_key_preview = f"{self.CHICORY_MCP_API_KEY[:8]}...{self.CHICORY_MCP_API_KEY[-4:]}" if len(self.CHICORY_MCP_API_KEY) > 12 else "***"
        logger.info(f"[CONFIG] Building Chicory MCP config:")
        logger.info(f"[CONFIG]   Base URL: {self.CHICORY_MCP_BASE_URL}")
        logger.info(f"[CONFIG]   Full URL: {self.chicory_mcp_url}")
        logger.info(f"[CONFIG]   API Key: {api_key_preview}")

        return {
            "chicory": {
                "type": "http",
                "url": self.chicory_mcp_url,
                "headers": {
                    "Authorization": f"Bearer {self.CHICORY_MCP_API_KEY}"
                },
                "timeout": self.MCP_TIMEOUT,
            }
        }

    def get_db_mcp_config(self, project_id: str) -> Dict[str, Any]:
        """
        Build DB MCP server configuration with project-specific endpoint.

        Args:
            project_id: Project ID for the MCP endpoint

        Returns:
            MCP server config dict, or empty dict if URL not set
        """
        if not self.DB_MCP_SERVER_URL:
            logger.debug("[CONFIG] DB_MCP_SERVER_URL not set, DB MCP server disabled")
            return {}

        # Build project-specific URL
        mcp_url = f"{self.DB_MCP_SERVER_URL}/mcp/{project_id}"
        logger.info(f"[CONFIG] Building DB MCP config for project {project_id}:")
        logger.info(f"[CONFIG]   URL: {mcp_url}")

        return {
            "db_mcp_server": {
                "type": "http",
                "url": mcp_url,
                "timeout": self.MCP_TIMEOUT,
            }
        }

    def get_tools_mcp_config(self, project_id: str) -> Dict[str, Any]:
        """
        Build Tools MCP server configuration with project-specific endpoint.

        Args:
            project_id: Project ID for the MCP endpoint

        Returns:
            MCP server config dict, or empty dict if URL not set
        """
        if not self.TOOLS_MCP_SERVER_URL:
            logger.debug("[CONFIG] TOOLS_MCP_SERVER_URL not set, Tools MCP server disabled")
            return {}

        # Build project-specific URL
        mcp_url = f"{self.TOOLS_MCP_SERVER_URL}/mcp/{project_id}"
        logger.info(f"[CONFIG] Building Tools MCP config for project {project_id}:")
        logger.info(f"[CONFIG]   URL: {mcp_url}")

        return {
            "tools_mcp_server": {
                "type": "http",
                "url": mcp_url,
                "timeout": self.MCP_TIMEOUT,
            }
        }

    def get_all_mcp_config(self, project_id: str) -> Dict[str, Any]:
        """
        Build complete MCP server configuration including all servers.

        Combines Chicory, DB, and Tools MCP server configurations.

        Args:
            project_id: Project ID for project-specific MCP endpoints

        Returns:
            Combined MCP server config dict
        """
        mcp_servers = {}

        # Add Chicory MCP (not project-specific)
        chicory_config = self.get_chicory_mcp_config()
        if chicory_config:
            mcp_servers.update(chicory_config)

        # TEMPORARILY DISABLED: DB and Tools MCP servers
        # The Claude Agent SDK has an issue with 3+ MCP servers causing
        # "Control request timeout: initialize" errors. Re-enable once fixed.
        # See: https://github.com/anthropics/claude-code/issues/XXX
        #
        # # Add DB MCP (project-specific)
        # db_config = self.get_db_mcp_config(project_id)
        # if db_config:
        #     mcp_servers.update(db_config)
        #
        # # Add Tools MCP (project-specific)
        # tools_config = self.get_tools_mcp_config(project_id)
        # if tools_config:
        #     mcp_servers.update(tools_config)

        logger.info(f"[CONFIG] Built complete MCP config with {len(mcp_servers)} servers: {list(mcp_servers.keys())}")
        return mcp_servers

    async def check_mcp_connection(self) -> Tuple[bool, str]:
        """
        Check if the Chicory MCP server is reachable.

        Returns:
            Tuple of (is_connected: bool, message: str)
        """
        if not self.CHICORY_MCP_API_KEY:
            return False, "CHICORY_MCP_API_KEY not configured"

        url = self.chicory_mcp_url
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {self.CHICORY_MCP_API_KEY}"}
                )
                if response.status_code == 200:
                    logger.info(f"[CONFIG] MCP server connection successful: {url}")
                    return True, f"Connected to {url}"
                elif response.status_code == 401:
                    logger.error(f"[CONFIG] MCP server auth failed (401): {url}")
                    return False, f"Authentication failed (401) - check CHICORY_MCP_API_KEY"
                elif response.status_code == 404:
                    # MCP endpoints may return 404 for GET, try OPTIONS or just report reachable
                    logger.info(f"[CONFIG] MCP server reachable (404 on GET is normal for MCP): {url}")
                    return True, f"Server reachable at {url} (MCP endpoint)"
                else:
                    logger.warning(f"[CONFIG] MCP server returned {response.status_code}: {url}")
                    return False, f"Server returned status {response.status_code}"
        except httpx.ConnectError as e:
            logger.error(f"[CONFIG] MCP server connection failed: {url} - {e}")
            return False, f"Connection failed: {url} - Cannot reach server"
        except httpx.TimeoutException as e:
            logger.error(f"[CONFIG] MCP server timeout: {url} - {e}")
            return False, f"Connection timeout: {url}"
        except Exception as e:
            logger.error(f"[CONFIG] MCP server check error: {url} - {e}")
            return False, f"Error: {str(e)}"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
