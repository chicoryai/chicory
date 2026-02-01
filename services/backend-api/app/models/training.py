import uuid
from typing import Optional, List, Dict, Any
from pydantic import BaseModel as PydanticBaseModel, Field
from app.models.base import BaseModel
from datetime import datetime


class TrainingCreate(PydanticBaseModel):
    """Schema for creating a training job"""
    data_source_ids: List[str] = Field(..., description="List of data source IDs to include in training")
    description: Optional[str] = Field(None, max_length=500, description="Optional description of the training job")


class TrainingProgress(PydanticBaseModel):
    """Schema for training progress details"""
    current_step: str = Field(..., description="Current processing step")
    steps_completed: int = Field(..., description="Number of steps completed")
    total_steps: int = Field(..., description="Total number of steps in the process")
    percent_complete: int = Field(..., description="Percent complete (0-100)")


class Training(BaseModel):
    """Training job document model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    project_id: str
    data_source_ids: List[str]
    status: str = Field(default="queued", description="Current status of the training job")
    description: Optional[str] = None
    progress: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    # ProjectMD Generation fields
    projectmd_status: Optional[str] = None  # queued, in_progress, completed, failed
    projectmd_documentation_agent_id: Optional[str] = None
    projectmd_documentation_project_id: Optional[str] = None
    projectmd_s3_url: Optional[str] = None
    projectmd_error_message: Optional[str] = None
    projectmd_started_at: Optional[datetime] = None
    projectmd_completed_at: Optional[datetime] = None
    
    class Settings:
        name = "training_jobs"
        indexes = [
            "project_id",  # Index for project lookups
            "status"      # Index for status lookups
        ]
        
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_schema_extra = {
            "example": {
                "id": "train_567890",
                "project_id": "proj_234567",
                "data_source_ids": ["ds_345678", "ds_456789"],
                "status": "in_progress",
                "description": "Training with GitHub and document sources",
                "progress": {
                    "current_step": "indexing",
                    "steps_completed": 2,
                    "total_steps": 5,
                    "percent_complete": 40
                },
                "created_at": "2025-04-11T13:00:00Z",
                "updated_at": "2025-04-11T13:05:00Z"
            }
        }


class ProjectMDGeneration(PydanticBaseModel):
    """Schema for project.md generation status"""
    status: Optional[str] = None
    documentation_agent_id: Optional[str] = None
    documentation_project_id: Optional[str] = None
    s3_url: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class TrainingResponse(PydanticBaseModel):
    """Schema for training job response"""
    id: str
    project_id: str
    data_source_ids: List[str]
    status: str
    description: Optional[str] = None
    progress: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str
    projectmd_generation: Optional[ProjectMDGeneration] = None
    
    class Config:
        from_attributes = True


class TrainingUpdate(PydanticBaseModel):
    """Schema for updating a training job"""
    status: Optional[str] = None
    description: Optional[str] = Field(None, max_length=500)
    progress: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    data_source_ids: Optional[List[str]] = None


class TrainingList(PydanticBaseModel):
    """Schema for list of training jobs"""
    training_jobs: List[TrainingResponse]
