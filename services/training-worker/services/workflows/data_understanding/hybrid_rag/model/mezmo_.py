import os
import requests
from langchain.tools import BaseTool
from typing import Optional, Type
from pydantic.v1 import BaseModel, Field

class MezmoAPIInput(BaseModel):
    action: str = Field(..., description="Action to perform: 'list_pipelines', 'get_pipeline', 'create_pipeline', 'update_pipeline', 'delete_pipeline', 'get_pipeline_config', 'update_pipeline_config', 'get_pipeline_status', 'start_pipeline', 'stop_pipeline', 'list_views', 'create_view', 'get_view', 'update_view', 'delete_view', 'list_preset_alerts', 'create_preset_alert', 'get_preset_alert', 'update_preset_alert', 'delete_preset_alert', 'list_categories', 'create_category', 'get_category', 'update_category', 'delete_category', 'get_index_rate_alert', 'update_index_rate_alert'")
    pipeline_id: Optional[str] = Field(None, description="ID of the specific pipeline")
    pipeline_config: Optional[dict] = Field(None, description="Configuration for creating or updating a pipeline")
    page: Optional[int] = Field(None, description="Page number for listing pipelines")
    page_size: Optional[int] = Field(None, description="Number of items per page for listing pipelines")
    view_id: Optional[str] = Field(None, description="ID of the specific view")
    view_config: Optional[dict] = Field(None, description="Configuration for creating or updating a view")
    preset_alert_id: Optional[str] = Field(None, description="ID of the specific preset alert")
    preset_alert_config: Optional[dict] = Field(None, description="Configuration for creating or updating a preset alert")
    category_type: Optional[str] = Field(None, description="Type of category (views, boards, screens)")
    category_id: Optional[str] = Field(None, description="ID of the specific category")
    category_config: Optional[dict] = Field(None, description="Configuration for creating or updating a category")
    index_rate_alert_config: Optional[dict] = Field(None, description="Configuration for updating an index rate alert")

class MezmoAPITool(BaseTool):
    name: str = "MezmoAPI"
    description: str = "Tool for interacting with Mezmo API to manage pipelines, views, preset alerts, categories, and index rate alerts"
    args_schema: Type[BaseModel] = MezmoAPIInput

    api_key: str = Field(..., description="The API key to authenticate with Mezmo API")
    base_url: str = Field(default="https://api.mezmo.com", description="The base URL for Mezmo API")
    headers: dict = Field(default_factory=dict)

    def __init__(self, **data):
        super().__init__(**data)
        self.headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json",
            "servicekey": self.api_key,
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
        response = requests.get(f"{self.base_url}/v1/pipelines", headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    def _get_pipeline(self, pipeline_id: str) -> dict:
        """
        Get details of a specific pipeline.

        :param pipeline_id: ID of the pipeline to retrieve
        :return: JSON response containing pipeline details
        """
        response = requests.get(f"{self.base_url}/v1/pipelines/{pipeline_id}", headers=self.headers)
        response.raise_for_status()
        return response.json()

    def _create_pipeline(self, pipeline_config: dict) -> dict:
        """
        Create a new pipeline.

        :param pipeline_config: Configuration for the new pipeline
        :return: JSON response containing created pipeline details
        """
        response = requests.post(f"{self.base_url}/v1/pipelines", headers=self.headers, json=pipeline_config)
        response.raise_for_status()
        return response.json()

    def _update_pipeline(self, pipeline_id: str, pipeline_config: dict) -> dict:
        """
        Update an existing pipeline.

        :param pipeline_id: ID of the pipeline to update
        :param pipeline_config: Updated configuration for the pipeline
        :return: JSON response containing updated pipeline details
        """
        response = requests.put(f"{self.base_url}/v1/pipelines/{pipeline_id}", headers=self.headers, json=pipeline_config)
        response.raise_for_status()
        return response.json()

    def _delete_pipeline(self, pipeline_id: str) -> dict:
        """
        Delete a pipeline.

        :param pipeline_id: ID of the pipeline to delete
        :return: JSON response confirming deletion
        """
        response = requests.delete(f"{self.base_url}/v1/pipelines/{pipeline_id}", headers=self.headers)
        response.raise_for_status()
        return response.json()

    def _get_pipeline_config(self, pipeline_id: str) -> dict:
        """
        Get the configuration of a specific pipeline.

        :param pipeline_id: ID of the pipeline to retrieve configuration for
        :return: JSON response containing pipeline configuration
        """
        response = requests.get(f"{self.base_url}/v1/pipelines/{pipeline_id}/config", headers=self.headers)
        response.raise_for_status()
        return response.json()

    def _update_pipeline_config(self, pipeline_id: str, pipeline_config: dict) -> dict:
        """
        Update the configuration of a specific pipeline.

        :param pipeline_id: ID of the pipeline to update configuration for
        :param pipeline_config: Updated configuration for the pipeline
        :return: JSON response containing updated pipeline configuration
        """
        response = requests.put(f"{self.base_url}/v1/pipelines/{pipeline_id}/config", headers=self.headers, json=pipeline_config)
        response.raise_for_status()
        return response.json()

    def _get_pipeline_status(self, pipeline_id: str) -> dict:
        """
        Get the status of a specific pipeline.

        :param pipeline_id: ID of the pipeline to retrieve status for
        :return: JSON response containing pipeline status
        """
        response = requests.get(f"{self.base_url}/v1/pipelines/{pipeline_id}/status", headers=self.headers)
        response.raise_for_status()
        return response.json()

    def _start_pipeline(self, pipeline_id: str) -> dict:
        """
        Start a specific pipeline.

        :param pipeline_id: ID of the pipeline to start
        :return: JSON response confirming pipeline start
        """
        response = requests.post(f"{self.base_url}/v1/pipelines/{pipeline_id}/start", headers=self.headers)
        response.raise_for_status()
        return response.json()

    def _stop_pipeline(self, pipeline_id: str) -> dict:
        """
        Stop a specific pipeline.

        :param pipeline_id: ID of the pipeline to stop
        :return: JSON response confirming pipeline stop
        """
        response = requests.post(f"{self.base_url}/v1/pipelines/{pipeline_id}/stop", headers=self.headers)
        response.raise_for_status()
        return response.json()

    def _list_views(self) -> dict:
        """
        List all views.

        :return: JSON response containing list of views
        """
        response = requests.get(f"{self.base_url}/v1/config/view", headers=self.headers)
        response.raise_for_status()
        return response.json()

    def _create_view(self, view_config: dict) -> dict:
        """
        Create a new view.

        :param view_config: Configuration for the new view
        :return: JSON response containing created view details
        """
        response = requests.post(f"{self.base_url}/v1/config/view", headers=self.headers, json=view_config)
        response.raise_for_status()
        return response.json()

    def _get_view(self, view_id: str) -> dict:
        """
        Get details of a specific view.

        :param view_id: ID of the view to retrieve
        :return: JSON response containing view details
        """
        response = requests.get(f"{self.base_url}/v1/config/view/{view_id}", headers=self.headers)
        response.raise_for_status()
        return response.json()

    def _update_view(self, view_id: str, view_config: dict) -> dict:
        """
        Update an existing view.

        :param view_id: ID of the view to update
        :param view_config: Updated configuration for the view
        :return: JSON response containing updated view details
        """
        response = requests.put(f"{self.base_url}/v1/config/view/{view_id}", headers=self.headers, json=view_config)
        response.raise_for_status()
        return response.json()

    def _delete_view(self, view_id: str) -> dict:
        """
        Delete a view.

        :param view_id: ID of the view to delete
        :return: JSON response confirming deletion
        """
        response = requests.delete(f"{self.base_url}/v1/config/view/{view_id}", headers=self.headers)
        response.raise_for_status()
        return response.json()

    def _list_preset_alerts(self) -> dict:
        """
        List all preset alerts.

        :return: JSON response containing list of preset alerts
        """
        response = requests.get(f"{self.base_url}/v1/config/presetalert", headers=self.headers)
        response.raise_for_status()
        return response.json()

    def _create_preset_alert(self, preset_alert_config: dict) -> dict:
        """
        Create a new preset alert.

        :param preset_alert_config: Configuration for the new preset alert
        :return: JSON response containing created preset alert details
        """
        response = requests.post(f"{self.base_url}/v1/config/presetalert", headers=self.headers, json=preset_alert_config)
        response.raise_for_status()
        return response.json()

    def _get_preset_alert(self, preset_alert_id: str) -> dict:
        """
        Get details of a specific preset alert.

        :param preset_alert_id: ID of the preset alert to retrieve
        :return: JSON response containing preset alert details
        """
        response = requests.get(f"{self.base_url}/v1/config/presetalert/{preset_alert_id}", headers=self.headers)
        response.raise_for_status()
        return response.json()

    def _update_preset_alert(self, preset_alert_id: str, preset_alert_config: dict) -> dict:
        """
        Update an existing preset alert.

        :param preset_alert_id: ID of the preset alert to update
        :param preset_alert_config: Updated configuration for the preset alert
        :return: JSON response containing updated preset alert details
        """
        response = requests.put(f"{self.base_url}/v1/config/presetalert/{preset_alert_id}", headers=self.headers, json=preset_alert_config)
        response.raise_for_status()
        return response.json()

    def _delete_preset_alert(self, preset_alert_id: str) -> dict:
        """
        Delete a preset alert.

        :param preset_alert_id: ID of the preset alert to delete
        :return: JSON response confirming deletion
        """
        response = requests.delete(f"{self.base_url}/v1/config/presetalert/{preset_alert_id}", headers=self.headers)
        response.raise_for_status()
        return response.json()

    def _list_categories(self, category_type: str) -> dict:
        """
        List all categories of a specific type.

        :param category_type: Type of category (views, boards, screens)
        :return: JSON response containing list of categories
        """
        response = requests.get(f"{self.base_url}/v1/config/categories/{category_type}", headers=self.headers)
        response.raise_for_status()
        return response.json()

    def _create_category(self, category_type: str, category_config: dict) -> dict:
        """
        Create a new category of a specific type.

        :param category_type: Type of category (views, boards, screens)
        :param category_config: Configuration for the new category
        :return: JSON response containing created category details
        """
        response = requests.post(f"{self.base_url}/v1/config/categories/{category_type}", headers=self.headers, json=category_config)
        response.raise_for_status()
        return response.json()

    def _get_category(self, category_type: str, category_id: str) -> dict:
        """
        Get details of a specific category.

        :param category_type: Type of category (views, boards, screens)
        :param category_id: ID of the category to retrieve
        :return: JSON response containing category details
        """
        response = requests.get(f"{self.base_url}/v1/config/categories/{category_type}/{category_id}", headers=self.headers)
        response.raise_for_status()
        return response.json()

    def _update_category(self, category_type: str, category_id: str, category_config: dict) -> dict:
        """
        Update an existing category.

        :param category_type: Type of category (views, boards, screens)
        :param category_id: ID of the category to update
        :param category_config: Updated configuration for the category
        :return: JSON response containing updated category details
        """
        response = requests.put(f"{self.base_url}/v1/config/categories/{category_type}/{category_id}", headers=self.headers, json=category_config)
        response.raise_for_status()
        return response.json()

    def _delete_category(self, category_type: str, category_id: str) -> dict:
        """
        Delete a category.

        :param category_type: Type of category (views, boards, screens)
        :param category_id: ID of the category to delete
        :return: JSON response confirming deletion
        """
        response = requests.delete(f"{self.base_url}/v1/config/categories/{category_type}/{category_id}", headers=self.headers)
        response.raise_for_status()
        return response.json()

    def _get_index_rate_alert(self) -> dict:
        """
        Get the configuration for an Index Rate Alert.

        :return: JSON response containing index rate alert configuration
        """
        response = requests.get(f"{self.base_url}/v1/config/index-rate", headers=self.headers)
        response.raise_for_status()
        return response.json()

    def _update_index_rate_alert(self, index_rate_alert_config: dict) -> dict:
        """
        Update an index rate alert.

        :param index_rate_alert_config: Updated configuration for the index rate alert
        :return: JSON response containing updated index rate alert configuration
        """
        response = requests.put(f"{self.base_url}/v1/config/index-rate", headers=self.headers, json=index_rate_alert_config)
        response.raise_for_status()
        return response.json()

    def _run(self, action: str, **kwargs) -> dict:
        """
        Run the specified action on the Mezmo API.

        :param action: The action to perform
        :param kwargs: Additional keyword arguments for the specific action
        :return: JSON response from the API
        """
        if action == "list_views":
            return self._list_views()
        elif action == "create_view":
            return self._create_view(kwargs.get("view_config"))
        elif action == "get_view":
            return self._get_view(kwargs.get("view_id"))
        elif action == "update_view":
            return self._update_view(kwargs.get("view_id"), kwargs.get("view_config"))
        elif action == "delete_view":
            return self._delete_view(kwargs.get("view_id"))
        elif action == "list_preset_alerts":
            return self._list_preset_alerts()
        elif action == "create_preset_alert":
            return self._create_preset_alert(kwargs.get("preset_alert_config"))
        elif action == "get_preset_alert":
            return self._get_preset_alert(kwargs.get("preset_alert_id"))
        elif action == "update_preset_alert":
            return self._update_preset_alert(kwargs.get("preset_alert_id"), kwargs.get("preset_alert_config"))
        elif action == "delete_preset_alert":
            return self._delete_preset_alert(kwargs.get("preset_alert_id"))
        elif action == "list_categories":
            return self._list_categories(kwargs.get("category_type"))
        elif action == "create_category":
            return self._create_category(kwargs.get("category_type"), kwargs.get("category_config"))
        elif action == "get_category":
            return self._get_category(kwargs.get("category_type"), kwargs.get("category_id"))
        elif action == "update_category":
            return self._update_category(kwargs.get("category_type"), kwargs.get("category_id"), kwargs.get("category_config"))
        elif action == "delete_category":
            return self._delete_category(kwargs.get("category_type"), kwargs.get("category_id"))
        elif action == "get_index_rate_alert":
            return self._get_index_rate_alert()
        elif action == "update_index_rate_alert":
            return self._update_index_rate_alert(kwargs.get("index_rate_alert_config"))
        else:
            # Handle existing pipeline actions
            return super()._run(action, **kwargs)

    def run(self, tool_input: MezmoAPIInput, **kwargs) -> dict:
        """
        Execute the Mezmo API tool with the given input.

        :param tool_input: Input parameters for the tool
        :param kwargs: Additional keyword arguments
        :return: JSON response from the API
        """
        return self._run(
            action=tool_input.action,
            pipeline_id=tool_input.pipeline_id,
            pipeline_config=tool_input.pipeline_config,
            page=tool_input.page,
            page_size=tool_input.page_size,
            view_id=tool_input.view_id,
            view_config=tool_input.view_config,
            preset_alert_id=tool_input.preset_alert_id,
            preset_alert_config=tool_input.preset_alert_config,
            category_type=tool_input.category_type,
            category_id=tool_input.category_id,
            category_config=tool_input.category_config,
            index_rate_alert_config=tool_input.index_rate_alert_config
        )