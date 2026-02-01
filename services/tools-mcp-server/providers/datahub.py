"""
DataHub provider for data catalog and metadata operations.
"""

import logging
import aiohttp
import asyncio
from typing import Any, Dict, List, Optional

from providers.base import ToolsProvider

logger = logging.getLogger(__name__)


class DataHubProvider(ToolsProvider):
    """
    DataHub provider for data catalog and metadata operations using DataHub APIs.
    """

    def __init__(self):
        super().__init__()
        self.base_url: Optional[str] = None
        self.api_key: Optional[str] = None
        self.session: Optional[aiohttp.ClientSession] = None

    async def _initialize_client(self) -> None:
        """Initialize DataHub API client with credentials."""
        if not self.credentials:
            raise ValueError("No credentials provided")

        # Extract DataHub connection parameters
        self.base_url = self.credentials.get("base_url")
        if self.base_url and "http" not in self.base_url:
            self.base_url = f"http://{self.base_url}"
        self.api_key = self.credentials.get("api_key")

        # Validate required parameters
        if not all([self.base_url, self.api_key]):
            raise ValueError("Missing required DataHub credentials: base_url, api_key")

        # Ensure base_url ends properly
        if self.base_url.endswith('/'):
            self.base_url = self.base_url.rstrip('/')

        # Create HTTP session
        self.session = aiohttp.ClientSession()

        logger.info("DataHub provider initialized successfully")

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make authenticated request to DataHub API."""
        try:
            self._ensure_initialized()

            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            if "headers" in kwargs:
                headers.update(kwargs.pop("headers"))

            async with self.session.request(method, url, headers=headers, **kwargs) as response:
                if response.status not in [200, 201]:
                    error_text = await response.text()
                    return {"error": f"HTTP {response.status}: {error_text}"}

                json_response = await response.json()
                # Ensure we always return a dictionary, not None
                if json_response is None:
                    return {"error": "Empty or invalid JSON response from DataHub API"}
                return json_response

        except Exception as e:
            logger.error(f"DataHub API request failed: {e}")
            return {"error": str(e)}

    async def search_entities(self, query: str = "*", entity_types: Optional[List[str]] = None, 
                             start: int = 0, count: int = 10) -> Dict[str, Any]:
        """Search for entities in DataHub."""
        self._log_operation("search_entities", query=query, entity_types=entity_types, start=start, count=count)

        body = {
            "input": query,
            "start": start,
            "count": count
        }

        if entity_types:
            body["entityTypes"] = entity_types

        result = await self._make_request("POST", "/api/graphql", json={
            "query": """
                query searchAcrossEntities($input: String!, $entityTypes: [EntityType!], $start: Int!, $count: Int!) {
                    searchAcrossEntities(input: {
                        types: $entityTypes,
                        query: $input,
                        start: $start,
                        count: $count
                    }) {
                        start
                        count
                        total
                        searchResults {
                            entity {
                                urn
                                type
                                ... on Dataset {
                                    properties {
                                        name
                                        description
                                    }
                                }
                                ... on Chart {
                                    properties {
                                        name
                                        description
                                    }
                                }
                                ... on Dashboard {
                                    properties {
                                        name
                                        description
                                    }
                                }
                            }
                        }
                    }
                }
            """,
            "variables": body
        })

        if result is None:
            return {"error": "No response from DataHub API"}

        if "error" in result:
            return result

        data = result.get("data", {}).get("searchAcrossEntities", {})
        return {
            "entities": data.get("searchResults", []),
            "total": data.get("total", 0),
            "start": start,
            "count": count
        }

    async def get_entity(self, urn: str) -> Dict[str, Any]:
        """Get details of a specific entity by URN."""
        self._log_operation("get_entity", urn=urn)

        result = await self._make_request("POST", "/api/graphql", json={
            "query": """
                query getEntity($urn: String!) {
                    entity(urn: $urn) {
                        urn
                        type
                        ... on Dataset {
                            properties {
                                name
                                description
                            }
                            platform {
                                name
                            }
                            schemaMetadata {
                                fields {
                                    fieldPath
                                    nativeDataType
                                    description
                                }
                            }
                        }
                        ... on Chart {
                            properties {
                                name
                                description
                            }
                        }
                        ... on Dashboard {
                            properties {
                                name
                                description
                            }
                            charts {
                                urn
                            }
                        }
                    }
                }
            """,
            "variables": {"urn": urn}
        })

        if result is None:
            return {"error": "No response from DataHub API"}

        if "error" in result:
            return result

        entity = result.get("data", {}).get("entity", {})
        return {"entity": entity}

    async def list_datasets(self, platform: Optional[str] = None, start: int = 0, count: int = 20) -> Dict[str, Any]:
        """List datasets in DataHub."""
        self._log_operation("list_datasets", platform=platform, start=start, count=count)

        query_filter = ""
        if platform:
            query_filter = f"platform:{platform}"

        result = await self.search_entities(
            query=query_filter or "*",
            entity_types=["DATASET"],
            start=start,
            count=count
        )

        if "error" in result:
            return result

        return {
            "datasets": result.get("entities", []),
            "total": result.get("total", 0),
            "start": start,
            "count": count
        }

    async def list_dashboards(self, start: int = 0, count: int = 20) -> Dict[str, Any]:
        """List dashboards in DataHub."""
        self._log_operation("list_dashboards", start=start, count=count)

        result = await self.search_entities(
            query="*",
            entity_types=["DASHBOARD"],
            start=start,
            count=count
        )

        if "error" in result:
            return result

        return {
            "dashboards": result.get("entities", []),
            "total": result.get("total", 0),
            "start": start,
            "count": count
        }

    async def list_charts(self, start: int = 0, count: int = 20) -> Dict[str, Any]:
        """List charts in DataHub."""
        self._log_operation("list_charts", start=start, count=count)

        result = await self.search_entities(
            query="*",
            entity_types=["CHART"],
            start=start,
            count=count
        )

        if "error" in result:
            return result

        return {
            "charts": result.get("entities", []),
            "total": result.get("total", 0),
            "start": start,
            "count": count
        }

    async def get_lineage(self, urn: str, direction: str = "DOWNSTREAM", start: int = 0, count: int = 100) -> Dict[str, Any]:
        """Get lineage information for an entity."""
        self._log_operation("get_lineage", urn=urn, direction=direction, start=start, count=count)

        result = await self._make_request("POST", "/api/graphql", json={
            "query": """
                query getLineage($urn: String!, $direction: LineageDirection!, $start: Int!, $count: Int!) {
                    entity(urn: $urn) {
                        ... on Dataset {
                            lineage(input: {
                                direction: $direction,
                                start: $start,
                                count: $count
                            }) {
                                start
                                count
                                total
                                relationships {
                                    entity {
                                        urn
                                        type
                                        ... on Dataset {
                                            properties {
                                                name
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            """,
            "variables": {
                "urn": urn,
                "direction": direction.upper(),
                "start": start,
                "count": count
            }
        })

        if result is None:
            return {"error": "No response from DataHub API"}

        if "error" in result:
            return result

        lineage_data = result.get("data", {}).get("entity", {}).get("lineage", {})
        return {
            "lineage": lineage_data.get("relationships", []),
            "total": lineage_data.get("total", 0),
            "start": start,
            "count": count,
            "direction": direction
        }

    async def get_platform_instances(self) -> Dict[str, Any]:
        """Get all platform instances in DataHub."""
        self._log_operation("get_platform_instances")

        result = await self._make_request("POST", "/api/graphql", json={
            "query": """
                query listPlatforms {
                    listPlatforms {
                        start
                        count
                        total
                        platforms {
                            urn
                            type
                            name
                            properties {
                                type
                                displayName
                                logoUrl
                            }
                        }
                    }
                }
            """
        })

        if result is None:
            return {"error": "No response from DataHub API"}

        if "error" in result:
            return result

        platforms_data = result.get("data", {}).get("listPlatforms", {})
        return {
            "platforms": platforms_data.get("platforms", []),
            "total": platforms_data.get("total", 0)
        }

    async def get_tags(self, start: int = 0, count: int = 20) -> Dict[str, Any]:
        """Get all tags in DataHub."""
        self._log_operation("get_tags", start=start, count=count)

        result = await self._make_request("POST", "/api/graphql", json={
            "query": """
                query listTags($start: Int!, $count: Int!) {
                    listTags(input: {
                        start: $start,
                        count: $count
                    }) {
                        start
                        count
                        total
                        tags {
                            urn
                            name
                            description
                        }
                    }
                }
            """,
            "variables": {"start": start, "count": count}
        })

        if result is None:
            return {"error": "No response from DataHub API"}

        if "error" in result:
            return result

        tags_data = result.get("data", {}).get("listTags", {})
        return {
            "tags": tags_data.get("tags", []),
            "total": tags_data.get("total", 0),
            "start": start,
            "count": count
        }

    async def cleanup(self) -> None:
        """Clean up DataHub provider resources."""
        if self.session:
            await self.session.close()
            self.session = None

        await super().cleanup()