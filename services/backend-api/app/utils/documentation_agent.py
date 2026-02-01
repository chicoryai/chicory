"""
Documentation agent creation and management utilities.
Uses atomic upsert pattern to prevent race conditions.
"""
import uuid
import logging
from datetime import datetime
from typing import Tuple
from pymongo import ReturnDocument
from fastapi import HTTPException
from app.models.project import Project
from app.models.agent import Agent

logger = logging.getLogger(__name__)

DOCUMENTATION_AGENT_NAME = "_chicory_documentation_agent"

DOCUMENTATION_AGENT_PROMPT = """You are a documentation generation agent for the Chicory platform.

Your task is to generate comprehensive project documentation (CLAUDE.md) based on the
scanned data sources, code repositories, and documents available in the project context.

## Your Context Directory
You have access to a READ-ONLY context directory containing scanned project data.
**IMPORTANT**: Before generating documentation, you MUST explore and read the available context files.

Key locations to examine (relative to your context directory):
- `raw/data/database_metadata/` - Database schema information (tables, columns, types)
  - `providers/bigquery/tables/**/*.json` - BigQuery table schemas
  - `providers/databricks/tables/**/*.json` - Databricks table schemas
  - `providers/snowflake/tables/**/*.json` - Snowflake table schemas
  - `providers/redshift/tables/**/*.json` - Redshift table schemas
- `raw/code/` - Scanned code repositories
- `raw/documents/` - Scanned documents (PDFs, markdown, etc.)
- `raw/data/` - Uploaded data files (CSV, Excel)

## Required Steps
1. First, explore the context directory to find available data
2. Read the database schema JSON files to understand the data structures
3. Look for README files or documentation in the code directories
4. Output the complete documentation as your response

## CRITICAL OUTPUT REQUIREMENT
**YOUR FINAL RESPONSE MUST BE THE COMPLETE MARKDOWN DOCUMENTATION.**
Do NOT write files. Do NOT provide a summary of what you generated.
The ENTIRE markdown document should be your response text.

## Output Format
Generate markdown documentation that includes:
1. **Project Overview** - What this project is about based on the data you found
2. **Data Sources** - Detailed schemas with table names, column names, and data types
3. **Architecture** - Key components and their relationships
4. **Key Concepts** - Important domain terminology and patterns found in the data
5. **Usage Guidelines** - How to work with this project's data

## Guidelines
- Be concise but comprehensive
- **YOU MUST READ THE ACTUAL FILES** before generating - do not produce generic documentation
- Include specific table names, column names, and data types from the schema files
- Structure content for AI agent consumption (clear, well-organized)
- Include relevant code snippets and examples where helpful
- **OUTPUT THE FULL DOCUMENTATION AS YOUR RESPONSE - DO NOT WRITE TO FILES**
"""


async def get_or_create_documentation_agent(project_id: str) -> Tuple[str, str]:
    """
    Get or create the documentation agent for a project.
    Uses atomic upsert to prevent race conditions.
    Also updates existing agents with the latest instructions.

    Args:
        project_id: The project ID to get/create the documentation agent for

    Returns:
        Tuple of (documentation_agent_id, project_id)

    Raises:
        HTTPException: If project not found
    """
    project = await Project.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    agent_collection = Agent.get_motor_collection()
    now = datetime.utcnow()
    new_id = str(uuid.uuid4())

    # Atomic upsert with instruction updates for existing agents
    # $setOnInsert only runs on insert, $set runs on both insert and update
    result = await agent_collection.find_one_and_update(
        {
            "project_id": project_id,
            "name": DOCUMENTATION_AGENT_NAME,
            "is_system_agent": True
        },
        {
            "$setOnInsert": {
                "_id": new_id,
                "project_id": project_id,
                "name": DOCUMENTATION_AGENT_NAME,
                "is_system_agent": True,
                "output_format": "markdown",
                "state": "enabled",
                "deployed": True,
                "task_count": 0,
                "owner": None,
                "api_key": None,
                "capabilities": [],
                "versions": [],
                "created_at": now,
            },
            # Always update instructions to ensure agents have latest prompt
            "$set": {
                "description": "System agent for generating project documentation",
                "instructions": DOCUMENTATION_AGENT_PROMPT,
                "metadata": {"system": True, "purpose": "documentation_generation"},
                "updated_at": now,
            }
        },
        upsert=True,
        return_document=ReturnDocument.AFTER
    )

    agent_id = str(result["_id"])

    # Update project's cached reference (idempotent)
    await Project.get_motor_collection().update_one(
        {"_id": project_id},
        {"$set": {"documentation_agent_id": agent_id, "updated_at": now}}
    )

    logger.info(f"Using documentation agent {agent_id} for project {project_id}")
    return agent_id, project_id
