import uuid
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime
from pydantic import BaseModel as PydanticBaseModel, Field, validator
from app.models.base import BaseModel
from beanie import Indexed


class EvaluationRunStatus(str, Enum):
    """Enum for evaluation run status"""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TestCaseRunStatus(str, Enum):
    """Enum for individual test case run status"""
    PENDING = "pending"
    RUNNING_TARGET = "running_target"
    RUNNING_GRADER = "running_grader"
    COMPLETED = "completed"
    FAILED = "failed"

class EvaluationCreate(PydanticBaseModel):
    """Schema for creating a new evaluation"""
    target_agent_id: str
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    criteria: str = Field(..., min_length=1, max_length=2000)  # Natural language evaluation criteria

class EvaluationUpdate(PydanticBaseModel):
    """Schema for updating an evaluation"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    target_agent_id: Optional[str] = None
    criteria: Optional[str] = Field(None, min_length=1)

class TestCaseCreate(PydanticBaseModel):
    """Schema for creating a test case"""
    task: str = Field(..., min_length=1, description="User query/task")
    expected_output: str = Field(..., min_length=1, description="Expected response")
    evaluation_guideline: Optional[str] = Field(None, description="How to judge the output")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @validator('task', 'expected_output')
    def validate_non_empty(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Field cannot be empty")
        return v.strip()

    @validator('evaluation_guideline')
    def validate_evaluation_guideline(cls, v):
        # Allow empty or None values
        return v.strip() if v else None

class TestCaseUpdate(PydanticBaseModel):
    """Schema for updating a test case"""
    task: Optional[str] = Field(None, min_length=1)
    expected_output: Optional[str] = Field(None, min_length=1)
    evaluation_guideline: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    @validator('task', 'expected_output')
    def validate_non_empty(cls, v):
        if v is not None and (not v or v.strip() == ""):
            raise ValueError("Field cannot be empty")
        return v.strip() if v else v

    @validator('evaluation_guideline')
    def validate_evaluation_guideline(cls, v):
        # Allow empty or None values
        return v.strip() if v else None

class TestCaseBulkCreate(PydanticBaseModel):
    """Schema for creating multiple test cases at once"""
    test_cases: List[TestCaseCreate] = Field(..., min_items=1, max_items=25, description="List of test cases to create")

class Evaluation(BaseModel):
    """Evaluation document model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    project_id: str
    target_agent_id: str  # Agent being evaluated
    name: str
    description: Optional[str] = None
    owner: str
    s3_bucket: Optional[str] = None  # S3 bucket for CSV file
    s3_key: Optional[str] = None  # S3 key for CSV file
    s3_url: Optional[str] = None  # S3 URL for CSV file
    original_filename: Optional[str] = None  # Original CSV filename
    file_size: Optional[int] = None  # File size in bytes
    criteria: str  # Natural language evaluation criteria
    test_cases: List[Dict[str, Any]] = Field(default_factory=list)  # Parsed CSV data
    test_case_count: int = Field(default=0)
    
    class Settings:
        name = "evaluations"
        
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_schema_extra = {
            "example": {
                "id": "eval-123e4567-e89b-12d3-a456-426614174000",
                "project_id": "proj-123",
                "target_agent_id": "agent-456",
                "grading_agent_id": "agent-789",
                "name": "Customer Support Bot Evaluation",
                "description": "Testing bot responses to common customer queries",
                "owner": "user@example.com",
                "csv_file_path": "/uploads/evaluations/eval-123/test_cases.csv",
                "criteria": "Evaluate if the response is helpful, accurate, and follows our brand tone",
                "grader_prompt": "You are an expert evaluator. Rate the response on helpfulness, accuracy, and brand tone...",
                "status": "draft",
                "test_cases": [
                    {
                        "id": "tc-001",
                        "task": "How do I reset my password?",
                        "expected_output": "Click on 'Forgot Password' link...",
                        "evaluation_guideline": "Response should include step-by-step instructions"
                    }
                ],
                "test_case_count": 25,
                "created_at": "2025-08-15T08:00:00Z",
                "updated_at": "2025-08-15T08:00:00Z"
            }
        }

class EvaluationResponse(PydanticBaseModel):
    """Schema for evaluation API responses"""
    id: str
    project_id: str
    target_agent_id: str
    name: str
    description: Optional[str]
    owner: str
    s3_bucket: Optional[str]
    s3_key: Optional[str]
    s3_url: Optional[str]
    original_filename: Optional[str]
    file_size: Optional[int]
    criteria: str
    test_case_count: int
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True

class EvaluationList(PydanticBaseModel):
    """Schema for list of Evaluations"""
    evaluations: List[EvaluationResponse]
    has_more: bool = False

class TestCaseResponse(PydanticBaseModel):
    """Schema for test case response"""
    id: str
    task: str
    expected_output: str
    evaluation_guideline: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class TestCaseList(PydanticBaseModel):
    """Schema for list of test cases"""
    test_cases: List[TestCaseResponse]
    total_count: int

# Phase 2: Evaluation Run Models

class TestCaseResult(PydanticBaseModel):
    """Schema for individual test case execution result"""
    test_case_id: str
    status: TestCaseRunStatus
    target_task_id: Optional[str] = None  # Task ID for target agent execution
    grader_task_id: Optional[str] = None  # Task ID for grading agent execution
    target_response: Optional[str] = None  # Response from target agent
    grader_response: Optional[str] = None  # Response from grading agent
    score: Optional[float] = None  # Score from 0.0 to 1.0
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class EvaluationRun(BaseModel):
    """Model for tracking evaluation execution"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    evaluation_id: str = Field(..., description="ID of the evaluation being run")
    project_id: str = Field(..., description="Project ID")
    target_agent_id: str = Field(..., description="Target agent ID")
    grading_agent_id: str = Field(..., description="Grading agent ID")
    grading_agent_project_id: str = Field(..., description="Grading agent project ID")
    status: EvaluationRunStatus = Field(default=EvaluationRunStatus.QUEUED)
    test_case_results: List[Dict[str, Any]] = Field(default_factory=list)
    total_test_cases: int = Field(..., description="Total number of test cases")
    completed_test_cases: int = Field(default=0)
    failed_test_cases: int = Field(default=0)
    overall_score: Optional[float] = Field(None, description="Overall evaluation score (0.0 to 1.0)")
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        collection = "evaluation_runs"
        use_state_management = True

class EvaluationRunCreate(PydanticBaseModel):
    """Schema for creating an evaluation run"""
    pass  # No additional fields needed - all info comes from the evaluation

class EvaluationRunResponse(PydanticBaseModel):
    """Schema for evaluation run response"""
    id: str
    evaluation_id: str
    project_id: str
    target_agent_id: str
    grading_agent_id: str
    grading_agent_project_id: str
    status: str
    test_case_results: List[TestCaseResult]
    total_test_cases: int
    completed_test_cases: int
    failed_test_cases: int
    overall_score: Optional[float]
    error_message: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True

class EvaluationRunList(PydanticBaseModel):
    """Schema for list of evaluation runs"""
    runs: List[EvaluationRunResponse]
    has_more: bool = False
