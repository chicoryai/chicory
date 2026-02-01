import pytest
import json
from fastapi.testclient import TestClient
from httpx import AsyncClient
import pytest_asyncio

@pytest.mark.asyncio
async def test_list_data_source_types(client: TestClient):
    """Test listing all available data source types"""
    response = client.get("/data-source-types")
    assert response.status_code == 200
    data = response.json()
    assert "data_source_types" in data
    assert len(data["data_source_types"]) >= 6  # We defined 6 types
    
    # Verify structure of a data source type
    first_type = data["data_source_types"][0]
    assert "id" in first_type
    assert "name" in first_type
    assert "category" in first_type
    assert "required_fields" in first_type

@pytest.mark.asyncio
async def test_create_data_source(client: TestClient, test_project_data: dict, test_data_source_data: dict):
    """Test creating a new data source"""
    # First create a project
    project_response = client.post("/projects", json=test_project_data)
    project_id = project_response.json()["id"]
    
    # Create a data source
    response = client.post(f"/projects/{project_id}/data-sources", json=test_data_source_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == test_data_source_data["name"]
    assert data["type"] == test_data_source_data["type"]
    assert data["project_id"] == project_id
    assert data["status"] == "configured"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data
    
    # Return data source ID for other tests
    return data["id"], project_id

@pytest.mark.asyncio
async def test_validate_data_source(client: TestClient, test_project_data: dict, test_data_source_data: dict):
    """Test validating a data source connection"""
    # First create a project and data source
    project_response = client.post("/projects", json=test_project_data)
    project_id = project_response.json()["id"]
    ds_response = client.post(f"/projects/{project_id}/data-sources", json=test_data_source_data)
    data_source_id = ds_response.json()["id"]
    
    # Validate the data source
    response = client.post(f"/projects/{project_id}/data-sources/{data_source_id}/validate")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "message" in data

@pytest.mark.asyncio
async def test_list_data_sources(client: TestClient, test_project_data: dict, test_data_source_data: dict):
    """Test listing data sources for a project"""
    # First create a project
    project_response = client.post("/projects", json=test_project_data)
    project_id = project_response.json()["id"]
    
    # Create multiple data sources
    client.post(f"/projects/{project_id}/data-sources", json=test_data_source_data)
    client.post(f"/projects/{project_id}/data-sources", json={
        "type": "direct_upload",
        "name": "Test Document Upload",
        "configuration": {}
    })
    
    # List all data sources for the project
    response = client.get(f"/projects/{project_id}/data-sources")
    assert response.status_code == 200
    data = response.json()
    assert "data_sources" in data
    assert len(data["data_sources"]) >= 2
    
    # Verify all data sources belong to the project
    assert all(ds["project_id"] == project_id for ds in data["data_sources"])

@pytest.mark.asyncio
async def test_update_data_source(client: TestClient, test_project_data: dict, test_data_source_data: dict):
    """Test updating a data source"""
    # First create a project and data source
    project_response = client.post("/projects", json=test_project_data)
    project_id = project_response.json()["id"]
    ds_response = client.post(f"/projects/{project_id}/data-sources", json=test_data_source_data)
    data_source_id = ds_response.json()["id"]
    
    # Update the data source
    update_data = {
        "name": "Updated Data Source",
        "configuration": {
            "access_token": "updated_token",
            "repository_url": "https://github.com/updated/repo"
        }
    }
    response = client.put(f"/projects/{project_id}/data-sources/{data_source_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == update_data["name"]
    assert data["configuration"]["access_token"] == update_data["configuration"]["access_token"]
    
    # Verify the update
    list_response = client.get(f"/projects/{project_id}/data-sources")
    updated_ds = next(ds for ds in list_response.json()["data_sources"] if ds["id"] == data_source_id)
    assert updated_ds["name"] == update_data["name"]

@pytest.mark.asyncio
async def test_delete_data_source(client: TestClient, test_project_data: dict, test_data_source_data: dict):
    """Test deleting a data source"""
    # First create a project and data source
    project_response = client.post("/projects", json=test_project_data)
    project_id = project_response.json()["id"]
    ds_response = client.post(f"/projects/{project_id}/data-sources", json=test_data_source_data)
    data_source_id = ds_response.json()["id"]
    
    # Delete the data source
    response = client.delete(f"/projects/{project_id}/data-sources/{data_source_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "Data source deleted successfully"
    
    # Verify it's deleted by listing data sources
    list_response = client.get(f"/projects/{project_id}/data-sources")
    assert data_source_id not in [ds["id"] for ds in list_response.json()["data_sources"]]
