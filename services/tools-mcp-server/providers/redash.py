"""
Redash provider for analytics operations.
"""

import logging
import aiohttp
import asyncio
from typing import Any, Dict, List, Optional

from providers.base import ToolsProvider

logger = logging.getLogger(__name__)


class RedashProvider(ToolsProvider):
    """
    Redash provider for analytics operations using Redash API.
    """

    def __init__(self):
        super().__init__()
        self.base_url: Optional[str] = None
        self.api_key: Optional[str] = None
        self.session: Optional[aiohttp.ClientSession] = None

    async def _initialize_client(self) -> None:
        """Initialize Redash API client with credentials."""
        if not self.credentials:
            raise ValueError("No credentials provided")

        # Extract Redash connection parameters
        self.base_url = self.credentials.get("base_url")
        if "http" not in self.base_url:
            self.base_url = f"http://{self.base_url}"
        self.api_key = self.credentials.get("api_key")

        # Validate required parameters
        if not all([self.base_url, self.api_key]):
            raise ValueError("Missing required Redash credentials: base_url, api_key")

        # Ensure base_url ends with /api if not already
        if not self.base_url.endswith('/api'):
            if self.base_url.endswith('/'):
                self.base_url = self.base_url + 'api'
            else:
                self.base_url = self.base_url + '/api'

        # Create HTTP session
        self.session = aiohttp.ClientSession()

        logger.info("Redash provider initialized successfully")

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make authenticated request to Redash API."""
        self._ensure_initialized()

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json"
        }

        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        try:
            async with self.session.request(method, url, headers=headers, **kwargs) as response:
                if response.status not in [200, 201]:
                    error_text = await response.text()
                    return {"error": f"HTTP {response.status}: {error_text}"}

                return await response.json()

        except Exception as e:
            logger.error(f"Redash API request failed: {e}")
            return {"error": str(e)}

    async def list_queries(self, page: int = 1, page_size: int = 25) -> Dict[str, Any]:
        """List all queries in Redash."""
        self._log_operation("list_queries", page=page, page_size=page_size)

        params = {
            "page": page,
            "page_size": page_size
        }

        result = await self._make_request("GET", "/queries", params=params)

        if "error" in result:
            return result

        return {
            "queries": result.get("results", []),
            "count": result.get("count", 0),
            "page": page,
            "page_size": page_size
        }

    async def get_query(self, query_id: str) -> Dict[str, Any]:
        """Get details of a specific query."""
        self._log_operation("get_query", query_id=query_id)

        result = await self._make_request("GET", f"/queries/{query_id}")

        if "error" in result:
            return result

        return {"query": result}

    async def execute_query(self, query_id: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a query and return results."""
        self._log_operation("execute_query", query_id=query_id, parameters=parameters)

        # Prepare request body
        body = {}
        if parameters:
            body["parameters"] = parameters

        # Execute the query
        if body:
            result = await self._make_request("POST", f"/queries/{query_id}/results", json=body)
        else:
            result = await self._make_request("POST", f"/queries/{query_id}/results")

        if "error" in result:
            return result

        # Check if we got immediate results or a job
        if "job" in result:
            job_id = result["job"]["id"]
            return {"job_id": job_id, "job": result["job"]}
        elif "query_result" in result:
            return {"query_result": result["query_result"]}
        else:
            return result

    async def get_query_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get status of a query execution job."""
        self._log_operation("get_query_job_status", job_id=job_id)

        result = await self._make_request("GET", f"/jobs/{job_id}")

        if "error" in result:
            return result

        return {"job": result}

    async def get_query_results(self, query_result_id: str) -> Dict[str, Any]:
        """Get results of a completed query execution."""
        self._log_operation("get_query_results", query_result_id=query_result_id)

        result = await self._make_request("GET", f"/query_results/{query_result_id}")

        if "error" in result:
            return result

        return {"query_result": result}

    async def refresh_query(self, query_id: str) -> Dict[str, Any]:
        """Refresh a query (execute with fresh data)."""
        self._log_operation("refresh_query", query_id=query_id)

        result = await self._make_request("POST", f"/queries/{query_id}/refresh")

        if "error" in result:
            return result

        return {"job": result}

    async def list_dashboards(self, page: int = 1, page_size: int = 25) -> Dict[str, Any]:
        """List all dashboards in Redash."""
        self._log_operation("list_dashboards", page=page, page_size=page_size)

        params = {
            "page": page,
            "page_size": page_size
        }

        result = await self._make_request("GET", "/dashboards", params=params)

        if "error" in result:
            return result

        return {
            "dashboards": result.get("results", []),
            "count": result.get("count", 0),
            "page": page,
            "page_size": page_size
        }

    async def get_dashboard(self, dashboard_id: str) -> Dict[str, Any]:
        """Get details of a specific dashboard."""
        self._log_operation("get_dashboard", dashboard_id=dashboard_id)

        result = await self._make_request("GET", f"/dashboards/{dashboard_id}")

        if "error" in result:
            return result

        return {"dashboard": result}

    async def list_data_sources(self) -> Dict[str, Any]:
        """List all data sources in Redash."""
        self._log_operation("list_data_sources")

        result = await self._make_request("GET", "/data_sources")

        if "error" in result:
            return result

        if isinstance(result, list):
            return {"data_sources": result}
        else:
            return {"data_sources": result.get("results", [])}
    
    async def create_query(self, data_source_id: str, name: str, query: str, 
                         description: str = "", schedule: Optional[Dict[str, Any]] = None,
                         options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a new query in Redash."""
        self._log_operation("create_query", data_source_id=data_source_id, name=name)
        
        payload = {
            "name": name,
            "query": query,
            "data_source_id": int(data_source_id),
            "description": description,
            "schedule": schedule,
            "options": options or {"parameters": []}
        }
        
        result = await self._make_request("POST", "/queries", json=payload)
        
        if "error" in result:
            return result
        
        return {"query": result}
    
    async def create_visualization(self, query_id: str, viz_type: str, name: str,
                                 options: Optional[Dict[str, Any]] = None,
                                 description: str = "") -> Dict[str, Any]:
        """Create a visualization for a query."""
        self._log_operation("create_visualization", query_id=query_id, viz_type=viz_type, name=name)
        
        payload = {
            "type": viz_type,
            "name": name,
            "description": description,
            "options": options or {},
            "query_id": int(query_id)
        }
        
        result = await self._make_request("POST", "/visualizations", json=payload)
        
        if "error" in result:
            return result
        
        return {"visualization": result}
    
    async def create_dashboard(self, name: str, layout: Optional[List[List[int]]] = None) -> Dict[str, Any]:
        """Create a new dashboard."""
        self._log_operation("create_dashboard", name=name)
        
        payload = {
            "name": name,
            "layout": layout or []
        }
        
        result = await self._make_request("POST", "/dashboards", json=payload)
        
        if "error" in result:
            return result
        
        return {"dashboard": result}
    
    async def add_widget(self, dashboard_id: str, 
                        visualization_id: Optional[str] = None,
                        text: Optional[str] = None,
                        full_width: bool = False,
                        position: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Add a widget to a dashboard."""
        self._log_operation("add_widget", dashboard_id=dashboard_id, 
                          visualization_id=visualization_id, text=text)
        
        # Build payload according to Redash widget API
        default_options = {
            "col": 0,
            "row": 0,
            "sizeX": 6 if full_width else 3,
            "sizeY": 4
        }

        payload = {
            "dashboard_id": int(dashboard_id),
            "width": 2,  # Redash expects width parameter
            "options": position or default_options
        }

        if visualization_id:
            payload["visualization_id"] = int(visualization_id)
        elif text:
            payload["text"] = text
        else:
            return {"error": "Must provide either visualization_id or text"}

        
        result = await self._make_request("POST", "/widgets", json=payload)
        
        if "error" in result:
            return result
        
        return {"widget": result}
    
    async def publish_dashboard(self, dashboard_id: str) -> Dict[str, Any]:
        """Publish a dashboard to make it accessible."""
        self._log_operation("publish_dashboard", dashboard_id=dashboard_id)
        
        payload = {"is_draft": False}
        
        result = await self._make_request("POST", f"/dashboards/{dashboard_id}", json=payload)
        
        if "error" in result:
            return result
        
        return {"dashboard": result}
    
    async def cleanup(self) -> None:
        """Clean up Redash provider resources."""
        if self.session:
            await self.session.close()
            self.session = None

        await super().cleanup()
