import os
import sys
import logging
import time
import pika
import json
import asyncio
import aiohttp
import signal
import boto3
from enum import Enum
from typing import Any, Dict, Optional
from datetime import datetime, timezone
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

# Define TaskStatus enum locally to match the API definition
class TaskStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

# Cancellation message constant
TASK_CANCELLED_MESSAGE = "Task was cancelled by user."

# Load default envs
from services.utils.config import load_default_envs
load_default_envs()

# Import from BrewSearch services
from services.workflows.data_understanding.hybrid_rag.adaptive_rag import initialize_agent
from services.integration.phoenix import initialize_phoenix

# Configure logging
logging_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=logging_format)

# Set higher log level for noisy libraries
logging.getLogger('pika').setLevel(logging.WARNING)
logging.getLogger('pika.adapters').setLevel(logging.WARNING)
logging.getLogger('pika.adapters.select_connection').setLevel(logging.WARNING)

# Get our application logger
logger = logging.getLogger(__name__)

# Base API URL for backend service (if needed)
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# DB MCP Server endpoint for database operations
DB_MCP_SERVER_URL = os.getenv("DB_MCP_SERVER_URL", "http://localhost:8080/mcp")
TOOLS_MCP_SERVER_URL = os.getenv("TOOLS_MCP_SERVER_URL", "http://localhost:8081/mcp")
GITHUB_MCP_SERVER_URL = os.getenv("GITHUB_MCP_SERVER_URL", "https://api.githubcopilot.com/mcp/")

# Global flag for graceful shutdown
shutdown_flag = False
_connection = None
_channel = None

# Initialize Phoenix tracing
initialize_phoenix()

# Task status enum - match values with backend API
class TaskStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class InferenceJobManager:
    """Manager class for handling inference jobs from RabbitMQ"""

    def __init__(self):
        self.api_base_url = API_BASE_URL
        # Base directory for projects
        self.base_dir = os.getenv("BASE_DIR", "/data")
        # Temporary directory for project data
        self.temp_base_dir = os.getenv("TEMP_BASE_DIR", "/tmp/data")
        # Signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _get_s3_client(self):
        """Create S3 client with optional custom endpoint (MinIO, LocalStack, etc.)"""
        region = os.getenv("S3_REGION", os.getenv("AWS_REGION", "us-east-1"))
        endpoint_url = os.getenv("S3_ENDPOINT_URL")

        boto_config = BotoConfig(
            max_pool_connections=50,
            retries={'max_attempts': 3}
        )

        client_kwargs = {
            'region_name': region,
            'config': boto_config
        }

        # Add endpoint URL if specified (for MinIO or other S3-compatible storage)
        if endpoint_url:
            client_kwargs['endpoint_url'] = endpoint_url
            logger.info(f"Using custom S3 endpoint: {endpoint_url}")

        # Add credentials if available
        aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        if aws_access_key and aws_secret_key:
            client_kwargs['aws_access_key_id'] = aws_access_key
            client_kwargs['aws_secret_access_key'] = aws_secret_key

        return boto3.client("s3", **client_kwargs)

    def sync_project_data_from_s3(self, project_id: str) -> bool:
        """
        Sync project-specific data from S3/MinIO to local filesystem.
        Downloads files from artifacts/{project_id}/ to /app/data/{project_id}/

        Args:
            project_id: The project ID to sync data for

        Returns:
            True if sync was successful, False otherwise
        """
        try:
            bucket = os.getenv("S3_BUCKET", os.getenv("S3_BUCKET_NAME", "chicory-data"))
            if not bucket:
                logger.warning("S3_BUCKET not set, skipping S3 sync")
                return False

            # S3 prefix for project data
            s3_prefix = f"artifacts/{project_id}/"

            # Local destination - use /app/data/{project_id} structure
            local_base = os.getenv("CONTEXT_DIR", "/app/data")
            local_dest = os.path.join(local_base, project_id)

            logger.info(f"Syncing project data from s3://{bucket}/{s3_prefix} to {local_dest}")

            # Ensure local directory exists
            os.makedirs(local_dest, exist_ok=True)

            # Get S3 client
            s3 = self._get_s3_client()

            # List and download objects
            paginator = s3.get_paginator("list_objects_v2")
            files_downloaded = 0

            for page in paginator.paginate(Bucket=bucket, Prefix=s3_prefix):
                if "Contents" not in page:
                    continue

                for obj in page["Contents"]:
                    key = obj["Key"]
                    # Skip directory markers
                    if key.endswith('/'):
                        continue

                    # Calculate relative path (remove the artifacts/{project_id}/ prefix)
                    relative_path = key[len(s3_prefix):]
                    if not relative_path:
                        continue

                    # Local file path
                    local_path = os.path.join(local_dest, relative_path)

                    # Create parent directories
                    os.makedirs(os.path.dirname(local_path), exist_ok=True)

                    # Download file
                    try:
                        s3.download_file(bucket, key, local_path)
                        files_downloaded += 1
                        logger.debug(f"Downloaded: {key} -> {local_path}")
                    except Exception as e:
                        logger.error(f"Error downloading {key}: {e}")

            logger.info(f"S3 sync complete: {files_downloaded} files downloaded for project {project_id}")
            return files_downloaded > 0

        except ClientError as e:
            logger.error(f"S3 client error during sync: {e}")
            return False
        except Exception as e:
            logger.error(f"Error syncing project data from S3: {e}")
            return False

    async def _build_mcp_configuration(self, project_id: str, agent_id: str = None) -> dict:
        """Build MCP server configuration using project-specific MCP endpoints."""
        mcp_servers = {}
        
        # Process default MCP servers - use project-specific endpoints
        default_servers = []
        
        # Add DB MCP Server if configured - use /mcp/{project_id} endpoint
        if DB_MCP_SERVER_URL:
            default_servers.append({
                "name": "db_mcp_server",
                "url": f"{DB_MCP_SERVER_URL}/mcp/{project_id}",
                "headers": {}
            })
        
        # Add Tools MCP Server if configured - use /mcp/{project_id} endpoint
        if TOOLS_MCP_SERVER_URL:
            default_servers.append({
                "name": "tools_mcp_server", 
                "url": f"{TOOLS_MCP_SERVER_URL}/mcp/{project_id}",
                "headers": {}
            })
        
        # Add GitHub MCP Server if configured
        # GitHub MCP requires authorization token from data source configuration
        if GITHUB_MCP_SERVER_URL:
            try:
                # Get data sources for the project
                data_sources = await self.get_data_sources(project_id)
                
                # Find GitHub data source
                github_datasource = None
                for ds in data_sources:
                    if ds.get("type") == "github" and ds.get("status") in ["configured", "connected"]:
                        github_datasource = ds
                        break
                
                if github_datasource:
                    # Extract the GitHub Access Token from configuration
                    config = github_datasource.get("configuration", {})
                    github_token = config.get("access_token")
                    
                    if github_token:
                        # Add GitHub MCP server with authorization header
                        default_servers.append({
                            "name": "github_mcp_server",
                            "url": GITHUB_MCP_SERVER_URL,
                            "headers": {
                                "Authorization": f"Bearer {github_token}"
                            }
                        })
                        logger.info(f"Added GitHub MCP server for project {project_id}")
                    else:
                        logger.warning(f"GitHub data source found but no access token configured for project {project_id}")
                else:
                    logger.debug(f"No connected GitHub data source found for project {project_id}")
            except Exception as e:
                logger.error(f"Error configuring GitHub MCP server for project {project_id}: {e}")
        
        # Process agent-specific MCP tools if agent_id provided
        agent_mcp_servers = []
        if agent_id:
            agent_tools = await self.get_agent_tools(project_id, agent_id)
            for tool in agent_tools:
                if tool.get("tool_type") == "mcp":
                    tool_config = tool.get("config", {})
                    server_url = tool_config.get("server_url")
                    if server_url:
                        agent_mcp_servers.append({
                            "name": tool.get("name"),
                            "url": server_url,
                            "headers": tool_config.get("headers", {})
                        })
        
        # Build server configurations
        all_servers = default_servers + agent_mcp_servers
        
        for server_config in all_servers:
            server_name = server_config["name"]
            server_url = server_config["url"]
            headers = server_config["headers"]
            
            # Add server to configuration
            mcp_server_config = {
                "url": server_url,
                "type": "http"
            }
            if headers and "Authorization" in headers:
                mcp_server_config["headers"] = {
                    "Authorization": headers["Authorization"],
                    "User-Agent": f"ChicoryAgent={agent_id}"
                }
            
            mcp_servers[server_name] = mcp_server_config
            logger.info(f"Added MCP server: {server_name} at {server_url}")
        
        mcp_config = {
            "servers": mcp_servers
        }
        
        logger.info(f"Built MCP configuration with {len(mcp_servers)} servers for project {project_id}")
        return mcp_config

    def _signal_handler(self, sig, frame):
        """Handle termination signals for graceful shutdown"""
        global shutdown_flag
        logger.info(f"Received signal {sig}, initiating graceful shutdown...")
        shutdown_flag = True
        # If we have an active connection, close it
        if _connection and _connection.is_open:
            _connection.close()

    def copy_project_to_temp(self, project_id):
        """
        Copy project data to a temporary directory for isolated processing.
        
        Args:
            project_id: The project ID to copy data for (lowercase)
            
        Returns:
            Path to the temporary project directory
        """
        from pathlib import Path
        from services.utils.dir import copy_folder_content
        
        # Source project directory
        source_dir = Path(self.base_dir) / project_id
        
        if not source_dir.exists():
            logger.warning(f"Source project directory not found: {source_dir}")
            return None
            
        # Create temporary directory path
        temp_dir = Path(self.temp_base_dir) / project_id
        
        # Use os.path to check if directory exists (more reliable than Path.exists in some environments)
        temp_dir_str = str(temp_dir)  # Convert Path to string for os.path functions
        
        # Create a fresh temporary directory
        os.makedirs(temp_dir_str, exist_ok=True)
        
        try:
            # Log operation
            logger.info(f"Copying project data: {source_dir} -> {temp_dir}")
            # Copy project data to temporary location
            copy_folder_content(str(source_dir), str(temp_dir))
            
            # Log success
            logger.info(f"Successfully copied project data to {temp_dir}")
            return str(temp_dir)
        except Exception as e:
            logger.error(f"Failed to copy project data: {str(e)}")
            return None
    
    async def get_data_sources(self, project_id: str) -> list:
        """
        Get data sources for a project using the API
        
        Args:
            project_id: The project ID to get data sources for
            
        Returns:
            List of data sources
        """
        try:
            # Get API base URL from environment or use default
            api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
            
            url = f"{api_base_url}/projects/{project_id}/data-sources"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Failed to get data sources for project {project_id}. Status: {response.status}, Error: {error_text}")
                        return []
                    
                    # Parse the response
                    response_data = await response.json()
                    all_data_sources = response_data.get("data_sources", [])
                    
                    return all_data_sources
        except Exception as e:
            logger.error(f"Error getting data sources: {str(e)}")
            return []

    async def get_anthropic_api_key(self, project_id: str) -> Optional[str]:
        """
        Get ANTHROPIC_API_KEY from project data sources.
        Falls back to CHICORY_ANTHROPIC_API_KEY if not found in data sources.
        
        Args:
            project_id: The project ID to get Anthropic credentials for
            
        Returns:
            The Anthropic API key if found, None otherwise
        """
        try:
            # Get data sources for the project
            data_sources = await self.get_data_sources(project_id)
            
            # Look for Anthropic data source
            anthropic_api_key = None
            for ds in data_sources:
                if ds.get("type") == "anthropic":
                    # Extract API key from configuration
                    config = ds.get("configuration", {})
                    anthropic_api_key = config.get("api_key")
                    if anthropic_api_key:
                        logger.info(f"Found Anthropic API key in project {project_id} data sources")
                        break
            
            # If not found in data sources, use fallback from environment
            if not anthropic_api_key:
                anthropic_api_key = os.getenv("CHICORY_ANTHROPIC_API_KEY")
                if anthropic_api_key:
                    logger.info(f"Using fallback Anthropic API key from CHICORY_ANTHROPIC_API_KEY for project {project_id}")
                else:
                    logger.warning(f"No Anthropic API key found for project {project_id}")
                    return None
            
            return anthropic_api_key
            
        except Exception as e:
            logger.error(f"Error getting Anthropic API key: {str(e)}")
            return None

    async def get_agent_tools(self, project_id, agent_id):
        """
        Get configured tools for a specific agent using the API
        
        Args:
            project_id: The project ID
            agent_id: The agent ID to get tools for
            
        Returns:
            List of agent tools
        """
        try:
            # Get API base URL from environment or use default
            api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
            
            url = f"{api_base_url}/projects/{project_id}/agents/{agent_id}/tools"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Failed to get tools for agent {agent_id} in project {project_id}. Status: {response.status}, Error: {error_text}")
                        return []
                    
                    # Parse the response
                    response_data = await response.json()
                    tools = response_data.get("tools", [])
                    
                    logger.info(f"Retrieved {len(tools)} tools for agent {agent_id} in project {project_id}")
                    return tools
        except Exception as e:
            logger.error(f"Error getting agent tools: {str(e)}")
            return []

    async def get_agent_env_variables(self, project_id: str, agent_id: str) -> Dict[str, str]:
        """
        Get configured environment variables for a specific agent using the API.
        
        Args:
            project_id: The project ID
            agent_id: The agent ID to get environment variables for
            
        Returns:
            Dictionary of environment variable key-value pairs
        """
        try:
            # Get API base URL from environment or use default
            api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
            
            url = f"{api_base_url}/projects/{project_id}/agents/{agent_id}/env-variables"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 404:
                        # No env variables configured - this is fine
                        logger.debug(f"No environment variables found for agent {agent_id} in project {project_id}")
                        return {}
                    
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Failed to get env variables for agent {agent_id} in project {project_id}. Status: {response.status}, Error: {error_text}")
                        return {}
                    
                    # Parse the response
                    response_data = await response.json()
                    env_vars_list = response_data.get("env_variables", [])
                    
                    # Convert list of env variable objects to dict
                    env_vars = {}
                    for ev in env_vars_list:
                        key, value = ev.get("key"), ev.get("value")
                        if key and value:
                            env_vars[key] = value
                        else:
                            logger.warning(f"Skipping invalid env variable entry for agent {agent_id}: key={key}, value={'<set>' if value else '<empty>'}")
                    
                    logger.info(f"Retrieved {len(env_vars)} environment variables for agent {agent_id} in project {project_id}")
                    return env_vars
        except Exception as e:
            logger.error(f"Error getting agent environment variables: {str(e)}")
            return {}

    async def get_workflow_client(self, project_id, agent_id=None, override_project_id: Optional[str] = None):
        """
        Always create and return a new workflow client for the specified agent within a project.
        Caching is intentionally bypassed so each invocation builds a fresh client.

        Tool configuration can be sourced from a different override project by passing
        override_project_id. The client itself is initialized for the provided project_id,
        but tools will be configured using override_project_id when provided.

        Args:
            project_id: The project ID to initialize the client for (lowercase)
            agent_id: The agent ID to get a client for (if None, falls back to project_id for compatibility)
            override_project_id: Optional override project to use when configuring tools

        Returns:
            A newly created workflow client for the agent
        """
        # Always ensure project_id is lowercase for consistency
        project_id = project_id.lower()
            
        # Use agent_id if provided, otherwise fall back to project_id
        if agent_id is None:
            agent_id = project_id
        else:
            agent_id = agent_id.lower()
        
        # Use override_project_id for configuration if provided, otherwise fall back to project_id
        config_project_id = (override_project_id or project_id).lower()
        
        logger.info(f"Initializing new workflow client for agent: {agent_id}, project: {project_id}, config_project: {config_project_id}")

        # Build MCP configuration with data source filtering
        mcp_config = await self._build_mcp_configuration(config_project_id, agent_id)
        
        # Initialize the data understanding workflow
        logger.info(f"Using Data Understanding workflow for project: {config_project_id}")
        
        # Initialize agent with MCP configuration
        logger.info(f"Initializing agent with MCP configuration for project: {config_project_id}")
        client = await initialize_agent('agent', config_project_id, mcp_config=mcp_config, 
                                       agent_id=agent_id, recursion_limit=150)
        
        return client

    def _build_complete_response(self, history, current_state):
        """
        Build a complete response from the accumulated history of streaming updates.
        This ensures the task always contains the full context and history.

        Args:
            history: Dictionary containing the response history by section
            current_state: The current processing state

        Returns:
            A formatted string with the complete response
        """
        # Get title for the section (use key as fallback with title case)
        if current_state == 'ontology_node':
            title = json.dumps({"status": "Generating Response"})
        elif current_state == 'agent_node':
            title = json.dumps({"status": "Rendering Output"})
        elif current_state == 'synthesis_node':
            title = json.dumps({"status": "Rendering Output"})
        else:
            title = json.dumps({"status": "Generating Response"})
        return title
            
    def get_rabbitmq_connection(self, retry_count=3, retry_delay=1.0):
        """
        Get a RabbitMQ connection with retry logic

        Args:
            retry_count: Number of connection attempts before giving up
            retry_delay: Delay in seconds between retry attempts

        Returns:
            A RabbitMQ connection

        Raises:
            AMQPConnectionError: If all connection attempts fail
        """
        global _connection

        # If we have an existing connection and it's open, return it
        if _connection is not None and _connection.is_open:
            try:
                # Verify the connection is actually usable
                _connection.process_data_events()
                return _connection
            except (AMQPConnectionError, StreamLostError):
                # Connection is broken, set to None and try to reconnect
                _connection = None
                logger.warning("Detected broken RabbitMQ connection, reconnecting...")

        # Get RabbitMQ connection details from environment variables with defaults
        rabbitmq_host = os.getenv("RABBITMQ_HOST", "localhost")
        rabbitmq_port = int(os.getenv("RABBITMQ_PORT", "5672"))
        rabbitmq_vhost = os.getenv("RABBITMQ_VHOST", "/")
        rabbitmq_username = os.getenv("RABBITMQ_USERNAME", "guest")
        rabbitmq_password = os.getenv("RABBITMQ_PASSWORD", "guest")

        # Check if we need SSL (port 5671 is the standard SSL port for RabbitMQ)
        use_ssl = rabbitmq_port == 5671

        # Set up SSL context if needed
        ssl_options = None
        if use_ssl:
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            ssl_options = pika.SSLOptions(ssl_context)
            logger.info("Using SSL for RabbitMQ connection")

        # Connect to RabbitMQ with appropriate SSL settings and enable heartbeats
        connection_params = pika.ConnectionParameters(
            host=rabbitmq_host,
            port=rabbitmq_port,
            virtual_host=rabbitmq_vhost,
            credentials=pika.PlainCredentials(
                rabbitmq_username,
                rabbitmq_password
            ),
            ssl_options=ssl_options,
            heartbeat=30,  # Send heartbeat every 30 seconds to detect broken connections
            blocked_connection_timeout=10,  # Timeout for blocked connections
            connection_attempts=2,  # Try to connect twice initially
            retry_delay=0.5  # Half second delay between initial connection attempts
        )

        # Try to connect with retry logic
        last_exception = None
        for attempt in range(retry_count):
            try:
                logger.info(
                    f"Connecting to RabbitMQ at {rabbitmq_host}:{rabbitmq_port} (attempt {attempt + 1}/{retry_count})")
                _connection = pika.BlockingConnection(connection_params)
                logger.info("Successfully connected to RabbitMQ")
                return _connection
            except Exception as e:
                last_exception = e
                logger.warning(f"RabbitMQ connection attempt {attempt + 1} failed: {str(e)}")
                if attempt < retry_count - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    # Increase delay for subsequent retries (backoff)
                    retry_delay = min(retry_delay * 1.5, 5.0)

        # If we get here, all retries failed
        logger.error(f"Failed to connect to RabbitMQ after {retry_count} attempts")
        raise last_exception or AMQPConnectionError("Failed to connect to RabbitMQ")

    def setup_rabbitmq_consumer(self):
        """
        Set up RabbitMQ resources for consuming training job messages

        Returns:
            Tuple of (connection, channel)
        """
        global _connection, _channel

        # Get a connection
        connection = self.get_rabbitmq_connection()
        _connection = connection

        # Create a channel
        channel = connection.channel()
        _channel = channel

        # Set prefetch count - only process one message at a time
        # This ensures we don't take on too many training jobs simultaneously
        channel.basic_qos(prefetch_count=1)

        # Define exchange and queue names
        exchange_name = os.getenv("AGENT_EXCHANGE_NAME", "agent_exchange")
        queue_name = os.getenv("AGENT_QUEUE_NAME", "agent_tasks_queue")
        routing_key = os.getenv("AGENT_ROUTING_KEY", "agent.message")

        # Ensure the exchange exists
        channel.exchange_declare(
            exchange=exchange_name,
            exchange_type='direct',
            durable=True  # Survive broker restarts
        )

        # Check if queue exists - do not create if it doesn't exist
        try:
            # Check if queue exists using passive declaration
            channel.queue_declare(queue=queue_name, passive=True)
            logger.info(f"Queue {queue_name} already exists, using existing configuration")
        except pika.exceptions.ChannelClosedByBroker:
            # Queue doesn't exist, exit with error
            logger.error(f"Queue {queue_name} does not exist in RabbitMQ. Please create the queue before starting the service.")
            # Close the connection before exiting
            if connection and connection.is_open:
                try:
                    connection.close()
                    logger.info("RabbitMQ connection closed")
                except Exception as e:
                    logger.error(f"Error closing connection: {str(e)}")
            # Exit with error code
            sys.exit(1)

        # Bind the queue to the exchange
        channel.queue_bind(
            queue=queue_name,
            exchange=exchange_name,
            routing_key=routing_key
        )

        logger.info(f"RabbitMQ consumer set up for queue: {queue_name}")

        return connection, channel

    async def get_agent_info(self, agent_id: str, project_id: str) -> dict[str, Any]:
        """
        Get agent information from the API.
        This retrieves agent configuration including instructions and output format.

        Args:
            agent_id: The ID of the agent to retrieve
            project_id: The project ID the agent belongs to

        Returns:
            Dict containing agent information or default values if not found
        """
        # Get API base URL from environment or use default
        api_base_url = API_BASE_URL

        try:
            # Build URL for retrieving agent info
            url = f"{api_base_url}/projects/{project_id}/agents/{agent_id}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        agent_data = await response.json()
                        logger.info(f"Successfully retrieved agent {agent_id} information")
                        return {
                            "id": agent_data.get("id"),
                            "name": agent_data.get("name"),
                            "description": agent_data.get("description"),
                            "instructions": agent_data.get("instructions"),
                            "output_format": agent_data.get("output_format", "text"),
                            "project_id": agent_data.get("project_id")
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to get agent {agent_id} via API. Status: {response.status}, Error: {error_text}")
                        return {
                            "instructions": None,
                            "description": None,
                            "output_format": "text",
                            "name": "Unknown Agent"
                        }
        except Exception as e:
            logger.error(f"Error retrieving agent {agent_id}: {str(e)}", exc_info=True)
            return {
                "instructions": None,
                "description": None,
                "output_format": "text",
                "name": "Unknown Agent"
            }

    async def get_agent_tasks(self, agent_id: str, project_id: str, limit: int = 5) -> list[dict[str, Any]]:
        """
        Get the most recent tasks for an agent to provide conversation history context.

        Args:
            agent_id: The ID of the agent
            project_id: The project ID
            limit: Maximum number of tasks to retrieve (default: 5)
            
        Returns:
            List of task objects, ordered from most recent to oldest
        """
        # Get API base URL from environment or use default
        api_base_url = API_BASE_URL
        
        try:
            # Use the enhanced API endpoint with filtering capabilities
            # - Limit the number of tasks to retrieve
            # - Filter to only include completed tasks for meaningful conversation history
            # - Explicitly request descending order (newest to oldest) using the sort_order parameter
            url = f"{api_base_url}/projects/{project_id}/agents/{agent_id}/tasks?limit={limit}&status=completed&sort_order=desc"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        tasks = response_data.get("tasks", [])
                        task_count = len(tasks)
                        logger.info(f"Retrieved {task_count} recent completed tasks for agent {agent_id}")
                        return tasks
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to get tasks for agent {agent_id}. Status: {response.status}, Error: {error_text}")
                        return []
        except Exception as e:
            logger.error(f"Error retrieving tasks for agent {agent_id}: {str(e)}", exc_info=True)
            return []
            
    async def update_task_status(self, task_id: str, status: TaskStatus, content: Optional[str] = None, project_id: str = None, agent_id: str = None):
        """
        Update the status and optionally the content of a task using the API.

        Args:
            task_id: The ID of the task to update
            status: The new status
            content: Optional new content for the task
            project_id: Project ID (required)
            agent_id: Agent ID (required)

        Returns:
            Boolean indicating success or failure
        """
        try:
            # Both project_id and agent_id are now required
            if not project_id or not agent_id:
                logger.error(f"Both project_id and agent_id are required to update task {task_id}")
                return False

            # Prepare update payload
            update_data = {
                'status': status.value  # Use the enum value for API compatibility
            }

            if content is not None:
                update_data['content'] = content

            # Call the API to update the task
            return await self.update_task(project_id, agent_id, task_id, update_data)
        except Exception as e:
            logger.error(f"Error updating task {task_id} via API: {str(e)}", exc_info=True)
            return False

    async def update_task(self, project_id: str, agent_id: str, task_id: str, update_data: dict[str, Any]) -> bool:
        """
        Update a task using the backend API.

        Args:
            project_id: The project ID
            agent_id: The chat ID
            task_id: The task ID to update
            update_data: The data to update

        Returns:
            Boolean indicating success or failure
        """
        # Get API base URL from environment or use default
        api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")

        # Construct the API endpoint URL
        url = f"{api_base_url}/projects/{project_id}/agents/{agent_id}/tasks/{task_id}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.put(url, json=update_data) as response:
                    if response.status == 200:
                        logger.info(f"Successfully updated task {task_id} via API")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to update task {task_id} via API. Status: {response.status}, Error: {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Error calling task update API for {task_id}: {str(e)}", exc_info=True)
            return False

    async def get_task_status(self, project_id: str, agent_id: str, task_id: str) -> Optional[str]:
        """
        Get the current status of a task using the backend API.

        Args:
            project_id: The project ID
            agent_id: The agent ID
            task_id: The task ID to check

        Returns:
            The task status as a string, or None if the task cannot be retrieved
        """
        # Get API base URL from environment or use default
        api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")

        # Construct the API endpoint URL
        url = f"{api_base_url}/projects/{project_id}/agents/{agent_id}/tasks/{task_id}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        task_data = await response.json()
                        status = task_data.get('status')
                        logger.debug(f"Task {task_id} status: {status}")
                        return status
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to get task {task_id} status via API. Status: {response.status}, Error: {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Error calling task get API for {task_id}: {str(e)}", exc_info=True)
            return None

    async def process_inference_message(self, ch, method, properties, body) -> None:
        """
        Process an inference message from RabbitMQ

        Args:
            ch: The channel object
            method: The method
            properties: The properties
            body: The message body
        """
        try:
            # Decode and process message
            message_data = json.loads(body.decode('utf-8'))
            task_id = message_data.get('task_id', 'unknown')
            assistant_task_id = message_data.get('assistant_task_id')

            # Example of a message format:
            # {
            #    "task_id": "26057f51-1882-4040-8f34-df43c2c26acc",
            #    "assistant_task_id": "89d52e20-0e95-411f-a39f-972a16dd7a2a",
            #    "agent_id": "c561f09f-4396-4dc1-8003-ec6563db8927",
            #    "project_id": "ba2a32e2-b122-4b89-829c-2b3f64b2cad4",
            #    "content": "What are the key tables in our database?",
            #    "metadata": {"source": "api_client", "priority": "normal"},
            #    "timestamp": "2025-04-28T21:00:51.356211+00:00",
            #    "action": "process_agent_task"
            # }

            logger.info(f"Received message: {task_id} with assistant message ID: {assistant_task_id}")
            
            # Get delivery timestamp to calculate message age
            delivery_time = properties.timestamp or time.time()
            message_age = time.time() - delivery_time
            
            # Check if the message is too old before processing
            if message_age >= 3600:  # 1 hour cutoff
                logger.warning(f"Task {task_id} is too old ({message_age:.1f} seconds), rejecting")
                # Reject the message and don't requeue it
                ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
                return
                
            # Acknowledge the message immediately to remove it from the queue
            # This prevents duplicate processing if the service crashes during processing
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(f"Acknowledged message {task_id} before processing (early ack strategy)")
            
            # Immediately update message statuses through the API
            if task_id != 'unknown' and assistant_task_id:
                # Extract required IDs from the message
                project_id = message_data.get('project_id')
                agent_id = message_data.get('agent_id')

                # Update user task status to COMPLETED as we've received it
                await self.update_task_status(task_id, TaskStatus.COMPLETED, project_id=project_id, agent_id=agent_id)

                # Update assistant task status to PROCESSING as we're starting to work on it
                await self.update_task_status(assistant_task_id, TaskStatus.PROCESSING, json.dumps({"status": "Gathering Context"}), project_id=project_id, agent_id=agent_id)

                logger.info(f"Updated task statuses: user task {task_id} -> COMPLETED, "
                            f"assistant task {assistant_task_id} -> PROCESSING")

            # Now process the task asynchronously - if it fails, we'll need to handle it differently
            # since the message is already removed from the queue
            try:
                await self.process_task(task_id, message_data)
                logger.info(f"Successfully processed message: {task_id}")
            except Exception as task_error:
                logger.error(f"Error processing task {task_id} after acknowledgment: {str(task_error)}", exc_info=True)
                
                # Since the message is already acknowledged, we need to handle the error differently
                # Update the assistant task to FAILED status
                if assistant_task_id:
                    project_id = message_data.get('project_id')
                    agent_id = message_data.get('agent_id')
                    try:
                        await self.update_task_status(
                            assistant_task_id,
                            TaskStatus.FAILED,
                            f"Processing error after acknowledgment: {str(task_error)}",
                            project_id=project_id,
                            agent_id=agent_id
                        )
                    except Exception as update_error:
                        logger.error(f"Failed to update task status after error: {str(update_error)}")
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)

            # Check if this is a recoverable error
            recoverable = False
            error_msg = str(e).lower()

            # These errors are likely temporary and might resolve on retry
            recoverable_patterns = [
                'connection', 'timeout', 'temporary', 'retry',
                'unavailable', 'overload', 'congestion', 'resource',
                'busy', 'rate limit', 'throttle'
            ]

            for pattern in recoverable_patterns:
                if pattern in error_msg:
                    recoverable = True
                    break

            if recoverable:
                # Negative acknowledgment and requeue the message for retry
                logger.warning(f"Recoverable error for task {task_id}, requeueing for retry")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            else:
                # Non-recoverable error, acknowledge to remove from queue
                logger.warning(f"Non-recoverable error for task {task_id}, acknowledging to prevent redelivery")
                ch.basic_ack(delivery_tag=method.delivery_tag)

                # Attempt to update the task to failed state via API
                try:
                    if message_data.get('assistant_task_id'):
                        # Update message status via API
                        await self.update_task_status(
                            message_data.get('assistant_task_id'),
                            TaskStatus.FAILED,
                            f"Processing error: {str(e)}",
                            project_id=message_data.get('project_id'),
                            agent_id=message_data.get('agent_id')
                        )
                except Exception as api_error:
                    logger.error(f"Failed to update task status via API: {str(api_error)}")
                    # Still acknowledge the message even if API update fails

    async def process_task(self, task_id: str, message_data: dict[str, Any]):
        """Process a message using the data understanding workflow."""
        # No need to initialize database connection as we're using API calls

        try:
            
            # Extract message IDs and data
            user_task_id = message_data.get('task_id')
            assistant_task_id = message_data.get('assistant_task_id')
            user_content = message_data.get('content', '')
            project_id = message_data.get('project_id')
            agent_id = message_data.get('agent_id')

            # Validate required fields
            if not all([user_task_id, assistant_task_id, user_content, project_id, agent_id]):
                logger.error(f"Missing required data in task: {message_data}")
                return

            # Update assistant task to processing status via API
            await self.update_task_status(assistant_task_id, TaskStatus.PROCESSING, project_id=project_id, agent_id=agent_id)

            # Set PROJECT environment variable - always use lowercase for directory naming consistency
            task_project = project_id.lower()

            # Sync project data from S3/MinIO to local filesystem
            # This ensures the agent has access to uploaded files (CSV, Excel, etc.)
            logger.info(f"Syncing project data from S3 for project: {project_id}")
            sync_result = self.sync_project_data_from_s3(project_id)
            if sync_result:
                logger.info(f"Successfully synced project data from S3")
            else:
                logger.warning(f"No files synced from S3 (may be empty or already synced)")

            # Process the message with the workflow
            logger.info(f"Processing message pair - user: {user_task_id}, assistant: {assistant_task_id}")

            # Extract thread_id, checkpoint_ns, checkpoint_id, and other settings from metadata if available
            metadata = message_data.get('metadata', {})
            thread_id = metadata.get('thread_id', assistant_task_id)
            checkpoint_ns = metadata.get('checkpoint_ns')
            checkpoint_id = metadata.get('checkpoint_id')

            # Extract stream and Redis publishing settings from metadata
            stream_response = metadata.get('stream', True)
            redis_publishing_enabled = metadata.get('redis_publishing_enabled', False)

            # Log what we're using
            logger.info(f"Using thread_id: {thread_id}")
            if checkpoint_ns and checkpoint_id:
                logger.info(f"Using checkpoint data: ns={checkpoint_ns}, id={checkpoint_id}")
            if stream_response:
                logger.info("Streaming mode enabled - will capture question breakdown and thinking states")

            # Get agent configuration (instructions, description, output format) from the API
            agent_info = await self.get_agent_info(agent_id, project_id)
            logger.info(f"Retrieved agent configuration: {agent_info.get('name')}")
            if agent_info.get('description'):
                logger.info(f"Agent description: {agent_info.get('description')[:50]}...")
            if agent_info.get('instructions'):
                logger.info(f"Using custom agent instructions: {agent_info.get('instructions')[:50]}...")
            logger.info(f"Using output format: {agent_info.get('output_format', 'text')}")

            # Determine which project to use in workflow config (allow override)
            override_project_id_value = metadata.get('override_project_id')
            project_for_config = (override_project_id_value or project_id or "").lower()

            # Initialize a fresh workflow client. Tools are configured using override_project_id if provided.
            agent_backend_app = await self.get_workflow_client(task_project, agent_id, override_project_id=project_for_config)
            logger.info(f"Using workflow client for agent: {agent_id}, project: {task_project}")

            # Run the workflow with thread and checkpoint information
            # Use same workflow for all projects including Mezmo
            response_data = await self.run_data_understanding_workflow(
                agent_backend_app,
                user_content,
                project_id,
                thread_id=thread_id,
                checkpoint_ns=checkpoint_ns,
                checkpoint_id=checkpoint_id,
                stream=stream_response,
                redis_publishing_enabled=redis_publishing_enabled,
                assistant_task_id=assistant_task_id,
                agent_name=agent_info.get('name'),
                agent_instructions=agent_info.get('instructions'),
                agent_description=agent_info.get('description'),
                output_format=agent_info.get('output_format', 'text'),
                agent_id=agent_id,
                override_project_id=project_for_config,
            )

            # Get the JSON response
            json_response = response_data

            # Parse the JSON response
            try:
                # Check if the response is already a JSON string
                if isinstance(json_response, str):
                    response_obj = json.loads(json_response)
                    response_text = response_obj.get('response', '')
                else:
                    # If not a string, assume it's already parsed or it's the old format
                    logger.warning(f"Response is not a JSON string: {type(json_response)}")
                    response_text = str(json_response)
                    # Create a valid response object
                    response_obj = {
                        "response": response_text
                    }
            except json.JSONDecodeError as je:
                logger.error(f"Error parsing JSON response: {str(je)}")
                # Fall back to treating it as plain text
                response_text = str(json_response)
                response_obj = {
                    "response": response_text
                }

            if response_text:
                # Use the response object as our final response
                final_response = response_obj

                # Convert the Python object to a JSON string before storing it
                json_string = json.dumps(final_response)
                logger.info(f"Storing response as JSON string")
                
                # Check if the task was cancelled - don't update to COMPLETED if cancelled
                # Check both the 'cancelled' flag and the response text
                is_cancelled = (
                    response_obj.get('cancelled') or 
                    response_text == TASK_CANCELLED_MESSAGE or
                    "Task was cancelled" in str(response_text)
                )
                
                if is_cancelled:
                    logger.info(f"Task {assistant_task_id} was cancelled, updating response but keeping CANCELLED status")
                    # Store the cancellation response but keep status as CANCELLED
                    await self.update_task_status(assistant_task_id, TaskStatus.CANCELLED, json_string, project_id=project_id, agent_id=agent_id)
                else:
                    await self.update_task_status(assistant_task_id, TaskStatus.COMPLETED, json_string, project_id=project_id, agent_id=agent_id)

                logger.info(f"Successfully processed message pair - user: {user_task_id}, assistant: {assistant_task_id}")
            else:
                # Check if task was cancelled before marking as FAILED
                current_task_status = await self.get_task_status(project_id, agent_id, assistant_task_id)
                if current_task_status == TaskStatus.CANCELLED.value:
                    logger.info(f"Task {assistant_task_id} was cancelled (empty response), not updating status")
                else:
                    # Update assistant task to FAILED status via API
                    error_response = {
                        "response": "Failed to generate response",
                        "error": True
                    }
                    await self.update_task_status(
                        assistant_task_id,
                        TaskStatus.FAILED,
                        json.dumps(error_response),
                        project_id=project_id,
                        agent_id=agent_id
                    )
                    logger.error(f"Failed to generate response for assistant task {assistant_task_id}")

        except Exception as e:
            logger.exception(f"Error processing task {task_id}: {str(e)}")

            # Try to update assistant task status via API if we have the ID
            assistant_id = message_data.get('assistant_task_id')
            if assistant_id:
                error_response = {
                    "response": f"Error processing message: {str(e)}",
                    "error": True,
                    "error_details": str(e)
                }
                await self.update_task_status(
                    assistant_id,
                    TaskStatus.FAILED,
                    json.dumps(error_response),
                    project_id=project_id,
                    agent_id=agent_id
                )

    async def run_data_understanding_workflow(self, agent_backend_app, question: str, project_id: str, thread_id: str = None,
                                              checkpoint_ns: str = None, checkpoint_id: str = None, stream: bool = True,
                                              redis_publishing_enabled: bool = True, assistant_task_id: str = None, agent_name: str = None, agent_instructions: str = None,
                                              agent_description: str = None, output_format: str = "text", agent_id: str = None,
                                              override_project_id: Optional[str] = None):
        """Run the data understanding workflow with the given question.

        Args:
            agent_backend_app: The workflow application instance
            question: The user question to process
            project_id: The project ID for context
            thread_id: Optional thread ID for conversation tracking
            checkpoint_ns: Optional checkpoint namespace
            checkpoint_id: Optional checkpoint ID
            stream: Whether to stream responses (default: True)
            assistant_task_id: ID of the assistant task to update during streaming
            agent_name: Name of the agent processing the request
            agent_instructions: Optional custom instructions for the agent
            agent_description: Optional description of the agent's purpose and capabilities
            output_format: Expected format for the agent's output (default: text)

        Returns:
            The generated response text
        """

        # Build context from agent instructions and details
        context = "Agent Details:"
        if agent_name:
            context += f"\nAgent Name: {agent_name}"
        else:
            context += "\n"
        if agent_description:
            context += f"\nAgent Description: {agent_description}"
        else:
            context += "\n"
        if agent_instructions:
            context += f"\nAgent Instructions: \n{agent_instructions}"
        else:
            context += "\n"

        # Invoke the workflow
        logger.info(f"Running workflow with question: {question}")

        try:
            # Check if task has been cancelled before starting the workflow
            if assistant_task_id is not None:
                task_status = await self.get_task_status(project_id, agent_id, assistant_task_id)
                if task_status == TaskStatus.CANCELLED.value:
                    logger.info(f"Task {assistant_task_id} has been cancelled before workflow started. Aborting.")
                    cancellation_response = {
                        "response": TASK_CANCELLED_MESSAGE,
                        "cancelled": True
                    }
                    return json.dumps(cancellation_response)
            
            # Prepare inputs for the workflow with agent-specific configuration
            inputs = {
                 "question": question.strip(),
                 "context_flag": True,
                 "context": context,
                 "output_format": output_format
            }

            # Use override_project_id for configuration if provided
            config_project_id = (override_project_id or project_id).lower()
            
            # Fetch agent environment variables
            env_variables = {}
            if agent_id:
                try:
                    env_variables = await self.get_agent_env_variables(config_project_id, agent_id)
                    if env_variables:
                        logger.info(f"Loaded {len(env_variables)} environment variables for agent {agent_id}")
                except Exception as e:
                    logger.warning(f"Failed to fetch environment variables for agent {agent_id}: {e}")
            
            # Remove user-provided ANTHROPIC_API_KEY if present - system key takes precedence
            if "ANTHROPIC_API_KEY" in env_variables:
                logger.warning("User-provided ANTHROPIC_API_KEY ignored - using project's configured key")
                del env_variables["ANTHROPIC_API_KEY"]
            
            # Add Anthropic API key from project data sources
            anthropic_api_key = await self.get_anthropic_api_key(config_project_id)
            if anthropic_api_key:
                env_variables["ANTHROPIC_API_KEY"] = anthropic_api_key
                logger.debug("Added ANTHROPIC_API_KEY to environment variables")

            # Add configuration for thread tracking and checkpointing - similar to main_slack.py
            config = {
                "recursion_limit": 50,  # Increased for more complex queries
                "handle_parsing_errors": True,
                "configurable": {
                    "thread_id": thread_id or f"chat-{project_id}",
                    "assistant_task_id": assistant_task_id,
                    "thread_ts": datetime.now().isoformat(),
                    "client": "chat-api",
                    "user": "chat-bot",
                    "project": project_id,
                    "redis_publishing_enabled": redis_publishing_enabled,
                    "env_variables": env_variables,  # Pass env variables to Claude Code SDK
                }
            }

            # Include a separate override_project_id field if provided
            if override_project_id:
                try:
                    config["configurable"]["override_project_id"] = override_project_id.lower()
                except Exception as _e:
                    logger.warning(f"Unable to set override_project_id in config: {_e}")

            # Add checkpoint information if provided
            if checkpoint_ns and checkpoint_id:
                config["configurable"]["checkpoint_ns"] = checkpoint_ns
                config["configurable"]["checkpoint_id"] = checkpoint_id
                logger.info(f"Using checkpoint data: ns={checkpoint_ns}, id={checkpoint_id}")

            # Initialize response data
            full_response = ""

            # Track the incremental states of processing for streaming updates
            thinking_content = ""
            breakdown_content = ""
            extraction_content = ""
            answer_content = ""
            current_state = "starting"

            # Keep track of the full response history for final message
            # Use keys that match the actual graph nodes in adaptive_rag.py
            full_response_history = {
                'question': "",         # Original question
                'breakdown': "",       # Question breakdown
                'data_summary': "",    # Data summary
                'documents': "",       # Retrieved documents
                'related_context': "", # Related context
                'generation': "",      # Generated content
                'error': ""            # Any errors
            }

            # No need to initialize database connection as we're using the API

            if stream:
                # Stream the response and update the assistant task in real-time
                logger.info("Using streaming mode for detailed analysis")
                try:
                    # Create cancellation check callback for Claude Code
                    async def check_cancellation() -> bool:
                        """Check if the task has been cancelled."""
                        if assistant_task_id is None:
                            return False
                        try:
                            task_status = await self.get_task_status(project_id, agent_id, assistant_task_id)
                            return task_status == TaskStatus.CANCELLED.value
                        except Exception as e:
                            logger.warning(f"Error checking task cancellation status: {e}")
                            return False
                    
                    # Create the async generator for streaming with cancellation callback
                    stream_generator = agent_backend_app.astream(inputs, config=config, cancellation_check=check_cancellation)
                    
                    async for event in stream_generator:
                        # Check if task has been cancelled before processing each event
                        if assistant_task_id is not None:
                            task_status = await self.get_task_status(project_id, agent_id, assistant_task_id)
                            if task_status == TaskStatus.CANCELLED.value:
                                logger.info(f"Task {assistant_task_id} has been cancelled. Stopping workflow execution.")
                                
                                # Close the async generator to stop LangGraph execution
                                try:
                                    await stream_generator.aclose()
                                    logger.info("Successfully closed LangGraph stream generator")
                                except Exception as close_error:
                                    logger.warning(f"Error closing stream generator: {close_error}")
                                
                                # Return early with cancellation message
                                cancellation_response = {
                                    "response": TASK_CANCELLED_MESSAGE,
                                    "cancelled": True
                                }
                                return json.dumps(cancellation_response)
                        
                        for key, value in event.items():
                            # Log the key for debugging
                            logger.debug(f"Node '{key}' received")

                            if assistant_task_id is not None:
                                # Prepare the streaming update based on the current state
                                streaming_update = None

                                # Handle any key that comes from the workflow
                                # Add the content to our history dictionary if it's a string or can be converted to one
                                if isinstance(value, (str, dict, list)) or value is not None:
                                    # Convert to string representation for storage
                                    content = value

                                    # Store in our history with the original key
                                    full_response_history[key] = content

                                    # Update current state based on the key we're processing
                                    current_state = key

                                    # Special cases for commonly expected keys
                                    if key:
                                        full_response = content
                                        logger.info(f"{key.capitalize()}: {len(content)} chars")
                                    elif key == 'error':
                                        logger.warning(f"Error in workflow: {content}")
                                    else:
                                        logger.info(f"{key.capitalize()}: {len(content)} chars")

                                    # Create a complete response with all the history so far
                                    streaming_update = self._build_complete_response(full_response_history, current_state)

                                # Skip suggested follow-up questions
                                if key == 'suggested_questions' and value:
                                    logger.debug(f"Skipping suggested questions")

                                # Check for completion state triggers (final response)
                                if key in ['generation', 'answer'] or (isinstance(value, dict) and 'response' in value):
                                    current_state = "completed"

                                # Update the assistant task with the latest streaming content
                                if streaming_update:
                                    # Use a special status for streaming updates
                                    update_status = TaskStatus.PROCESSING
                                    # For the final completed state, mark as completed
                                    # But first check if task was cancelled to avoid overwriting cancelled status
                                    if current_state == "completed":
                                        # Re-check task status before marking as completed
                                        current_task_status = await self.get_task_status(project_id, agent_id, assistant_task_id)
                                        if current_task_status != TaskStatus.CANCELLED.value:
                                            update_status = TaskStatus.COMPLETED
                                        else:
                                            logger.info(f"Task {assistant_task_id} was cancelled, not updating to COMPLETED")
                                            continue  # Skip this update

                                    # Send the streaming update via API
                                    await self.update_task_status(
                                        assistant_task_id,
                                        update_status,
                                        streaming_update,
                                        project_id=project_id,
                                        agent_id=agent_id
                                    )
                                    logger.debug(f"Updated assistant task with {current_state} content")

                    # If we get here without a response, return what we have
                    # Extract just the string content from generation key if it exists
                    if isinstance(full_response, dict) and 'generation' in full_response:
                        response_text = full_response['generation']
                    else:
                        response_text = full_response if full_response else "Analysis completed but no specific response was generated."

                    # Create a proper JSON response object
                    response_json = {
                        "response": response_text
                    }
                    # Return serialized JSON string
                    return json.dumps(response_json)
                except Exception as stream_error:
                    logger.error(f"Error during streaming: {str(stream_error)}")
                    raise
            else:
                # Get the output from the workflow as a single response
                logger.info("Using single invoke mode (non-streaming)")
                output = await agent_backend_app.ainvoke(inputs, config=config)

                # Extract the response text from the output (different formats)
                if isinstance(output, dict):
                    if 'answer' in output:
                        response_text = output["answer"]
                    elif 'generation' in output:
                        response_text = output["generation"]
                    elif 'data_summary' in output:
                        response_text = str(output["data_summary"])
                    elif 'response' in output:
                        response_text = output["response"]
                    else:
                        # Return the whole output as a string if we can't find a response field
                        response_text = str(output)

                    # Skip suggested follow-up questions
                    pass
                else:
                    # The output is likely a string already
                    response_text = str(output)

                # Extract just the generation content if available
                if isinstance(response_text, dict) and 'generation' in response_text:
                    response_text = response_text['generation']

                # Ensure response text is clean
                if isinstance(response_text, str):
                    response_text = response_text.strip()

                # Create a proper JSON response object
                response_json = {
                    "response": response_text
                }

                # Return serialized JSON string
                return json.dumps(response_json)

        except Exception as e:
            logger.exception(f"Error running workflow: {str(e)}")
            raise

    def start_consumer(self):
        """
        Start consuming messages from the RabbitMQ queue
        """
        # Set up initial variables
        connection = None
        channel = None
        reconnect_delay = 5  # Start with 5 seconds delay
        max_reconnect_delay = 60  # Maximum delay of 60 seconds
        queue_name = os.getenv("AGENT_QUEUE_NAME", "agent_tasks_queue")

        # Set up message consumption
        # Set visibility timeout via consumer configuration
        # Consumer will have sole access to the message during processing
        visibility_timeout = int(os.getenv("RABBITMQ_VISIBILITY_TIMEOUT", "7200"))  # 2 hours default

        logger.info(f"Setting RabbitMQ message visibility timeout to {visibility_timeout} seconds")

        # Initial connection setup
        try:
            connection, channel = self.setup_rabbitmq_consumer()
        except Exception as e:
            logger.error(f"Failed to establish initial RabbitMQ connection: {str(e)}")
            # Let the exception propagate to trigger container restart
            raise

        def callback(ch, method, properties, body):
            # Run the coroutine in the event loop
            try:
                asyncio.run(self.process_inference_message(ch, method, properties, body))
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
                # Acknowledge the message even if processing fails, to avoid infinite retry loops
                # This is a safety measure since we should already be acknowledging in process_inference_message
                try:
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                except Exception as ack_error:
                    logger.error(f"Failed to acknowledge message after error: {str(ack_error)}")

        # Start consuming messages with extended visibility timeout
        channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=False)

        logger.info(f"Started consuming messages from queue: {queue_name}")
        logger.info("Waiting for training job messages. Press CTRL+C to exit.")

        try:
            # Start consuming in a loop that checks for shutdown flag
            while not shutdown_flag:
                if not connection or not connection.is_open:
                    # If connection is not available, try to reconnect
                    try:
                        logger.info("Attempting to reconnect to RabbitMQ...")
                        # Close the old connection if it's still around
                        if connection and connection.is_open:
                            try:
                                connection.close()
                            except Exception as close_error:
                                logger.warning(f"Error closing old connection: {str(close_error)}")

                        # Set up a fresh connection
                        connection, channel = self.setup_rabbitmq_consumer()
                        channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=False)
                        logger.info("Successfully reconnected to RabbitMQ")
                        reconnect_delay = 5  # Reset delay after successful reconnection
                    except Exception as reconnect_error:
                        logger.error(f"Failed to reconnect: {str(reconnect_error)}")
                        # Implement exponential backoff for reconnect attempts
                        logger.info(f"Waiting {reconnect_delay} seconds before trying again")
                        time.sleep(reconnect_delay)
                        # Increase delay for next attempt, up to max_reconnect_delay
                        reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
                        continue  # Skip to next iteration after reconnect attempt

                try:
                    # Process messages but don't block indefinitely
                    connection.process_data_events(time_limit=1.0)
                    time.sleep(0.1)
                except (pika.exceptions.AMQPError, KeyboardInterrupt, ConnectionError, OSError) as e:
                    logger.warning(f"Connection issue: {str(e)}")
                    if not shutdown_flag:
                        # Mark the connection as closed to trigger reconnect on next iteration
                        if connection and connection.is_open:
                            try:
                                connection.close()
                            except Exception as close_error:
                                logger.warning(f"Error closing problematic connection: {str(close_error)}")
                        connection = None
                        channel = None
                        # Wait before trying again, but don't increase delay yet
                        time.sleep(reconnect_delay)
        except KeyboardInterrupt:
            logger.info("Interrupted by user, shutting down...")
        finally:
            # Clean up
            if connection and connection.is_open:
                try:
                    connection.close()
                    logger.info("RabbitMQ connection closed")
                except Exception as e:
                    logger.error(f"Error closing connection: {str(e)}")


def main():
    """Main entry point for the inference managed service"""
    try:
        # Initialize the inference job manager
        manager = InferenceJobManager()
        
        # Start consuming messages
        manager.start_consumer()
    except Exception as e:
        logger.error(f"Main process error: {str(e)}", exc_info=True)
        # Exit with error code
        sys.exit(1)


if __name__ == "__main__":
    main()
