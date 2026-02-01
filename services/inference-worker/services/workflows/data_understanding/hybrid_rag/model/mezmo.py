import os
import requests
from langchain.tools import BaseTool
from typing import Optional, Type
from pydantic.v1 import BaseModel, Field

class MezmoAPIInput(BaseModel):
    action: str = Field(..., description="Action to perform: 'list_pipelines', 'get_pipeline', 'create_pipeline', 'update_pipeline', 'delete_pipeline', 'get_pipeline_config', 'update_pipeline_config', 'get_pipeline_status', 'start_pipeline', 'stop_pipeline'")
    pipeline_id: Optional[str] = Field(None, description="ID of the specific pipeline")
    pipeline_config: Optional[dict] = Field(None, description="Configuration for creating or updating a pipeline")
    page: Optional[int] = Field(None, description="Page number for listing pipelines")
    page_size: Optional[int] = Field(None, description="Number of items per page for listing pipelines")

class MezmoAPITool(BaseTool):
    name: str = "MezmoAPI"
    description: str = "Tool for interacting with Mezmo Pipeline API to manage pipelines"
    args_schema: Type[BaseModel] = MezmoAPIInput

    api_key: str = Field(..., description="The API key to authenticate with Mezmo API")
    base_url: str = Field(default="https://api.mezmo.com", description="The base URL for Mezmo API")
    headers: dict = Field(default_factory=dict)

    def __init__(self, **data):
        super().__init__(**data)
        self.headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json"
        }

    def _list_pipelines(self, page: Optional[int] = None, page_size: Optional[int] = None) -> dict:
        """
        List all pipelines with optional pagination.

        :param page: Page number for pagination
        :param page_size: Number of items per page
        :return: JSON response containing list of pipelines
        """
        params = {}
        if page:
            params['page'] = page
        if page_size:
            params['page_size'] = page_size
        response = requests.get(f"{self.base_url}/v3/pipeline", headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    def _get_pipeline(self, pipeline_id: str) -> dict:
        """
        Get details of a specific pipeline.

        :param pipeline_id: ID of the pipeline to retrieve
        :return: JSON response containing pipeline details
        """
        response = requests.get(f"{self.base_url}/v3/pipeline/{pipeline_id}", headers=self.headers)
        response.raise_for_status()
        return response.json()

    def _create_pipeline(self, pipeline_config: dict) -> dict:
        """
        Create a new pipeline.

        :param pipeline_config: Configuration for the new pipeline
        :return: JSON response containing created pipeline details
        """
        response = requests.post(f"{self.base_url}/v3/pipeline", headers=self.headers, json=pipeline_config)
        response.raise_for_status()
        return response.json()

    def _update_pipeline(self, pipeline_id: str, pipeline_config: dict) -> dict:
        """
        Update an existing pipeline.

        :param pipeline_id: ID of the pipeline to update
        :param pipeline_config: Updated configuration for the pipeline
        :return: JSON response containing updated pipeline details
        """
        response = requests.put(f"{self.base_url}/v3/pipeline/{pipeline_id}", headers=self.headers, json=pipeline_config)
        response.raise_for_status()
        return response.json()

    def _delete_pipeline(self, pipeline_id: str) -> dict:
        """
        Delete a pipeline.

        :param pipeline_id: ID of the pipeline to delete
        :return: JSON response confirming deletion
        """
        response = requests.delete(f"{self.base_url}/v3/pipeline/{pipeline_id}", headers=self.headers)
        response.raise_for_status()
        return response.json()

    def _get_pipeline_config(self, pipeline_id: str) -> dict:
        """
        Get the configuration of a specific pipeline.

        :param pipeline_id: ID of the pipeline to retrieve configuration for
        :return: JSON response containing pipeline configuration
        """
        response = requests.get(f"{self.base_url}/v3/pipeline/{pipeline_id}/config", headers=self.headers)
        response.raise_for_status()
        return response.json()

    def _update_pipeline_config(self, pipeline_id: str, pipeline_config: dict) -> dict:
        """
        Update the configuration of a specific pipeline.

        :param pipeline_id: ID of the pipeline to update configuration for
        :param pipeline_config: Updated configuration for the pipeline
        :return: JSON response containing updated pipeline configuration
        """
        response = requests.put(f"{self.base_url}/v3/pipeline/{pipeline_id}/config", headers=self.headers, json=pipeline_config)
        response.raise_for_status()
        return response.json()

    def _get_pipeline_status(self, pipeline_id: str) -> dict:
        """
        Get the status of a specific pipeline.

        :param pipeline_id: ID of the pipeline to retrieve status for
        :return: JSON response containing pipeline status
        """
        response = requests.get(f"{self.base_url}/v3/pipeline/{pipeline_id}/status", headers=self.headers)
        response.raise_for_status()
        return response.json()

    def _start_pipeline(self, pipeline_id: str) -> dict:
        """
        Start a specific pipeline.

        :param pipeline_id: ID of the pipeline to start
        :return: JSON response confirming pipeline start
        """
        response = requests.post(f"{self.base_url}/v3/pipeline/{pipeline_id}/start", headers=self.headers)
        response.raise_for_status()
        return response.json()

    def _stop_pipeline(self, pipeline_id: str) -> dict:
        """
        Stop a specific pipeline.

        :param pipeline_id: ID of the pipeline to stop
        :return: JSON response confirming pipeline stop
        """
        response = requests.post(f"{self.base_url}/v3/pipeline/{pipeline_id}/stop", headers=self.headers)
        response.raise_for_status()
        return response.json()

    def _run(self, action: str, pipeline_id: Optional[str] = None, pipeline_config: Optional[dict] = None, page: Optional[int] = None, page_size: Optional[int] = None) -> dict:
        """
        Run the specified action on the Mezmo Pipeline API.

        :param action: The action to perform
        :param pipeline_id: ID of the pipeline (if required)
        :param pipeline_config: Configuration for creating or updating a pipeline (if required)
        :param page: Page number for listing pipelines (if required)
        :param page_size: Number of items per page for listing pipelines (if required)
        :return: JSON response from the API
        """
        if action == "list_pipelines":
            return self._list_pipelines(page, page_size)
        elif action == "get_pipeline":
            if not pipeline_id:
                raise ValueError("pipeline_id is required for get_pipeline action")
            return self._get_pipeline(pipeline_id)
        elif action == "create_pipeline":
            if not pipeline_config:
                raise ValueError("pipeline_config is required for create_pipeline action")
            return self._create_pipeline(pipeline_config)
        elif action == "update_pipeline":
            if not pipeline_id or not pipeline_config:
                raise ValueError("pipeline_id and pipeline_config are required for update_pipeline action")
            return self._update_pipeline(pipeline_id, pipeline_config)
        elif action == "delete_pipeline":
            if not pipeline_id:
                raise ValueError("pipeline_id is required for delete_pipeline action")
            return self._delete_pipeline(pipeline_id)
        elif action == "get_pipeline_config":
            if not pipeline_id:
                raise ValueError("pipeline_id is required for get_pipeline_config action")
            return self._get_pipeline_config(pipeline_id)
        elif action == "update_pipeline_config":
            if not pipeline_id or not pipeline_config:
                raise ValueError("pipeline_id and pipeline_config are required for update_pipeline_config action")
            return self._update_pipeline_config(pipeline_id, pipeline_config)
        elif action == "get_pipeline_status":
            if not pipeline_id:
                raise ValueError("pipeline_id is required for get_pipeline_status action")
            return self._get_pipeline_status(pipeline_id)
        elif action == "start_pipeline":
            if not pipeline_id:
                raise ValueError("pipeline_id is required for start_pipeline action")
            return self._start_pipeline(pipeline_id)
        elif action == "stop_pipeline":
            if not pipeline_id:
                raise ValueError("pipeline_id is required for stop_pipeline action")
            return self._stop_pipeline(pipeline_id)
        else:
            raise ValueError(f"Invalid action: {action}")

    def run(self, tool_input: MezmoAPIInput, **kwargs) -> dict:
        """
        Execute the Mezmo Pipeline API tool with the given input.

        :param tool_input: Input parameters for the tool
        :param kwargs: Additional keyword arguments
        :return: JSON response from the API
        """
        return self._run(
            action=tool_input.action,
            pipeline_id=tool_input.pipeline_id,
            pipeline_config=tool_input.pipeline_config,
            page=tool_input.page,
            page_size=tool_input.page_size
        )
    