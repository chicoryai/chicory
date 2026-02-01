from fastapi import APIRouter

from app.api.routes import (
    projects,
    data_sources,
    folder_uploads,
    training,
    agents,
    tasks,
    tasks_acp,
    tools,
    evaluations,
    mcp_gateway,
    workzones,
    conversations,
)

api_router = APIRouter()

api_router.include_router(projects.router, tags=["projects"])
api_router.include_router(data_sources.router, tags=["data_sources"])
api_router.include_router(folder_uploads.router, tags=["folder_uploads"])
api_router.include_router(training.router, tags=["training"])
api_router.include_router(agents.router, tags=["agents"])
api_router.include_router(tasks.router, tags=["tasks"])
api_router.include_router(tasks_acp.router, tags=["tasks_acp"])
api_router.include_router(tools.router, tags=["tools"])
api_router.include_router(evaluations.router, tags=["evaluations"])
api_router.include_router(mcp_gateway.router, tags=["mcp_gateway"])
api_router.include_router(workzones.router, tags=["workzones"])
api_router.include_router(conversations.router, tags=["conversations"])
