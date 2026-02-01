from fastapi import APIRouter, HTTPException, status, File, UploadFile, Form
from typing import List, Optional, Dict, Any
import asyncio
import os
import pandas as pd
import boto3
import io
import json
import uuid
import yaml
from pathlib import Path, PurePosixPath
from botocore.exceptions import ClientError
import logging
import time
from app.utils.mcp_tools import fetch_tools_from_mcp_server
from app.utils.s3_utils import get_s3_client, delete_folder_upload as s3_delete_folder_upload

from app.models.data_source import (
    DataSource, DataSourceCreate, DataSourceUpdate, DataSourceResponse, DataSourceList, 
    DataSourceType, DataSourceStatus, DataSourceValidationResponse, 
    DataSourceTypeList, DataSourceTypeDefinition, DataSourceFieldDefinition, DataSourceCategory
)
from app.models.project import Project
from app.models.folder_upload import FolderUpload
from app.models.tool import ToolResponse, ToolList
from datetime import datetime
from app.validators.data_sources import validator_factory

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(tags=["data-sources"])


# Environment variables for internal MCP servers
# DB_MCP_SERVER_URL: URL for the database MCP server (e.g., http://db-mcp-server:8000)
# TOOLS_MCP_SERVER_URL: URL for the tools MCP server (e.g., http://tools-mcp-server:8000)
# GITHUB_MCP_SERVER_URL: URL for the GitHub MCP server (e.g., https://api.githubcopilot.com/mcp/)
DB_MCP_SERVER_URL = os.getenv("DB_MCP_SERVER_URL", "")
TOOLS_MCP_SERVER_URL = os.getenv("TOOLS_MCP_SERVER_URL", "")
GITHUB_MCP_SERVER_URL = os.getenv("GITHUB_MCP_SERVER_URL", "https://api.githubcopilot.com/mcp/")

# fetch_tools_from_mcp_server is now imported from app.utils.mcp_tools
async def fetch_data_source_tools(project_id: str) -> List[ToolResponse]:
    """Fetch tools available for project's data sources from internal MCP servers
    
    Uses project-specific MCP endpoints that automatically filter tools based on
    the project's configured data sources.
    
    Parameters
    ----------
    project_id : str
        The project ID to fetch data sources for
        
    Returns
    -------
    List[ToolResponse]
        List of tools available for the project's data sources
    """
    
    # Generate a unique agent ID for MCP tools
    mcp_agent_id = f"mcp_{project_id}"
    
    # Call internal MCP servers using project-specific endpoints
    all_mcp_tools = []
    
    # Try to fetch tools from DB MCP server using /mcp/{project_id} endpoint
    if DB_MCP_SERVER_URL:
        try:
            db_tools = await asyncio.wait_for(
                fetch_tools_from_mcp_server(
                    f"{DB_MCP_SERVER_URL}/mcp/{project_id}",
                    "db_mcp_server"
                ),
                timeout=5.0  # 5 second timeout
            )
            all_mcp_tools.extend(db_tools)
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching tools from DB MCP server for project {project_id}")
        except Exception as e:
            logger.error(f"Error fetching tools from DB MCP server for project {project_id}: {e}")
    
    # Try to fetch tools from Tools MCP server using /mcp/{project_id} endpoint
    if TOOLS_MCP_SERVER_URL:
        try:
            tools_tools = await asyncio.wait_for(
                fetch_tools_from_mcp_server(
                    f"{TOOLS_MCP_SERVER_URL}/mcp/{project_id}",
                    "tools_mcp_server"
                ),
                timeout=5.0  # 5 second timeout
            )
            all_mcp_tools.extend(tools_tools)
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching tools from Tools MCP server for project {project_id}")
        except Exception as e:
            logger.error(f"Error fetching tools from Tools MCP server for project {project_id}: {e}")
    
    # Try to fetch tools from GitHub MCP server
    # GitHub MCP requires authorization token from data source configuration
    if GITHUB_MCP_SERVER_URL:
        try:
            # Find GitHub MCP data source for this project (must be CONNECTED for validated credentials)
            github_datasource = await DataSource.find_one({
                "project_id": project_id,
                "type": DataSourceType.GITHUB,
                "status": DataSourceStatus.CONNECTED
            })
            
            if github_datasource:
                # Extract the GitHub Access Token from configuration
                github_token = github_datasource.configuration.get("access_token")
                
                if github_token :
                    # Prepare authorization headers
                    headers = {
                        "Authorization": f"Bearer {github_token}"
                    }
                    
                    # Fetch tools from GitHub MCP with timeout
                    github_tools = await asyncio.wait_for(
                        fetch_tools_from_mcp_server(
                            GITHUB_MCP_SERVER_URL,
                            "github_mcp_server",
                            headers=headers
                        ),
                        timeout=8.0  # 8 second timeout for external API
                    )
                    all_mcp_tools.extend(github_tools)
                    logger.info(f"Fetched {len(github_tools)} tools from GitHub MCP server")
                else:
                    logger.warning(f"GitHub data source found but no access token configured for project {project_id}")
            else:
                logger.debug(f"No connected GitHub data source found for project {project_id}")
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching tools from GitHub MCP server for project {project_id}")
        except Exception as e:
            logger.error(f"Error fetching tools from GitHub MCP server for project {project_id}: {e}")
    
    if not all_mcp_tools:
        logger.warning(f"No tools found from any MCP server for project {project_id}")
        return []
    
    # MCP servers now return only relevant tools, so no filtering needed
    # Just ensure schema compliance for all tools
    for tool in all_mcp_tools:
        tool_params = tool.get("parameters", {
            "type": "object",
            "properties": {},
            "required": []
        })
        
        # Ensure schema compliance
        tool_params["additionalProperties"] = False
        tool_params["$schema"] = "http://json-schema.org/draft-07/schema#"
        
        # Update the tool with enhanced parameters
        tool["parameters"] = tool_params
    
    # Create a list to hold our tool response
    tools = []
    
    # Combine all tools into a single group
    if all_mcp_tools:
        # Create a single ToolResponse for all MCP tools
        default_tools_response = ToolResponse(
            id="mcp_default_tools",
            agent_id=mcp_agent_id,
            name="default_tools",
            description="Project-specific MCP Tools",
            tool_type="mcp",
            provider="default_mcp",
            config={
                "available_tools": all_mcp_tools
            },
            enabled=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        tools.append(default_tools_response)
    
    logger.info(f"Fetched {len(all_mcp_tools)} tools from MCP servers for project {project_id}")
    return tools



async def upload_file_to_s3(file_data, s3_key, content_type=None):
    """Upload a file to S3
    
    Parameters
    ----------
    file_data : bytes or BytesIO
        The file data to upload
    s3_key : str
        The S3 key to use
    content_type : str, optional
        The content type of the file
        
    Returns
    -------
    dict
        Dictionary with s3_bucket, s3_key, and s3_url
    """
    s3_client, s3_bucket, s3_region = await get_s3_client()
    
    try:
        # If file_data is bytes, convert to BytesIO
        if isinstance(file_data, bytes):
            file_io = io.BytesIO(file_data)
        else:
            file_io = file_data
            
        # Ensure position is at start
        file_io.seek(0)
        
        # Prepare upload args
        upload_args = {}
        if content_type:
            upload_args['ExtraArgs'] = {'ContentType': content_type}
        
        # Upload to S3
        if 'ExtraArgs' in upload_args:
            s3_client.upload_fileobj(
                file_io,
                s3_bucket,
                s3_key,
                ExtraArgs=upload_args['ExtraArgs']
            )
        else:
            s3_client.upload_fileobj(
                file_io,
                s3_bucket,
                s3_key
            )
            
        # Generate S3 URL
        s3_url = f"https://{s3_bucket}.s3.{s3_region}.amazonaws.com/{s3_key}"
        
        return {
            "s3_bucket": s3_bucket,
            "s3_key": s3_key,
            "s3_url": s3_url
        }
    except Exception as e:
        logger.error(f"Error uploading to S3: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file to S3: {str(e)}"
        )


async def delete_object_from_s3(s3_bucket, s3_key):
    """Delete an object from S3
    
    Parameters
    ----------
    s3_bucket : str
        The S3 bucket name
    s3_key : str
        The S3 key to delete
        
    Returns
    -------
    dict
        Dictionary with status and message
    """
    try:
        # Get S3 client
        s3_client, _, _ = await get_s3_client()
        
        # Result dictionary to track status
        result = {
            "status": "success",
            "message": f"Deleted S3 object: s3://{s3_bucket}/{s3_key}"
        }
        
        # Check if object exists first
        try:
            s3_client.head_object(Bucket=s3_bucket, Key=s3_key)
            # Object exists, delete it
            s3_client.delete_object(Bucket=s3_bucket, Key=s3_key)
            logger.info(f"Deleted S3 object: s3://{s3_bucket}/{s3_key}")
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                logger.warning(f"S3 object not found: s3://{s3_bucket}/{s3_key}")
                result["status"] = "warning"
                result["message"] = "S3 object not found"
            else:
                logger.error(f"Error checking S3 object: {str(e)}")
                result["status"] = "error"
                result["message"] = str(e)
        
        return result
    except Exception as e:
        logger.error(f"Error deleting S3 object: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

async def validate_data_source_credentials(data_source: DataSource) -> DataSourceValidationResponse:
    """
    Validate credentials for any data source type
    
    Args:
        data_source: The data source to validate
        
    Returns:
        DataSourceValidationResponse with status and message
    """
    logger.info(f"Validating credentials for {data_source.type} data source {data_source.id}")
    
    # Extract credentials from data source configuration
    if not data_source.configuration:
        logger.error(f"No configuration found for {data_source.type} data source")
        return DataSourceValidationResponse(
            status="error",
            message=f"No configuration found for {data_source.type} data source"
        )
    
    # Extract credentials from the configuration
    credentials = data_source.configuration.get("credentials")
    if not credentials:
        credentials = data_source.configuration
    if not credentials:
        logger.error(f"No credentials found in {data_source.type} data source configuration")
        return DataSourceValidationResponse(
            status="error",
            message=f"No credentials found in {data_source.type} data source configuration"
        )
    
    # Use the validator factory to get the appropriate validator
    try:
        # Run the validation in a separate thread to not block the event loop
        # since validation might use synchronous code (like requests)
        validation_result = await asyncio.to_thread(
            validator_factory.validate,
            data_source.type,
            credentials,
            data_source.project_id
        )
        
        # Update data source status based on validation result
        if validation_result["status"] == "success":
            await data_source.update({"$set": {"status": DataSourceStatus.CONNECTED}})
            return DataSourceValidationResponse(
                status="success",
                message=validation_result["message"]
            )
        else:
            await data_source.update({"$set": {"status": DataSourceStatus.ERROR}})
            return DataSourceValidationResponse(
                status="error",
                message=validation_result["message"]
            )
    except Exception as e:
        logger.error(f"Error validating {data_source.type} credentials: {str(e)}")
        await data_source.update({"$set": {"status": DataSourceStatus.ERROR}})
        return DataSourceValidationResponse(
            status="error",
            message=f"Failed to validate {data_source.type} credentials: {str(e)}"
        )

@router.get("/projects/{project_id}/data-sources/metadata")
async def get_data_source_metadata(project_id: str):
    """Get the raw filesystem tree that agents see in the sandbox.

    Lists all files under {project_id}/raw/ in S3, building an exact
    directory tree mirroring what the agent has access to.
    """
    project = await Project.get(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )

    try:
        s3_client, s3_bucket, s3_region = await get_s3_client()
    except Exception as e:
        logger.error(f"Could not connect to S3: {e}")
        return {"status": "no_scan", "last_scanned_at": None, "providers": []}

    raw_prefix = f"{project_id}/raw/"

    # Collect all S3 objects into a nested dict
    MAX_FILES = 10000
    tree_dict: Dict[str, Any] = {}
    file_count = 0
    tree_truncated = False

    paginator = s3_client.get_paginator('list_objects_v2')
    try:
        for s3_page in paginator.paginate(Bucket=s3_bucket, Prefix=raw_prefix):
            for obj in s3_page.get("Contents", []):
                key = obj["Key"]
                rel_path = key[len(raw_prefix):]
                if not rel_path:
                    continue
                size = obj.get("Size", 0)
                parts = rel_path.split("/")
                file_count += 1

                if file_count > MAX_FILES:
                    logger.warning(f"Project {project_id} has more than {MAX_FILES} files, truncating metadata")
                    tree_truncated = True
                    break

                # Build nested dict: folders are dicts, files are leaf entries
                current = tree_dict
                for i, part in enumerate(parts):
                    if i == len(parts) - 1:
                        current[part] = {"_size": size, "_key": key}
                    else:
                        if part not in current:
                            current[part] = {}
                        elif not isinstance(current[part], dict) or "_key" in current[part]:
                            logger.warning(f"Name collision: '{part}' in {project_id}, overwriting file at key '{current[part].get('_key', 'unknown')}'")
                            current[part] = {}
                        current = current[part]
            if tree_truncated:
                break
    except Exception as e:
        logger.error(f"Error listing S3 objects for {project_id}: {e}")
        return {"status": "no_scan", "last_scanned_at": None, "providers": []}

    if not tree_dict:
        return {"status": "no_scan", "last_scanned_at": None, "providers": []}

    # Convert nested dict to tree nodes
    def dict_to_nodes(d: dict) -> list:
        nodes = []
        for name, value in sorted(d.items()):
            if isinstance(value, dict) and "_key" in value:
                # It's a file
                nodes.append({
                    "name": name,
                    "type": "table",
                    "size_bytes": value.get("_size", 0),
                    "preview_path": value["_key"],
                })
            elif isinstance(value, dict):
                # It's a directory
                children = dict_to_nodes(value)
                nodes.append({
                    "name": name,
                    "type": "folder",
                    "children": children,
                })
            else:
                nodes.append({"name": name, "type": "table"})
        return nodes

    # Build top-level: the children of raw/ become the providers
    providers = []
    for name, value in sorted(tree_dict.items()):
        if isinstance(value, dict) and "_key" not in value:
            children = dict_to_nodes(value)
            providers.append({
                "name": name,
                "type": "provider",
                "children": children,
            })
        elif isinstance(value, dict) and "_key" in value:
            # File at root of raw/
            providers.append({
                "name": name,
                "type": "table",
                "size_bytes": value.get("_size", 0),
                "preview_path": value["_key"],
            })
        else:
            providers.append({"name": name, "type": "table"})

    return {
        "status": "available",
        "last_scanned_at": None,
        "providers": providers,
        "truncated": tree_truncated,
    }


@router.get("/projects/{project_id}/data-sources/preview")
async def get_data_source_preview(
    project_id: str,
    path: Optional[str] = None,
    max_rows: int = 20
):
    """Preview a file from the sandbox by its S3 key.

    Reads the file and returns content based on file type:
    - .json: parsed JSON content (table cards get schema extraction)
    - .csv: column schema + sample data rows
    - .md: markdown content with front matter parsing
    - other: raw text preview
    """
    if not path:
        raise HTTPException(status_code=400, detail="path parameter is required")

    project = await Project.get(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Path traversal protection
    try:
        normalized = PurePosixPath(path)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path format")

    if normalized.is_absolute():
        raise HTTPException(status_code=400, detail="Absolute paths not allowed")
    if any(part == ".." for part in normalized.parts):
        raise HTTPException(status_code=400, detail="Path traversal not allowed")

    normalized_path = str(normalized)

    # Case-sensitive prefix check — the real security boundary.
    # Even if ".." normalization resolves segments, the prefix check ensures
    # the final path stays within this project's S3 namespace.
    expected_prefix = f"{project_id}/"
    if not normalized_path.startswith(expected_prefix):
        raise HTTPException(status_code=403, detail="Path does not belong to this project")

    # Use the normalized path from here on
    path = normalized_path

    if max_rows <= 0:
        raise HTTPException(status_code=400, detail="max_rows must be positive")
    if max_rows > 100:
        raise HTTPException(status_code=400, detail="max_rows cannot exceed 100")

    try:
        s3_client, s3_bucket, _ = await get_s3_client()
        obj = s3_client.get_object(Bucket=s3_bucket, Key=path)
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            raise HTTPException(status_code=404, detail="File not found")
        logger.error(f"S3 error accessing {path}: {str(e)}")
        raise HTTPException(status_code=500, detail="Storage service error")

    file_name = path.split("/")[-1]
    file_size = obj.get("ContentLength", 0)

    # Prevent DoS from very large files
    MAX_PREVIEW_SIZE = 10 * 1024 * 1024  # 10MB
    if file_size > MAX_PREVIEW_SIZE:
        return {
            "type": "binary",
            "name": file_name,
            "size_bytes": file_size,
            "description": f"File too large for preview ({file_size / (1024*1024):.1f}MB). Limit is {MAX_PREVIEW_SIZE // (1024*1024)}MB.",
            "content": "",
            "columns": [],
            "sample_rows": [],
        }

    # --- JSON files ---
    if file_name.endswith(".json"):
        try:
            content = json.loads(obj["Body"].read().decode("utf-8"))
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for {path}: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid JSON format")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="File encoding is not valid UTF-8")
        except Exception as e:
            logger.error(f"Error parsing JSON file {path}: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to parse JSON file")

        # Database table card (has "columns" key)
        if isinstance(content, dict) and "columns" in content:
            columns = content.get("columns", [])
            return {
                "type": "table_card",
                "name": file_name,
                "fqtn": content.get("fqtn", ""),
                "row_count": content.get("row_count"),
                "size_bytes": content.get("size_bytes"),
                "created_date": content.get("created_date"),
                "description": content.get("description", ""),
                "columns": [
                    {
                        "name": c.get("name", ""),
                        "type": c.get("type", ""),
                        "nullable": c.get("nullable", True),
                        "description": c.get("description", ""),
                    }
                    for c in columns
                ],
                "sample_rows": [],
            }

        # Generic JSON — skip pretty-printing for large files to avoid memory spike
        if file_size > 1024 * 1024:  # > 1MB
            formatted = json.dumps(content, default=str)
        else:
            formatted = json.dumps(content, indent=2, default=str)
        is_truncated = len(formatted) > 50000
        return {
            "type": "json",
            "name": file_name,
            "size_bytes": file_size,
            "description": "",
            "columns": [],
            "sample_rows": [],
            "content": formatted[:50000],
            "truncated": is_truncated,
        }

    # --- CSV files ---
    if file_name.endswith(".csv"):
        try:
            csv_bytes = obj["Body"].read()
            # Cheap row count from raw bytes (count newlines, subtract header)
            row_count = max(csv_bytes.count(b'\n') - 1, 0)
            # Read only 1000 rows for schema/nullable detection (approximate but safe)
            df_schema = pd.read_csv(io.BytesIO(csv_bytes), nrows=1000)
            df_sample = df_schema.head(max_rows)
            schema = [
                {
                    "name": col,
                    "type": str(df_schema[col].dtype),
                    "nullable": bool(df_schema[col].isnull().any()),
                    "description": "",
                }
                for col in df_schema.columns
            ]
            sample_rows = df_sample.fillna("").to_dict(orient="records")
        except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as e:
            logger.error(f"CSV parse error for {path}: {e}")
            raise HTTPException(status_code=400, detail="Failed to parse CSV: invalid format")
        except Exception as e:
            logger.error(f"Unexpected error reading CSV {path}: {e}")
            raise HTTPException(status_code=500, detail="Internal error processing CSV")

        return {
            "type": "csv",
            "name": file_name,
            "row_count": row_count,
            "size_bytes": file_size,
            "description": "",
            "columns": schema,
            "sample_rows": sample_rows,
        }

    # --- Markdown files ---
    if file_name.endswith(".md"):
        md_content = obj["Body"].read().decode("utf-8", errors="replace")

        # Parse YAML front matter if present
        title = ""
        source_url = ""
        body = md_content
        if md_content.startswith("---"):
            end = md_content.find("---", 3)
            if end > 0:
                front_matter_raw = md_content[3:end]
                if len(front_matter_raw) > 5000:
                    logger.warning(f"Front matter too large ({len(front_matter_raw)} bytes), skipping YAML parse")
                else:
                    try:
                        front_matter = yaml.safe_load(front_matter_raw)
                        if isinstance(front_matter, dict):
                            title = str(front_matter.get("title", ""))
                            source_url = str(front_matter.get("source", ""))
                    except yaml.YAMLError as e:
                        logger.warning(f"Failed to parse YAML front matter: {e}")
                body = md_content[end + 3:].strip()

        return {
            "type": "markdown",
            "name": title or file_name,
            "source_url": source_url,
            "description": source_url,
            "size_bytes": file_size,
            "content": body[:50000],
            "truncated": len(body) > 50000,
            "columns": [],
            "sample_rows": [],
        }

    # --- Other text files ---
    try:
        text_content = obj["Body"].read().decode("utf-8")
        return {
            "type": "text",
            "name": file_name,
            "size_bytes": file_size,
            "description": "",
            "content": text_content[:50000],
            "truncated": len(text_content) > 50000,
            "columns": [],
            "sample_rows": [],
        }
    except (UnicodeDecodeError, ValueError):
        return {
            "type": "binary",
            "name": file_name,
            "size_bytes": file_size,
            "description": "Binary file — preview not available",
            "content": "",
            "columns": [],
            "sample_rows": [],
        }



@router.get("/data-source-types", response_model=DataSourceTypeList)
async def list_data_source_types():
    """List all available data source types"""
    # Define the available data source types
    data_source_types = [
        DataSourceTypeDefinition(
            id="google_drive",
            name="Google Drive",
            category=DataSourceCategory.DOCUMENT,
            required_fields=[
                DataSourceFieldDefinition(
                    name="project_id",
                    type="string",
                    description="Google Cloud project ID"
                ),
                DataSourceFieldDefinition(
                    name="private_key_id",
                    type="string",
                    description="Service account private key ID"
                ),
                DataSourceFieldDefinition(
                    name="private_key",
                    type="password",
                    description="Service account private key"
                ),
                DataSourceFieldDefinition(
                    name="client_email",
                    type="string",
                    description="Service account client email"
                ),
                DataSourceFieldDefinition(
                    name="client_id",
                    type="string",
                    description="Service account client ID"
                ),
                DataSourceFieldDefinition(
                    name="client_cert_url",
                    type="string",
                    description="Service account client certificate URL"
                ),
                DataSourceFieldDefinition(
                    name="folder_id",
                    type="string",
                    description="Google Drive folder ID to access"
                )
            ]
        ),
        DataSourceTypeDefinition(
            id="github",
            name="GitHub",
            category=DataSourceCategory.CODE,
            required_fields=[
                DataSourceFieldDefinition(
                    name="access_token",
                    type="password",
                    description="GitHub personal access token"
                ),
                DataSourceFieldDefinition(
                    name="username",
                    type="string",
                    description="GitHub username"
                )
            ]
        ),
        DataSourceTypeDefinition(
            id="databricks",
            name="Databricks",
            category=DataSourceCategory.DATA,
            required_fields=[
                DataSourceFieldDefinition(
                    name="host",
                    type="string",
                    description="Databricks host URL"
                ),
                DataSourceFieldDefinition(
                    name="access_token",
                    type="password",
                    description="Databricks access token"
                ),
                DataSourceFieldDefinition(
                    name="http_path",
                    type="string",
                    description="Databricks HTTP path for SQL warehouse"
                ),
                DataSourceFieldDefinition(
                    name="catalog",
                    type="string",
                    description="Databricks catalog name",
                    optional=True
                ),
                DataSourceFieldDefinition(
                    name="schema",
                    type="string",
                    description="Databricks schema name",
                    optional=True
                )
            ]
        ),
        DataSourceTypeDefinition(
            id="snowflake",
            name="Snowflake",
            category=DataSourceCategory.DATA,
            required_fields=[
                DataSourceFieldDefinition(
                    name="account",
                    type="string",
                    description="Snowflake account name"
                ),
                DataSourceFieldDefinition(
                    name="username",
                    type="string",
                    description="Snowflake username"
                ),
                DataSourceFieldDefinition(
                    name="password",
                    type="password",
                    description="Snowflake password (required if private_key is not provided)",
                    optional=True
                ),
                DataSourceFieldDefinition(
                    name="private_key",
                    type="password",
                    description="Private key for key pair authentication (required if password is not provided)",
                    optional=True
                ),
                DataSourceFieldDefinition(
                    name="private_key_passphrase",
                    type="password",
                    description="Passphrase for encrypted private key",
                    optional=True
                ),
                DataSourceFieldDefinition(
                    name="role",
                    type="string",
                    description="Snowflake role to use for the session",
                    optional=True
                ),
                DataSourceFieldDefinition(
                    name="warehouse",
                    type="string",
                    description="Snowflake warehouse name"
                ),
                DataSourceFieldDefinition(
                    name="database",
                    type="string",
                    description="Snowflake database name",
                    optional=True
                ),
                DataSourceFieldDefinition(
                    name="schema",
                    type="string",
                    description="Snowflake schema name",
                    optional=True
                )
            ]
        ),

        DataSourceTypeDefinition(
            id="generic_file_upload",
            name="File Upload",
            category=DataSourceCategory.DOCUMENT,
            required_fields=[]
        ),
        DataSourceTypeDefinition(
            id="folder_upload",
            name="Folder Upload",
            category=DataSourceCategory.DOCUMENT,
            required_fields=[]
        ),
        DataSourceTypeDefinition(
            id="bigquery",
            name="BigQuery",
            category=DataSourceCategory.DATA,
            required_fields=[
                DataSourceFieldDefinition(
                    name="project_id",
                    type="string",
                    description="Google Cloud project ID"
                ),
                DataSourceFieldDefinition(
                    name="private_key_id",
                    type="string",
                    description="Service account private key ID"
                ),
                DataSourceFieldDefinition(
                    name="private_key",
                    type="password",
                    description="Service account private key"
                ),
                DataSourceFieldDefinition(
                    name="client_email",
                    type="string",
                    description="Service account client email"
                ),
                DataSourceFieldDefinition(
                    name="client_id",
                    type="string",
                    description="Service account client ID"
                ),
                DataSourceFieldDefinition(
                    name="client_cert_url",
                    type="string",
                    description="Service account client certificate URL"
                ),
                DataSourceFieldDefinition(
                    name="dataset_id",
                    type="string",
                    description="BigQuery dataset ID to access",
                    optional=True
                )
            ]
        ),
        DataSourceTypeDefinition(
            id="glue",
            name="AWS Glue",
            category=DataSourceCategory.DATA,
            required_fields=[
                DataSourceFieldDefinition(
                    name="role_arn",
                    type="string",
                    description="IAM role ARN to assume for Glue access (e.g., arn:aws:iam::123456789012:role/RoleName)"
                ),
                DataSourceFieldDefinition(
                    name="region",
                    type="string",
                    description="AWS Glue region (e.g., us-east-1, us-west-2)"
                ),
                DataSourceFieldDefinition(
                    name="external_id",
                    type="string",
                    description="External ID for secure cross-account access (auto-generated as 'chicory-{project_id}' if not provided)",
                    optional=True
                )
            ]
        ),
        DataSourceTypeDefinition(
            id="datazone",
            name="AWS DataZone",
            category=DataSourceCategory.TOOL,
            required_fields=[
                DataSourceFieldDefinition(
                    name="role_arn",
                    type="string",
                    description="IAM role ARN to assume for DataZone access (e.g., arn:aws:iam::123456789012:role/RoleName)"
                ),
                DataSourceFieldDefinition(
                    name="region",
                    type="string",
                    description="AWS Datazone region (e.g., us-east-1, us-west-2)"
                ),
                DataSourceFieldDefinition(
                    name="external_id",
                    type="string",
                    description="External ID for secure cross-account access (auto-generated as 'chicory-{project_id}' if not provided)",
                    optional=True
                )
            ]
        ),
        DataSourceTypeDefinition(
            id="s3",
            name="Amazon S3",
            category=DataSourceCategory.DOCUMENT,
            required_fields=[
                DataSourceFieldDefinition(
                    name="role_arn",
                    type="string",
                    description="IAM role ARN to assume for S3 access (e.g., arn:aws:iam::123456789012:role/RoleName)"
                ),
                DataSourceFieldDefinition(
                    name="region",
                    type="string",
                    description="AWS S3 region (e.g., us-east-1, us-west-2). Defaults to us-east-1 if not provided",
                    optional=True
                ),
                DataSourceFieldDefinition(
                    name="external_id",
                    type="string",
                    description="External ID for secure cross-account access (auto-generated as 'chicory-{project_id}' if not provided)",
                    optional=True
                )
            ]
        ),
        DataSourceTypeDefinition(
            id="redash",
            name="Redash",
            category=DataSourceCategory.TOOL,
            required_fields=[
                DataSourceFieldDefinition(
                    name="base_url",
                    type="string",
                    description="Redash instance base URL"
                ),
                DataSourceFieldDefinition(
                    name="api_key",
                    type="password",
                    description="Redash API key"
                )
            ]
        ),
        DataSourceTypeDefinition(
            id="dbt",
            name="DBT",
            category=DataSourceCategory.TOOL,
            required_fields=[
                DataSourceFieldDefinition(
                    name="api_token",
                    type="password",
                    description="DBT API token"
                ),
                DataSourceFieldDefinition(
                    name="account_id",
                    type="string",
                    description="DBT account ID"
                ),
                DataSourceFieldDefinition(
                    name="base_url",
                    type="string",
                    description="DBT base URL",
                    optional=True
                ),
                DataSourceFieldDefinition(
                    name="project_id",
                    type="string",
                    description="DBT project ID",
                    optional=True
                ),
                DataSourceFieldDefinition(
                    name="environment_id",
                    type="string",
                    description="DBT environment ID",
                    optional=True
                )
            ]
        ),
        DataSourceTypeDefinition(
            id="looker",
            name="Looker",
            category=DataSourceCategory.TOOL,
            required_fields=[
                DataSourceFieldDefinition(
                    name="base_url",
                    type="string",
                    description="Looker instance base URL"
                ),
                DataSourceFieldDefinition(
                    name="client_id",
                    type="string",
                    description="Looker API client ID"
                ),
                DataSourceFieldDefinition(
                    name="client_secret",
                    type="password",
                    description="Looker API client secret"
                )
            ]
        ),
        DataSourceTypeDefinition(
            id="datahub",
            name="DataHub",
            category=DataSourceCategory.TOOL,
            required_fields=[
                DataSourceFieldDefinition(
                    name="base_url",
                    type="string",
                    description="DataHub instance base URL"
                ),
                DataSourceFieldDefinition(
                    name="api_key",
                    type="password",
                    description="DataHub API key"
                )
            ]
        ),
        DataSourceTypeDefinition(
            id="airflow",
            name="Airflow",
            category=DataSourceCategory.TOOL,
            required_fields=[
                DataSourceFieldDefinition(
                    name="base_url",
                    type="string",
                    description="Airflow instance base URL"
                ),
                DataSourceFieldDefinition(
                    name="username",
                    type="string",
                    description="Airflow username"
                ),
                DataSourceFieldDefinition(
                    name="password",
                    type="password",
                    description="Airflow password"
                )
            ]
        ),
        DataSourceTypeDefinition(
            id="anthropic",
            name="Anthropic",
            category=DataSourceCategory.TOOL,
            required_fields=[
                DataSourceFieldDefinition(
                    name="api_key",
                    type="password",
                    description="Anthropic API key"
                )
            ]
        ),
        DataSourceTypeDefinition(
            id="jira",
            name="Jira",
            category=DataSourceCategory.TOOL,
            required_fields=[
                DataSourceFieldDefinition(
                    name="access_token",
                    type="string",
                    description="Jira OAuth access token"
                ),
                DataSourceFieldDefinition(
                    name="cloud_id",
                    type="string",
                    description="Jira Cloud instance ID"
                )
            ]
        ),
        DataSourceTypeDefinition(
            id="azure_blob_storage",
            name="Azure Blob Storage",
            category=DataSourceCategory.DOCUMENT,
            required_fields=[
                DataSourceFieldDefinition(
                    name="tenant_id",
                    type="string",
                    description="Azure AD Tenant ID"
                ),
                DataSourceFieldDefinition(
                    name="client_id",
                    type="string",
                    description="Application (Client) ID"
                ),
                DataSourceFieldDefinition(
                    name="client_secret",
                    type="password",
                    description="Client Secret"
                ),
                DataSourceFieldDefinition(
                    name="subscription_id",
                    type="string",
                    description="Azure Subscription ID"
                ),
                DataSourceFieldDefinition(
                    name="storage_account_name",
                    type="string",
                    description="Storage Account Name"
                )
            ]
        ),
        DataSourceTypeDefinition(
            id="azure_data_factory",
            name="Azure Data Factory",
            category=DataSourceCategory.TOOL,
            required_fields=[
                DataSourceFieldDefinition(
                    name="tenant_id",
                    type="string",
                    description="Azure AD Tenant ID"
                ),
                DataSourceFieldDefinition(
                    name="client_id",
                    type="string",
                    description="Application (Client) ID"
                ),
                DataSourceFieldDefinition(
                    name="client_secret",
                    type="password",
                    description="Client Secret"
                ),
                DataSourceFieldDefinition(
                    name="subscription_id",
                    type="string",
                    description="Azure Subscription ID"
                ),
                DataSourceFieldDefinition(
                    name="resource_group",
                    type="string",
                    description="Resource Group Name"
                ),
                DataSourceFieldDefinition(
                    name="factory_name",
                    type="string",
                    description="Data Factory Name"
                )
            ]
        ),
        DataSourceTypeDefinition(
            id="webfetch",
            name="Web Fetch (Firecrawl)",
            category=DataSourceCategory.DOCUMENT,
            required_fields=[
                DataSourceFieldDefinition(
                    name="api_key",
                    type="password",
                    description="Firecrawl API key"
                ),
                DataSourceFieldDefinition(
                    name="mode",
                    type="string",
                    description="Fetch mode: 'scrape' for single page, 'crawl' for multiple pages"
                ),
                DataSourceFieldDefinition(
                    name="url",
                    type="string",
                    description="URL to scrape (for scrape mode)",
                    optional=True
                ),
                DataSourceFieldDefinition(
                    name="start_url",
                    type="string",
                    description="Starting URL for crawl (for crawl mode)",
                    optional=True
                ),
                DataSourceFieldDefinition(
                    name="max_pages",
                    type="integer",
                    description="Maximum pages to crawl (default: 100, max: 1000)",
                    optional=True
                )
            ]
        ),
        DataSourceTypeDefinition(
            id="atlan",
            name="Atlan",
            category=DataSourceCategory.TOOL,
            required_fields=[
                DataSourceFieldDefinition(
                    name="tenant_url",
                    type="string",
                    description="Atlan tenant URL (e.g., https://org.atlan.com)"
                ),
                DataSourceFieldDefinition(
                    name="api_token",
                    type="password",
                    description="Atlan API token for authentication"
                )
            ]
        )
    ]

    return DataSourceTypeList(data_source_types=data_source_types)

@router.post("/projects/{project_id}/data-sources", response_model=DataSourceResponse, status_code=status.HTTP_201_CREATED)
async def create_data_source(project_id: str, data_source: DataSourceCreate):
    """Connect a data source to a project"""
    # Verify project exists
    project = await Project.get(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    
    # Create new data source document
    new_data_source = DataSource(
        project_id=project_id,
        type=data_source.type,
        name=data_source.name,
        configuration=data_source.configuration,
        status=DataSourceStatus.CONFIGURED
    )
    
    # Save to database
    await new_data_source.insert()
    
    # Format the response
    return DataSourceResponse(
        id=new_data_source.id,
        project_id=new_data_source.project_id,
        type=new_data_source.type.value,
        name=new_data_source.name,
        configuration=new_data_source.configuration,
        status=new_data_source.status.value,
        created_at=new_data_source.created_at.isoformat(),
        updated_at=new_data_source.updated_at.isoformat()
    )

@router.post("/projects/{project_id}/data-sources/{data_source_id}/validate", response_model=DataSourceValidationResponse)
async def validate_data_source(project_id: str, data_source_id: str):
    """Test the connection to a data source"""
    try:
        # Get the data source
        data_source = await DataSource.get(data_source_id)
        
        # Check if data source exists and belongs to the specified project
        if not data_source or data_source.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Data source with ID {data_source_id} not found in project {project_id}"
            )
            
        logger.info(f"Validating data source {data_source_id} in project {project_id}")
        
        # Delegate to the credential validation function
        return await validate_data_source_credentials(data_source)
    except Exception as e:
        logger.error(f"Error validating data source: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error validating data source: {str(e)}"
        )


@router.post("/data-sources/validate", response_model=DataSourceValidationResponse)
async def validate_credentials(data_source_credentials: Dict[str, Any]):
    """Validate data source credentials without requiring a data source ID
    
    This endpoint allows validating credentials directly, before creating a data source.
    
    Example for GitHub:
    {
        "type": "github",
        "credentials": {
            "access_token": "your_github_personal_access_token",
            "username": "your_github_username"
        }
    }
    """
    try:
        if "type" not in data_source_credentials:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Data source type is required"
            )
            
        data_source_type = data_source_credentials["type"]
        credentials = data_source_credentials.get("credentials", {})
        
        if not credentials:
            return DataSourceValidationResponse(
                status="error",
                message=f"No credentials provided for {data_source_type} validation"
            )
        
        logger.info(f"Validating credentials for {data_source_type} data source")
        
        # Use the validator factory to get the appropriate validator
        try:
            # Run the validation in a separate thread to not block the event loop
            validation_result = await asyncio.to_thread(
                validator_factory.validate,
                data_source_type,
                credentials
            )
            
            return DataSourceValidationResponse(
                status=validation_result["status"],
                message=validation_result["message"]
            )
        except Exception as e:
            logger.error(f"Error validating {data_source_type} credentials: {str(e)}")
            return DataSourceValidationResponse(
                status="error",
                message=f"Failed to validate {data_source_type} credentials: {str(e)}"
            )
            
    except Exception as e:
        logger.error(f"Error in validate_credentials endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error validating credentials: {str(e)}"
        )

@router.get("/projects/{project_id}/data-sources/tools", response_model=ToolList)
async def list_data_source_tools(
    project_id: str):
    """List tools available for project's data sources
    
    Only tools that match with data source types are included in the response.
    
    Returns
    -------
    ToolList
        List of tools available for the project's data sources
    """
    # Verify project exists
    project = await Project.get(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    
    # Fetch tools from internal MCP servers
    tools = await fetch_data_source_tools(project_id)
    
    return ToolList(tools=tools)


@router.get("/projects/{project_id}/data-sources", response_model=DataSourceList)
async def list_data_sources(project_id: str):
    """List all data sources connected to a project"""
    # Verify project exists
    project = await Project.get(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    
    # Find all data sources for this project
    data_sources = await DataSource.find({"project_id": project_id}).to_list()
    
    # Format the response
    data_source_responses = [
        DataSourceResponse(
            id=ds.id,
            project_id=ds.project_id,
            type=ds.type.value,
            name=ds.name,
            configuration=ds.configuration,
            status=ds.status.value,
            created_at=ds.created_at.isoformat(),
            updated_at=ds.updated_at.isoformat()
        ) for ds in data_sources
    ]
    
    return DataSourceList(data_sources=data_source_responses)

@router.put("/projects/{project_id}/data-sources/{data_source_id}", response_model=DataSourceResponse)
async def update_data_source(project_id: str, data_source_id: str, data_source_update: DataSourceUpdate):
    """Update an existing data source"""
    # Find the data source
    data_source = await DataSource.get(data_source_id)
    if not data_source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source with ID {data_source_id} not found"
        )
    
    # Verify data source belongs to the specified project
    if data_source.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source with ID {data_source_id} not found in project {project_id}"
        )
    
    # Update fields if provided
    update_data = data_source_update.dict(exclude_unset=True)
    if update_data:
        # Add updated_at timestamp
        update_data["updated_at"] = datetime.utcnow()
        
        # Update the data source
        await data_source.update({"$set": update_data})
        
        # Refresh the data source with latest data
        data_source = await DataSource.get(data_source_id)
    
    return DataSourceResponse(
        id=data_source.id,
        project_id=data_source.project_id,
        type=data_source.type.value,
        name=data_source.name,
        configuration=data_source.configuration,
        status=data_source.status.value,
        created_at=data_source.created_at.isoformat(),
        updated_at=data_source.updated_at.isoformat()
    )

@router.post("/projects/{project_id}/data-sources/excel-upload", status_code=status.HTTP_201_CREATED, response_model=DataSourceResponse)
async def upload_excel_data_source(
    project_id: str,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...)
):
    """Upload an Excel file as a data source and store it in S3"""
    logger.info(f"Uploading Excel file for project {project_id} with name {name}")
    
    # Verify project exists
    project = await Project.get(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    
    # Get filename and verify it's not empty
    filename = file.filename
    if not filename:
        logger.error("No filename provided")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided"
        )
    
    # Verify file type is Excel
    file_extension = filename.split('.')[-1].lower() if '.' in filename else ""
    if file_extension not in ['xls', 'xlsx']:
        logger.error(f"Invalid file type: {file_extension}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type: {file_extension}. Must be .xls or .xlsx"
        )
    
    # Read file content
    contents = await file.read()
    
    # Validate Excel file and extract metadata
    try:
        import pandas as pd
        excel_io = io.BytesIO(contents)
        
        # Use pandas to read and validate the Excel file
        # If there are multiple sheets, we'll capture information about all of them
        sheet_info = {}
        excel_file = pd.ExcelFile(excel_io)
        sheet_names = excel_file.sheet_names
        
        for sheet_name in sheet_names:
            df = pd.read_excel(excel_io, sheet_name=sheet_name)
            sheet_info[sheet_name] = {
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": df.columns.tolist()
            }
        
        logger.info(f"Excel validated: {len(sheet_names)} sheets")
    except Exception as e:
        logger.error(f"Invalid Excel file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid Excel file: {str(e)}"
        )
    
    try:
        # Generate a safe filename with a UUID to ensure uniqueness
        original_filename = filename.replace(' ', '_')
        unique_filename = f"{uuid.uuid4()}_{original_filename}"
        
        # Create S3 key using project ID and data type for better organization
        # For Excel uploads, we're in the DATA category
        data_type = DataSourceCategory.DATA.value  # Use the enum value for consistency
        
        s3_key = f"artifacts/{project_id.lower()}/{data_type}/raw/{unique_filename}"
        
        # Determine content type based on file extension
        content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' \
            if file_extension == 'xlsx' else 'application/vnd.ms-excel'
        
        # Upload to S3 using helper function
        logger.info(f"Uploading Excel file to S3: {s3_key}")
        s3_result = await upload_file_to_s3(excel_io, s3_key, content_type)
        
        # Create data source in database with S3 references and sheet information
        data_source = DataSource(
            project_id=project_id,
            type=DataSourceType.XLSX_UPLOAD,
            name=name,
            configuration={
                "s3_bucket": s3_result["s3_bucket"],
                "s3_key": s3_result["s3_key"],
                "s3_url": s3_result["s3_url"],
                "file_name": original_filename,
                "file_extension": file_extension,
                "description": description,
                "original_size": len(contents),
                "sheet_count": len(sheet_names),
                "sheet_names": sheet_names,
                "sheet_info": sheet_info
            },
            status=DataSourceStatus.CONNECTED
        )
        
        # Save to database
        await data_source.insert()
        
        return DataSourceResponse(
            id=data_source.id,
            project_id=data_source.project_id,
            type=data_source.type.value,
            name=data_source.name,
            configuration=data_source.configuration,
            status=data_source.status.value,
            created_at=data_source.created_at.isoformat(),
            updated_at=data_source.updated_at.isoformat()
        )
    except Exception as e:
        logger.error(f"Error processing Excel upload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process Excel file: {str(e)}"
        )

@router.post("/projects/{project_id}/data-sources/csv-upload", response_model=DataSourceResponse)
async def upload_csv_data_source(
    project_id: str,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...)
):
    """Upload a CSV file as a data source and store it in S3"""
    # Check if the project exists
    project = await Project.get(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    
    # Validate that the file is a CSV
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be a CSV file"
        )
    
    # Check file size (limit to 50MB)
    contents = await file.read()
    if len(contents) > 50 * 1024 * 1024:  # 50MB
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds the 50MB limit"
        )
    
    # Validate CSV content before uploading to S3
    try:
        # Use BytesIO to avoid writing to disk first
        csv_io = io.BytesIO(contents)
        df = pd.read_csv(csv_io)
        row_count = len(df)
        column_count = len(df.columns)
        columns = df.columns.tolist()
        logger.info(f"CSV validated: {row_count} rows, {column_count} columns")
    except Exception as e:
        logger.error(f"Invalid CSV file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid CSV file: {str(e)}"
        )
    
    # Use our helper functions for S3 operations
    
    try:
        # Generate a safe filename with a UUID to ensure uniqueness
        original_filename = file.filename.replace(' ', '_')
        file_extension = original_filename.split('.')[-1]
        unique_filename = f"{uuid.uuid4()}_{original_filename}"
        
        # Create S3 key using project ID and data type for better organization
        # For CSV uploads, we're in the DATA category
        data_type = DataSourceCategory.DATA.value  # Use the enum value for consistency
            
        s3_key = f"artifacts/{project_id}/{data_type}/raw/{unique_filename}"
        
        # Upload to S3 using helper function
        logger.info(f"Uploading CSV file to S3: {s3_key}")
        s3_result = await upload_file_to_s3(csv_io, s3_key, 'text/csv')
        
        # Create data source in database with S3 references
        data_source = DataSource(
            project_id=project_id,
            type=DataSourceType.CSV_UPLOAD,
            name=name,
            description=description,
            configuration={
                "s3_bucket": s3_result["s3_bucket"],
                "s3_key": s3_result["s3_key"],
                "s3_url": s3_result["s3_url"],
                "original_filename": original_filename,
                "file_size": len(contents),
                "row_count": row_count,
                "column_count": column_count,
                "columns": columns
            },
            status=DataSourceStatus.CONNECTED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        await data_source.create()
        logger.info(f"CSV data source created in S3: {data_source.id}")
        
        return DataSourceResponse(
            id=data_source.id,
            project_id=data_source.project_id,
            type=data_source.type.value,
            name=data_source.name,
            configuration=data_source.configuration,
            status=data_source.status.value,
            created_at=data_source.created_at.isoformat(),
            updated_at=data_source.updated_at.isoformat()
        )
    except Exception as e:
        logger.error(f"Error uploading CSV: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload CSV: {str(e)}"
        )


@router.post("/projects/{project_id}/data-sources/generic-upload", response_model=DataSourceResponse)
async def upload_generic_file_data_source(
    project_id: str,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    category: str = Form(...),  # Required parameter
    file: UploadFile = File(...)
):
    """Upload any file type as a data source and store it in S3"""
    # Check if the project exists
    project = await Project.get(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    
    # Validate that category is either 'document' or 'code'
    if category.lower() not in ['document', 'code']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category must be either 'document' or 'code'"
        )
    
    # Check file size (limit to 50MB)
    contents = await file.read()
    if len(contents) > 50 * 1024 * 1024:  # 50MB
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds the 50MB limit"
        )
    
    try:
        # Generate a safe filename with a UUID to ensure uniqueness
        original_filename = file.filename.replace(' ', '_')
        file_extension = original_filename.split('.')[-1] if '.' in original_filename else ''
        unique_filename = f"{uuid.uuid4()}_{original_filename}"
        
        # Create S3 key using project ID and category for better organization
        # Map category to the appropriate data source type and storage path
        data_source_type = DataSourceType.GENERIC_FILE_UPLOAD
        
        if category.lower() == 'document':
            data_type = DataSourceCategory.DOCUMENT.value
        else:  # code
            data_type = DataSourceCategory.CODE.value
        
        s3_key = f"artifacts/{project_id.lower()}/{data_type}/raw/{unique_filename}"
        
        # Use python-magic to detect content type from file contents
        try:
            import magic
            # Detect MIME type using python-magic
            content_type = magic.from_buffer(contents, mime=True)
            logger.info(f"Detected content type using python-magic: {content_type}")
        except ImportError:
            logger.warning("python-magic is not installed. Falling back to extension-based content type detection.")
            # Fallback: Attempt to guess content type based on extension
            content_type = None
            if file_extension:
                # Basic mapping for common file types
                content_type_map = {
                    'pdf': 'application/pdf',
                    'doc': 'application/msword',
                    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    'txt': 'text/plain',
                    'csv': 'text/csv',
                    'json': 'application/json',
                    'py': 'text/x-python',
                    'js': 'application/javascript',
                    'html': 'text/html',
                    'css': 'text/css',
                    'xml': 'application/xml',
                    'xls': 'application/vnd.ms-excel',
                    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                }
                content_type = content_type_map.get(file_extension.lower())
                if content_type:
                    logger.info(f"Inferred content type from extension: {content_type}")
                else:
                    # For unknown extensions, use a generic binary content type
                    content_type = 'application/octet-stream'
                    logger.info(f"Unknown file extension '{file_extension}', using default content type: {content_type}")
        
        # Use BytesIO to handle the file data
        file_io = io.BytesIO(contents)
        
        # Upload to S3 using helper function
        logger.info(f"Uploading file to S3: {s3_key}")
        s3_result = await upload_file_to_s3(file_io, s3_key, content_type)
        
        # Create data source in database with S3 references
        data_source = DataSource(
            project_id=project_id,
            type=data_source_type,
            name=name,
            description=description,
            configuration={
                "s3_bucket": s3_result["s3_bucket"],
                "s3_key": s3_result["s3_key"],
                "s3_url": s3_result["s3_url"],
                "original_filename": original_filename,
                "file_size": len(contents),
                "file_extension": file_extension,
                "content_type": content_type or "application/octet-stream",
                "category": category.lower()
            },
            status=DataSourceStatus.CONNECTED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        await data_source.create()
        logger.info(f"Generic file data source created in S3: {data_source.id}")
        
        return DataSourceResponse(
            id=data_source.id,
            project_id=data_source.project_id,
            type=data_source.type.value,
            name=data_source.name,
            configuration=data_source.configuration,
            status=data_source.status.value,
            created_at=data_source.created_at.isoformat(),
            updated_at=data_source.updated_at.isoformat()
        )
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )

@router.delete("/projects/{project_id}/data-sources/{data_source_id}", status_code=status.HTTP_200_OK)
async def delete_data_source(project_id: str, data_source_id: str, delete_s3_object: bool = True, force: bool = False):
    """
    Delete a data source and optionally its associated S3 object
    
    Args:
        project_id: ID of the project the data source belongs to
        data_source_id: ID of the data source to delete
        delete_s3_object: Whether to delete the associated S3 object (default: True)
        force: Force deletion even if validation fails (default: False)
    """
    try:
        # Find the data source using the model (with validation)
        data_source = await DataSource.get(data_source_id)
        if not data_source:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Data source with ID {data_source_id} not found"
            )
        
        # Verify data source belongs to the specified project
        if data_source.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Data source with ID {data_source_id} not found in project {project_id}"
            )
    except Exception as e:
        if not force:
            # If not forcing deletion, re-raise the exception
            raise
        
        # If forcing deletion, try to get raw data directly from the database
        logger.warning(f"Validation error when retrieving data source: {str(e)}")
        logger.info(f"Force flag is set, bypassing validation to delete data source {data_source_id}")
        
        # Get the document directly from MongoDB without validation
        data_source_raw = await DataSource.find_one(
            {"_id": data_source_id, "project_id": project_id},
            bypass_document_validation=True
        )
        
        if not data_source_raw:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Data source with ID {data_source_id} not found in project {project_id}"
            )
        
        # Use the raw document as our data source
        data_source = data_source_raw
    
    result = {
        "message": "Data source deleted successfully"
    }
    
    # Handle S3 object deletion if requested and applicable
    s3_types = [
        DataSourceType.CSV_UPLOAD, 
        DataSourceType.XLSX_UPLOAD, 
        DataSourceType.GENERIC_FILE_UPLOAD
    ]
    if delete_s3_object and data_source.type in s3_types and data_source.configuration:
        # Case 1: S3 storage
        if "s3_bucket" in data_source.configuration and "s3_key" in data_source.configuration:
            try:
                s3_bucket = data_source.configuration["s3_bucket"]
                s3_key = data_source.configuration["s3_key"]
                
                # Use our helper function to delete the object
                s3_delete_result = await delete_object_from_s3(s3_bucket, s3_key)
                
                # Update our result with the S3 deletion status
                if s3_delete_result["status"] == "success":
                    logger.info(s3_delete_result["message"])
                elif s3_delete_result["status"] == "warning":
                    logger.warning(s3_delete_result["message"])
                    result["s3_warning"] = s3_delete_result["message"]
                else:
                    logger.error(s3_delete_result["message"])
                    result["s3_error"] = s3_delete_result["message"]
            except Exception as e:
                logger.error(f"Error deleting S3 object: {str(e)}")
                result["s3_error"] = str(e)
                
        # Case 2: Local storage (backward compatibility)
        elif "file_path" in data_source.configuration:
            try:
                file_path = Path(data_source.configuration["file_path"])
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"Deleted local file: {file_path}")
                else:
                    logger.warning(f"Local file not found: {file_path}")
                    result["local_warning"] = "Local file not found"
            except Exception as e:
                logger.error(f"Error deleting local file: {str(e)}")
                result["local_error"] = str(e)

    # Handle folder upload deletion - clean up S3 files and FolderUpload document
    if delete_s3_object and data_source.type == DataSourceType.FOLDER_UPLOAD and data_source.configuration:
        folder_upload_id = data_source.configuration.get("folder_upload_id")
        if folder_upload_id:
            try:
                # Delete all files in S3 for this folder upload
                await s3_delete_folder_upload(project_id, folder_upload_id)
                logger.info(f"Deleted S3 files for folder upload {folder_upload_id}")

                # Delete the FolderUpload document
                folder_upload = await FolderUpload.find_one({"_id": folder_upload_id})
                if folder_upload:
                    await folder_upload.delete()
                    logger.info(f"Deleted FolderUpload document {folder_upload_id}")
                else:
                    logger.warning(f"FolderUpload document {folder_upload_id} not found")
                    result["folder_upload_warning"] = "FolderUpload document not found"
            except Exception as e:
                logger.error(f"Error cleaning up folder upload: {str(e)}")
                result["folder_upload_error"] = str(e)

    # Delete the data source from the database
    try:
        await data_source.delete()
    except Exception as e:
        if force:
            # If force flag is set and delete fails, try raw deletion
            logger.warning(f"Error during model deletion: {str(e)}")
            logger.info(f"Attempting raw deletion from database for {data_source_id}")
            
            # Delete directly from MongoDB collection without validation
            await DataSource.get_motor_collection().delete_one({"_id": data_source_id})
            logger.info(f"Successfully deleted data source {data_source_id} using raw deletion")
        else:
            # If not forcing deletion, re-raise the exception
            raise
    
    return result
