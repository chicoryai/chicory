"""
Atlan provider for data catalog and metadata operations.
Provides full read/write access to Atlan's asset management, search, lineage, and glossary APIs.
"""

import ipaddress
import logging
import aiohttp
import asyncio
import re
import socket
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from urllib.parse import urlparse, quote

from providers.base import ToolsProvider

logger = logging.getLogger(__name__)

# Valid values for validation
VALID_CERTIFICATION_STATUSES = {"VERIFIED", "DEPRECATED", "DRAFT"}
VALID_LINEAGE_DIRECTIONS = {"UPSTREAM", "DOWNSTREAM", "BOTH"}

# GUID format pattern (UUID format)
GUID_PATTERN = re.compile(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', re.I)

# Type name pattern (alphanumeric with optional underscores, no path traversal)
TYPE_NAME_PATTERN = re.compile(r'^[A-Za-z][A-Za-z0-9_]*$')

# Pagination limits
MAX_PAGE_SIZE = 100
MIN_PAGE_SIZE = 1
MAX_PAGINATION_OFFSET = 10000

# Search query limits
MAX_QUERY_LENGTH = 2000

# Classification name pattern (alphanumeric with underscores)
CLASSIFICATION_NAME_PATTERN = re.compile(r'^[A-Za-z][A-Za-z0-9_]*$')

# Maximum retry-after delay (seconds)
MAX_RETRY_AFTER = 300

# Text field limits
MAX_DESCRIPTION_LENGTH = 5000
MAX_NAME_LENGTH = 500
MAX_MESSAGE_LENGTH = 2000
MAX_OWNER_LENGTH = 200
MAX_OWNERS_COUNT = 50
MAX_ATTRIBUTE_LENGTH = 100
MAX_ATTRIBUTES_COUNT = 50

# Attribute name pattern (alphanumeric with underscores)
ATTRIBUTE_NAME_PATTERN = re.compile(r'^[A-Za-z][A-Za-z0-9_]*$')

# Blocked hostnames for SSRF protection
BLOCKED_HOSTNAMES = {
    'localhost', 'localhost.localdomain',
    'metadata.google.internal', 'metadata.goog',
    'metadata.azure.internal', 'metadata.aws.internal',
    'kubernetes.default.svc',
    '169.254.169.254', '169.254.170.2',
}

# Cloud metadata IPs to block
CLOUD_METADATA_IPS = {
    '169.254.169.254', '169.254.170.2', 'fd00:ec2::254',
}

# Blocked domain suffixes
BLOCKED_DOMAIN_SUFFIXES = (
    '.internal', '.local', '.localhost', '.localdomain',
    '.intranet', '.corp', '.lan'
)


class AtlanProvider(ToolsProvider):
    """
    Atlan provider for data catalog operations using Atlan's REST API.

    Capabilities:
    - Asset search (Elasticsearch DSL)
    - Asset CRUD operations
    - Lineage traversal
    - Business glossary management
    - Classifications/Tags management
    - Custom metadata
    """

    def __init__(self):
        super().__init__()
        self.tenant_url: Optional[str] = None
        self.api_token: Optional[str] = None
        self.session: Optional[aiohttp.ClientSession] = None
        # Rate limiting with lock for thread safety
        self._request_times: List[datetime] = []
        self._rate_limit = 100  # requests per minute
        self._rate_window = 60  # seconds
        self._rate_lock = asyncio.Lock()

    # ==================== VALIDATION HELPERS ====================

    def _validate_guid(self, guid: str) -> Tuple[bool, str]:
        """Validate GUID format (UUID format)."""
        if not guid:
            return False, "GUID is required"
        if not GUID_PATTERN.match(guid):
            return False, f"Invalid GUID format: {guid}. Expected UUID format."
        return True, ""

    def _validate_pagination(self, from_: int, size: int) -> Tuple[bool, str]:
        """Validate pagination parameters."""
        if from_ < 0:
            return False, f"from_ must be >= 0, got {from_}"
        if size < MIN_PAGE_SIZE:
            return False, f"size must be >= {MIN_PAGE_SIZE}, got {size}"
        if size > MAX_PAGE_SIZE:
            return False, f"size must be <= {MAX_PAGE_SIZE}, got {size}"
        # Check total offset (from_ + size) doesn't exceed limit
        if from_ + size > MAX_PAGINATION_OFFSET:
            return False, f"from_ + size must be <= {MAX_PAGINATION_OFFSET}, got {from_ + size}"
        return True, ""

    def _validate_type_name(self, type_name: str) -> Tuple[bool, str]:
        """Validate asset type name to prevent path traversal attacks."""
        if not type_name:
            return False, "type_name is required"
        if not TYPE_NAME_PATTERN.match(type_name):
            return False, f"Invalid type_name format: {type_name}. Must be alphanumeric starting with a letter."
        if len(type_name) > 100:
            return False, f"type_name too long: {len(type_name)} chars. Maximum is 100."
        return True, ""

    def _validate_qualified_name(self, qualified_name: str) -> Tuple[bool, str]:
        """Validate qualified name parameter."""
        if not qualified_name:
            return False, "qualified_name is required"
        if len(qualified_name) > 1000:
            return False, f"qualified_name too long: {len(qualified_name)} chars. Maximum is 1000."
        # Block dangerous characters that could cause injection
        dangerous_chars = ['<', '>', '"', "'", '\\', '\n', '\r', '\x00']
        for char in dangerous_chars:
            if char in qualified_name:
                return False, f"qualified_name contains invalid character"
        return True, ""

    def _validate_asset_types(self, asset_types: List[str]) -> Tuple[bool, str]:
        """Validate list of asset type names."""
        if not asset_types:
            return True, ""  # Empty list is valid (no filter)
        for i, type_name in enumerate(asset_types):
            is_valid, error_msg = self._validate_type_name(type_name)
            if not is_valid:
                return False, f"Invalid asset type at index {i}: {error_msg}"
        return True, ""

    def _validate_query(self, query: str) -> Tuple[bool, str]:
        """Validate search query parameter to prevent Elasticsearch injection."""
        if not query:
            return False, "query is required"
        if len(query) > MAX_QUERY_LENGTH:
            return False, f"query too long: {len(query)} chars. Maximum is {MAX_QUERY_LENGTH}."
        # Block null bytes and control characters
        if '\x00' in query or any(ord(c) < 32 and c not in '\t\n\r' for c in query):
            return False, "query contains invalid control characters"
        return True, ""

    def _validate_classification_name(self, classification_name: str) -> Tuple[bool, str]:
        """Validate classification name to prevent URL path injection."""
        if not classification_name:
            return False, "classification_name is required"
        if not CLASSIFICATION_NAME_PATTERN.match(classification_name):
            return False, f"Invalid classification_name format: {classification_name}. Must be alphanumeric starting with a letter."
        if len(classification_name) > 100:
            return False, f"classification_name too long: {len(classification_name)} chars. Maximum is 100."
        return True, ""

    def _validate_text_field(self, value: Optional[str], field_name: str, max_length: int) -> Tuple[bool, str]:
        """Validate a text field for length and dangerous characters."""
        if value is None:
            return False, f"{field_name} is required"
        if len(value) > max_length:
            return False, f"{field_name} too long: {len(value)} chars. Maximum is {max_length}."
        # Block null bytes and control characters
        if '\x00' in value or any(ord(c) < 32 and c not in '\t\n\r' for c in value):
            return False, f"{field_name} contains invalid control characters"
        return True, ""

    def _validate_name(self, name: str) -> Tuple[bool, str]:
        """Validate asset/term name parameter."""
        if not name:
            return False, "name is required"
        if len(name) > MAX_NAME_LENGTH:
            return False, f"name too long: {len(name)} chars. Maximum is {MAX_NAME_LENGTH}."
        # Block characters that would break qualified name format
        if '@' in name or '\x00' in name or '\n' in name or '\r' in name:
            return False, "name contains invalid characters (@ or control characters not allowed)"
        return True, ""

    def _validate_owners(self, owners: Optional[List[str]], field_name: str) -> Tuple[bool, str]:
        """Validate owner list parameter."""
        if not owners:
            return True, ""  # Empty/None is valid
        if len(owners) > MAX_OWNERS_COUNT:
            return False, f"{field_name} has too many items: {len(owners)}. Maximum is {MAX_OWNERS_COUNT}."
        seen = set()
        for i, owner in enumerate(owners):
            if not owner or not isinstance(owner, str):
                return False, f"{field_name}[{i}] must be a non-empty string"
            if len(owner) > MAX_OWNER_LENGTH:
                return False, f"{field_name}[{i}] too long: {len(owner)} chars. Maximum is {MAX_OWNER_LENGTH}."
            if '\x00' in owner or any(ord(c) < 32 for c in owner):
                return False, f"{field_name}[{i}] contains invalid control characters"
            if owner in seen:
                return False, f"{field_name} contains duplicate value: {owner}"
            seen.add(owner)
        return True, ""

    def _validate_attributes(self, attributes: Optional[List[str]]) -> Tuple[bool, str]:
        """Validate attribute names list."""
        if not attributes:
            return True, ""  # Empty/None is valid
        if len(attributes) > MAX_ATTRIBUTES_COUNT:
            return False, f"Too many attributes: {len(attributes)}. Maximum is {MAX_ATTRIBUTES_COUNT}."
        for i, attr in enumerate(attributes):
            if not attr or not isinstance(attr, str):
                return False, f"Attribute at index {i} must be a non-empty string"
            if len(attr) > MAX_ATTRIBUTE_LENGTH:
                return False, f"Attribute '{attr}' too long: {len(attr)} chars. Maximum is {MAX_ATTRIBUTE_LENGTH}."
            if not ATTRIBUTE_NAME_PATTERN.match(attr):
                return False, f"Invalid attribute name '{attr}'. Must be alphanumeric starting with a letter."
        return True, ""

    def _validate_url_for_ssrf(self, url: str) -> Tuple[bool, str]:
        """
        Validate tenant URL to prevent SSRF attacks.

        Checks:
        - HTTPS scheme required
        - Blocked hostnames (localhost, metadata endpoints)
        - Blocked domain suffixes (internal domains)
        - Private/reserved IP addresses
        """
        try:
            parsed = urlparse(url)

            # Require HTTPS
            if parsed.scheme != 'https':
                return False, "Only HTTPS URLs are allowed"

            hostname = parsed.hostname
            if not hostname:
                return False, "Invalid URL: no hostname found"

            hostname_lower = hostname.lower()

            # Check blocked hostnames
            if hostname_lower in BLOCKED_HOSTNAMES:
                return False, f"Blocked hostname: {hostname}"

            # Check blocked domain suffixes
            if hostname_lower.endswith(BLOCKED_DOMAIN_SUFFIXES):
                return False, f"Internal domain not allowed: {hostname}"

            # Check if hostname is a private/reserved IP
            try:
                ip = ipaddress.ip_address(hostname)
                if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local:
                    return False, f"Private/reserved IP not allowed: {hostname}"
                if hostname in CLOUD_METADATA_IPS:
                    return False, f"Cloud metadata endpoint not allowed: {hostname}"
            except ValueError:
                pass  # Not an IP address, continue

            # Validate Atlan domain (warning only for flexibility)
            if not hostname_lower.endswith('.atlan.com'):
                logger.warning(f"Non-standard Atlan domain: {hostname}. Expected *.atlan.com")

            return True, ""

        except Exception as e:
            return False, f"URL validation failed: {str(e)}"

    async def _initialize_client(self) -> None:
        """Initialize Atlan API client with credentials."""
        if not self.credentials:
            raise ValueError("No credentials provided")

        self.tenant_url = self.credentials.get("tenant_url")
        self.api_token = self.credentials.get("api_token")

        if not all([self.tenant_url, self.api_token]):
            raise ValueError("Missing required Atlan credentials: tenant_url, api_token")

        # Normalize URL
        self.tenant_url = self.tenant_url.strip().rstrip('/')

        # Reject HTTP URLs
        if self.tenant_url.lower().startswith('http://'):
            raise ValueError("Only HTTPS URLs are allowed for Atlan tenant")

        # Add https:// if no scheme
        if not self.tenant_url.lower().startswith('https://'):
            self.tenant_url = f"https://{self.tenant_url}"

        # Validate URL for SSRF protection
        is_valid, error_msg = self._validate_url_for_ssrf(self.tenant_url)
        if not is_valid:
            raise ValueError(f"Invalid tenant URL: {error_msg}")

        # Configure session with timeouts and connection limits
        timeout = aiohttp.ClientTimeout(total=30, connect=10, sock_read=15)
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
        self.session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        logger.info(f"Atlan provider initialized successfully for tenant: {self.tenant_url}")

    async def _wait_for_rate_limit(self):
        """Implement sliding window rate limiting with thread safety."""
        async with self._rate_lock:
            now = datetime.now()
            window_start = now - timedelta(seconds=self._rate_window)

            # Clean old entries
            self._request_times = [t for t in self._request_times if t > window_start]

            if len(self._request_times) >= self._rate_limit:
                # Wait for oldest request to exit window
                sleep_time = (self._request_times[0] - window_start).total_seconds()
                await asyncio.sleep(sleep_time + 0.1)

            self._request_times.append(now)

    async def _make_request(self, method: str, endpoint: str,
                           max_retries: int = 3, **kwargs) -> Dict[str, Any]:
        """Make authenticated request to Atlan API with retry logic."""
        await self._wait_for_rate_limit()

        try:
            self._ensure_initialized()

            url = f"{self.tenant_url}/api/meta/{endpoint.lstrip('/')}"
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }

            if "headers" in kwargs:
                headers.update(kwargs.pop("headers"))

            for attempt in range(max_retries):
                try:
                    async with self.session.request(method, url, headers=headers, **kwargs) as response:
                        # Handle rate limiting
                        if response.status == 429:
                            retry_after = int(response.headers.get('Retry-After', 60))
                            # Cap retry_after to prevent DoS via long delays
                            retry_after = min(retry_after, MAX_RETRY_AFTER)
                            logger.warning(f"Rate limited, waiting {retry_after}s")
                            await asyncio.sleep(retry_after)
                            continue

                        if response.status not in [200, 201, 204]:
                            error_text = await response.text()
                            if attempt < max_retries - 1:
                                await asyncio.sleep(2 ** attempt)
                                continue
                            return {"error": f"HTTP {response.status}: {error_text}"}

                        if response.status == 204:
                            return {"success": True}

                        return await response.json()

                except aiohttp.ClientError as e:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    return {"error": str(e)}

            return {"error": "Max retries exceeded"}

        except Exception as e:
            logger.error(f"Atlan API request failed: {e}")
            return {"error": str(e)}

    # ==================== SEARCH OPERATIONS ====================

    async def search_assets(self, query: str = "*",
                           asset_types: Optional[List[str]] = None,
                           from_: int = 0, size: int = 25,
                           attributes: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Search for assets in Atlan using Elasticsearch DSL.

        Args:
            query: Search query string (supports Elasticsearch query syntax)
            asset_types: List of asset type names to filter (Table, Column, Dashboard, etc.)
            from_: Pagination start offset (0 to 10000)
            size: Number of results to return (1 to 100)
            attributes: List of attribute names to include in response
        """
        # Validate pagination parameters
        is_valid, error_msg = self._validate_pagination(from_, size)
        if not is_valid:
            return {"error": error_msg}

        # Validate asset_types if provided
        if asset_types:
            is_valid, error_msg = self._validate_asset_types(asset_types)
            if not is_valid:
                return {"error": error_msg}

        # Validate query parameter
        is_valid, error_msg = self._validate_query(query)
        if not is_valid:
            return {"error": error_msg}

        # Validate attributes if provided
        if attributes:
            is_valid, error_msg = self._validate_attributes(attributes)
            if not is_valid:
                return {"error": error_msg}

        self._log_operation("search_assets", query=query, asset_types=asset_types)

        dsl = {
            "from": from_,
            "size": size,
            "query": {
                "bool": {
                    "must": [{"query_string": {"query": query}}]
                }
            }
        }

        if asset_types:
            dsl["query"]["bool"]["filter"] = [
                {"terms": {"__typeName.keyword": asset_types}}
            ]

        body = {"dsl": dsl}
        if attributes:
            body["attributes"] = attributes
        else:
            # Default attributes to retrieve
            body["attributes"] = [
                "name", "qualifiedName", "description", "ownerUsers",
                "certificateStatus", "createTime", "updateTime"
            ]

        result = await self._make_request("POST", "search/indexsearch", json=body)

        if "error" in result:
            return result

        return {
            "entities": result.get("entities", []),
            "approximateCount": result.get("approximateCount", 0),
            "from": from_,
            "size": size
        }

    async def search_by_type(self, type_name: str, from_: int = 0, size: int = 25) -> Dict[str, Any]:
        """Search for all assets of a specific type."""
        return await self.search_assets(
            query="*",
            asset_types=[type_name],
            from_=from_,
            size=size
        )

    # ==================== ASSET CRUD OPERATIONS ====================

    async def get_asset(self, guid: str, attributes: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get a specific asset by GUID."""
        # Validate GUID format
        is_valid, error_msg = self._validate_guid(guid)
        if not is_valid:
            return {"error": error_msg}

        # Validate attributes if provided
        if attributes:
            is_valid, error_msg = self._validate_attributes(attributes)
            if not is_valid:
                return {"error": error_msg}

        self._log_operation("get_asset", guid=guid)

        params = {}
        if attributes:
            params["attr"] = ",".join(attributes)

        result = await self._make_request("GET", f"entity/guid/{guid}", params=params)

        if "error" in result:
            return result

        return {"entity": result.get("entity", result)}

    async def get_asset_by_qualified_name(self, type_name: str, qualified_name: str) -> Dict[str, Any]:
        """Get asset by type and qualified name."""
        # Validate type_name to prevent path traversal
        is_valid, error_msg = self._validate_type_name(type_name)
        if not is_valid:
            return {"error": error_msg}

        # Validate qualified_name
        is_valid, error_msg = self._validate_qualified_name(qualified_name)
        if not is_valid:
            return {"error": error_msg}

        self._log_operation("get_asset_by_qualified_name", type_name=type_name, qualified_name=qualified_name)

        result = await self._make_request(
            "GET",
            f"entity/uniqueAttribute/type/{type_name}",
            params={"attr:qualifiedName": qualified_name}
        )

        return result

    async def create_asset(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new asset in Atlan."""
        self._log_operation("create_asset", type_name=entity.get("typeName"))

        body = {"entities": [entity]}
        result = await self._make_request("POST", "entity/bulk", json=body)

        return result

    async def update_asset(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing asset."""
        self._log_operation("update_asset", guid=entity.get("guid"))

        body = {"entities": [entity]}
        result = await self._make_request("POST", "entity/bulk", json=body)

        return result

    async def delete_asset(self, guid: str, hard_delete: bool = False) -> Dict[str, Any]:
        """Delete an asset by GUID (soft or hard delete)."""
        # Validate GUID format
        is_valid, error_msg = self._validate_guid(guid)
        if not is_valid:
            return {"error": error_msg}

        self._log_operation("delete_asset", guid=guid, hard_delete=hard_delete)

        endpoint = f"entity/guid/{guid}"
        if hard_delete:
            endpoint += "?deleteType=HARD"

        result = await self._make_request("DELETE", endpoint)

        return result

    async def update_asset_description(self, guid: str, description: str) -> Dict[str, Any]:
        """Update the description of an asset."""
        # Validate GUID format
        is_valid, error_msg = self._validate_guid(guid)
        if not is_valid:
            return {"error": error_msg}

        # Validate description
        is_valid, error_msg = self._validate_text_field(description, "description", MAX_DESCRIPTION_LENGTH)
        if not is_valid:
            return {"error": error_msg}

        self._log_operation("update_asset_description", guid=guid)

        entity = {
            "guid": guid,
            "attributes": {
                "description": description
            }
        }

        return await self.update_asset(entity)

    async def update_asset_owners(self, guid: str, owner_users: List[str] = None,
                                  owner_groups: List[str] = None) -> Dict[str, Any]:
        """Update the owners of an asset."""
        # Validate GUID format
        is_valid, error_msg = self._validate_guid(guid)
        if not is_valid:
            return {"error": error_msg}

        # Validate owner_users if provided
        is_valid, error_msg = self._validate_owners(owner_users, "owner_users")
        if not is_valid:
            return {"error": error_msg}

        # Validate owner_groups if provided
        is_valid, error_msg = self._validate_owners(owner_groups, "owner_groups")
        if not is_valid:
            return {"error": error_msg}

        self._log_operation("update_asset_owners", guid=guid)

        entity = {
            "guid": guid,
            "attributes": {}
        }

        if owner_users:
            entity["attributes"]["ownerUsers"] = owner_users
        if owner_groups:
            entity["attributes"]["ownerGroups"] = owner_groups

        return await self.update_asset(entity)

    # ==================== LINEAGE OPERATIONS ====================

    async def get_lineage(self, guid: str, direction: str = "BOTH",
                         depth: int = 3) -> Dict[str, Any]:
        """
        Get lineage for an asset.

        Args:
            guid: Asset GUID
            direction: UPSTREAM, DOWNSTREAM, or BOTH
            depth: How many hops to traverse (1-10)
        """
        # Validate GUID format
        is_valid, error_msg = self._validate_guid(guid)
        if not is_valid:
            return {"error": error_msg}

        # Validate direction
        direction_upper = direction.upper() if direction else "BOTH"
        if direction_upper not in VALID_LINEAGE_DIRECTIONS:
            return {"error": f"Invalid direction: {direction}. Must be one of: {', '.join(VALID_LINEAGE_DIRECTIONS)}"}
        direction = direction_upper

        self._log_operation("get_lineage", guid=guid, direction=direction, depth=depth)

        params = {
            "direction": direction,
            "depth": min(depth, 10)
        }

        result = await self._make_request("GET", f"lineage/{guid}", params=params)

        if "error" in result:
            return result

        return {
            "baseEntityGuid": guid,
            "lineageDirection": direction,
            "lineageDepth": depth,
            "guidEntityMap": result.get("guidEntityMap", {}),
            "relations": result.get("relations", [])
        }

    # ==================== GLOSSARY OPERATIONS ====================

    async def list_glossaries(self, from_: int = 0, size: int = 25) -> Dict[str, Any]:
        """List all glossaries."""
        self._log_operation("list_glossaries")

        return await self.search_assets(
            query="*",
            asset_types=["AtlasGlossary"],
            from_=from_,
            size=size
        )

    async def get_glossary(self, guid: str) -> Dict[str, Any]:
        """Get a specific glossary by GUID."""
        return await self.get_asset(guid)

    async def list_glossary_terms(self, glossary_guid: Optional[str] = None,
                                  from_: int = 0, size: int = 25) -> Dict[str, Any]:
        """List glossary terms, optionally filtered by glossary."""
        # Validate glossary_guid if provided
        if glossary_guid:
            is_valid, error_msg = self._validate_guid(glossary_guid)
            if not is_valid:
                return {"error": f"Invalid glossary GUID: {error_msg}"}

        self._log_operation("list_glossary_terms", glossary_guid=glossary_guid)

        query = "*"
        if glossary_guid:
            query = f"__glossary:{glossary_guid}"

        return await self.search_assets(
            query=query,
            asset_types=["AtlasGlossaryTerm"],
            from_=from_,
            size=size
        )

    async def get_glossary_term(self, guid: str) -> Dict[str, Any]:
        """Get a specific glossary term by GUID."""
        return await self.get_asset(guid)

    async def create_glossary_term(self, name: str, glossary_guid: str,
                                   description: Optional[str] = None,
                                   short_description: Optional[str] = None) -> Dict[str, Any]:
        """Create a new glossary term."""
        # Validate name
        is_valid, error_msg = self._validate_name(name)
        if not is_valid:
            return {"error": error_msg}

        # Validate glossary_guid
        is_valid, error_msg = self._validate_guid(glossary_guid)
        if not is_valid:
            return {"error": f"Invalid glossary GUID: {error_msg}"}

        self._log_operation("create_glossary_term", name=name, glossary_guid=glossary_guid)

        entity = {
            "typeName": "AtlasGlossaryTerm",
            "attributes": {
                "name": name,
                "qualifiedName": f"{name}@{glossary_guid}",
                "anchor": {"guid": glossary_guid}
            }
        }

        if description:
            is_valid, error_msg = self._validate_text_field(description, "description", MAX_DESCRIPTION_LENGTH)
            if not is_valid:
                return {"error": error_msg}
            entity["attributes"]["longDescription"] = description

        if short_description:
            is_valid, error_msg = self._validate_text_field(short_description, "short_description", MAX_NAME_LENGTH)
            if not is_valid:
                return {"error": error_msg}
            entity["attributes"]["shortDescription"] = short_description

        return await self.create_asset(entity)

    async def list_glossary_categories(self, glossary_guid: Optional[str] = None,
                                       from_: int = 0, size: int = 25) -> Dict[str, Any]:
        """List glossary categories."""
        # Validate glossary_guid if provided
        if glossary_guid:
            is_valid, error_msg = self._validate_guid(glossary_guid)
            if not is_valid:
                return {"error": f"Invalid glossary GUID: {error_msg}"}

        self._log_operation("list_glossary_categories", glossary_guid=glossary_guid)

        query = "*"
        if glossary_guid:
            query = f"__glossary:{glossary_guid}"

        return await self.search_assets(
            query=query,
            asset_types=["AtlasGlossaryCategory"],
            from_=from_,
            size=size
        )

    async def link_term_to_asset(self, term_guid: str, asset_guid: str) -> Dict[str, Any]:
        """Link a glossary term to an asset."""
        # Validate GUID formats
        is_valid, error_msg = self._validate_guid(term_guid)
        if not is_valid:
            return {"error": f"Invalid term GUID: {error_msg}"}
        is_valid, error_msg = self._validate_guid(asset_guid)
        if not is_valid:
            return {"error": f"Invalid asset GUID: {error_msg}"}

        self._log_operation("link_term_to_asset", term_guid=term_guid, asset_guid=asset_guid)

        # Get the asset first to get its type
        asset_result = await self.get_asset(asset_guid)
        if "error" in asset_result:
            return asset_result

        entity = asset_result.get("entity", {})
        type_name = entity.get("typeName")

        # Validate type_name was returned
        if not type_name:
            return {"error": "Could not determine asset type from Atlan API response"}

        # Update asset with term reference
        update_entity = {
            "guid": asset_guid,
            "typeName": type_name,
            "attributes": {
                "meanings": [{"guid": term_guid}]
            }
        }

        return await self.update_asset(update_entity)

    # ==================== CLASSIFICATION/TAG OPERATIONS ====================

    async def list_classifications(self) -> Dict[str, Any]:
        """List all classification types (tags)."""
        self._log_operation("list_classifications")

        result = await self._make_request("GET", "types/typedefs", params={"type": "classification"})

        if "error" in result:
            return result

        return {
            "classifications": result.get("classificationDefs", [])
        }

    async def add_classification_to_asset(self, guid: str, classification_name: str,
                                          attributes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Add a classification (tag) to an asset."""
        # Validate GUID format
        is_valid, error_msg = self._validate_guid(guid)
        if not is_valid:
            return {"error": error_msg}

        # Validate classification_name
        is_valid, error_msg = self._validate_classification_name(classification_name)
        if not is_valid:
            return {"error": error_msg}

        self._log_operation("add_classification", guid=guid, classification=classification_name)

        body = {
            "classification": {
                "typeName": classification_name,
                "attributes": attributes or {}
            },
            "entityGuids": [guid]
        }

        result = await self._make_request("POST", "entity/bulk/classification", json=body)

        return result

    async def remove_classification_from_asset(self, guid: str, classification_name: str) -> Dict[str, Any]:
        """Remove a classification from an asset."""
        # Validate GUID format
        is_valid, error_msg = self._validate_guid(guid)
        if not is_valid:
            return {"error": error_msg}

        # Validate classification_name
        is_valid, error_msg = self._validate_classification_name(classification_name)
        if not is_valid:
            return {"error": error_msg}

        self._log_operation("remove_classification", guid=guid, classification=classification_name)

        # URL encode classification_name for safety
        encoded_classification = quote(classification_name, safe='')

        result = await self._make_request(
            "DELETE",
            f"entity/guid/{guid}/classification/{encoded_classification}"
        )

        return result

    # ==================== ASSET TYPE SPECIFIC QUERIES ====================

    async def list_tables(self, from_: int = 0, size: int = 25) -> Dict[str, Any]:
        """List all table assets."""
        return await self.search_by_type("Table", from_, size)

    async def list_columns(self, table_guid: Optional[str] = None,
                          from_: int = 0, size: int = 25) -> Dict[str, Any]:
        """List columns, optionally filtered by parent table."""
        # Validate table_guid if provided
        if table_guid:
            is_valid, error_msg = self._validate_guid(table_guid)
            if not is_valid:
                return {"error": f"Invalid table GUID: {error_msg}"}

        self._log_operation("list_columns", table_guid=table_guid)

        query = "*"
        if table_guid:
            query = f"table.guid:{table_guid}"

        return await self.search_assets(
            query=query,
            asset_types=["Column"],
            from_=from_,
            size=size
        )

    async def list_databases(self, from_: int = 0, size: int = 25) -> Dict[str, Any]:
        """List all database assets."""
        return await self.search_by_type("Database", from_, size)

    async def list_schemas(self, from_: int = 0, size: int = 25) -> Dict[str, Any]:
        """List all schema assets."""
        return await self.search_by_type("Schema", from_, size)

    async def list_dashboards(self, from_: int = 0, size: int = 25) -> Dict[str, Any]:
        """List all BI dashboard assets."""
        return await self.search_assets(
            query="*",
            asset_types=[
                "TableauDashboard", "LookerDashboard", "PowerBIDashboard",
                "MetabaseDashboard", "ModeReport", "SigmaWorkbook"
            ],
            from_=from_,
            size=size
        )

    async def list_dbt_models(self, from_: int = 0, size: int = 25) -> Dict[str, Any]:
        """List dbt model assets."""
        return await self.search_assets(
            query="*",
            asset_types=["DbtModel", "DbtSource"],
            from_=from_,
            size=size
        )

    async def list_airflow_dags(self, from_: int = 0, size: int = 25) -> Dict[str, Any]:
        """List Airflow DAG assets."""
        return await self.search_assets(
            query="*",
            asset_types=["AirflowDag", "AirflowTask"],
            from_=from_,
            size=size
        )

    async def list_kafka_topics(self, from_: int = 0, size: int = 25) -> Dict[str, Any]:
        """List Kafka topic assets."""
        return await self.search_by_type("KafkaTopic", from_, size)

    async def list_s3_objects(self, from_: int = 0, size: int = 25) -> Dict[str, Any]:
        """List S3 object assets."""
        return await self.search_assets(
            query="*",
            asset_types=["S3Bucket", "S3Object", "ADLS", "GCSBucket"],
            from_=from_,
            size=size
        )

    # ==================== CUSTOM METADATA OPERATIONS ====================

    async def update_custom_metadata(self, guid: str, custom_metadata_name: str,
                                     attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Update custom metadata on an asset."""
        # Validate GUID format
        is_valid, error_msg = self._validate_guid(guid)
        if not is_valid:
            return {"error": error_msg}

        # Validate custom_metadata_name (same pattern as classification)
        if not custom_metadata_name:
            return {"error": "custom_metadata_name is required"}
        if not CLASSIFICATION_NAME_PATTERN.match(custom_metadata_name):
            return {"error": f"Invalid custom_metadata_name format: {custom_metadata_name}. Must be alphanumeric starting with a letter."}
        if len(custom_metadata_name) > 100:
            return {"error": f"custom_metadata_name too long: {len(custom_metadata_name)} chars. Maximum is 100."}

        self._log_operation("update_custom_metadata", guid=guid, metadata_name=custom_metadata_name)

        body = {
            "guid": guid,
            "businessAttributes": {
                custom_metadata_name: attributes
            }
        }

        result = await self._make_request("POST", "entity/businessmetadata", json=body)

        return result

    async def get_custom_metadata_types(self) -> Dict[str, Any]:
        """Get all custom metadata type definitions."""
        self._log_operation("get_custom_metadata_types")

        result = await self._make_request("GET", "types/typedefs", params={"type": "business_metadata"})

        if "error" in result:
            return result

        return {
            "customMetadataTypes": result.get("businessMetadataDefs", [])
        }

    # ==================== CERTIFICATION OPERATIONS ====================

    async def certify_asset(self, guid: str, status: str = "VERIFIED",
                           message: Optional[str] = None) -> Dict[str, Any]:
        """
        Certify an asset.

        Args:
            guid: Asset GUID
            status: VERIFIED, DEPRECATED, or DRAFT
            message: Optional certification message
        """
        # Validate GUID format
        is_valid, error_msg = self._validate_guid(guid)
        if not is_valid:
            return {"error": error_msg}

        # Validate status
        status_upper = status.upper() if status else "VERIFIED"
        if status_upper not in VALID_CERTIFICATION_STATUSES:
            return {"error": f"Invalid status: {status}. Must be one of: {', '.join(VALID_CERTIFICATION_STATUSES)}"}
        status = status_upper

        # Validate message if provided
        if message:
            is_valid, error_msg = self._validate_text_field(message, "message", MAX_MESSAGE_LENGTH)
            if not is_valid:
                return {"error": error_msg}

        self._log_operation("certify_asset", guid=guid, status=status)

        entity = {
            "guid": guid,
            "attributes": {
                "certificateStatus": status
            }
        }

        if message:
            entity["attributes"]["certificateStatusMessage"] = message

        return await self.update_asset(entity)

    # ==================== BULK OPERATIONS ====================

    async def bulk_update_assets(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Update multiple assets in a single request."""
        # Validate entities
        if not entities:
            return {"error": "entities list is required and cannot be empty"}
        if not isinstance(entities, list):
            return {"error": "entities must be a list"}
        if len(entities) > MAX_PAGE_SIZE:
            return {"error": f"Too many entities. Maximum is {MAX_PAGE_SIZE}, got {len(entities)}"}

        # Validate each entity has required fields
        for i, entity in enumerate(entities):
            if not isinstance(entity, dict):
                return {"error": f"Entity at index {i} must be a dictionary"}
            # Each entity must have either guid (for update) or typeName (for create)
            if not entity.get("guid") and not entity.get("typeName"):
                return {"error": f"Entity at index {i} must have either 'guid' (for update) or 'typeName' (for create)"}
            # Validate GUID format if provided
            if entity.get("guid"):
                is_valid, error_msg = self._validate_guid(entity["guid"])
                if not is_valid:
                    return {"error": f"Entity at index {i}: {error_msg}"}

        self._log_operation("bulk_update_assets", count=len(entities))

        body = {"entities": entities}
        result = await self._make_request("POST", "entity/bulk", json=body)

        return result

    async def cleanup(self) -> None:
        """Clean up Atlan provider resources."""
        if self.session:
            await self.session.close()
            self.session = None

        await super().cleanup()
