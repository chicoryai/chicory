from fastapi import APIRouter

from app.core.config import settings, CHICORY_MCP_TOOLS

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "agent-service"}


@router.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    return {"status": "ready", "service": "agent-service"}


@router.get("/health/mcp")
async def mcp_health_check():
    """
    Check MCP server connectivity and configuration.

    Returns detailed status of the Chicory MCP integration.
    """
    # Check configuration
    mcp_config = settings.get_chicory_mcp_config()
    is_configured = bool(mcp_config)

    # Check connectivity
    is_connected, connection_message = await settings.check_mcp_connection()

    # Build response
    response = {
        "status": "healthy" if is_connected else "unhealthy",
        "service": "agent-service",
        "mcp": {
            "configured": is_configured,
            "connected": is_connected,
            "message": connection_message,
            "base_url": settings.CHICORY_MCP_BASE_URL,
            "endpoint": settings.chicory_mcp_url if is_configured else None,
            "api_key_set": bool(settings.CHICORY_MCP_API_KEY),
            "tools_count": len(CHICORY_MCP_TOOLS) if is_configured else 0,
            "tools": CHICORY_MCP_TOOLS if is_configured else [],
        }
    }

    # Log for debugging
    print(f"[HEALTH] MCP Health Check:")
    print(f"[HEALTH]   configured: {is_configured}")
    print(f"[HEALTH]   connected: {is_connected}")
    print(f"[HEALTH]   message: {connection_message}")
    print(f"[HEALTH]   base_url: {settings.CHICORY_MCP_BASE_URL}")
    print(f"[HEALTH]   api_key_set: {bool(settings.CHICORY_MCP_API_KEY)}")

    return response
