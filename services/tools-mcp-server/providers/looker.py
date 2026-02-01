"""
Looker provider for analytics operations.
"""

import logging
import aiohttp
import asyncio
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

from providers.base import ToolsProvider

logger = logging.getLogger(__name__)


class LookerProvider(ToolsProvider):
    """
    Looker provider for analytics operations using Looker API.
    """

    def __init__(self):
        super().__init__()
        self.base_url: Optional[str] = None
        self.client_id: Optional[str] = None
        self.client_secret: Optional[str] = None
        self.access_token: Optional[str] = None
        self.session: Optional[aiohttp.ClientSession] = None

    async def _initialize_client(self) -> None:
        """Initialize Looker API client with credentials."""
        if not self.credentials:
            raise ValueError("No credentials provided")

        # Extract Looker connection parameters
        self.base_url = self.credentials.get("base_url")
        self.client_id = self.credentials.get("client_id")
        self.client_secret = self.credentials.get("client_secret")

        # Validate required parameters
        if not all([self.base_url, self.client_id, self.client_secret]):
            raise ValueError("Missing required Looker credentials: base_url, client_id, client_secret")

        # Ensure base_url ends with /api/4.0 if not already
        if not self.base_url.endswith('/api/4.0'):
            if self.base_url.endswith('/'):
                self.base_url = self.base_url + 'api/4.0'
            else:
                self.base_url = self.base_url + '/api/4.0'

        # Create HTTP session
        self.session = aiohttp.ClientSession()

        # Authenticate and get access token
        await self._authenticate()

        logger.info("Looker provider initialized successfully")

    async def _authenticate(self) -> None:
        """Authenticate with Looker and get access token."""
        auth_url = f"{self.base_url}/login"

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }

        async with self.session.post(auth_url, data=data) as response:
            if response.status != 200:
                error_text = await response.text()
                raise ValueError(f"Looker authentication failed: {error_text}")

            auth_result = await response.json()
            self.access_token = auth_result.get("access_token")

            if not self.access_token:
                raise ValueError("No access token received from Looker")

        logger.info("Looker authentication successful")

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make authenticated request to Looker API."""
        self._ensure_initialized()

        if not self.access_token:
            await self._authenticate()

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        try:
            async with self.session.request(method, url, headers=headers, **kwargs) as response:
                if response.status == 401:
                    # Token might be expired, try re-authenticating
                    await self._authenticate()
                    headers["Authorization"] = f"Bearer {self.access_token}"

                    async with self.session.request(method, url, headers=headers, **kwargs) as retry_response:
                        if retry_response.status != 200:
                            error_text = await retry_response.text()
                            return {"error": f"HTTP {retry_response.status}: {error_text}"}
                        return await retry_response.json()

                elif response.status != 200:
                    error_text = await response.text()
                    return {"error": f"HTTP {response.status}: {error_text}"}

                return await response.json()

        except Exception as e:
            logger.error(f"Looker API request failed: {e}")
            return {"error": str(e)}

    async def get_models(self) -> Dict[str, Any]:
        """Get all Looker models."""
        self._log_operation("get_models")

        result = await self._make_request("GET", "/lookml_models")

        if isinstance(result, list):
            return {"models": result}
        elif "error" in result:
            return result
        else:
            return {"models": []}

    async def get_explores(self, model_name: str) -> Dict[str, Any]:
        """Get explores for a specific model."""
        self._log_operation("get_explores", model_name=model_name)

        result = await self._make_request("GET", f"/lookml_models/{model_name}/explores")

        if isinstance(result, list):
            return {"explores": result}
        elif "error" in result:
            return result
        else:
            return {"explores": []}

    async def get_dimensions(self, model_name: str, explore_name: str) -> Dict[str, Any]:
        """Get dimensions for a specific explore."""
        self._log_operation("get_dimensions", model_name=model_name, explore_name=explore_name)

        result = await self._make_request("GET", f"/lookml_models/{model_name}/explores/{explore_name}")

        if "error" in result:
            return result

        dimensions = []
        for dimension_group in result.get("dimension_groups", []):
            dimensions.extend(dimension_group.get("dimensions", []))

        dimensions.extend(result.get("dimensions", []))

        return {"dimensions": dimensions}

    async def get_measures(self, model_name: str, explore_name: str) -> Dict[str, Any]:
        """Get measures for a specific explore."""
        self._log_operation("get_measures", model_name=model_name, explore_name=explore_name)

        result = await self._make_request("GET", f"/lookml_models/{model_name}/explores/{explore_name}")

        if "error" in result:
            return result

        measures = result.get("measures", [])
        return {"measures": measures}

    async def get_filters(self, model_name: str, explore_name: str) -> Dict[str, Any]:
        """Get filters for a specific explore."""
        self._log_operation("get_filters", model_name=model_name, explore_name=explore_name)

        result = await self._make_request("GET", f"/lookml_models/{model_name}/explores/{explore_name}")

        if "error" in result:
            return result

        filters = result.get("filters", [])
        return {"filters": filters}

    async def query(self, model_name: str, explore_name: str, dimensions: List[str],
                    measures: List[str], filters: Optional[Dict[str, str]] = None,
                    limit: int = 100) -> Dict[str, Any]:
        """Execute a Looker query."""
        self._log_operation("query", model_name=model_name, explore_name=explore_name,
                            dimensions=dimensions, measures=measures, filters=filters, limit=limit)

        query_body = {
            "model": model_name,
            "explore": explore_name,
            "fields": dimensions + measures,
            "limit": limit
        }

        if filters:
            query_body["filters"] = filters

        # Create and run query
        create_result = await self._make_request("POST", "/queries", json=query_body)

        if "error" in create_result:
            return create_result

        query_id = create_result.get("id")
        if not query_id:
            return {"error": "No query ID returned"}

        # Run the query
        run_result = await self._make_request("GET", f"/queries/{query_id}/run/json")

        if "error" in run_result:
            return run_result

        # Format results
        if isinstance(run_result, list):
            columns = []
            if run_result:
                columns = list(run_result[0].keys())

            return {
                "rows": run_result,
                "columns": columns
            }
        else:
            return {"error": "Unexpected query result format"}

    async def query_sql(self, sql: str) -> Dict[str, Any]:
        """Execute raw SQL query."""
        self._log_operation("query_sql", sql=sql[:100])

        query_body = {
            "sql": sql
        }

        result = await self._make_request("POST", "/sql_queries", json=query_body)

        if "error" in result:
            return result

        # The result should contain the query results directly
        if isinstance(result, dict) and "data" in result:
            data = result["data"]
            columns = []
            if data and isinstance(data, list) and data:
                columns = list(data[0].keys())

            return {
                "rows": data,
                "columns": columns
            }
        else:
            return {"error": "Unexpected SQL query result format"}

    async def get_looks(self, folder_id: Optional[str] = None) -> Dict[str, Any]:
        """Get all Looks (saved queries)."""
        self._log_operation("get_looks", folder_id=folder_id)

        endpoint = "/looks"
        if folder_id:
            endpoint += f"?folder_id={folder_id}"

        result = await self._make_request("GET", endpoint)

        if isinstance(result, list):
            return {"looks": result}
        elif "error" in result:
            return result
        else:
            return {"looks": []}

    async def run_look(self, look_id: str, limit: int = 100) -> Dict[str, Any]:
        """Run a specific Look and get results."""
        self._log_operation("run_look", look_id=look_id, limit=limit)

        # First get Look details
        look_result = await self._make_request("GET", f"/looks/{look_id}")

        if "error" in look_result:
            return look_result

        # Run the Look
        run_result = await self._make_request("GET", f"/looks/{look_id}/run/json",
                                              params={"limit": limit})

        if "error" in run_result:
            return run_result

        # Format results
        if isinstance(run_result, list):
            columns = []
            if run_result:
                columns = list(run_result[0].keys())

            return {
                "rows": run_result,
                "columns": columns,
                "look_info": {
                    "title": look_result.get("title"),
                    "model": look_result.get("model", {}).get("name"),
                    "explore": look_result.get("explore")
                }
            }
        else:
            return {"error": "Unexpected Look result format"}

    async def query_url(self, model_name: str, explore_name: str, dimensions: List[str],
                        measures: List[str], filters: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Generate URL for a Looker query."""
        self._log_operation("query_url", model_name=model_name, explore_name=explore_name,
                            dimensions=dimensions, measures=measures, filters=filters)

        # Build query parameters
        fields = dimensions + measures
        params = {
            "fields": ",".join(fields)
        }

        if filters:
            for key, value in filters.items():
                params[f"f[{key}]"] = value

        query_string = urlencode(params)

        # Construct Looker explore URL
        base_explore_url = self.base_url.replace("/api/4.0", "")
        url = f"{base_explore_url}/explore/{model_name}/{explore_name}?{query_string}"

        return {"url": url}

    async def get_parameters(self, model_name: str, explore_name: str) -> Dict[str, Any]:
        """Get parameters for a specific explore."""
        self._log_operation("get_parameters", model_name=model_name, explore_name=explore_name)

        result = await self._make_request("GET", f"/lookml_models/{model_name}/explores/{explore_name}")

        if "error" in result:
            return result

        parameters = result.get("parameters", [])
        return {"parameters": parameters}

    async def cleanup(self) -> None:
        """Clean up Looker provider resources."""
        if self.session:
            await self.session.close()
            self.session = None

        self.access_token = None
        await super().cleanup()
