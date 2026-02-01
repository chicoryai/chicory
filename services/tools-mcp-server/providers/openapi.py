"""
OpenAPI provider for REST API operations.
"""

import logging
import aiohttp
import json
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

from providers.base import ToolsProvider

logger = logging.getLogger(__name__)


class OpenAPIProvider(ToolsProvider):
    """
    OpenAPI provider for REST API operations using OpenAPI specifications.
    """

    def __init__(self):
        super().__init__()
        self.base_url: Optional[str] = None
        self.spec_url: Optional[str] = None
        self.api_key: Optional[str] = None
        self.auth_header: Optional[str] = None
        self.spec: Optional[Dict[str, Any]] = None
        self.session: Optional[aiohttp.ClientSession] = None

    async def _initialize_client(self) -> None:
        """Initialize OpenAPI client with credentials."""
        if not self.credentials:
            raise ValueError("No credentials provided")

        # Extract OpenAPI connection parameters
        self.base_url = self.credentials.get("base_url")
        self.spec_url = self.credentials.get("spec_url")
        self.api_key = self.credentials.get("api_key")
        self.auth_header = self.credentials.get("auth_header", "Authorization")

        # Validate required parameters
        if not self.base_url:
            raise ValueError("Missing required OpenAPI credential: base_url")

        # If spec_url not provided, try common locations
        if not self.spec_url:
            self.spec_url = urljoin(self.base_url, "/openapi.json")
            # Try alternative locations if the first fails
            alt_specs = ["/swagger.json", "/api-docs", "/v3/api-docs"]

        # Create HTTP session
        self.session = aiohttp.ClientSession()

        # Load OpenAPI specification
        await self._load_spec()

        logger.info("OpenAPI provider initialized successfully")

    async def _load_spec(self) -> None:
        """Load OpenAPI specification from URL."""
        try:
            async with self.session.get(self.spec_url) as response:
                if response.status == 200:
                    self.spec = await response.json()
                    logger.info(f"Loaded OpenAPI spec from {self.spec_url}")
                    return
                else:
                    logger.warning(f"Failed to load spec from {self.spec_url}: {response.status}")
        except Exception as e:
            logger.warning(f"Error loading spec from {self.spec_url}: {e}")

        # Try alternative spec locations
        alt_specs = ["/swagger.json", "/api-docs", "/v3/api-docs", "/openapi.yaml"]
        for alt_spec in alt_specs:
            try:
                alt_url = urljoin(self.base_url, alt_spec)
                async with self.session.get(alt_url) as response:
                    if response.status == 200:
                        self.spec = await response.json()
                        self.spec_url = alt_url
                        logger.info(f"Loaded OpenAPI spec from {alt_url}")
                        return
            except Exception as e:
                logger.debug(f"Failed to load spec from {alt_url}: {e}")
                continue

        # If we can't load the spec, create a minimal one
        logger.warning("Could not load OpenAPI spec, creating minimal spec")
        self.spec = {
            "openapi": "3.0.0",
            "info": {"title": "Unknown API", "version": "1.0.0"},
            "paths": {}
        }

    async def _make_request(self, method: str, path: str,
                            parameters: Optional[Dict[str, Any]] = None,
                            data: Optional[Dict[str, Any]] = None,
                            headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Make authenticated request to the API."""
        self._ensure_initialized()

        # Construct full URL
        if path.startswith('http'):
            url = path
        else:
            url = urljoin(self.base_url, path.lstrip('/'))

        # Prepare headers
        request_headers = {}
        if self.api_key:
            if self.auth_header.lower() == "authorization":
                request_headers["Authorization"] = f"Bearer {self.api_key}"
            else:
                request_headers[self.auth_header] = self.api_key

        if headers:
            request_headers.update(headers)

        # Prepare request kwargs
        kwargs = {"headers": request_headers}

        if parameters:
            kwargs["params"] = parameters

        if data:
            if method.upper() in ["POST", "PUT", "PATCH"]:
                kwargs["json"] = data
                request_headers["Content-Type"] = "application/json"

        try:
            async with self.session.request(method, url, **kwargs) as response:
                response_data = {}

                # Try to parse JSON response
                try:
                    response_data = await response.json()
                except:
                    # If not JSON, get text
                    response_data = await response.text()

                return {
                    "response": {
                        "status_code": response.status,
                        "headers": dict(response.headers),
                        "data": response_data
                    }
                }

        except Exception as e:
            logger.error(f"OpenAPI request failed: {e}")
            return {"error": str(e)}

    async def get_spec(self) -> Dict[str, Any]:
        """Get the OpenAPI specification."""
        self._log_operation("get_spec")

        if not self.spec:
            return {"error": "No OpenAPI specification loaded"}

        return {
            "spec": self.spec,
            "base_url": self.base_url,
            "spec_url": self.spec_url
        }

    async def list_endpoints(self, tag: Optional[str] = None) -> Dict[str, Any]:
        """List all available endpoints in the API."""
        self._log_operation("list_endpoints", tag=tag)

        if not self.spec:
            return {"error": "No OpenAPI specification loaded"}

        paths = self.spec.get("paths", {})
        endpoints = []

        for path, path_info in paths.items():
            for method, operation in path_info.items():
                if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]:
                    endpoint_info = {
                        "method": method.upper(),
                        "path": path,
                        "summary": operation.get("summary", ""),
                        "description": operation.get("description", ""),
                        "tags": operation.get("tags", [])
                    }

                    # Filter by tag if specified
                    if tag and tag not in endpoint_info["tags"]:
                        continue

                    endpoints.append(endpoint_info)

        return {"endpoints": endpoints}

    async def get_endpoint_schema(self, method: str, path: str) -> Dict[str, Any]:
        """Get schema definition for a specific endpoint."""
        self._log_operation("get_endpoint_schema", method=method, path=path)

        if not self.spec:
            return {"error": "No OpenAPI specification loaded"}

        paths = self.spec.get("paths", {})
        path_info = paths.get(path, {})
        operation = path_info.get(method.lower(), {})

        if not operation:
            return {"error": f"Endpoint {method.upper()} {path} not found"}

        return {"schema": operation}

    async def call_endpoint(self, method: str, path: str,
                            parameters: Optional[Dict[str, Any]] = None,
                            data: Optional[Dict[str, Any]] = None,
                            headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Call a specific endpoint."""
        self._log_operation("call_endpoint", method=method, path=path,
                            parameters=parameters, data=data)

        return await self._make_request(method, path, parameters, data, headers)

    async def get_servers(self) -> Dict[str, Any]:
        """Get available servers from the OpenAPI spec."""
        self._log_operation("get_servers")

        if not self.spec:
            return {"error": "No OpenAPI specification loaded"}

        servers = self.spec.get("servers", [])
        return {"servers": servers}

    async def get_components(self) -> Dict[str, Any]:
        """Get components (schemas, responses, etc.) from the OpenAPI spec."""
        self._log_operation("get_components")

        if not self.spec:
            return {"error": "No OpenAPI specification loaded"}

        components = self.spec.get("components", {})
        return {"components": components}

    async def get_security_schemes(self) -> Dict[str, Any]:
        """Get security schemes from the OpenAPI spec."""
        self._log_operation("get_security_schemes")

        if not self.spec:
            return {"error": "No OpenAPI specification loaded"}

        components = self.spec.get("components", {})
        security_schemes = components.get("securitySchemes", {})
        return {"security_schemes": security_schemes}

    async def cleanup(self) -> None:
        """Clean up OpenAPI provider resources."""
        if self.session:
            await self.session.close()
            self.session = None

        self.spec = None
        await super().cleanup()
