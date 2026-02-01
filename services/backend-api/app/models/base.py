from datetime import datetime
from typing import Optional
from pydantic import Field
from beanie import Document

class BaseModel(Document):
    """Base model for all database documents"""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
