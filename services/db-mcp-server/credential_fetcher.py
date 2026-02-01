"""
Credential fetcher for database connections.
Fetches credentials from the backend API based on project ID.
"""

import aiohttp
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class CredentialFetcher:
    """Fetches database credentials from the backend API."""
    
    def __init__(self, api_base_url: str):
        self.api_base_url = api_base_url.rstrip('/')
    
    async def get_credentials(self, project_id: str, provider_type: str) -> Optional[Dict[str, Any]]:
        """
        Fetch database credentials for a project from the backend API.
        
        Args:
            project_id: Project identifier
            provider_type: Provider type (databricks, snowflake)
            
        Returns:
            Dictionary containing database credentials or None if not found
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
                    
                    # Find data source matching the specified provider type
                    for ds in data_sources:
                        ds_type = ds.get("type")
                        
                        # Only look for the specified provider type
                        if ds_type != provider_type:
                            continue
                        
                        if ds_type == "databricks":
                            credentials = self._extract_databricks_credentials(ds)
                            if credentials:
                                logger.info(f"Retrieved Databricks credentials for project: {project_id}")
                                return {
                                    "type": "databricks",
                                    "configuration": credentials
                                }
                        elif ds_type == "snowflake":
                            credentials = self._extract_snowflake_credentials(ds)
                            if credentials:
                                logger.info(f"Retrieved Snowflake credentials for project: {project_id}")
                                return {
                                    "type": "snowflake", 
                                    "configuration": credentials
                                }
                        elif ds_type == "bigquery":
                            credentials = self._extract_bigquery_credentials(ds)
                            if credentials:
                                logger.info(f"Retrieved BigQuery credentials for project: {project_id}")
                                return {
                                    "type": "bigquery",
                                    "configuration": credentials
                                }
                        elif ds_type == "redshift":
                            credentials = self._extract_redshift_credentials(ds)
                            if credentials:
                                logger.info(f"Retrieved Redshift credentials for project: {project_id}")
                                return {
                                    "type": "redshift",
                                    "configuration": credentials
                                }
                        elif ds_type == "glue":
                            credentials = self._extract_glue_credentials(ds)
                            if credentials:
                                logger.info(f"Retrieved Glue credentials for project: {project_id}")
                                return {
                                    "type": "glue",
                                    "configuration": credentials
                                }

                    logger.warning(f"No {provider_type} data source found for project: {project_id}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching credentials for project {project_id}: {str(e)}")
            return None
    
    def _extract_databricks_credentials(self, data_source: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract Databricks credentials from data source configuration.
        
        Args:
            data_source: Data source configuration from API
            
        Returns:
            Dictionary with Databricks connection parameters
        """
        try:
            config = data_source.get("configuration", {})
            
            # Extract required Databricks fields
            host = config.get("host")
            http_path = config.get("http_path")
            access_token = config.get("access_token")
            
            # Validate required fields
            if not all([host, http_path, access_token]):
                logger.error("Missing required Databricks credentials: host, http_path, or access_token")
                return None
            
            # Clean up host (remove https:// if present)
            if host.startswith("https://"):
                host = host[8:]
            elif host.startswith("http://"):
                host = host[7:]
            
            return {
                "provider": "databricks",
                "host": host,
                "http_path": http_path,
                "access_token": access_token
            }
            
        except Exception as e:
            logger.error(f"Error extracting Databricks credentials: {str(e)}")
            return None
    
    def _extract_snowflake_credentials(self, data_source: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract Snowflake credentials from data source configuration.
        Supports both password-based and private key-based authentication.

        Args:
            data_source: Data source configuration from API

        Returns:
            Dictionary with Snowflake connection parameters
        """
        try:
            config = data_source.get("configuration", {})

            # Extract required Snowflake fields
            account = config.get("account")
            username = config.get("username")
            password = config.get("password")
            warehouse = config.get("warehouse")
            database = config.get("database")
            schema = config.get("schema")

            # Extract private key authentication fields (following OpenMetadata standards)
            private_key = config.get("privateKey") or config.get("private_key")

            # Normalize private key if present - ensure proper newlines
            if private_key and isinstance(private_key, str):
                private_key = private_key.replace("\\n", "\n")

            passphrase = config.get("passphrase")
            role = config.get("role")

            # Validate required fields: account, username, and warehouse are always required
            # Either password OR private_key must be provided
            if not all([account, username, warehouse]):
                logger.error("Missing required Snowflake credentials: account, username, or warehouse")
                return None

            # Ensure at least one authentication method is provided
            if not password and not private_key:
                logger.error("Either password or private_key must be provided for Snowflake authentication")
                return None

            result = {
                "account": account,
                "username": username,
                "warehouse": warehouse,
                "database": database,
                "schema": schema
            }

            # Add authentication credentials
            if private_key:
                result["private_key"] = private_key
                if passphrase:
                    result["passphrase"] = passphrase
            if password:
                result["password"] = password
            if role:
                result["role"] = role

            return result

        except Exception as e:
            logger.error(f"Error extracting Snowflake credentials: {str(e)}")
            return None
    
    def _extract_bigquery_credentials(self, data_source: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract BigQuery credentials from data source configuration.
        
        Args:
            data_source: Data source configuration from API
            
        Returns:
            Dictionary with BigQuery service account credentials
        """
        try:
            config = data_source.get("configuration", {})
            
            # BigQuery credentials can be stored in different formats:
            # 1. Direct service account JSON object
            # 2. Service account info as a nested object
            # 3. Service account JSON as a string
            
            service_account_info = None
            
            # Check if config itself is a service account JSON
            if config.get("type") == "service_account" and config.get("project_id"):
                service_account_info = config
            # Check for nested service_account_info
            elif "service_account_info" in config:
                service_account_info = config["service_account_info"]
                # If it's a string, parse it as JSON
                if isinstance(service_account_info, str):
                    import json
                    service_account_info = json.loads(service_account_info)
            # Check for individual service account fields
            elif all(key in config for key in ["project_id", "private_key", "client_email"]):
                config["private_key"] = config["private_key"].replace("\\n", "\n")
                service_account_info = {
                    "type": "service_account",
                    "project_id": config["project_id"],
                    "private_key_id": config.get("private_key_id", ""),
                    "private_key": config["private_key"],
                    "client_email": config["client_email"],
                    "client_id": config.get("client_id", ""),
                    "auth_uri": config.get("auth_uri", "https://accounts.google.com/o/oauth2/auth"),
                    "token_uri": config.get("token_uri", "https://oauth2.googleapis.com/token"),
                    "auth_provider_x509_cert_url": config.get("auth_provider_x509_cert_url", "https://www.googleapis.com/oauth2/v1/certs"),
                    "client_x509_cert_url": config.get("client_x509_cert_url", ""),
                    "universe_domain": config.get("universe_domain", "googleapis.com")
                }
            
            if not service_account_info:
                logger.error("Missing required BigQuery service account credentials")
                return None
            
            # Validate required service account fields
            required_fields = ["type", "project_id", "private_key", "client_email"]
            if not all(field in service_account_info for field in required_fields):
                logger.error(f"Missing required BigQuery service account fields: {required_fields}")
                return None
            
            # Return the service account info directly - the BigQuery provider expects this format
            result = service_account_info.copy()
            
            # Add optional dataset if specified in config
            if "dataset" in config:
                result["dataset"] = config["dataset"]
            
            return result
            
        except Exception as e:
            logger.error(f"Error extracting BigQuery credentials: {str(e)}")
            return None
    
    def _extract_redshift_credentials(self, data_source: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract Redshift credentials from data source configuration.
        
        Args:
            data_source: Data source configuration from API
            
        Returns:
            Dictionary with Redshift connection parameters
        """
        try:
            config = data_source.get("configuration", {})
            
            # Extract required Redshift fields
            host = config.get("host")
            port = config.get("port", 5439)  # Default Redshift port
            database = config.get("database")
            user = config.get("user")
            password = config.get("password")
            
            # Validate required fields
            if not all([host, user, password]):
                logger.error("Missing required Redshift credentials: host, user, or password")
                return None
            
            # Clean up host (remove protocol if present)
            if host.startswith("redshift://"):
                host = host[11:]
            elif host.startswith("postgresql://"):
                host = host[13:]
            elif host.startswith("postgres://"):
                host = host[11:]
            
            return {
                "host": host,
                "port": int(port),
                "database": database,
                "user": user,
                "password": password
            }
            
        except Exception as e:
            logger.error(f"Error extracting Redshift credentials: {str(e)}")
            return None

    def _extract_glue_credentials(self, data_source: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract AWS Glue credentials from data source configuration.

        The IAM role specified by role_arn must have the following permissions:

        AWS Glue Data Catalog Read Permissions:
        - glue:GetDatabases
        - glue:GetDatabase
        - glue:GetTables
        - glue:GetTable
        - glue:GetPartitions
        - glue:GetPartition
        - glue:GetColumnStatisticsForTable
        - glue:GetColumnStatisticsForPartition

        AWS Glue Data Quality Permissions:
        - glue:GetDataQualityRuleset
        - glue:ListDataQualityRulesets
        - glue:CreateDataQualityRuleset
        - glue:UpdateDataQualityRuleset
        - glue:DeleteDataQualityRuleset
        - glue:StartDataQualityRuleRecommendationRun
        - glue:GetDataQualityRuleRecommendationRun
        - glue:StartDataQualityRulesetEvaluationRun
        - glue:GetDataQualityRulesetEvaluationRun
        - glue:ListDataQualityResults

        AWS Glue Column Statistics Permissions:
        - glue:UpdateColumnStatisticsForTable
        - glue:UpdateColumnStatisticsForPartition
        - glue:DeleteColumnStatisticsForTable
        - glue:DeleteColumnStatisticsForPartition

        AWS Athena Workgroup Permissions:
        - athena:CreateWorkGroup
        - athena:ListWorkGroups
        - athena:GetWorkGroup
        - athena:UpdateWorkGroup
        - athena:DeleteWorkGroup

        AWS Athena Data Catalog Permissions:
        - athena:GetDataCatalog
        - athena:ListDataCatalogs
        - athena:UpdateDataCatalog

        AWS Athena Query Execution Permissions:
        - athena:StartQueryExecution
        - athena:GetQueryExecution
        - athena:StopQueryExecution
        - athena:GetQueryResults
        - athena:ListQueryExecutions
        - athena:BatchGetQueryExecution

        AWS S3 Permissions (for Athena query results):
        - s3:GetBucketLocation
        - s3:GetObject
        - s3:ListBucket
        - s3:PutObject
        - s3:DeleteObject (for managing query results)

        Additional IAM Permissions:
        - iam:PassRole (required when using Data Quality runs or Athena workgroups with IAM roles)

        Args:
            data_source: Data source configuration from API

        Returns:
            Dictionary with AWS Glue connection parameters
        """
        try:
            config = data_source.get("configuration", {})

            # Extract required AWS Glue fields for role assumption
            role_arn = config.get("role_arn")
            region = config.get("region", "us-east-1")

            # Extract optional external_id for secure role assumption
            external_id = config.get("external_id")

            # Validate required fields
            if not role_arn:
                logger.error("Missing required Glue credentials: role_arn")
                return None

            result = {
                "role_arn": role_arn,
                "region": region
            }

            # Add optional external_id if present
            if external_id:
                result["external_id"] = external_id

            return result

        except Exception as e:
            logger.error(f"Error extracting Glue credentials: {str(e)}")
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
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Failed to get data sources for project {project_id}. "
                                   f"Status: {response.status}, Error: {error_text}")
                        return []
                    
                    data = await response.json()
                    return data.get("data_sources", [])
                    
        except Exception as e:
            logger.error(f"Error fetching data sources for project {project_id}: {str(e)}")
            return []
