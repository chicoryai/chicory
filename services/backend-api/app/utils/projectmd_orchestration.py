"""
Project.md generation orchestration utilities.
Handles background agent invocation and S3 upload for project documentation.
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException
import logging

from app.models.training import Training
from app.models.tasks import Task, TaskRole, TaskStatus
from app.models.agent import Agent
from app.utils.rabbitmq_client import queue_agent_task
from app.utils.projectmd_utils import upload_projectmd_to_s3

logger = logging.getLogger(__name__)

class ProjectMDOrchestrator:
    """Orchestrates project.md generation with agent invocation and S3 upload"""
    
    def __init__(self, training: Training, documentation_agent_id: str, documentation_project_id: str):
        self.training = training
        self.documentation_agent_id = documentation_agent_id
        self.documentation_project_id = documentation_project_id
        self.documentation_task_id: Optional[str] = None
        
    async def start_generation(self):
        """Start the project.md generation process"""
        try:
            logger.info(f"Starting project.md generation for training {self.training.id}")
            
            # Update status to in_progress
            await self._update_training_status("in_progress")
            
            # Create documentation task
            await self._create_documentation_task()
            
            # Start polling for completion
            await self._poll_for_completion()
            
        except Exception as e:
            logger.error(f"Error in project.md orchestration: {e}")
            await self._mark_generation_failed(str(e))
    
    async def _create_documentation_task(self):
        """Create task for the documentation agent"""
        try:
            # Create documentation prompt
            documentation_prompt = "Please provide your claude.md now."
            
            # Create user task for documentation agent
            user_task = Task(
                agent_id=self.documentation_agent_id,
                project_id=self.documentation_project_id, 
                role=TaskRole.USER,
                content=documentation_prompt,
                status=TaskStatus.QUEUED,
                metadata={
                    "training_id": str(self.training.id),
                    "override_project_id": self.training.project_id,
                    "task_type": "project_md_generation"
                }
            )
            await user_task.save()
            
            # Create assistant task
            assistant_task = Task(
                agent_id=self.documentation_agent_id,
                project_id=self.documentation_project_id, 
                role=TaskRole.ASSISTANT,
                content="",
                status=TaskStatus.QUEUED,
                related_task_id=str(user_task.id),
                metadata={
                    "training_id": str(self.training.id),
                    "override_project_id": self.training.project_id,
                    "task_type": "project_md_generation"
                }
            )
            await assistant_task.save()
            
            # Store task ID for tracking
            self.documentation_task_id = str(assistant_task.id)
            
            # Queue the task for processing
            await queue_agent_task(
                task_id=str(user_task.id),
                assistant_task_id=str(assistant_task.id),
                agent_id=self.documentation_agent_id,
                project_id=self.documentation_project_id,  # Use agent's project
                content=documentation_prompt,
                metadata={
                    "training_id": str(self.training.id),
                    "override_project_id": self.training.project_id,
                    "task_type": "project_md_generation"
                }
            )
            
            logger.info(f"Created documentation task {assistant_task.id} for training {self.training.id}")
            
        except Exception as e:
            logger.error(f"Error creating documentation task: {e}")
            await self._mark_generation_failed(f"Failed to create documentation task: {str(e)}")
    
    async def _poll_for_completion(self):
        """Poll for task completion and process results"""
        max_polls = 1800  # 30 minutes with 1-second intervals
        poll_count = 0
        
        while poll_count < max_polls:
            try:
                # Check if documentation task is completed
                if await self._check_task_completion():
                    break
                
                # Wait before next poll
                await asyncio.sleep(1)
                poll_count += 1
                
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                await self._mark_generation_failed(str(e))
                break
        
        if poll_count >= max_polls:
            await self._mark_generation_failed("Project.md generation timed out")
    
    async def _check_task_completion(self) -> bool:
        """Check if documentation task is completed and process result"""
        if not self.documentation_task_id:
            return False
        
        # Check if task is completed
        task = await Task.get(self.documentation_task_id)
        if task and task.status == TaskStatus.COMPLETED:
            logger.info(f"Documentation task {self.documentation_task_id} completed")
            
            # Upload project.md content to S3
            await self._upload_to_s3(task.content)
            return True
        
        return False
    
    async def _upload_to_s3(self, project_md_content: str):
        """Upload generated project.md content to S3"""
        try:
            # Upload to S3
            s3_url = await upload_projectmd_to_s3(
                project_md_content=project_md_content,
                project_id=self.training.project_id,
                training_id=str(self.training.id)
            )
            
            # Update training with completion status and S3 URL
            await self._update_training_completion(s3_url)
            
            logger.info(f"Successfully uploaded project.md to S3: {s3_url}")
            
        except Exception as e:
            logger.error(f"Error uploading project.md to S3: {e}")
            await self._mark_generation_failed(f"Failed to upload to S3: {str(e)}")
    
    async def _update_training_status(self, status: str):
        """Update training projectmd status"""
        update_data = {
            "projectmd_status": status,
            "updated_at": datetime.now(timezone.utc)
        }
        
        await self.training.update({"$set": update_data})
        self.training.projectmd_status = status
    
    async def _update_training_completion(self, s3_url: str):
        """Update training with completion status and S3 URL"""
        update_data = {
            "projectmd_status": "completed",
            "projectmd_s3_url": s3_url,
            "projectmd_completed_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        await self.training.update({"$set": update_data})
    
    async def _mark_generation_failed(self, error_message: str):
        """Mark project.md generation as failed"""
        update_data = {
            "projectmd_status": "failed",
            "projectmd_error_message": error_message,
            "projectmd_completed_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        await self.training.update({"$set": update_data})
        
        logger.error(f"Project.md generation failed for training {self.training.id}: {error_message}")


async def start_projectmd_orchestration(
    training: Training,
    documentation_agent_id: str,
    documentation_project_id: str
):
    """Start project.md generation orchestration in the background"""
    try:
        # Validate documentation agent exists
        documentation_agent = await Agent.get(documentation_agent_id)
        if not documentation_agent:
            logger.error(f"Documentation agent {documentation_agent_id} not found")
            return
        
        # Start orchestration with agent IDs passed directly
        orchestrator = ProjectMDOrchestrator(training, documentation_agent_id, documentation_project_id)
        await orchestrator.start_generation()
        
    except Exception as e:
        logger.error(f"Error starting project.md orchestration: {e}")
