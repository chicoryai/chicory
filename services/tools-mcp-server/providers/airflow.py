"""
Airflow provider for workflow orchestration operations.
"""

import logging
import aiohttp
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime

from providers.base import ToolsProvider

logger = logging.getLogger(__name__)


class AirflowProvider(ToolsProvider):
    """
    Airflow provider for workflow orchestration operations using Airflow REST API.
    """

    def __init__(self):
        super().__init__()
        self.base_url: Optional[str] = None
        self.username: Optional[str] = None
        self.password: Optional[str] = None
        self.session: Optional[aiohttp.ClientSession] = None

    async def _initialize_client(self) -> None:
        """Initialize Airflow API client with credentials."""
        if not self.credentials:
            raise ValueError("No credentials provided")

        # Extract Airflow connection parameters
        self.base_url = self.credentials.get("base_url")
        if "http" not in self.base_url:
            self.base_url = f"http://{self.base_url}"
        self.username = self.credentials.get("username")
        self.password = self.credentials.get("password")

        # Validate required parameters
        if not all([self.base_url, self.username, self.password]):
            raise ValueError("Missing required Airflow credentials: base_url, username, password")

        # Ensure base_url ends with /api/v1 if not already
        if not self.base_url.endswith('/api/v1'):
            if self.base_url.endswith('/'):
                self.base_url = self.base_url + 'api/v1'
            else:
                self.base_url = self.base_url + '/api/v1'

        # Create HTTP session with basic auth
        auth = aiohttp.BasicAuth(self.username, self.password)
        self.session = aiohttp.ClientSession(auth=auth)

        logger.info("Airflow provider initialized successfully")

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make authenticated request to Airflow API."""
        self._ensure_initialized()

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
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
            logger.error(f"Airflow API request failed: {e}", exc_info=True)
            return {"error": str(e)}

    async def list_dags(self, limit: int = 100, offset: int = 0, only_active: bool = True) -> Dict[str, Any]:
        """List all DAGs in Airflow."""
        self._log_operation("list_dags", limit=limit, offset=offset, only_active=only_active)

        params = {
            "limit": limit,
            "offset": offset,
            "only_active": str(only_active).lower()
        }

        result = await self._make_request("GET", "/dags", params=params)

        if "error" in result:
            return result

        return {
            "dags": result.get("dags", []),
            "total_entries": result.get("total_entries", 0),
            "limit": limit,
            "offset": offset
        }

    async def get_dag(self, dag_id: str) -> Dict[str, Any]:
        """Get details of a specific DAG."""
        self._log_operation("get_dag", dag_id=dag_id)

        result = await self._make_request("GET", f"/dags/{dag_id}")

        if "error" in result:
            return result

        return {"dag": result}

    async def get_dag_runs(self, dag_id: str, limit: int = 25, offset: int = 0) -> Dict[str, Any]:
        """Get DAG runs for a specific DAG."""
        self._log_operation("get_dag_runs", dag_id=dag_id, limit=limit, offset=offset)

        params = {
            "limit": limit,
            "offset": offset
        }

        result = await self._make_request("GET", f"/dags/{dag_id}/dagRuns", params=params)

        if "error" in result:
            return result

        return {
            "dag_runs": result.get("dag_runs", []),
            "total_entries": result.get("total_entries", 0),
            "limit": limit,
            "offset": offset
        }

    async def trigger_dag(self, dag_id: str, conf: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Trigger a DAG run."""
        self._log_operation("trigger_dag", dag_id=dag_id, conf=conf)

        payload = {
            "conf": conf or {}
        }

        result = await self._make_request("POST", f"/dags/{dag_id}/dagRuns", json=payload)

        if "error" in result:
            return result

        return {"dag_run": result}

    async def get_dag_run(self, dag_id: str, dag_run_id: str) -> Dict[str, Any]:
        """Get details of a specific DAG run."""
        self._log_operation("get_dag_run", dag_id=dag_id, dag_run_id=dag_run_id)

        result = await self._make_request("GET", f"/dags/{dag_id}/dagRuns/{dag_run_id}")

        if "error" in result:
            return result

        return {"dag_run": result}

    async def get_task_instances(self, dag_id: str, dag_run_id: str) -> Dict[str, Any]:
        """Get task instances for a DAG run."""
        self._log_operation("get_task_instances", dag_id=dag_id, dag_run_id=dag_run_id)

        result = await self._make_request("GET", f"/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances")

        if "error" in result:
            return result

        return {"task_instances": result.get("task_instances", [])}

    async def get_task_instance(self, dag_id: str, dag_run_id: str, task_id: str) -> Dict[str, Any]:
        """Get details of a specific task instance."""
        self._log_operation("get_task_instance", dag_id=dag_id, dag_run_id=dag_run_id, task_id=task_id)

        result = await self._make_request("GET", f"/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances/{task_id}")

        if "error" in result:
            return result

        return {"task_instance": result}

    async def get_task_logs(self, dag_id: str, dag_run_id: str, task_id: str, task_try_number: int = 1) -> Dict[str, Any]:
        """Get logs for a task instance."""
        self._log_operation("get_task_logs", dag_id=dag_id, dag_run_id=dag_run_id, task_id=task_id, task_try_number=task_try_number)

        result = await self._make_request("GET", f"/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances/{task_id}/logs/{task_try_number}")

        if "error" in result:
            return result

        return {"logs": result}

    async def pause_dag(self, dag_id: str) -> Dict[str, Any]:
        """Pause a DAG."""
        self._log_operation("pause_dag", dag_id=dag_id)

        payload = {"is_paused": True}

        result = await self._make_request("PATCH", f"/dags/{dag_id}", json=payload)

        if "error" in result:
            return result

        return {"dag": result}

    async def unpause_dag(self, dag_id: str) -> Dict[str, Any]:
        """Unpause a DAG."""
        self._log_operation("unpause_dag", dag_id=dag_id)

        payload = {"is_paused": False}

        result = await self._make_request("PATCH", f"/dags/{dag_id}", json=payload)

        if "error" in result:
            return result

        return {"dag": result}

    async def get_connections(self, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """List all connections in Airflow."""
        self._log_operation("get_connections", limit=limit, offset=offset)

        params = {
            "limit": limit,
            "offset": offset
        }

        result = await self._make_request("GET", "/connections", params=params)

        if "error" in result:
            return result

        return {
            "connections": result.get("connections", []),
            "total_entries": result.get("total_entries", 0),
            "limit": limit,
            "offset": offset
        }

    async def get_variables(self, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """List all variables in Airflow."""
        self._log_operation("get_variables", limit=limit, offset=offset)

        params = {
            "limit": limit,
            "offset": offset
        }

        result = await self._make_request("GET", "/variables", params=params)

        if "error" in result:
            return result

        return {
            "variables": result.get("variables", []),
            "total_entries": result.get("total_entries", 0),
            "limit": limit,
            "offset": offset
        }

    async def cleanup(self) -> None:
        """Clean up Airflow provider resources."""
        if self.session:
            await self.session.close()
            self.session = None

        await super().cleanup()