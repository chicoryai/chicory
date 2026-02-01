import pytest
import json
from fastapi.testclient import TestClient
from httpx import AsyncClient
import pytest_asyncio

@pytest.mark.asyncio
async def test_create_project(client: TestClient, test_project_data: dict):
    """Test creating a new project"""
    response = client.post("/projects", json=test_project_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == test_project_data["name"]
    assert data["description"] == test_project_data["description"]
    assert data["organization_id"] == test_project_data["organization_id"]
    assert data["members"] == test_project_data["members"]
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data

    # Save project ID for other tests
    return data["id"]

@pytest.mark.asyncio
async def test_get_project(client: TestClient, test_project_data: dict):
    """Test retrieving a project"""
    # First create a project
    create_response = client.post("/projects", json=test_project_data)
    project_id = create_response.json()["id"]

    # Then get the project
    response = client.get(f"/projects/{project_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == project_id
    assert data["name"] == test_project_data["name"]
    assert data["description"] == test_project_data["description"]
    assert data["members"] == test_project_data["members"]

@pytest.mark.asyncio
async def test_update_project(client: TestClient, test_project_data: dict):
    """Test updating a project"""
    # First create a project
    create_response = client.post("/projects", json=test_project_data)
    project_id = create_response.json()["id"]
    
    # Update the project
    update_data = {"name": "Updated Project Name", "description": "Updated description"}
    response = client.put(f"/projects/{project_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == update_data["name"]
    assert data["description"] == update_data["description"]
    
    # Verify the update
    get_response = client.get(f"/projects/{project_id}")
    assert get_response.json()["name"] == update_data["name"]

@pytest.mark.asyncio
async def test_list_projects(client: TestClient, test_project_data: dict):
    """Test listing projects"""
    # Create multiple projects
    client.post("/projects", json=test_project_data)
    client.post("/projects", json={
        "name": "Another Project",
        "organization_id": test_project_data["organization_id"],
        "description": "Another test project",
        "members": ["c3d4e5f6-a7b8-4901-c234-56789abcdef0"]
    })

    # List all projects
    response = client.get("/projects")
    assert response.status_code == 200
    data = response.json()
    assert "projects" in data
    assert len(data["projects"]) >= 2

    # Filter by organization_id
    response = client.get(f"/projects?organization_id={test_project_data['organization_id']}")
    assert response.status_code == 200
    data = response.json()
    assert all(p["organization_id"] == test_project_data["organization_id"] for p in data["projects"])
    # Verify all projects have members
    assert all("members" in p for p in data["projects"])

@pytest.mark.asyncio
async def test_delete_project(client: TestClient, test_project_data: dict):
    """Test deleting a project"""
    # First create a project
    create_response = client.post("/projects", json=test_project_data)
    project_id = create_response.json()["id"]

    # Delete the project
    response = client.delete(f"/projects/{project_id}")
    assert response.status_code == 204

    # Verify it's deleted
    get_response = client.get(f"/projects/{project_id}")
    assert get_response.status_code == 404

@pytest.mark.asyncio
async def test_invalid_members_uuid_format(client: TestClient, test_project_data: dict):
    """Test that invalid UUID format for members is rejected"""
    project_data = test_project_data.copy()
    project_data["members"] = [
        "a1b2c3d4-e5f6-4789-a012-3456789abcde",
        "not-a-valid-uuid"
    ]
    project_data["name"] = "Invalid Members UUID Project"

    response = client.post("/projects", json=project_data)
    assert response.status_code == 422
    assert "must be valid UUID format" in response.text

@pytest.mark.asyncio
async def test_update_members(client: TestClient, test_project_data: dict):
    """Test updating members field"""
    # Create a project
    create_response = client.post("/projects", json=test_project_data)
    project_id = create_response.json()["id"]

    # Update members
    new_members = ["b8c9d0e1-f2a3-4456-b789-abcdef012345", "c9d0e1f2-a3b4-4567-c890-bcdef0123456"]
    update_data = {"members": new_members}

    response = client.put(f"/projects/{project_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert set(data["members"]) == set(new_members)

@pytest.mark.asyncio
async def test_create_project_with_empty_members(client: TestClient, test_project_data: dict):
    """Test creating a project with empty members list"""
    project_data = test_project_data.copy()
    project_data["members"] = []
    project_data["name"] = "Empty Members Project"

    response = client.post("/projects", json=project_data)
    assert response.status_code == 201
    data = response.json()
    assert data["members"] == []
    assert data["name"] == project_data["name"]

@pytest.mark.asyncio
async def test_create_project_without_members_field(client: TestClient, test_project_data: dict):
    """Test backward compatibility - creating project without members field"""
    project_data = test_project_data.copy()
    del project_data["members"]
    project_data["name"] = "No Members Field Project"

    response = client.post("/projects", json=project_data)
    assert response.status_code == 201
    data = response.json()
    assert "members" in data
    assert data["members"] == []
    assert data["name"] == project_data["name"]

@pytest.mark.asyncio
async def test_duplicate_members(client: TestClient, test_project_data: dict):
    """Test creating project with duplicate member UUIDs"""
    project_data = test_project_data.copy()
    duplicate_uuid = "a1b2c3d4-e5f6-4789-a012-3456789abcde"
    project_data["members"] = [duplicate_uuid, duplicate_uuid]
    project_data["name"] = "Duplicate Members Project"

    response = client.post("/projects", json=project_data)
    # Should succeed - duplicates are allowed, business logic should handle deduplication if needed
    assert response.status_code == 201
    data = response.json()
    assert duplicate_uuid in data["members"]
