"""
Credential fetcher for analytics service connections.
Fetches credentials from the backend API based on project ID.
"""

import aiohttp
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class CredentialFetcher:
    """Fetches analytics service credentials from the backend API."""

    def __init__(self, api_base_url: str):
        self.api_base_url = api_base_url.rstrip('/')

    async def get_credentials(self, project_id: str, provider_type: str) -> Optional[Dict[str, Any]]:
        """
        Fetch analytics service credentials for a project from the backend API.

        Args:
            project_id: Project identifier
            provider_type: Provider type (looker, redash, openapi, airflow, dbt, datahub, datazone, s3)

        Returns:
            Dictionary containing service credentials or None if not found
        """
        try:
            url = f"{self.api_base_url}/projects/{project_id}/data-sources"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Failed to get data sources for project {project_id}. "
                                   f"Status: {response.status}, Error: {error_text}")
                        return None

                    data = await response.json()
                    data_sources = data.get("data_sources", [])

                    # Find analytics source matching the specified provider type
                    for source in data_sources:
                        source_type = source.get("type")

                        # Only look for the specified provider type
                        if source_type != provider_type:
                            continue

                        if source_type == "looker":
                            credentials = self._extract_looker_credentials(source)
                            if credentials:
                                logger.info(f"Retrieved Looker credentials for project: {project_id}")
                                return {
                                    "type": "looker",
                                    "configuration": credentials
                                }
                        elif source_type == "redash":
                            credentials = self._extract_redash_credentials(source)
                            if credentials:
                                logger.info(f"Retrieved Redash credentials for project: {project_id}")
                                return {
                                    "type": "redash",
                                    "configuration": credentials
                                }
                        elif source_type == "openapi":
                            credentials = self._extract_openapi_credentials(source)
                            if credentials:
                                logger.info(f"Retrieved OpenAPI credentials for project: {project_id}")
                                return {
                                    "type": "openapi",
                                    "configuration": credentials
                                }
                        elif source_type == "dbt":
                            credentials = self._extract_dbt_credentials(source)
                            if credentials:
                                logger.info(f"Retrieved dbt Cloud credentials for project: {project_id}")
                                return {
                                    "type": "dbt",
                                    "configuration": credentials
                                }
                        elif source_type == "datahub":
                            credentials = self._extract_datahub_credentials(source)
                            if credentials:
                                logger.info(f"Retrieved DataHub credentials for project: {project_id}")
                                return {
                                    "type": "datahub",
                                    "configuration": credentials
                                }
                        elif source_type == "airflow":
                            credentials = self._extract_airflow_credentials(source)
                            if credentials:
                                logger.info(f"Retrieved Airflow credentials for project: {project_id}")
                                return {
                                    "type": "airflow",
                                    "configuration": credentials
                                }
                        elif source_type == "datazone":
                            credentials = self._extract_datazone_credentials(source)
                            if credentials:
                                logger.info(f"Retrieved DataZone credentials for project: {project_id}")
                                return {
                                    "type": "datazone",
                                    "configuration": credentials
                                }
                        elif source_type == "s3":
                            credentials = self._extract_s3_credentials(source)
                            if credentials:
                                logger.info(f"Retrieved S3 credentials for project: {project_id}")
                                return {
                                    "type": "s3",
                                    "configuration": credentials
                                }
                        elif source_type == "jira":
                            credentials = self._extract_jira_credentials(source)
                            if credentials:
                                logger.info(f"Retrieved Jira credentials for project: {project_id}")
                                return {
                                    "type": "jira",
                                    "configuration": credentials
                                }
                        elif source_type == "azure_blob_storage":
                            credentials = self._extract_azure_blob_storage_credentials(source)
                            if credentials:
                                logger.info(f"Retrieved Azure Blob Storage credentials for project: {project_id}")
                                return {
                                    "type": "azure_blob_storage",
                                    "configuration": credentials
                                }
                        elif source_type == "azure_data_factory":
                            credentials = self._extract_azure_data_factory_credentials(source)
                            if credentials:
                                logger.info(f"Retrieved Azure Data Factory credentials for project: {project_id}")
                                return {
                                    "type": "azure_data_factory",
                                    "configuration": credentials
                                }
                        elif source_type == "atlan":
                            credentials = self._extract_atlan_credentials(source)
                            if credentials:
                                logger.info(f"Retrieved Atlan credentials for project: {project_id}")
                                return {
                                    "type": "atlan",
                                    "configuration": credentials
                                }

                    logger.warning(f"No {provider_type} analytics source found for project: {project_id}")
                    return None

        except Exception as e:
            logger.error(f"Error fetching credentials for project {project_id}: {str(e)}")
            return None

    def _extract_looker_credentials(self, analytics_source: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract Looker credentials from analytics source configuration.

        Args:
            analytics_source: Analytics source configuration from API

        Returns:
            Dictionary with Looker connection parameters
        """
        try:
            config = analytics_source.get("configuration", {})

            # Extract required Looker fields
            base_url = config.get("base_url")
            client_id = config.get("client_id")
            client_secret = config.get("client_secret")

            # Validate required fields
            if not all([base_url, client_id, client_secret]):
                logger.error("Missing required Looker credentials: base_url, client_id, or client_secret")
                return None

            return {
                "base_url": base_url,
                "client_id": client_id,
                "client_secret": client_secret
            }

        except Exception as e:
            logger.error(f"Error extracting Looker credentials: {str(e)}")
            return None

    def _extract_redash_credentials(self, analytics_source: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract Redash credentials from analytics source configuration.

        Args:
            analytics_source: Analytics source configuration from API

        Returns:
            Dictionary with Redash connection parameters
        """
        try:
            config = analytics_source.get("configuration", {})

            # Extract required Redash fields
            base_url = config.get("base_url")
            api_key = config.get("api_key")

            # Validate required fields
            if not all([base_url, api_key]):
                logger.error("Missing required Redash credentials: base_url or api_key")
                return None

            return {
                "base_url": base_url,
                "api_key": api_key
            }

        except Exception as e:
            logger.error(f"Error extracting Redash credentials: {str(e)}")
            return None

    def _extract_openapi_credentials(self, analytics_source: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract OpenAPI credentials from analytics source configuration.

        Args:
            analytics_source: Analytics source configuration from API

        Returns:
            Dictionary with OpenAPI connection parameters
        """
        try:
            config = analytics_source.get("configuration", {})

            # Extract required OpenAPI fields
            base_url = config.get("base_url")

            # Validate required fields
            if not base_url:
                logger.error("Missing required OpenAPI credential: base_url")
                return None

            # Optional fields
            spec_url = config.get("spec_url")
            api_key = config.get("api_key")
            auth_header = config.get("auth_header", "Authorization")

            credentials = {
                "base_url": base_url,
                "auth_header": auth_header
            }

            if spec_url:
                credentials["spec_url"] = spec_url

            if api_key:
                credentials["api_key"] = api_key

            return credentials

        except Exception as e:
            logger.error(f"Error extracting OpenAPI credentials: {str(e)}")
            return None

    def _extract_dbt_credentials(self, analytics_source: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract dbt Cloud credentials from analytics source configuration.

        Args:
            analytics_source: Analytics source configuration from API

        Returns:
            Dictionary with dbt Cloud connection parameters
        """
        try:
            config = analytics_source.get("configuration", {})

            # Extract required dbt Cloud fields
            api_token = config.get("api_token")
            account_id = config.get("account_id")

            # Validate required fields
            if not all([api_token, account_id]):
                logger.error("Missing required dbt Cloud credentials: api_token or account_id")
                return None

            # Optional fields
            base_url = config.get("base_url", "https://cloud.getdbt.com")
            project_id = config.get("project_id")
            environment_id = config.get("environment_id")

            credentials = {
                "base_url": base_url,
                "api_token": api_token,
                "account_id": account_id
            }

            if project_id:
                credentials["project_id"] = project_id

            if environment_id:
                credentials["environment_id"] = environment_id

            return credentials

        except Exception as e:
            logger.error(f"Error extracting dbt Cloud credentials: {str(e)}")
            return None

    def _extract_datahub_credentials(self, analytics_source: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract Datahub credentials from analytics source configuration.

        Args:
            analytics_source: Analytics source configuration from API

        Returns:
            Dictionary with Datahub connection parameters
        """
        try:
            config = analytics_source.get("configuration", {})

            # Extract required dbt Cloud fields
            base_url = config.get("base_url")
            api_key = config.get("api_key")

            # Validate required fields
            if not all([base_url, api_key]):
                logger.error("Missing required Datahub credentials: api_token or account_id")
                return None

            credentials = {
                "base_url": base_url,
                "api_key": api_key,
            }

            return credentials

        except Exception as e:
            logger.error(f"Error extracting Datahub credentials: {str(e)}")
            return None

    def _extract_airflow_credentials(self, analytics_source: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract Airflow credentials from analytics source configuration.

        Args:
            analytics_source: Analytics source configuration from API

        Returns:
            Dictionary with Airflow connection parameters
        """
        try:
            config = analytics_source.get("configuration", {})

            # Extract required Airflow fields
            base_url = config.get("base_url")
            username = config.get("username")
            password = config.get("password")

            # Validate required fields
            if not all([base_url, username, password]):
                logger.error("Missing required Airflow credentials: base_url, username, or password")
                return None

            return {
                "base_url": base_url,
                "username": username,
                "password": password
            }

        except Exception as e:
            logger.error(f"Error extracting Airflow credentials: {str(e)}")
            return None

    def _extract_datazone_credentials(self, analytics_source: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract DataZone credentials from analytics source configuration.

        Args:
            analytics_source: Analytics source configuration from API

        Returns:
            Dictionary with DataZone connection parameters
        """
        try:
            config = analytics_source.get("configuration", {})

            # Extract required DataZone fields
            region = config.get("region")
            role_arn = config.get("role_arn")
            external_id = config.get("external_id")

            # Validate required fields
            if not all([region, role_arn, external_id]):
                logger.error("Missing required DataZone credentials: region, role_arn, or external_id")
                return None

            return {
                "region": region,
                "role_arn": role_arn,
                "external_id": external_id
            }

        except Exception as e:
            logger.error(f"Error extracting DataZone credentials: {str(e)}")
            return None

    def _extract_s3_credentials(self, analytics_source: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract S3 credentials from analytics source configuration.

        Args:
            analytics_source: Analytics source configuration from API

        Returns:
            Dictionary with S3 connection parameters
        """
        try:
            config = analytics_source.get("configuration", {})

            # Extract required S3 fields
            region = config.get("region", "us-east-1")
            role_arn = config.get("role_arn")
            external_id = config.get("external_id")

            # Validate required fields
            if not all([role_arn, external_id]):
                logger.error("Missing required S3 credentials: role_arn, or external_id")
                return None

            return {
                "region": region,
                "role_arn": role_arn,
                "external_id": external_id
            }

        except Exception as e:
            logger.error(f"Error extracting S3 credentials: {str(e)}")
            return None

    def _extract_jira_credentials(self, analytics_source: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract Jira credentials from analytics source configuration.

        Args:
            analytics_source: Analytics source configuration from API

        Returns:
            Dictionary with Jira connection parameters
        """
        try:
            config = analytics_source.get("configuration", {})

            # Extract OAuth 2.0 fields
            access_token = config.get("access_token")
            refresh_token = config.get("refresh_token")
            cloud_id = config.get("cloud_id")
            site_url = config.get("site_url")
            account_id = config.get("account_id")
            expires_in = config.get("expires_in", 3600)
            auth_method = config.get("auth_method", "oauth")

            # Extract token creation timestamp for accurate expiration tracking
            created_at = analytics_source.get("created_at")

            # Validate required fields
            if not all([access_token, cloud_id, site_url]):
                logger.error("Missing required Jira credentials: access_token, cloud_id, or site_url")
                return None

            credentials = {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "cloud_id": cloud_id,
                "site_url": site_url,
                "account_id": account_id,
                "expires_in": expires_in,
                "auth_method": auth_method,
                # Optional fields
                "email": config.get("email"),
                "display_name": config.get("display_name"),
                "avatar_url": config.get("avatar_url"),
                "scope": config.get("scope")
            }

            # Add created_at if available for accurate expiration tracking
            if created_at:
                credentials["created_at"] = created_at

            return credentials

        except Exception as e:
            logger.error(f"Error extracting Jira credentials: {str(e)}")
            return None

    def _extract_azure_blob_storage_credentials(self, analytics_source: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract Azure Blob Storage credentials from analytics source configuration.

        Args:
            analytics_source: Analytics source configuration from API

        Returns:
            Dictionary with Azure Blob Storage connection parameters
        """
        try:
            config = analytics_source.get("configuration", {})

            # Extract required Azure Blob Storage fields
            tenant_id = config.get("tenant_id")
            client_id = config.get("client_id")
            client_secret = config.get("client_secret")
            subscription_id = config.get("subscription_id")
            storage_account_name = config.get("storage_account_name")

            # Validate required fields
            if not all([tenant_id, client_id, client_secret, storage_account_name]):
                logger.error("Missing required Azure Blob Storage credentials: tenant_id, client_id, client_secret, or storage_account_name")
                return None

            return {
                "tenant_id": tenant_id,
                "client_id": client_id,
                "client_secret": client_secret,
                "subscription_id": subscription_id,
                "storage_account_name": storage_account_name
            }

        except Exception as e:
            logger.error(f"Error extracting Azure Blob Storage credentials: {str(e)}")
            return None

    def _extract_azure_data_factory_credentials(self, analytics_source: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract Azure Data Factory credentials from analytics source configuration.

        Args:
            analytics_source: Analytics source configuration from API

        Returns:
            Dictionary with Azure Data Factory connection parameters
        """
        try:
            config = analytics_source.get("configuration", {})

            # Extract required Azure Data Factory fields
            tenant_id = config.get("tenant_id")
            client_id = config.get("client_id")
            client_secret = config.get("client_secret")
            subscription_id = config.get("subscription_id")
            resource_group = config.get("resource_group")
            factory_name = config.get("factory_name")

            # Validate required fields
            if not all([tenant_id, client_id, client_secret, subscription_id, resource_group, factory_name]):
                logger.error("Missing required Azure Data Factory credentials: tenant_id, client_id, client_secret, subscription_id, resource_group, or factory_name")
                return None

            return {
                "tenant_id": tenant_id,
                "client_id": client_id,
                "client_secret": client_secret,
                "subscription_id": subscription_id,
                "resource_group": resource_group,
                "factory_name": factory_name
            }

        except Exception as e:
            logger.error(f"Error extracting Azure Data Factory credentials: {str(e)}")
            return None

    def _extract_atlan_credentials(self, analytics_source: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract Atlan credentials from analytics source configuration.

        Args:
            analytics_source: Analytics source configuration from API

        Returns:
            Dictionary with Atlan connection parameters
        """
        try:
            config = analytics_source.get("configuration", {})

            # Extract required Atlan fields
            tenant_url = config.get("tenant_url")
            api_token = config.get("api_token")

            # Validate required fields
            if not all([tenant_url, api_token]):
                logger.error("Missing required Atlan credentials: tenant_url or api_token")
                return None

            return {
                "tenant_url": tenant_url,
                "api_token": api_token
            }

        except Exception as e:
            logger.error(f"Error extracting Atlan credentials: {str(e)}")
            return None

    async def get_all_data_sources(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Get all data sources for a project.

        Args:
            project_id: Project identifier

        Returns:
            List of data source configurations
        """
        try:
            url = f"{self.api_base_url}/projects/{project_id}/data-sources"
            logger.info(f"Fetching data sources from: {url}")

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Failed to get data sources for project {project_id}. "
                                   f"Status: {response.status}, Error: {error_text}")
                        return []

                    data = await response.json()
                    data_sources = data.get("data_sources", [])
                    logger.info(f"Retrieved {len(data_sources)} data sources for project {project_id}")
                    logger.debug(f"Data source types: {[ds.get('type') for ds in data_sources]}")
                    return data_sources

        except Exception as e:
            logger.error(f"Error fetching data sources for project {project_id}: {str(e)}", exc_info=True)
            return []
