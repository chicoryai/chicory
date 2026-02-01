"""
dbt Cloud provider for analytics operations.
"""

import logging
import aiohttp
import asyncio
import json
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from providers import ToolsProvider

logger = logging.getLogger(__name__)


class DbtProvider(ToolsProvider):
    """
    dbt Cloud provider for analytics operations using dbt Cloud APIs.
    """

    def __init__(self):
        super().__init__()
        self.base_url: Optional[str] = None
        self.api_token: Optional[str] = None
        self.account_id: Optional[str] = None
        self.project_id: Optional[str] = None
        self.environment_id: Optional[str] = None
        self.session: Optional[aiohttp.ClientSession] = None

    async def _initialize_client(self) -> None:
        """Initialize dbt Cloud API client with credentials."""
        if not self.credentials:
            raise ValueError("No credentials provided")

        # Extract dbt Cloud connection parameters
        self.base_url = self.credentials.get("base_url", "https://cloud.getdbt.com")
        self.api_token = self.credentials.get("api_token")
        self.account_id = self.credentials.get("account_id")
        self.project_id = self.credentials.get("project_id")
        self.environment_id = self.credentials.get("environment_id")

        # Validate required parameters
        if not all([self.api_token, self.account_id]):
            raise ValueError("Missing required dbt Cloud credentials: api_token, account_id")

        # Ensure base_url ends with /api/v2 if not already
        if not self.base_url.endswith('/api/v2'):
            if self.base_url.endswith('/'):
                self.base_url = self.base_url + 'api/v2'
            else:
                self.base_url = self.base_url + '/api/v2'

        # Create HTTP session
        self.session = aiohttp.ClientSession()

        logger.info("dbt Cloud provider initialized successfully")

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make authenticated request to dbt Cloud API."""
        self._ensure_initialized()

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        try:
            async with self.session.request(method, url, headers=headers, **kwargs) as response:
                if response.status not in [200, 201, 202]:
                    error_text = await response.text()
                    return {"error": f"HTTP {response.status}: {error_text}"}

                return await response.json()

        except Exception as e:
            logger.error(f"dbt Cloud API request failed: {e}")
            return {"error": str(e)}

    async def list_accounts(self) -> Dict[str, Any]:
        """List all accounts accessible to the user."""
        self._log_operation("list_accounts")

        result = await self._make_request("GET", "/accounts/")

        if "error" in result:
            return result

        return {"accounts": result.get("data", [])}

    async def list_projects(self) -> Dict[str, Any]:
        """List all projects in the account."""
        self._log_operation("list_projects")

        if not self.account_id:
            return {"error": "Account ID not configured"}

        result = await self._make_request("GET", f"/accounts/{self.account_id}/projects/")

        if "error" in result:
            return result

        return {"projects": result.get("data", [])}

    async def list_environments(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """List all environments in a project."""
        self._log_operation("list_environments", project_id=project_id)

        if not self.account_id:
            return {"error": "Account ID not configured"}

        proj_id = project_id or self.project_id
        if not proj_id:
            return {"error": "Project ID not provided or configured"}

        result = await self._make_request("GET", f"/accounts/{self.account_id}/environments/",
                                          params={"project_id": proj_id})

        if "error" in result:
            return result

        return {"environments": result.get("data", [])}

    async def list_jobs(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """List all jobs in a project."""
        self._log_operation("list_jobs", project_id=project_id)

        if not self.account_id:
            return {"error": "Account ID not configured"}

        proj_id = project_id or self.project_id
        if not proj_id:
            return {"error": "DBT Project ID not provided or configured"}

        result = await self._make_request("GET", f"/accounts/{self.account_id}/jobs/",
                                          params={"project_id": proj_id})

        if "error" in result:
            return result

        return {"jobs": result.get("data", [])}

    async def trigger_job_run(self, job_id: str, cause: str = "API trigger",
                              git_sha: Optional[str] = None,
                              schema_override: Optional[str] = None,
                              dbt_version_override: Optional[str] = None,
                              target_name_override: Optional[str] = None,
                              generate_docs_override: Optional[bool] = None,
                              timeout_seconds_override: Optional[int] = None,
                              steps_override: Optional[List[str]] = None) -> Dict[str, Any]:
        """Trigger a job run with optional overrides."""
        self._log_operation("trigger_job_run", job_id=job_id, cause=cause)

        if not self.account_id:
            return {"error": "Account ID not configured"}

        payload = {"cause": cause}

        # Add optional overrides
        if git_sha:
            payload["git_sha"] = git_sha
        if schema_override:
            payload["schema_override"] = schema_override
        if dbt_version_override:
            payload["dbt_version_override"] = dbt_version_override
        if target_name_override:
            payload["target_name_override"] = target_name_override
        if generate_docs_override is not None:
            payload["generate_docs_override"] = generate_docs_override
        if timeout_seconds_override:
            payload["timeout_seconds_override"] = timeout_seconds_override
        if steps_override:
            payload["steps_override"] = steps_override

        result = await self._make_request("POST", f"/accounts/{self.account_id}/jobs/{job_id}/run/",
                                          json=payload)

        if "error" in result:
            return result

        return {"run": result.get("data", {})}

    async def get_job_run(self, run_id: str, include_related: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get details of a specific job run."""
        self._log_operation("get_job_run", run_id=run_id)

        if not self.account_id:
            return {"error": "Account ID not configured"}

        params = {}
        if include_related:
            params["include_related"] = include_related

        result = await self._make_request("GET", f"/accounts/{self.account_id}/runs/{run_id}/",
                                          params=params)

        if "error" in result:
            return result

        return {"run": result.get("data", {})}

    async def list_job_runs(self, job_id: Optional[str] = None,
                            status: Optional[str] = None,
                            order_by: str = "-id",
                            offset: int = 0,
                            limit: int = 100) -> Dict[str, Any]:
        """List job runs with optional filtering."""
        self._log_operation("list_job_runs", job_id=job_id, status=status)

        if not self.account_id:
            return {"error": "Account ID not configured"}

        params = {
            "order_by": order_by,
            "offset": offset,
            "limit": limit
        }

        if job_id:
            params["job_definition_id"] = job_id
        if status:
            params["status"] = status

        result = await self._make_request("GET", f"/accounts/{self.account_id}/runs/", params=params)

        if "error" in result:
            return result

        return {
            "runs": result.get("data", []),
            "total_count": result.get("extra", {}).get("pagination", {}).get("total_count", 0)
        }

    async def cancel_job_run(self, run_id: str) -> Dict[str, Any]:
        """Cancel a running job."""
        self._log_operation("cancel_job_run", run_id=run_id)

        if not self.account_id:
            return {"error": "Account ID not configured"}

        result = await self._make_request("POST", f"/accounts/{self.account_id}/runs/{run_id}/cancel/")

        if "error" in result:
            return result

        return {"run": result.get("data", {})}

    async def get_run_artifacts(self, run_id: str, path: str = "manifest.json") -> Dict[str, Any]:
        """Get artifacts from a completed run."""
        self._log_operation("get_run_artifacts", run_id=run_id, path=path)

        if not self.account_id:
            return {"error": "Account ID not configured"}

        result = await self._make_request("GET", f"/accounts/{self.account_id}/runs/{run_id}/artifacts/{path}")

        if "error" in result:
            return result

        return {"artifact": result}

    async def list_models(self, environment_id: Optional[str] = None) -> Dict[str, Any]:
        """List models using Discovery API."""
        self._log_operation("list_models", environment_id=environment_id)

        if not self.account_id:
            return {"error": "Account ID not configured"}

        env_id = environment_id or self.environment_id
        if not env_id:
            return {"error": "Environment ID not provided or configured"}

        # Use Discovery API
        discovery_url = self.base_url.replace("/api/v2", "/api/v1/graphql")

        query = """
        query GetModels($environmentId: Int!) {
            environment(id: $environmentId) {
                definition {
                    models {
                        uniqueId
                        name
                        schema
                        database
                        description
                        packageName
                        materializedType
                        tags
                        meta
                    }
                }
            }
        }
        """

        variables = {"environmentId": int(env_id)}

        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

        try:
            async with self.session.post(discovery_url,
                                         json={"query": query, "variables": variables},
                                         headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return {"error": f"GraphQL HTTP {response.status}: {error_text}"}

                result = await response.json()

                if "errors" in result:
                    return {"error": f"GraphQL errors: {result['errors']}"}

                models = result.get("data", {}).get("environment", {}).get("definition", {}).get("models", [])
                return {"models": models}

        except Exception as e:
            logger.error(f"Discovery API request failed: {e}")
            return {"error": str(e)}

    async def get_model_details(self, model_unique_id: str, environment_id: Optional[str] = None) -> Dict[str, Any]:
        """Get detailed information about a specific model."""
        self._log_operation("get_model_details", model_unique_id=model_unique_id)

        if not self.account_id:
            return {"error": "Account ID not configured"}

        env_id = environment_id or self.environment_id
        if not env_id:
            return {"error": "Environment ID not provided or configured"}

        discovery_url = self.base_url.replace("/api/v2", "/api/v1/graphql")

        query = """
        query GetModelDetails($environmentId: Int!, $uniqueId: String!) {
            environment(id: $environmentId) {
                definition {
                    model(uniqueId: $uniqueId) {
                        uniqueId
                        name
                        schema
                        database
                        description
                        packageName
                        materializedType
                        tags
                        meta
                        rawSql
                        compiledSql
                        columns {
                            name
                            description
                            type
                            tags
                            meta
                        }
                        parents {
                            uniqueId
                            name
                            resourceType
                        }
                        children {
                            uniqueId
                            name
                            resourceType
                        }
                    }
                }
            }
        }
        """

        variables = {"environmentId": int(env_id), "uniqueId": model_unique_id}

        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

        try:
            async with self.session.post(discovery_url,
                                         json={"query": query, "variables": variables},
                                         headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return {"error": f"GraphQL HTTP {response.status}: {error_text}"}

                result = await response.json()

                if "errors" in result:
                    return {"error": f"GraphQL errors: {result['errors']}"}

                model = result.get("data", {}).get("environment", {}).get("definition", {}).get("model")
                if not model:
                    return {"error": f"Model {model_unique_id} not found"}

                return {"model": model}

        except Exception as e:
            logger.error(f"Discovery API request failed: {e}")
            return {"error": str(e)}

    async def list_metrics(self, environment_id: Optional[str] = None) -> Dict[str, Any]:
        """List metrics using Semantic Layer API."""
        self._log_operation("list_metrics", environment_id=environment_id)

        if not self.account_id:
            return {"error": "Account ID not configured"}

        env_id = environment_id or self.environment_id
        if not env_id:
            return {"error": "Environment ID not provided or configured"}

        # Use Semantic Layer API
        sl_url = self.base_url.replace("/api/v2",
                                       f"/semantic-layer/v1/accounts/{self.account_id}/environments/{env_id}")

        result = await self._make_request("GET", f"{sl_url}/metrics")

        if "error" in result:
            return result

        return {"metrics": result.get("data", [])}

    async def query_metrics(self, metrics: List[str],
                            group_by: Optional[List[str]] = None,
                            where: Optional[List[str]] = None,
                            order_by: Optional[List[str]] = None,
                            limit: Optional[int] = None,
                            environment_id: Optional[str] = None) -> Dict[str, Any]:
        """Query metrics using Semantic Layer API."""
        self._log_operation("query_metrics", metrics=metrics, group_by=group_by)

        if not self.account_id:
            return {"error": "Account ID not configured"}

        env_id = environment_id or self.environment_id
        if not env_id:
            return {"error": "Environment ID not provided or configured"}

        # Use Semantic Layer API
        sl_url = self.base_url.replace("/api/v2",
                                       f"/semantic-layer/v1/accounts/{self.account_id}/environments/{env_id}")

        payload = {"metrics": metrics}

        if group_by:
            payload["group_by"] = group_by
        if where:
            payload["where"] = where
        if order_by:
            payload["order_by"] = order_by
        if limit:
            payload["limit"] = limit

        result = await self._make_request("POST", f"{sl_url}/query", json=payload)

        if "error" in result:
            return result

        return {"query_result": result.get("data", {})}

    async def execute_sql(self, sql: str, environment_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute SQL using dbt Cloud SQL API."""
        self._log_operation("execute_sql", sql=sql[:100])

        if not self.account_id:
            return {"error": "Account ID not configured"}

        env_id = environment_id or self.environment_id
        if not env_id:
            return {"error": "Environment ID not provided or configured"}

        # Use SQL API
        sql_url = self.base_url.replace("/api/v2", f"/sql/v1/accounts/{self.account_id}/environments/{env_id}")

        payload = {"sql": sql}

        result = await self._make_request("POST", f"{sql_url}/query", json=payload)

        if "error" in result:
            return result

        return {"sql_result": result.get("data", {})}

    async def cleanup(self) -> None:
        """Clean up dbt Cloud provider resources."""
        if self.session:
            await self.session.close()
            self.session = None

        await super().cleanup()
