"""
Project cleanup utilities for cascade deletion of project resources.

This module handles the deletion of all resources associated with a project,
including S3 objects and database documents.
"""
import os
import logging
from typing import Dict, Any
from datetime import datetime

from app.models.agent import Agent
from app.models.tasks import Task
from app.models.tool import Tool
from app.models.evaluation import Evaluation, EvaluationRun
from app.models.training import Training
from app.models.data_source import DataSource
from app.models.playground import Playground, PlaygroundInvocation
from app.models.workzone import WorkzoneInvocation
from app.models.mcp_gateway import MCPGateway, MCPTool, ToolInvocation
from app.utils.s3_utils import delete_objects_by_prefix

logger = logging.getLogger(__name__)


async def cascade_delete_project_resources(project_id: str) -> Dict[str, Any]:
    """
    Delete all resources associated with a project.
    
    This function runs as a background task after the project document is deleted.
    It handles:
    1. S3 objects under the project prefix (audit trails, uploaded files)
    2. All database documents associated with the project
    
    Args:
        project_id: The ID of the project to clean up
        
    Returns:
        Dict with deletion results and any errors
    """
    logger.info(f"Starting cascade deletion for project {project_id}")
    started_at = datetime.utcnow()
    
    results = {
        "project_id": project_id,
        "started_at": started_at.isoformat(),
        "s3_deletion": {},
        "db_deletions": {},
        "errors": []
    }
    
    # 1. Delete S3 objects under project prefix
    try:
        s3_result = await _delete_project_s3_objects(project_id)
        results["s3_deletion"] = s3_result
        logger.info(f"S3 cleanup for project {project_id}: {s3_result}")
    except Exception as e:
        error_msg = f"S3 cleanup failed: {str(e)}"
        logger.error(f"Project {project_id}: {error_msg}")
        results["errors"].append(error_msg)
    
    # 2. Delete database resources in order (leaf to parent)
    db_deletions = await _delete_project_db_resources(project_id)
    results["db_deletions"] = db_deletions["deletions"]
    results["errors"].extend(db_deletions["errors"])
    
    # Finalize results
    completed_at = datetime.utcnow()
    results["completed_at"] = completed_at.isoformat()
    results["duration_seconds"] = (completed_at - started_at).total_seconds()
    results["status"] = "completed" if not results["errors"] else "partial"
    
    logger.info(f"Cascade deletion for project {project_id} completed in {results['duration_seconds']:.2f}s with status: {results['status']}")
    
    return results


async def _delete_project_s3_objects(project_id: str) -> Dict[str, Any]:
    """
    Delete all S3 objects under the project prefixes.
    
    Deletes objects at:
    - s3://{TASK_AUDIT_TRAIL_S3_BUCKET_NAME}/{project_id.lower()}/  (audit trails)
    - s3://{S3_BUCKET_NAME}/artifacts/{project_id}/  (artifacts)
    
    Args:
        project_id: The project ID
        
    Returns:
        Dict with deletion counts and status per prefix
    """
    results = {
        "audit_trails": {},
        "artifacts": {},
        "total_deleted": 0,
        "total_failed": 0,
        "errors": []
    }
    
    # 1. Delete audit trails: s3://{audit_bucket}/{project_id.lower()}/
    audit_bucket = os.environ.get('TASK_AUDIT_TRAIL_S3_BUCKET_NAME', 'chicory-agents-audit-trails')
    audit_prefix = f"{project_id.lower()}/"
    
    logger.info(f"Deleting S3 audit trails: s3://{audit_bucket}/{audit_prefix}")
    
    try:
        audit_result = await delete_objects_by_prefix(audit_bucket, audit_prefix)
        results["audit_trails"] = audit_result
        results["total_deleted"] += audit_result.get("deleted_count", 0)
        results["total_failed"] += audit_result.get("failed_count", 0)
        results["errors"].extend(audit_result.get("errors", []))
    except Exception as e:
        error_msg = f"Audit trails deletion failed: {str(e)}"
        results["errors"].append(error_msg)
        logger.error(error_msg)
    
    # 2. Delete artifacts: s3://{s3_bucket}/artifacts/{project_id}/
    s3_bucket = os.environ.get('S3_BUCKET_NAME')
    if s3_bucket:
        artifacts_prefix = f"artifacts/{project_id}/"
        
        logger.info(f"Deleting S3 artifacts: s3://{s3_bucket}/{artifacts_prefix}")
        
        try:
            artifacts_result = await delete_objects_by_prefix(s3_bucket, artifacts_prefix)
            results["artifacts"] = artifacts_result
            results["total_deleted"] += artifacts_result.get("deleted_count", 0)
            results["total_failed"] += artifacts_result.get("failed_count", 0)
            results["errors"].extend(artifacts_result.get("errors", []))
        except Exception as e:
            error_msg = f"Artifacts deletion failed: {str(e)}"
            results["errors"].append(error_msg)
            logger.error(error_msg)
    else:
        logger.warning("S3_BUCKET_NAME not set, skipping artifacts deletion")
    
    return results


async def _delete_project_db_resources(project_id: str) -> Dict[str, Any]:
    """
    Delete all database resources associated with a project.
    
    Deletion order (leaf to parent to avoid orphans):
    1. Tool Invocations (via MCP Tools)
    2. MCP Tools (via Gateways)
    3. MCP Gateways
    4. Playground Invocations
    5. Playgrounds
    6. Workzone Invocations
    7. Tasks
    8. Tools (via Agents)
    9. Evaluation Runs
    10. Evaluations
    11. Training Jobs
    12. Data Sources
    13. Agents
    
    Args:
        project_id: The project ID
        
    Returns:
        Dict with deletion counts per resource type and any errors
    """
    deletions = {}
    errors = []
    
    # Initialize ID lists to avoid NameError if early queries fail
    gateway_ids = []
    playground_ids = []
    agent_ids = []
    
    # 1. Delete Tool Invocations via MCP Tools via Gateways
    try:
        gateways = await MCPGateway.find({"project_id": project_id}).to_list()
        gateway_ids = [g.id for g in gateways]
        
        if gateway_ids:
            mcp_tools = await MCPTool.find({"gateway_id": {"$in": gateway_ids}}).to_list()
            tool_ids = [t.id for t in mcp_tools]
            
            if tool_ids:
                invocation_result = await ToolInvocation.find({"tool_id": {"$in": tool_ids}}).delete()
                deletions["tool_invocations"] = invocation_result.deleted_count if invocation_result else 0
                logger.info(f"Deleted {deletions['tool_invocations']} tool invocations")
            else:
                deletions["tool_invocations"] = 0
        else:
            deletions["tool_invocations"] = 0
    except Exception as e:
        deletions["tool_invocations"] = 0
        errors.append(f"Tool invocations deletion failed: {str(e)}")
        logger.error(f"Project {project_id}: {errors[-1]}")
    
    # 2. Delete MCP Tools via Gateways
    try:
        if gateway_ids:
            mcp_tools_result = await MCPTool.find({"gateway_id": {"$in": gateway_ids}}).delete()
            deletions["mcp_tools"] = mcp_tools_result.deleted_count if mcp_tools_result else 0
            logger.info(f"Deleted {deletions['mcp_tools']} MCP tools")
        else:
            deletions["mcp_tools"] = 0
    except Exception as e:
        deletions["mcp_tools"] = 0
        errors.append(f"MCP tools deletion failed: {str(e)}")
        logger.error(f"Project {project_id}: {errors[-1]}")
    
    # 3. Delete MCP Gateways
    try:
        gateways_result = await MCPGateway.find({"project_id": project_id}).delete()
        deletions["mcp_gateways"] = gateways_result.deleted_count if gateways_result else 0
        logger.info(f"Deleted {deletions['mcp_gateways']} MCP gateways")
    except Exception as e:
        deletions["mcp_gateways"] = 0
        errors.append(f"MCP gateways deletion failed: {str(e)}")
        logger.error(f"Project {project_id}: {errors[-1]}")
    
    # 4. Delete Playground Invocations via Playgrounds
    try:
        playgrounds = await Playground.find({"project_id": project_id}).to_list()
        playground_ids = [p.id for p in playgrounds]
        
        if playground_ids:
            pg_invocations_result = await PlaygroundInvocation.find({"playground_id": {"$in": playground_ids}}).delete()
            deletions["playground_invocations"] = pg_invocations_result.deleted_count if pg_invocations_result else 0
            logger.info(f"Deleted {deletions['playground_invocations']} playground invocations")
        else:
            deletions["playground_invocations"] = 0
    except Exception as e:
        deletions["playground_invocations"] = 0
        errors.append(f"Playground invocations deletion failed: {str(e)}")
        logger.error(f"Project {project_id}: {errors[-1]}")
    
    # 5. Delete Playgrounds
    try:
        playgrounds_result = await Playground.find({"project_id": project_id}).delete()
        deletions["playgrounds"] = playgrounds_result.deleted_count if playgrounds_result else 0
        logger.info(f"Deleted {deletions['playgrounds']} playgrounds")
    except Exception as e:
        deletions["playgrounds"] = 0
        errors.append(f"Playgrounds deletion failed: {str(e)}")
        logger.error(f"Project {project_id}: {errors[-1]}")
    
    # 6. Delete Workzone Invocations (Workzones are org-level, only delete invocations)
    try:
        wz_invocations_result = await WorkzoneInvocation.find({"project_id": project_id}).delete()
        deletions["workzone_invocations"] = wz_invocations_result.deleted_count if wz_invocations_result else 0
        logger.info(f"Deleted {deletions['workzone_invocations']} workzone invocations")
    except Exception as e:
        deletions["workzone_invocations"] = 0
        errors.append(f"Workzone invocations deletion failed: {str(e)}")
        logger.error(f"Project {project_id}: {errors[-1]}")
    
    # 7. Delete Tasks
    try:
        tasks_result = await Task.find({"project_id": project_id}).delete()
        deletions["tasks"] = tasks_result.deleted_count if tasks_result else 0
        logger.info(f"Deleted {deletions['tasks']} tasks")
    except Exception as e:
        deletions["tasks"] = 0
        errors.append(f"Tasks deletion failed: {str(e)}")
        logger.error(f"Project {project_id}: {errors[-1]}")
    
    # 8. Delete Tools via Agents
    try:
        agents = await Agent.find({"project_id": project_id}).to_list()
        agent_ids = [a.id for a in agents]
        
        if agent_ids:
            tools_result = await Tool.find({"agent_id": {"$in": agent_ids}}).delete()
            deletions["tools"] = tools_result.deleted_count if tools_result else 0
            logger.info(f"Deleted {deletions['tools']} tools")
        else:
            deletions["tools"] = 0
    except Exception as e:
        deletions["tools"] = 0
        errors.append(f"Tools deletion failed: {str(e)}")
        logger.error(f"Project {project_id}: {errors[-1]}")
    
    # 9. Delete Evaluation Runs
    try:
        eval_runs_result = await EvaluationRun.find({"project_id": project_id}).delete()
        deletions["evaluation_runs"] = eval_runs_result.deleted_count if eval_runs_result else 0
        logger.info(f"Deleted {deletions['evaluation_runs']} evaluation runs")
    except Exception as e:
        deletions["evaluation_runs"] = 0
        errors.append(f"Evaluation runs deletion failed: {str(e)}")
        logger.error(f"Project {project_id}: {errors[-1]}")
    
    # 10. Delete Evaluations
    try:
        evaluations_result = await Evaluation.find({"project_id": project_id}).delete()
        deletions["evaluations"] = evaluations_result.deleted_count if evaluations_result else 0
        logger.info(f"Deleted {deletions['evaluations']} evaluations")
    except Exception as e:
        deletions["evaluations"] = 0
        errors.append(f"Evaluations deletion failed: {str(e)}")
        logger.error(f"Project {project_id}: {errors[-1]}")
    
    # 11. Delete Training Jobs
    try:
        training_result = await Training.find({"project_id": project_id}).delete()
        deletions["training_jobs"] = training_result.deleted_count if training_result else 0
        logger.info(f"Deleted {deletions['training_jobs']} training jobs")
    except Exception as e:
        deletions["training_jobs"] = 0
        errors.append(f"Training jobs deletion failed: {str(e)}")
        logger.error(f"Project {project_id}: {errors[-1]}")
    
    # 12. Delete Data Sources
    try:
        data_sources_result = await DataSource.find({"project_id": project_id}).delete()
        deletions["data_sources"] = data_sources_result.deleted_count if data_sources_result else 0
        logger.info(f"Deleted {deletions['data_sources']} data sources")
    except Exception as e:
        deletions["data_sources"] = 0
        errors.append(f"Data sources deletion failed: {str(e)}")
        logger.error(f"Project {project_id}: {errors[-1]}")
    
    # 13. Delete Agents
    try:
        agents_result = await Agent.find({"project_id": project_id}).delete()
        deletions["agents"] = agents_result.deleted_count if agents_result else 0
        logger.info(f"Deleted {deletions['agents']} agents")
    except Exception as e:
        deletions["agents"] = 0
        errors.append(f"Agents deletion failed: {str(e)}")
        logger.error(f"Project {project_id}: {errors[-1]}")
    
    return {"deletions": deletions, "errors": errors}
