import json
import os
import datetime
import time
import hashlib
from typing import Dict, List, Optional, Any
from services.utils.logger import logger

# Try to import requests
try:
    import requests
    from requests.exceptions import HTTPError, RequestException, Timeout
    REQUESTS_AVAILABLE = True
except ImportError:
    logger.warning("requests library not available. Install with: pip install requests")
    REQUESTS_AVAILABLE = False


class AtlanClient:
    """Synchronous HTTP client for Atlan API during metadata scanning"""

    def __init__(self, tenant_url: str, api_token: str):
        """
        Initialize Atlan client

        Args:
            tenant_url: Atlan tenant URL (e.g., https://org.atlan.com)
            api_token: Atlan API token
        """
        self.tenant_url = tenant_url.rstrip('/')
        if not self.tenant_url.startswith('http://') and not self.tenant_url.startswith('https://'):
            self.tenant_url = f"https://{self.tenant_url}"

        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        self.timeout = 30
        self.request_delay = 0.1  # 100ms delay between requests

    def _request(self, method: str, endpoint: str, json_data: Optional[Dict] = None) -> Optional[Dict]:
        """Make HTTP request with rate limiting"""
        url = f"{self.tenant_url}{endpoint}"

        try:
            time.sleep(self.request_delay)  # Rate limiting

            if method == "GET":
                response = requests.get(url, headers=self.headers, timeout=self.timeout)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=json_data, timeout=self.timeout)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return None

            response.raise_for_status()
            return response.json()

        except HTTPError as e:
            logger.warning(f"HTTP error for {endpoint}: {e}")
            return None
        except Timeout:
            logger.warning(f"Request timeout for {endpoint}")
            return None
        except RequestException as e:
            logger.warning(f"Request error for {endpoint}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Unexpected error for {endpoint}: {e}")
            return None

    def test_connection(self) -> bool:
        """Test connection to Atlan"""
        result = self._request("GET", "/api/meta/types/typedefs/headers")
        return result is not None

    def search_assets(self, asset_types: Optional[List[str]] = None,
                     from_: int = 0, size: int = 100,
                     attributes: Optional[List[str]] = None) -> Optional[Dict]:
        """
        Search for assets in Atlan

        Args:
            asset_types: List of asset types to filter (e.g., ["Table", "View"])
            from_: Pagination offset
            size: Page size
            attributes: List of attributes to return

        Returns:
            Search response dictionary
        """
        query = {"match_all": {}}

        if asset_types:
            query = {
                "bool": {
                    "filter": [
                        {"terms": {"__typeName.keyword": asset_types}}
                    ]
                }
            }

        payload = {
            "dsl": {
                "from": from_,
                "size": size,
                "query": query
            },
            "attributes": attributes or [
                "name", "qualifiedName", "description", "certificateStatus",
                "ownerUsers", "ownerGroups", "createTime", "updateTime",
                "classifications", "meanings"
            ]
        }

        return self._request("POST", "/api/meta/search/indexsearch", payload)

    def get_asset(self, guid: str) -> Optional[Dict]:
        """Get asset details by GUID"""
        return self._request("GET", f"/api/meta/entity/guid/{guid}")

    def get_lineage(self, guid: str, direction: str = "BOTH", depth: int = 1) -> Optional[Dict]:
        """
        Get lineage for an asset

        Args:
            guid: Asset GUID
            direction: UPSTREAM, DOWNSTREAM, or BOTH
            depth: Lineage depth
        """
        return self._request("GET", f"/api/meta/lineage/{guid}?direction={direction}&depth={depth}")

    def list_glossaries(self) -> Optional[Dict]:
        """List all glossaries"""
        payload = {
            "dsl": {
                "from": 0,
                "size": 100,
                "query": {
                    "bool": {
                        "filter": [
                            {"term": {"__typeName.keyword": "AtlasGlossary"}}
                        ]
                    }
                }
            },
            "attributes": ["name", "qualifiedName", "shortDescription", "longDescription"]
        }
        return self._request("POST", "/api/meta/search/indexsearch", payload)

    def list_glossary_terms(self, glossary_guid: Optional[str] = None) -> Optional[Dict]:
        """List glossary terms, optionally filtered by glossary"""
        filters = [{"term": {"__typeName.keyword": "AtlasGlossaryTerm"}}]

        if glossary_guid:
            filters.append({"term": {"anchor.guid": glossary_guid}})

        payload = {
            "dsl": {
                "from": 0,
                "size": 100,
                "query": {
                    "bool": {
                        "filter": filters
                    }
                }
            },
            "attributes": [
                "name", "qualifiedName", "shortDescription", "longDescription",
                "examples", "anchor", "categories", "assignedEntities"
            ]
        }
        return self._request("POST", "/api/meta/search/indexsearch", payload)

    def paginate_glossary_terms(self, glossary_guid: Optional[str] = None,
                                max_results: int = 5000) -> List[Dict]:
        """
        Paginate through all glossary terms

        Args:
            glossary_guid: Optional glossary GUID to filter terms
            max_results: Maximum number of terms to return

        Returns:
            List of glossary term dictionaries
        """
        terms = []
        from_ = 0
        page_size = 100

        while len(terms) < max_results:
            filters = [{"term": {"__typeName.keyword": "AtlasGlossaryTerm"}}]
            if glossary_guid:
                filters.append({"term": {"anchor.guid": glossary_guid}})

            payload = {
                "dsl": {
                    "from": from_,
                    "size": page_size,
                    "query": {
                        "bool": {
                            "filter": filters
                        }
                    }
                },
                "attributes": [
                    "name", "qualifiedName", "shortDescription", "longDescription",
                    "examples", "anchor", "categories", "assignedEntities"
                ]
            }

            result = self._request("POST", "/api/meta/search/indexsearch", payload)
            if not result:
                break

            entities = result.get("entities", [])
            if not entities:
                break

            terms.extend(entities)
            from_ += page_size

            if len(entities) < page_size:
                break

        return terms[:max_results]

    def paginate_assets(self, asset_types: Optional[List[str]] = None,
                       max_results: int = 10000) -> List[Dict]:
        """
        Paginate through all assets of given types

        Args:
            asset_types: List of asset types to fetch
            max_results: Maximum number of results to return

        Returns:
            List of asset dictionaries
        """
        assets = []
        from_ = 0
        page_size = 100

        while len(assets) < max_results:
            result = self.search_assets(
                asset_types=asset_types,
                from_=from_,
                size=page_size
            )

            if not result:
                break

            entities = result.get("entities", [])
            if not entities:
                break

            assets.extend(entities)
            from_ += page_size

            # Log progress
            if len(assets) % 500 == 0:
                logger.info(f"Fetched {len(assets)} assets...")

            # Check if we've reached the end
            if len(entities) < page_size:
                break

        return assets[:max_results]


def setup_atlan_client(atlan_config: Dict) -> Optional[AtlanClient]:
    """
    Set up Atlan client

    Args:
        atlan_config: Dictionary containing Atlan configuration
            - tenant_url: Atlan tenant URL
            - api_token: Atlan API token

    Returns:
        AtlanClient instance or None
    """
    if not REQUESTS_AVAILABLE:
        raise ImportError("requests library not installed")

    try:
        tenant_url = atlan_config.get("tenant_url")
        api_token = atlan_config.get("api_token")

        if not tenant_url or not api_token:
            logger.error("Missing required Atlan configuration (tenant_url, api_token)")
            return None

        client = AtlanClient(tenant_url, api_token)

        # Test connection
        if not client.test_connection():
            logger.error("Failed to connect to Atlan")
            return None

        logger.info(f"Atlan client created for tenant: {tenant_url}")
        return client

    except Exception as e:
        logger.error(f"Failed to create Atlan client: {e}")
        return None


def format_asset_metadata(entity: Dict, provider: str = "atlan") -> Dict:
    """
    Format asset metadata for storage

    Args:
        entity: Raw entity from Atlan API
        provider: Provider name

    Returns:
        Formatted metadata dictionary
    """
    attrs = entity.get("attributes", {})
    type_name = entity.get("typeName", attrs.get("__typeName", "Unknown"))

    # Build qualified name for FQTN
    qualified_name = attrs.get("qualifiedName", "")
    name = attrs.get("name", entity.get("guid", "Unknown"))

    # Extract owners
    owner_users = attrs.get("ownerUsers", [])
    owner_groups = attrs.get("ownerGroups", [])

    # Extract classifications/tags
    classifications = []
    for cls in entity.get("classifications", []) or attrs.get("classifications", []) or []:
        if isinstance(cls, dict):
            classifications.append(cls.get("typeName", cls.get("name", "")))
        elif isinstance(cls, str):
            classifications.append(cls)

    # Extract glossary term links
    meanings = []
    for meaning in attrs.get("meanings", []) or []:
        if isinstance(meaning, dict):
            meanings.append({
                "term_name": meaning.get("displayText", ""),
                "term_guid": meaning.get("termGuid", meaning.get("guid", ""))
            })

    metadata = {
        "guid": entity.get("guid"),
        "type_name": type_name,
        "name": name,
        "qualified_name": qualified_name,
        "description": attrs.get("description", ""),
        "certificate_status": attrs.get("certificateStatus", ""),
        "owner_users": owner_users if isinstance(owner_users, list) else [],
        "owner_groups": owner_groups if isinstance(owner_groups, list) else [],
        "classifications": classifications,
        "glossary_terms": meanings,
        "create_time": attrs.get("createTime"),
        "update_time": attrs.get("updateTime"),
        "provider": provider
    }

    # Add type-specific attributes
    if type_name in ["Table", "View", "MaterializedView"]:
        metadata.update({
            "database_name": attrs.get("databaseName", ""),
            "schema_name": attrs.get("schemaName", ""),
            "column_count": attrs.get("columnCount", 0),
            "row_count": attrs.get("rowCount"),
            "size_bytes": attrs.get("sizeBytes")
        })
    elif type_name == "Column":
        metadata.update({
            "data_type": attrs.get("dataType", ""),
            "is_nullable": attrs.get("isNullable"),
            "is_primary": attrs.get("isPrimary"),
            "table_qualified_name": attrs.get("tableQualifiedName", "")
        })
    elif type_name in ["Dashboard", "LookerDashboard", "TableauDashboard", "PowerBIDashboard"]:
        metadata.update({
            "dashboard_type": type_name,
            "connection_name": attrs.get("connectionName", "")
        })
    elif type_name in ["DbtModel", "DbtSource"]:
        metadata.update({
            "dbt_project_name": attrs.get("dbtProjectName", ""),
            "dbt_package_name": attrs.get("dbtPackageName", ""),
            "dbt_model_sql": attrs.get("dbtModelSql", "")
        })
    elif type_name in ["AirflowDag", "AirflowTask"]:
        metadata.update({
            "dag_id": attrs.get("airflowDagId", attrs.get("dagId", "")),
            "schedule_interval": attrs.get("scheduleInterval", "")
        })
    elif type_name == "KafkaTopic":
        metadata.update({
            "partition_count": attrs.get("partitionCount"),
            "replication_factor": attrs.get("replicationFactor")
        })
    elif type_name in ["S3Object", "S3Bucket"]:
        metadata.update({
            "s3_bucket_name": attrs.get("s3BucketName", attrs.get("bucketName", "")),
            "s3_object_key": attrs.get("s3ObjectKey", attrs.get("objectKey", ""))
        })

    return metadata


def generate_atlan_overview(base_dir: str, project_config: Dict, dest_folder: str,
                           target_asset_types: Optional[List[str]] = None,
                           atlan_config: Optional[Dict] = None,
                           output_format: str = "json"):
    """
    Generate Atlan metadata overview

    Args:
        base_dir: Base directory for project data
        project_config: Project configuration
        dest_folder: Destination folder for metadata files
        target_asset_types: Optional list of specific asset types to scan
        atlan_config: Atlan connection configuration
        output_format: Output format - "json" or "both"
    """
    if not REQUESTS_AVAILABLE:
        logger.error("requests library not available. Cannot generate Atlan overview.")
        return

    if not atlan_config:
        logger.error("Atlan configuration not provided")
        return

    try:
        # Setup Atlan client
        client = setup_atlan_client(atlan_config)
        if not client:
            logger.error("Failed to setup Atlan client")
            return

        # Create metadata directory structure
        metadata_base = os.path.join(dest_folder, "database_metadata")
        provider_dir = os.path.join(metadata_base, "providers", "atlan")
        tables_dir = os.path.join(provider_dir, "tables")
        glossary_dir = os.path.join(provider_dir, "glossary")
        lineage_dir = os.path.join(provider_dir, "lineage")
        os.makedirs(tables_dir, exist_ok=True)
        os.makedirs(glossary_dir, exist_ok=True)
        os.makedirs(lineage_dir, exist_ok=True)

        # Define default asset types if not specified
        if not target_asset_types:
            target_asset_types = [
                "Table", "View", "MaterializedView",
                "Column",
                "Database", "Schema",
                "Dashboard", "LookerDashboard", "TableauDashboard", "PowerBIDashboard", "MetabaseDashboard",
                "DbtModel", "DbtSource",
                "AirflowDag", "AirflowTask",
                "KafkaTopic",
                "S3Object", "S3Bucket",
                "AtlasGlossaryTerm"
            ]

        # Get configuration options
        max_assets = atlan_config.get("max_assets", 10000)
        include_lineage = atlan_config.get("include_lineage", True)
        include_glossary = atlan_config.get("include_glossary", True)

        logger.info(f"Scanning Atlan for asset types: {target_asset_types}")

        # Fetch assets
        assets = client.paginate_assets(
            asset_types=target_asset_types,
            max_results=max_assets
        )

        logger.info(f"Retrieved {len(assets)} assets from Atlan")

        if not assets:
            logger.warning("No assets found in Atlan")
            return

        # Track statistics
        stats = {
            "total_assets": 0,
            "by_type": {},
            "tables_with_lineage": 0,
            "glossary_terms": 0,
            "failed_assets": 0
        }
        manifest_entries = []

        # Process each asset
        for entity in assets:
            try:
                type_name = entity.get("typeName", entity.get("attributes", {}).get("__typeName", "Unknown"))
                guid = entity.get("guid", "")
                name = entity.get("attributes", {}).get("name", guid)

                # Format metadata
                metadata = format_asset_metadata(entity)

                # Create safe filename - sanitize to prevent path traversal
                safe_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in name)
                safe_name = safe_name.lstrip("._")  # Remove leading dots/underscores
                safe_name = safe_name[:100] if safe_name else ""
                if not safe_name:
                    safe_name = f"asset_{guid[:20]}" if guid else "unknown"

                # Determine subdirectory based on type
                if type_name in ["Table", "View", "MaterializedView", "Column",
                                "Dashboard", "LookerDashboard", "TableauDashboard",
                                "PowerBIDashboard", "MetabaseDashboard",
                                "DbtModel", "DbtSource", "AirflowDag", "AirflowTask",
                                "KafkaTopic", "S3Object", "S3Bucket", "Database", "Schema"]:
                    subdir = type_name
                    file_dir = os.path.join(tables_dir, subdir)
                elif type_name == "AtlasGlossaryTerm":
                    file_dir = glossary_dir
                else:
                    subdir = "Other"
                    file_dir = os.path.join(tables_dir, subdir)

                os.makedirs(file_dir, exist_ok=True)

                # Save asset metadata
                file_path = os.path.join(file_dir, f"{safe_name}.json")
                with open(file_path, 'w') as f:
                    json.dump(metadata, f, indent=2, default=str)

                # Add to manifest
                rel_path = os.path.relpath(file_path, provider_dir)
                manifest_entries.append({
                    "fqtn": f"atlan://{atlan_config.get('tenant_url', '').replace('https://', '').replace('http://', '')}/{type_name}/{name}",
                    "provider": "atlan",
                    "type": type_name,
                    "name": name,
                    "guid": guid,
                    "file_path": f"providers/atlan/{rel_path}"
                })

                # Update stats
                stats["total_assets"] += 1
                stats["by_type"][type_name] = stats["by_type"].get(type_name, 0) + 1

                # Fetch lineage for tables/views if enabled
                if include_lineage and type_name in ["Table", "View", "MaterializedView", "DbtModel"]:
                    try:
                        lineage_data = client.get_lineage(guid, direction="BOTH", depth=1)
                        if lineage_data:
                            lineage_file = os.path.join(lineage_dir, f"{safe_name}_lineage.json")
                            with open(lineage_file, 'w') as f:
                                json.dump(lineage_data, f, indent=2, default=str)
                            stats["tables_with_lineage"] += 1
                    except Exception as e:
                        logger.warning(f"Failed to fetch lineage for {name}: {e}")

            except Exception as e:
                logger.warning(f"Failed to process asset: {e}")
                stats["failed_assets"] += 1
                continue

        # Fetch glossary terms if enabled (with pagination)
        if include_glossary:
            logger.info("Fetching glossary terms with pagination...")
            try:
                terms = client.paginate_glossary_terms(max_results=5000)
                logger.info(f"Found {len(terms)} glossary terms")
                if terms:
                    for term in terms:
                        try:
                            term_metadata = format_asset_metadata(term)
                            term_name = term.get("attributes", {}).get("name", term.get("guid", "unknown"))
                            safe_term_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in term_name)
                            safe_term_name = safe_term_name.lstrip("._")[:100]
                            if not safe_term_name:
                                safe_term_name = f"term_{term.get('guid', 'unknown')[:20]}"

                            term_file = os.path.join(glossary_dir, f"{safe_term_name}.json")
                            with open(term_file, 'w') as f:
                                json.dump(term_metadata, f, indent=2, default=str)

                            stats["glossary_terms"] += 1
                        except Exception as e:
                            logger.warning(f"Failed to process glossary term: {e}")
                    logger.info(f"Processed {stats['glossary_terms']} glossary terms")
            except Exception as e:
                logger.warning(f"Failed to fetch glossary terms: {e}")

        # Create provider overview
        provider_overview = {
            "provider": "atlan",
            "tenant_url": atlan_config.get("tenant_url"),
            "total_assets": stats["total_assets"],
            "assets_by_type": stats["by_type"],
            "tables_with_lineage": stats["tables_with_lineage"],
            "glossary_terms": stats["glossary_terms"],
            "failed_assets": stats["failed_assets"],
            "scanned_at": datetime.datetime.now().isoformat()
        }

        with open(os.path.join(provider_dir, "provider_overview.json"), 'w') as f:
            json.dump(provider_overview, f, indent=2, default=str)

        # Create manifest
        manifest = {
            "version": "1.0",
            "provider": "atlan",
            "resources": manifest_entries
        }

        with open(os.path.join(provider_dir, "manifest.json"), 'w') as f:
            json.dump(manifest, f, indent=2, default=str)

        # Log completion
        logger.info(f"Atlan metadata generation completed:")
        logger.info(f"  - Total assets: {stats['total_assets']}")
        logger.info(f"  - Assets by type: {stats['by_type']}")
        logger.info(f"  - Tables with lineage: {stats['tables_with_lineage']}")
        logger.info(f"  - Glossary terms: {stats['glossary_terms']}")
        if stats["failed_assets"] > 0:
            logger.warning(f"  - Failed assets: {stats['failed_assets']}")

    except Exception as e:
        logger.error(f"Failed to generate Atlan overview: {e}", exc_info=True)
