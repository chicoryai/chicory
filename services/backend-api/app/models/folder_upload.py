"""
Folder Upload Model

Represents folder hierarchies uploaded as data sources.
Stores individual file entries with their paths and metadata.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel as PydanticBaseModel, Field
from app.models.base import BaseModel
from beanie import Indexed


class FolderUploadStatus(str, Enum):
    """Enum for folder upload status"""
    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"


class FolderFileEntry(PydanticBaseModel):
    """Individual file within a folder upload"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    relative_path: str  # e.g., "src/components/Button.tsx"
    filename: str  # e.g., "Button.tsx"
    file_extension: str  # e.g., ".tsx"
    file_size: int  # bytes
    content_type: str  # MIME type
    s3_key: str  # Full S3 key
    s3_url: str  # S3 URL for access
    depth: int  # Directory depth (0-9)
    parent_path: str  # e.g., "src/components" or "" for root
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    checksum: Optional[str] = None  # SHA-256 hash

    class Config:
        json_schema_extra = {
            "example": {
                "id": "file-uuid",
                "relative_path": "src/components/Button.tsx",
                "filename": "Button.tsx",
                "file_extension": ".tsx",
                "file_size": 2048,
                "content_type": "text/typescript",
                "s3_key": "artifacts/proj-123/folders/upload-456/files/src/components/Button.tsx",
                "s3_url": "https://bucket.s3.amazonaws.com/...",
                "depth": 2,
                "parent_path": "src/components",
                "created_at": "2025-04-11T12:00:00Z",
                "checksum": "a1b2c3d4..."
            }
        }


class FolderUpload(BaseModel):
    """Folder upload document model - represents entire folder hierarchy"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    project_id: Indexed(str)
    data_source_id: Optional[str] = None  # Links to parent DataSource (set after upload complete)
    name: str  # User-friendly name
    root_folder_name: str  # Original uploaded folder name
    category: str = "document"  # document, code, or data
    total_files: int = 0
    total_size: int = 0  # Total bytes
    max_depth: int = 0  # Deepest level in hierarchy
    files: List[FolderFileEntry] = Field(default_factory=list)
    status: FolderUploadStatus = FolderUploadStatus.UPLOADING
    s3_prefix: str = ""  # e.g., "artifacts/{project_id}/folders/{upload_id}/"
    error_message: Optional[str] = None

    class Settings:
        name = "folder_uploads"

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_schema_extra = {
            "example": {
                "id": "upload-uuid",
                "project_id": "proj-123",
                "data_source_id": "ds-456",
                "name": "My Project Files",
                "root_folder_name": "my-project",
                "category": "code",
                "total_files": 42,
                "total_size": 15000000,
                "max_depth": 5,
                "status": "ready",
                "s3_prefix": "artifacts/proj-123/folders/upload-uuid/",
                "created_at": "2025-04-11T12:00:00Z",
                "updated_at": "2025-04-11T12:00:00Z"
            }
        }


# Request/Response schemas

class FolderUploadInitRequest(PydanticBaseModel):
    """Schema for initializing a folder upload"""
    name: str = Field(..., min_length=1, max_length=100)
    root_folder_name: str = Field(..., min_length=1, max_length=255)
    category: str = Field(default="document", pattern="^(document|code|data)$")
    total_files: int = Field(..., ge=1, le=1000)
    total_size: int = Field(..., ge=1, le=500 * 1024 * 1024)  # Max 500MB
    max_depth: int = Field(..., ge=0, le=10)
    file_manifest: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Optional list of files with relative_path and file_size"
    )


class FolderUploadInitResponse(PydanticBaseModel):
    """Schema for folder upload initialization response"""
    upload_id: str
    project_id: str
    s3_prefix: str
    status: str
    message: str


class FolderFileUploadRequest(PydanticBaseModel):
    """Schema for uploading files to a folder"""
    relative_paths: List[str] = Field(
        ...,
        min_items=1,
        max_items=50,
        description="Relative paths corresponding to uploaded files"
    )


class BatchUploadResponse(PydanticBaseModel):
    """Schema for batch upload response"""
    upload_id: str
    files_uploaded: int
    files_failed: int
    total_size: int
    results: List[Dict[str, Any]]


class FolderUploadCompleteResponse(PydanticBaseModel):
    """Schema for folder upload completion response"""
    upload_id: str
    data_source_id: str
    status: str
    total_files: int
    total_size: int
    message: str


class FolderFileListResponse(PydanticBaseModel):
    """Schema for folder file listing response"""
    data_source_id: str
    upload_id: str
    root_folder_name: str
    total_files: int
    total_size: int
    files: List[Dict[str, Any]]
    tree: Optional[Dict[str, Any]] = None  # Tree structure for UI


class FolderFileResponse(PydanticBaseModel):
    """Schema for single file response"""
    id: str
    relative_path: str
    filename: str
    file_extension: str
    file_size: int
    content_type: str
    download_url: str
    preview_supported: bool
    created_at: str


class FolderUploadResponse(PydanticBaseModel):
    """Schema for folder upload response"""
    id: str
    project_id: str
    data_source_id: Optional[str]
    name: str
    root_folder_name: str
    category: str
    total_files: int
    total_size: int
    max_depth: int
    status: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True
