"""
Utilities for task rate limiting
"""
import os
from app.models.tasks import Task, TaskStatus, TaskRole

# Default max concurrent tasks per agent if not specified in environment
DEFAULT_MAX_CONCURRENT_TASKS = 10

async def active_task_details(project_id: str, agent_id: str):
    """
    Get details for active tasks for a specific project and agent
    
    Args:
        project_id: ID of the project
        agent_id: ID of the agent
        
    Returns:
        int: Number of active tasks
        bool: True if max concurrent tasks limit is exceeded, False otherwise
    """
    active_task_count = await Task.find({
        "project_id": project_id,
        "agent_id": agent_id,
        "status": {"$in": [TaskStatus.QUEUED, TaskStatus.PROCESSING]},
        "role": TaskRole.USER
    }).count()

    max_concurrent = os.getenv("MAX_CONCURRENT_TASKS", DEFAULT_MAX_CONCURRENT_TASKS)
    max_concurrent = int(max_concurrent)

    active_tasks = active_task_count >= max_concurrent

    return active_task_count, active_tasks