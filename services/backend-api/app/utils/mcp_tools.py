"""
Utility functions for working with MCP servers and tools.
This module provides shared functionality for connecting to and fetching tools from MCP servers.
"""
from typing import List, Dict, Any, Optional
import logging
from langchain_mcp_adapters.client import MultiServerMCPClient

# Configure logging
logger = logging.getLogger(__name__)

async def fetch_tools_from_mcp_server(
    server_url: str, 
    server_name: str, 
    headers: Optional[Dict[str, str]] = None,
    transport: str = "streamable_http"
) -> List[Dict[str, Any]]:
    """Fetch tools from a single MCP server using MCP client
    
    Parameters
    ----------
    server_url : str
        URL of the MCP server
    server_name : str
        Name to identify the server in logs and configuration
    headers : Optional[Dict[str, str]]
        Optional headers to include in the request
    transport : str
        Transport protocol to use, defaults to "streamable_http"
        
    Returns
    -------
    List[Dict[str, Any]]
        List of tools from the MCP server in dictionary format
    """
    # Use provided headers or default to empty dict
    headers = headers or {}
        
    try:
        # Create MCP client configuration
        mcp_config = {
            server_name: {
                "url": server_url,
                "transport": transport,
                "headers": headers
            }
        }
        
        logger.info(f"Connecting to MCP server {server_name} at {server_url}")
        if headers.get("Authorization"):
            logger.info(f"Using authentication headers for {server_name}")
        else:
            logger.info(f"No authentication headers provided for {server_name}")
            
        # Initialize client and get tools
        client = MultiServerMCPClient(mcp_config)
        mcp_tools = await client.get_tools()
        
        logger.info(f"Fetched {len(mcp_tools)} tools from {server_name}: {[tool.name for tool in mcp_tools]}")
        
        # Convert MCP tools to dictionary format
        tools_data = []
        for tool in mcp_tools:
            tool_data = {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.args_schema
            }
            tools_data.append(tool_data)
        
        return tools_data
        
    except Exception as e:
        logger.error(f"Error fetching tools from {server_name}: {str(e)}")
        return []
