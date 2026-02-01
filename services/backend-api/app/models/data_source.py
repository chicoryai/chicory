import uuid
from typing import Optional, List, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel as PydanticBaseModel, Field, validator
from app.models.base import BaseModel
from beanie import Indexed

class DataSourceType(str, Enum):
    """Enum for data source types"""
    GOOGLE_DRIVE = "google_drive"
    GITHUB = "github"
    JIRA = "jira"
    DATABRICKS = "databricks"
    DIRECT_UPLOAD = "direct_upload"
    CSV_UPLOAD = "csv_upload"
    XLSX_UPLOAD = "xlsx_upload"
    GENERIC_FILE_UPLOAD = "generic_file_upload"
    FOLDER_UPLOAD = "folder_upload"
    SNOWFLAKE = "snowflake"
    BIGQUERY = "bigquery"
    GLUE = "glue"
    DATAZONE = "datazone"
    REDASH = "redash"
    DBT = "dbt"
    LOOKER = "looker"
    DATAHUB = "datahub"
    AIRFLOW = "airflow"
    ANTHROPIC = "anthropic"
    S3 = "s3"
    AZURE_BLOB_STORAGE = "azure_blob_storage"
    AZURE_DATA_FACTORY = "azure_data_factory"
    WEBFETCH = "webfetch"
    ATLAN = "atlan"

class DataSourceCategory(str, Enum):
    """Enum for data source categories"""
    DOCUMENT = "document"
    CODE = "code"
    DATA = "data"
    TOOL = "tool"

class DataSourceStatus(str, Enum):
    """Enum for data source status"""
    CONFIGURED = "configured"
    CONNECTED = "connected"
    ERROR = "error"
    SYNCING = "syncing"

class DataSourceFieldDefinition(PydanticBaseModel):
    """Schema for data source field definition"""
    name: str
    type: str
    description: str
    optional: bool = False

class DataSourceTypeDefinition(PydanticBaseModel):
    """Schema for data source type definition"""
    id: str
    name: str
    category: DataSourceCategory
    required_fields: List[DataSourceFieldDefinition]

class DataSourceTypeList(PydanticBaseModel):
    """Schema for list of data source types"""
    data_source_types: List[DataSourceTypeDefinition]

class DataSourceCreate(PydanticBaseModel):
    """Schema for creating a data source"""
    type: DataSourceType
    name: str = Field(..., min_length=1, max_length=100)
    configuration: Dict[str, Any] = Field(default_factory=dict)

class DataSourceUpdate(PydanticBaseModel):
    """Schema for updating a data source"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    configuration: Optional[Dict[str, Any]] = None

class DataSource(BaseModel):
    """Data source document model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    project_id: str
    type: DataSourceType
    name: Indexed(str)
    configuration: Dict[str, Any] = Field(default_factory=dict)
    status: DataSourceStatus = DataSourceStatus.CONFIGURED
    
    class Settings:
        name = "data_sources"
        
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_schema_extra = {
            "example": {
                "id": "a1b2c3d4-e5f6-7890-a1b2-c3d4e5f67890",
                "project_id": "12345678-90ab-cdef-1234-567890abcdef",
                "type": "github",
                "name": "My GitHub Repository",
                "configuration": {
                    "access_token": "access_token",
                    "username": "githubuser"
                },
                "status": "configured",
                "created_at": "2025-04-11T12:00:00Z",
                "updated_at": "2025-04-11T12:00:00Z"
            }
        }

class DataSourceResponse(PydanticBaseModel):
    """Schema for data source response"""
    id: str
    project_id: str
    type: str
    name: str
    configuration: Dict[str, Any]
    status: str
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True

class DataSourceList(PydanticBaseModel):
    """Schema for list of data sources"""
    data_sources: List[DataSourceResponse]

class DataSourceValidationResponse(PydanticBaseModel):
    """Schema for data source validation response"""
    status: str
    message: str

