"""
Tool metadata generation orchestration utilities.
Handles background task execution for generating MCP tool metadata using agent invocation.
"""

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from app.models.agent import Agent
from app.models.tasks import Task, TaskRole, TaskStatus
from app.models.mcp_gateway import MCPTool, MCPToolStatus, MCPGateway
from app.utils.rabbitmq_client import queue_agent_task

logger = logging.getLogger(__name__)

class ToolMetadataOrchestrator:
    """Orchestrates tool metadata generation using agent invocation"""
    
    def __init__(self, tool: MCPTool):
        self.tool = tool
        self.tool_id = str(tool.id)
        self.source_agent = None
        self.metadata_agent_id = None
        self.task_id = None
        
    async def start_metadata_generation(self):
        """Start the metadata generation process"""
        try:
            logger.info(f"Starting metadata generation for tool {self.tool_id}")
            
            # Load tool and source agent
            await self._load_tool_and_agent()
            
            # Update tool status to generating
            await self._update_tool_status(MCPToolStatus.GENERATING)
            
            # Get metadata generation agent
            self.metadata_agent_id = await self._get_metadata_agent_id()
            
            # Create metadata generation prompt
            prompt = self._create_metadata_prompt()
            
            # Create and queue metadata generation task
            self.task_id = await self._create_metadata_task(prompt)
            
            # Poll for completion and update tool
            await self._poll_and_update_tool()
            
        except Exception as e:
            logger.error(f"Error in tool metadata orchestration: {e}")
            await self._mark_tool_failed(str(e))
    
    async def _load_tool_and_agent(self):
        """Load source agent data"""
        # Tool is already passed in constructor, just load the agent
        self.source_agent = await Agent.get(self.tool.agent_id)
        if not self.source_agent:
            raise Exception(f"Source agent {self.tool.agent_id} not found")
        
        logger.info(f"Loaded tool {self.tool.tool_name} based on agent {self.source_agent.name}")
    
    async def _get_metadata_agent_id(self) -> str:
        """Get metadata generation agent ID from environment"""
        # Check for dedicated metadata generation agent
        metadata_agent_id = os.environ.get("MCP_TOOL_METADATA_GENERATION_AGENT_ID")
        if not metadata_agent_id:
            raise Exception("MCP_TOOL_METADATA_GENERATION_AGENT_ID environment variable is required")
        
        # Verify the agent exists
        metadata_agent = await Agent.get(metadata_agent_id)
        if not metadata_agent:
            raise Exception(f"Metadata generation agent {metadata_agent_id} not found")
        
        logger.info(f"Using dedicated metadata agent {metadata_agent_id}")
        return metadata_agent_id
    
    async def _get_metadata_agent_project_id(self) -> str:
        """Get project ID for metadata generation agent"""
        # Check for dedicated metadata agent project
        metadata_project_id = os.environ.get("MCP_TOOL_METADATA_GENERATION_PROJECT_ID")
        if not metadata_project_id:
            raise Exception("MCP_TOOL_METADATA_GENERATION_PROJECT_ID environment variable is required")
        
        logger.info(f"Using dedicated metadata project {metadata_project_id}")
        return metadata_project_id
    
    def _create_metadata_prompt(self) -> str:
        """Create prompt for metadata generation based on source agent"""
        capabilities_text = ', '.join(self.source_agent.capabilities) if self.source_agent.capabilities else 'General purpose'
        
        return f"""You are an expert at converting AI agents into MCP (Model Context Protocol) tools. 
Generate comprehensive metadata for an MCP tool based on the following agent information:

AGENT INFORMATION:
- Name: {self.source_agent.name}
- Description: {self.source_agent.description or 'No description provided'}
- Instructions: {self.source_agent.instructions or 'No specific instructions'}
- Capabilities: {capabilities_text}
- Output Format: {self.source_agent.output_format}
- Tool Name: {self.tool.tool_name}

TASK: Generate metadata for this MCP tool that external applications can use.

REQUIREMENTS:
- Create a clear, professional description (1-2 sentences)
- Design input schema following JSON Schema specification
- Consider the agent's capabilities when defining parameters
- Make the tool useful for external MCP clients
- Output format should match the agent's specified format

Generate the metadata now:"""
    
    async def _create_metadata_task(self, prompt: str) -> str:
        """Create task for metadata generation"""
        # Get project ID for metadata generation
        project_id = await self._get_metadata_agent_project_id()
        
        # Create user task
        user_task = Task(
            agent_id=self.metadata_agent_id,
            project_id=project_id,
            role=TaskRole.USER,
            content=prompt,
            status=TaskStatus.QUEUED,
            metadata={
                "tool_id": self.tool_id,
                "source_agent_id": self.tool.agent_id,
                "task_type": "metadata_generation",
                "gateway_id": self.tool.gateway_id
            }
        )
        await user_task.save()
        
        # Create assistant task
        assistant_task = Task(
            agent_id=self.metadata_agent_id,
            project_id=project_id,
            role=TaskRole.ASSISTANT,
            content="",
            status=TaskStatus.QUEUED,
            related_task_id=str(user_task.id),
            metadata={
                "tool_id": self.tool_id,
                "source_agent_id": self.tool.agent_id,
                "task_type": "metadata_generation",
                "gateway_id": self.tool.gateway_id
            }
        )
        await assistant_task.save()
        
        # Queue the task for processing
        await queue_agent_task(
            task_id=str(user_task.id),
            assistant_task_id=str(assistant_task.id),
            agent_id=self.metadata_agent_id,
            project_id=project_id,
            content=prompt,
            metadata={
                "tool_id": self.tool_id,
                "source_agent_id": self.tool.agent_id,
                "task_type": "metadata_generation"
            }
        )
        
        logger.info(f"Created metadata generation task {assistant_task.id} for tool {self.tool_id}")
        return str(assistant_task.id)
    
    async def _poll_and_update_tool(self, max_wait_seconds: int = 300):
        """Poll for task completion and update tool with generated metadata"""
        start_time = datetime.now(timezone.utc)
        poll_interval = 5  # seconds
        
        while True:
            # Check if we've exceeded max wait time
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            if elapsed > max_wait_seconds:
                logger.error(f"Metadata generation timed out after {elapsed} seconds for tool {self.tool_id}")
                await self._mark_tool_failed("Metadata generation timed out")
                return
            
            # Get task status
            task = await Task.get(self.task_id)
            if not task:
                logger.error(f"Metadata generation task {self.task_id} not found for tool {self.tool_id}")
                await self._mark_tool_failed("Metadata generation task not found")
                return
            
            logger.info(f"Polling task {self.task_id} status: {task.status} (elapsed: {elapsed:.1f}s)")
            
            if task.status == TaskStatus.COMPLETED:
                logger.info(f"Task {self.task_id} completed, applying metadata to tool {self.tool_id}")
                # Parse and apply metadata
                await self._apply_generated_metadata(task.content)
                return
            elif task.status == TaskStatus.FAILED:
                error_msg = task.metadata.get("error_message", "Unknown error") if task.metadata else "Unknown error"
                logger.error(f"Task {self.task_id} failed: {error_msg}")
                await self._mark_tool_failed(f"Metadata generation failed: {error_msg}")
                return
            
            # Wait before next poll
            await asyncio.sleep(poll_interval)
    
    async def _apply_generated_metadata(self, generated_content: str):
        """Parse and apply generated metadata to the tool"""
        try:
            logger.info(f"Processing generated content for tool {self.tool_id}: {generated_content[:200]}...")
            
            # Parse the task response to get the actual content
            try:
                task_response = json.loads(generated_content)
                actual_content = task_response.get("response", generated_content)
            except json.JSONDecodeError:
                actual_content = generated_content
            
            # Extract JSON from the response
            json_content = self._extract_json_from_response(actual_content)
            if not json_content:
                logger.error(f"No valid JSON found in generated content")
                await self._mark_tool_failed("Failed to extract valid JSON from AI response")
                return
            
            logger.info(f"Extracted JSON content: {json_content}")
            metadata = json.loads(json_content)
            
            # Validate required fields
            required_fields = ["tool_name", "description", "input_schema", "output_format"]
            missing_fields = [field for field in required_fields if field not in metadata]
            if missing_fields:
                logger.error(f"Missing required metadata fields {missing_fields}")
                logger.error(f"Extracted JSON content: {json_content}")
                await self._mark_tool_failed(f"AI response missing required fields: {missing_fields}")
                return
            
            logger.info(f"Metadata validation passed, updating tool {self.tool_id}")
            
            # Update tool with generated metadata
            update_data = {
                "tool_name": metadata["tool_name"],
                "description": metadata["description"],
                "input_schema": metadata["input_schema"],
                "output_format": metadata["output_format"],
                "status": MCPToolStatus.READY.value,
                "enabled": True,
                "updated_at": datetime.now(timezone.utc)
            }
            
            logger.info(f"Updating tool with data: {update_data}")
            await self.tool.update({"$set": update_data})
            
            # Update agent metadata with MCP gateway ID when tool is successfully enabled
            await self._update_agent_metadata_with_gateway_id()
            
            logger.info(f"Successfully applied AI-generated metadata to tool {self.tool_id}")
            
        except Exception as e:
            logger.error(f"Error applying metadata to tool {self.tool_id}: {e}")
            logger.exception("Full exception details:")
            await self._mark_tool_failed(f"Failed to apply metadata: {str(e)}")
    
    
    def _extract_json_from_response(self, content: str) -> Optional[str]:
        """Extract JSON object from response content"""
        try:
            # First try to extract from markdown code blocks
            markdown_json_pattern = r'```json\s*\n(.*?)\n```'
            markdown_match = re.search(markdown_json_pattern, content, re.DOTALL)
            if markdown_match:
                json_content = markdown_match.group(1).strip()
                # Clean up backticks around field names and values
                cleaned_content = re.sub(r'"`([^`"]+)`"', r'"\1"', json_content)
                json.loads(cleaned_content)
                return cleaned_content
            
            # Clean up backticks around field names and values
            cleaned_content = re.sub(r'"`([^`"]+)`"', r'"\1"', content.strip())
            
            # Try to parse the cleaned content as JSON
            json.loads(cleaned_content)
            return cleaned_content
        except json.JSONDecodeError:
            pass
        
        # Look for JSON object in the response using regex
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, content, re.DOTALL)
        
        for match in matches:
            try:
                # Clean up backticks and try to parse
                cleaned_match = re.sub(r'"`([^`"]+)`"', r'"\1"', match)
                json.loads(cleaned_match)
                return cleaned_match
            except json.JSONDecodeError:
                continue
        
        return None
    
    async def _update_agent_metadata_with_gateway_id(self):
        """Update agent metadata with MCP gateway ID when tool is successfully enabled"""
        try:
            # Get the gateway ID from the tool
            gateway_id = self.tool.gateway_id
            
            if not gateway_id:
                logger.warning(f"No gateway_id found for tool {self.tool_id}")
                return
            
            # Get current agent metadata
            current_metadata = self.source_agent.metadata or {}
            
            # Initialize mcp_gateways array if it doesn't exist
            if "mcp_gateways" not in current_metadata:
                current_metadata["mcp_gateways"] = []
            
            # Create new gateway entry
            new_gateway_entry = {
                "gateway_id": gateway_id,
                "tool_id": self.tool_id,
                "enabled_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Check if this gateway is already in the list (prevent duplicates)
            existing_gateways = current_metadata["mcp_gateways"]
            gateway_exists = any(
                entry.get("gateway_id") == gateway_id and entry.get("tool_id") == self.tool_id
                for entry in existing_gateways
            )
            
            if not gateway_exists:
                # Add the new gateway entry to the array
                current_metadata["mcp_gateways"].append(new_gateway_entry)
                
                # Update the agent document
                await self.source_agent.update({
                    "$set": {
                        "metadata": current_metadata,
                        "updated_at": datetime.now(timezone.utc)
                    }
                })
                
                logger.info(f"Successfully added MCP gateway {gateway_id} to agent {self.source_agent.id} metadata")
            else:
                logger.info(f"MCP gateway {gateway_id} already exists in agent {self.source_agent.id} metadata")
            
        except Exception as e:
            logger.error(f"Error updating agent metadata with gateway ID: {e}")
            # Don't fail the entire process if metadata update fails
    
    async def _update_tool_status(self, status: MCPToolStatus):
        """Update tool status"""
        try:
            await self.tool.update({
                "$set": {
                    "status": status.value,
                    "updated_at": datetime.now(timezone.utc)
                }
            })
        except Exception as e:
            logger.error(f"Error updating tool status: {e}")
    
    async def _mark_tool_failed(self, error_message: str):
        """Mark tool as failed with error message"""
        try:
            await self.tool.update({
                "$set": {
                    "status": MCPToolStatus.FAILED.value,
                    "metadata": {"error_message": error_message},
                    "updated_at": datetime.now(timezone.utc)
                }
            })
            logger.error(f"Marked tool {self.tool_id} as failed: {error_message}")
        except Exception as e:
            logger.error(f"Error marking tool as failed: {e}")


async def start_tool_metadata_generation(tool: MCPTool):
    """Background task entry point for tool metadata generation"""
    try:
        logger.info(f"Starting background metadata generation for tool {tool.id}")
        
        # Create orchestrator and start process
        orchestrator = ToolMetadataOrchestrator(tool)
        await orchestrator.start_metadata_generation()
        
        logger.info(f"Completed metadata generation for tool {tool.id}")
        
    except Exception as e:
        logger.error(f"Error in background metadata generation for tool {tool.id}: {e}")
        
        # Try to mark tool as failed
        try:
            await tool.update({
                "$set": {
                    "status": MCPToolStatus.FAILED.value,
                    "metadata": {"error_message": f"Background generation failed: {str(e)}"},
                    "updated_at": datetime.now(timezone.utc)
                }
            })
        except Exception as update_error:
            logger.error(f"Failed to update tool status after error: {update_error}")
