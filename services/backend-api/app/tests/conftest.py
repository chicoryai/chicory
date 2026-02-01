import os
import pytest
import asyncio
from typing import Generator, Any
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from app.main import app
from app.database.connection import db
from app.models.project import Project
from app.models.data_source import DataSource

# Set test environment
os.environ["TESTING"] = "True"
os.environ["MONGODB_URI"] = "mongodb://localhost:27017/test_db"

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def client() -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI app."""
    # Setup test database
    db.client = AsyncIOMotorClient(os.environ["MONGODB_URI"])
    await init_beanie(
        database=db.client.get_database("test_db"),
        document_models=[
            Project,
            DataSource
        ]
    )
    
    # Clear test database
    await Project.delete_all()
    await DataSource.delete_all()
    
    # Create test client
    with TestClient(app) as client:
        yield client
    
    # Cleanup
    await Project.delete_all()
    await DataSource.delete_all()
    db.client.close()

@pytest.fixture
def test_project_data() -> dict[str, Any]:
    """Test project data for use in tests."""
    return {
        "name": "Test Project",
        "organization_id": "test_org_123",
        "description": "A test project",
        "members": ["a1b2c3d4-e5f6-4789-a012-3456789abcde", "b2c3d4e5-f6a7-4890-b123-456789abcdef"]
    }

@pytest.fixture
def test_data_source_data() -> dict[str, Any]:
    """Test data source data for use in tests."""
    return {
        "type": "github",
        "name": "Test GitHub Repository",
        "configuration": {
            "access_token": "test_token",
            "repository_url": "https://github.com/test/repo"
        }
    }
