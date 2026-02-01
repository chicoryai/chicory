import uuid
from typing import Optional, List
from pydantic import BaseModel as PydanticBaseModel, Field, field_validator
from app.models.base import BaseModel


def validate_uuid_list(v: Optional[List[str]]) -> Optional[List[str]]:
    """Validate that all items in the list are valid UUID format"""
    if v is None:
        return v
    for item_id in v:
        try:
            uuid.UUID(item_id)
        except ValueError:
            raise ValueError(f"All members must be valid UUID format: {item_id} is invalid")
    return v


class ProjectCreate(PydanticBaseModel):
    """Schema for creating a project"""
    name: str = Field(..., min_length=1, max_length=100)
    organization_id: str = Field(..., min_length=1)
    description: Optional[str] = Field(None, max_length=500)
    members: List[str] = Field(default=[], description="List of UUIDs of project members")

    @field_validator('members')
    @classmethod
    def validate_members_uuids(cls, v: List[str]) -> List[str]:
        """Validate that all members are valid UUID format"""
        return validate_uuid_list(v)


class ProjectUpdate(PydanticBaseModel):
    """Schema for updating a project"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    api_key: Optional[str] = None
    members: Optional[List[str]] = Field(None, description="List of UUIDs of project members")

    @field_validator('members')
    @classmethod
    def validate_members_uuids(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate that all members are valid UUID format"""
        return validate_uuid_list(v)

class Project(BaseModel):
    """Project document model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    organization_id: str
    name: str
    description: Optional[str] = None
    api_key: Optional[str] = None
    members: List[str] = []
    documentation_agent_id: Optional[str] = None  # Reference to auto-created documentation agent

    class Settings:
        name = "projects"

        # Just define simple field indexes without trying to enforce uniqueness at DB level
        # We'll handle uniqueness validation in the API layer
        indexes = [
            "organization_id",  # Index for organization_id lookups
            "name"             # Index for name lookups
        ]
        
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_schema_extra = {
            "example": {
                "id": "12345678-90ab-cdef-1234-567890abcdef",
                "organization_id": "org_123456",
                "name": "My Project",
                "description": "Optional project description",
                "api_key": "pk_live_1234567890abcdef",
                "members": ["a1b2c3d4-e5f6-4789-a012-3456789abcde", "b2c3d4e5-f6a7-4890-b123-456789abcdef"],
                "created_at": "2025-04-11T11:00:00Z",
                "updated_at": "2025-04-11T11:00:00Z"
            }
        }

class ProjectResponse(PydanticBaseModel):
    """Schema for project response"""
    id: str
    organization_id: str
    name: str
    description: Optional[str] = None
    api_key: Optional[str] = None
    members: List[str]
    documentation_agent_id: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

class ProjectList(PydanticBaseModel):
    """Schema for list of projects"""
    projects: List[ProjectResponse]