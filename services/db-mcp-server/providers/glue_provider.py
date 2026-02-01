"""
AWS Glue Data Catalog provider implementation using boto3.
"""

import logging
import boto3
from typing import Dict, Any, Optional, List
from botocore.exceptions import ClientError, BotoCoreError

from .base_provider import DatabaseProvider

logger = logging.getLogger(__name__)


class GlueProvider(DatabaseProvider):
    """AWS Glue Data Catalog provider using boto3."""

    def __init__(self):
        super().__init__()
        self.glue_client = None
        self.athena_client = None
        self.region: Optional[str] = None
        self.role_arn: Optional[str] = None
        self.external_id: Optional[str] = None

    async def initialize(self, credentials: Dict[str, Any]) -> None:
        """Initialize AWS Glue client by assuming role in customer account."""
        try:
            self.credentials = credentials

            # Extract connection parameters
            self.region = credentials.get("region", "us-east-1")
            self.role_arn = credentials.get("role_arn")
            self.external_id = credentials.get("external_id")

            # Validate required fields
            if not self.role_arn:
                raise ValueError("Missing required Glue credentials: role_arn")

            # Create Glue client by assuming role in customer account
            self.glue_client = self._get_glue_client_for_customer(
                role_arn=self.role_arn,
                external_id=self.external_id,
                region=self.region
            )

            # Create Athena client by assuming the same role
            self.athena_client = self._get_athena_client_for_customer(
                role_arn=self.role_arn,
                external_id=self.external_id,
                region=self.region
            )

            self._initialized = True
            logger.info(f"Glue provider initialized successfully for role {self.role_arn} in region {self.region}")

        except Exception as e:
            logger.error(f"Failed to initialize Glue provider: {e}")
            self._initialized = False
            raise

    def _get_glue_client_for_customer(
        self,
        role_arn: str,
        external_id: Optional[str] = None,
        region: str = "us-east-1"
    ):
        """
        Get Glue client by assuming a role in the customer's AWS account.

        Args:
            role_arn: Full ARN of the IAM role to assume (e.g., arn:aws:iam::123456789012:role/role-name)
            external_id: External ID for role assumption (optional)
            region: AWS region (default: us-east-1)

        Returns:
            boto3 Glue client
        """
        sts_client = boto3.client("sts")

        assume_role_kwargs = {
            "RoleArn": role_arn,
            "RoleSessionName": "chicory-mcp-session"
        }

        if external_id:
            assume_role_kwargs["ExternalId"] = external_id

        resp = sts_client.assume_role(**assume_role_kwargs)
        creds = resp["Credentials"]

        glue_client = boto3.client(
            "glue",
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
            region_name=region
        )

        logger.info(f"Successfully assumed role {role_arn} for Glue access")
        return glue_client

    def _get_athena_client_for_customer(
        self,
        role_arn: str,
        external_id: Optional[str] = None,
        region: str = "us-east-1"
    ):
        """
        Get Athena client by assuming a role in the customer's AWS account.

        Args:
            role_arn: Full ARN of the IAM role to assume (e.g., arn:aws:iam::123456789012:role/role-name)
            external_id: External ID for role assumption (optional)
            region: AWS region (default: us-east-1)

        Returns:
            boto3 Athena client
        """
        sts_client = boto3.client("sts")

        assume_role_kwargs = {
            "RoleArn": role_arn,
            "RoleSessionName": "chicory-mcp-athena-session"
        }

        if external_id:
            assume_role_kwargs["ExternalId"] = external_id

        resp = sts_client.assume_role(**assume_role_kwargs)
        creds = resp["Credentials"]

        athena_client = boto3.client(
            "athena",
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
            region_name=region
        )

        logger.info(f"Successfully assumed role {role_arn} for Athena access")
        return athena_client

    async def test_connection(self) -> bool:
        """Test the Glue connection by listing databases."""
        try:
            if not self.glue_client:
                return False

            # Simple test - list databases with limit of 1
            self.glue_client.get_databases(MaxResults=1)

            logger.info("Glue connection test successful")
            return True

        except Exception as e:
            logger.error(f"Glue connection test failed: {e}")
            return False

    async def cleanup(self) -> None:
        """Clean up Glue resources."""
        try:
            if self.glue_client:
                self.glue_client = None
            if self.athena_client:
                self.athena_client = None

            await super().cleanup()
            logger.info("Glue provider cleanup completed")

        except Exception as e:
            logger.error(f"Error during Glue provider cleanup: {e}")

    async def list_databases(self) -> Dict[str, Any]:
        """
        List all databases in the Glue Data Catalog.

        Returns:
            Dictionary with list of databases and metadata
        """
        try:
            if not self.glue_client:
                raise RuntimeError("Glue client not initialized")

            databases = []
            paginator = self.glue_client.get_paginator('get_databases')

            for page in paginator.paginate():
                for db in page.get('DatabaseList', []):
                    databases.append({
                        "name": db.get('Name'),
                        "description": db.get('Description', ''),
                        "location_uri": db.get('LocationUri', ''),
                        "create_time": db.get('CreateTime').isoformat() if db.get('CreateTime') else None,
                        "parameters": db.get('Parameters', {})
                    })

            return {
                "databases": databases,
                "count": len(databases)
            }

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error listing Glue databases: {e}")
            return {"error": str(e)}

    async def list_tables(self, database_name: str) -> Dict[str, Any]:
        """
        List tables in a Glue database.

        Args:
            database_name: Database name in Glue Data Catalog

        Returns:
            Dictionary with list of tables and metadata
        """
        try:
            if not self.glue_client:
                raise RuntimeError("Glue client not initialized")

            tables = []
            paginator = self.glue_client.get_paginator('get_tables')

            for page in paginator.paginate(DatabaseName=database_name):
                for table in page.get('TableList', []):
                    tables.append({
                        "name": table.get('Name'),
                        "database": table.get('DatabaseName'),
                        "create_time": table.get('CreateTime').isoformat() if table.get('CreateTime') else None,
                        "update_time": table.get('UpdateTime').isoformat() if table.get('UpdateTime') else None,
                        "last_access_time": table.get('LastAccessTime').isoformat() if table.get('LastAccessTime') else None,
                        "retention": table.get('Retention', 0),
                        "storage_descriptor": {
                            "location": table.get('StorageDescriptor', {}).get('Location', ''),
                            "input_format": table.get('StorageDescriptor', {}).get('InputFormat', ''),
                            "output_format": table.get('StorageDescriptor', {}).get('OutputFormat', ''),
                            "num_buckets": table.get('StorageDescriptor', {}).get('NumberOfBuckets', 0)
                        },
                        "partition_keys": [
                            {
                                "name": pk.get('Name'),
                                "type": pk.get('Type'),
                                "comment": pk.get('Comment', '')
                            }
                            for pk in table.get('PartitionKeys', [])
                        ],
                        "table_type": table.get('TableType', ''),
                        "parameters": table.get('Parameters', {})
                    })

            return {
                "tables": tables,
                "database": database_name,
                "count": len(tables)
            }

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error listing Glue tables in database {database_name}: {e}")
            return {"error": str(e)}

    async def describe_table(self, database_name: str, table_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a Glue table including schema.

        Args:
            database_name: Database name in Glue Data Catalog
            table_name: Table name to describe

        Returns:
            Dictionary with table metadata and schema information
        """
        try:
            if not self.glue_client:
                raise RuntimeError("Glue client not initialized")

            response = self.glue_client.get_table(
                DatabaseName=database_name,
                Name=table_name
            )

            table = response.get('Table', {})
            storage_descriptor = table.get('StorageDescriptor', {})

            # Extract column information
            columns = []
            for col in storage_descriptor.get('Columns', []):
                columns.append({
                    "name": col.get('Name'),
                    "type": col.get('Type'),
                    "comment": col.get('Comment', ''),
                    "parameters": col.get('Parameters', {})
                })

            # Extract partition keys
            partition_keys = []
            for pk in table.get('PartitionKeys', []):
                partition_keys.append({
                    "name": pk.get('Name'),
                    "type": pk.get('Type'),
                    "comment": pk.get('Comment', '')
                })

            return {
                "table_name": table.get('Name'),
                "database": table.get('DatabaseName'),
                "description": table.get('Description', ''),
                "owner": table.get('Owner', ''),
                "create_time": table.get('CreateTime').isoformat() if table.get('CreateTime') else None,
                "update_time": table.get('UpdateTime').isoformat() if table.get('UpdateTime') else None,
                "last_access_time": table.get('LastAccessTime').isoformat() if table.get('LastAccessTime') else None,
                "retention": table.get('Retention', 0),
                "storage_descriptor": {
                    "location": storage_descriptor.get('Location', ''),
                    "input_format": storage_descriptor.get('InputFormat', ''),
                    "output_format": storage_descriptor.get('OutputFormat', ''),
                    "compressed": storage_descriptor.get('Compressed', False),
                    "num_buckets": storage_descriptor.get('NumberOfBuckets', 0),
                    "serde_info": {
                        "name": storage_descriptor.get('SerdeInfo', {}).get('Name', ''),
                        "serialization_library": storage_descriptor.get('SerdeInfo', {}).get('SerializationLibrary', ''),
                        "parameters": storage_descriptor.get('SerdeInfo', {}).get('Parameters', {})
                    },
                    "bucket_columns": storage_descriptor.get('BucketColumns', []),
                    "sort_columns": [
                        {
                            "column": sc.get('Column'),
                            "sort_order": sc.get('SortOrder')
                        }
                        for sc in storage_descriptor.get('SortColumns', [])
                    ],
                    "parameters": storage_descriptor.get('Parameters', {}),
                    "stored_as_sub_directories": storage_descriptor.get('StoredAsSubDirectories', False)
                },
                "partition_keys": partition_keys,
                "table_type": table.get('TableType', ''),
                "parameters": table.get('Parameters', {}),
                "columns": columns,
                "column_count": len(columns)
            }

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error describing Glue table {database_name}.{table_name}: {e}")
            return {"error": str(e)}

    async def get_partitions(self, database_name: str, table_name: str, max_results: int = 100) -> Dict[str, Any]:
        """
        Get partitions for a Glue table.

        Args:
            database_name: Database name in Glue Data Catalog
            table_name: Table name
            max_results: Maximum number of partitions to return

        Returns:
            Dictionary with partition information
        """
        try:
            if not self.glue_client:
                raise RuntimeError("Glue client not initialized")

            partitions = []
            paginator = self.glue_client.get_paginator('get_partitions')

            page_count = 0
            for page in paginator.paginate(
                DatabaseName=database_name,
                TableName=table_name,
                PaginationConfig={'MaxItems': max_results}
            ):
                for partition in page.get('Partitions', []):
                    storage_descriptor = partition.get('StorageDescriptor', {})

                    partitions.append({
                        "values": partition.get('Values', []),
                        "database": partition.get('DatabaseName'),
                        "table": partition.get('TableName'),
                        "create_time": partition.get('CreationTime').isoformat() if partition.get('CreationTime') else None,
                        "last_access_time": partition.get('LastAccessTime').isoformat() if partition.get('LastAccessTime') else None,
                        "storage_descriptor": {
                            "location": storage_descriptor.get('Location', ''),
                            "input_format": storage_descriptor.get('InputFormat', ''),
                            "output_format": storage_descriptor.get('OutputFormat', ''),
                            "num_buckets": storage_descriptor.get('NumberOfBuckets', 0)
                        },
                        "parameters": partition.get('Parameters', {})
                    })

                page_count += 1
                if len(partitions) >= max_results:
                    break

            return {
                "partitions": partitions,
                "database": database_name,
                "table": table_name,
                "count": len(partitions)
            }

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error getting partitions for {database_name}.{table_name}: {e}")
            return {"error": str(e)}

    # Data Quality Ruleset Operations
    async def create_data_quality_ruleset(
        self,
        name: str,
        ruleset: str,
        database_name: str,
        table_name: str,
        description: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Create a data quality ruleset for a Glue table.

        Args:
            name: Name of the data quality ruleset
            ruleset: The data quality rules (DQDL format)
            database_name: Target database name
            table_name: Target table name
            description: Optional description
            tags: Optional tags for the ruleset

        Returns:
            Dictionary with ruleset creation result
        """
        try:
            if not self.glue_client:
                raise RuntimeError("Glue client not initialized")

            params = {
                "Name": name,
                "Ruleset": ruleset,
                "TargetTable": {
                    "DatabaseName": database_name,
                    "TableName": table_name
                }
            }

            if description:
                params["Description"] = description
            if tags:
                params["Tags"] = tags

            response = self.glue_client.create_data_quality_ruleset(**params)

            return {
                "name": response.get("Name"),
                "status": "created"
            }

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error creating data quality ruleset {name}: {e}")
            return {"error": str(e)}

    async def get_data_quality_ruleset(self, name: str) -> Dict[str, Any]:
        """
        Get a data quality ruleset by name.

        Args:
            name: Name of the data quality ruleset

        Returns:
            Dictionary with ruleset details
        """
        try:
            if not self.glue_client:
                raise RuntimeError("Glue client not initialized")

            response = self.glue_client.get_data_quality_ruleset(Name=name)

            ruleset = {
                "name": response.get("Name"),
                "description": response.get("Description", ""),
                "ruleset": response.get("Ruleset"),
                "target_table": response.get("TargetTable", {}),
                "created_on": response.get("CreatedOn").isoformat() if response.get("CreatedOn") else None,
                "last_modified_on": response.get("LastModifiedOn").isoformat() if response.get("LastModifiedOn") else None
            }

            return ruleset

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error getting data quality ruleset {name}: {e}")
            return {"error": str(e)}

    async def update_data_quality_ruleset(
        self,
        name: str,
        ruleset: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update a data quality ruleset.

        Args:
            name: Name of the data quality ruleset
            ruleset: Updated data quality rules (DQDL format)
            description: Updated description

        Returns:
            Dictionary with update result
        """
        try:
            if not self.glue_client:
                raise RuntimeError("Glue client not initialized")

            params = {"Name": name}

            if ruleset:
                params["Ruleset"] = ruleset
            if description:
                params["Description"] = description

            response = self.glue_client.update_data_quality_ruleset(**params)

            return {
                "name": response.get("Name"),
                "status": "updated"
            }

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error updating data quality ruleset {name}: {e}")
            return {"error": str(e)}

    async def delete_data_quality_ruleset(self, name: str) -> Dict[str, Any]:
        """
        Delete a data quality ruleset.

        Args:
            name: Name of the data quality ruleset

        Returns:
            Dictionary with deletion result
        """
        try:
            if not self.glue_client:
                raise RuntimeError("Glue client not initialized")

            self.glue_client.delete_data_quality_ruleset(Name=name)

            return {
                "name": name,
                "status": "deleted"
            }

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error deleting data quality ruleset {name}: {e}")
            return {"error": str(e)}

    async def list_data_quality_rulesets(
        self,
        database_name: Optional[str] = None,
        table_name: Optional[str] = None,
        max_results: int = 100
    ) -> Dict[str, Any]:
        """
        List data quality rulesets, optionally filtered by target table.

        Args:
            database_name: Optional filter by database name
            table_name: Optional filter by table name
            max_results: Maximum number of rulesets to return

        Returns:
            Dictionary with list of rulesets
        """
        try:
            if not self.glue_client:
                raise RuntimeError("Glue client not initialized")

            params = {"MaxResults": max_results}

            if database_name and table_name:
                params["Filter"] = {
                    "TargetTable": {
                        "DatabaseName": database_name,
                        "TableName": table_name
                    }
                }

            rulesets = []
            paginator = self.glue_client.get_paginator('list_data_quality_rulesets')

            for page in paginator.paginate(**params):
                for ruleset in page.get('Rulesets', []):
                    rulesets.append({
                        "name": ruleset.get("Name"),
                        "description": ruleset.get("Description", ""),
                        "target_table": ruleset.get("TargetTable", {}),
                        "created_on": ruleset.get("CreatedOn").isoformat() if ruleset.get("CreatedOn") else None,
                        "last_modified_on": ruleset.get("LastModifiedOn").isoformat() if ruleset.get("LastModifiedOn") else None
                    })

            return {
                "rulesets": rulesets,
                "count": len(rulesets)
            }

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error listing data quality rulesets: {e}")
            return {"error": str(e)}

    async def start_data_quality_rule_recommendation_run(
        self,
        database_name: str,
        table_name: str,
        role: str,
        number_of_workers: int = 5
    ) -> Dict[str, Any]:
        """
        Start a data quality rule recommendation run.

        Args:
            database_name: Database name
            table_name: Table name
            role: IAM role for the recommendation run
            number_of_workers: Number of workers (default: 5)

        Returns:
            Dictionary with run ID
        """
        try:
            if not self.glue_client:
                raise RuntimeError("Glue client not initialized")

            response = self.glue_client.start_data_quality_rule_recommendation_run(
                DataSource={
                    "GlueTable": {
                        "DatabaseName": database_name,
                        "TableName": table_name
                    }
                },
                Role=role,
                NumberOfWorkers=number_of_workers
            )

            return {
                "run_id": response.get("RunId"),
                "status": "started"
            }

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error starting data quality rule recommendation run: {e}")
            return {"error": str(e)}

    async def get_data_quality_rule_recommendation_run(self, run_id: str) -> Dict[str, Any]:
        """
        Get the status of a data quality rule recommendation run.

        Args:
            run_id: Run ID from start_data_quality_rule_recommendation_run

        Returns:
            Dictionary with run status and recommended rules
        """
        try:
            if not self.glue_client:
                raise RuntimeError("Glue client not initialized")

            response = self.glue_client.get_data_quality_rule_recommendation_run(RunId=run_id)

            return {
                "run_id": response.get("RunId"),
                "status": response.get("Status"),
                "started_on": response.get("StartedOn").isoformat() if response.get("StartedOn") else None,
                "completed_on": response.get("CompletedOn").isoformat() if response.get("CompletedOn") else None,
                "execution_time": response.get("ExecutionTime"),
                "recommended_ruleset": response.get("RecommendedRuleset", ""),
                "number_of_workers": response.get("NumberOfWorkers")
            }

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error getting data quality rule recommendation run {run_id}: {e}")
            return {"error": str(e)}

    async def start_data_quality_ruleset_evaluation_run(
        self,
        database_name: str,
        table_name: str,
        ruleset_names: List[str],
        role: str,
        number_of_workers: int = 5,
        additional_run_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Start a data quality ruleset evaluation run.

        Args:
            database_name: Database name
            table_name: Table name
            ruleset_names: List of ruleset names to evaluate
            role: IAM role for the evaluation run
            number_of_workers: Number of workers (default: 5)
            additional_run_options: Additional options for the run

        Returns:
            Dictionary with run ID
        """
        try:
            if not self.glue_client:
                raise RuntimeError("Glue client not initialized")

            params = {
                "DataSource": {
                    "GlueTable": {
                        "DatabaseName": database_name,
                        "TableName": table_name
                    }
                },
                "Role": role,
                "RulesetNames": ruleset_names,
                "NumberOfWorkers": number_of_workers
            }

            if additional_run_options:
                params["AdditionalRunOptions"] = additional_run_options

            response = self.glue_client.start_data_quality_ruleset_evaluation_run(**params)

            return {
                "run_id": response.get("RunId"),
                "status": "started"
            }

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error starting data quality ruleset evaluation run: {e}")
            return {"error": str(e)}

    async def get_data_quality_ruleset_evaluation_run(self, run_id: str) -> Dict[str, Any]:
        """
        Get the status of a data quality ruleset evaluation run.

        Args:
            run_id: Run ID from start_data_quality_ruleset_evaluation_run

        Returns:
            Dictionary with run status and results
        """
        try:
            if not self.glue_client:
                raise RuntimeError("Glue client not initialized")

            response = self.glue_client.get_data_quality_ruleset_evaluation_run(RunId=run_id)

            return {
                "run_id": response.get("RunId"),
                "status": response.get("Status"),
                "started_on": response.get("StartedOn").isoformat() if response.get("StartedOn") else None,
                "completed_on": response.get("CompletedOn").isoformat() if response.get("CompletedOn") else None,
                "execution_time": response.get("ExecutionTime"),
                "ruleset_names": response.get("RulesetNames", []),
                "result_ids": response.get("ResultIds", []),
                "number_of_workers": response.get("NumberOfWorkers")
            }

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error getting data quality ruleset evaluation run {run_id}: {e}")
            return {"error": str(e)}

    async def list_data_quality_results(
        self,
        database_name: Optional[str] = None,
        table_name: Optional[str] = None,
        max_results: int = 100
    ) -> Dict[str, Any]:
        """
        List data quality results, optionally filtered by table.

        Args:
            database_name: Optional filter by database name
            table_name: Optional filter by table name
            max_results: Maximum number of results to return

        Returns:
            Dictionary with list of data quality results
        """
        try:
            if not self.glue_client:
                raise RuntimeError("Glue client not initialized")

            params = {"MaxResults": max_results}

            if database_name and table_name:
                params["Filter"] = {
                    "DataSource": {
                        "GlueTable": {
                            "DatabaseName": database_name,
                            "TableName": table_name
                        }
                    }
                }

            results = []
            paginator = self.glue_client.get_paginator('list_data_quality_results')

            for page in paginator.paginate(**params):
                for result in page.get('Results', []):
                    results.append({
                        "result_id": result.get("ResultId"),
                        "score": result.get("Score"),
                        "started_on": result.get("StartedOn").isoformat() if result.get("StartedOn") else None,
                        "completed_on": result.get("CompletedOn").isoformat() if result.get("CompletedOn") else None,
                        "job_name": result.get("JobName", ""),
                        "ruleset_name": result.get("RulesetName", "")
                    })

            return {
                "results": results,
                "count": len(results)
            }

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error listing data quality results: {e}")
            return {"error": str(e)}

    # Column Statistics Operations
    async def get_column_statistics_for_table(
        self,
        database_name: str,
        table_name: str,
        column_names: List[str]
    ) -> Dict[str, Any]:
        """
        Get column statistics for specified columns in a table.

        Args:
            database_name: Database name
            table_name: Table name
            column_names: List of column names to get statistics for

        Returns:
            Dictionary with column statistics
        """
        try:
            if not self.glue_client:
                raise RuntimeError("Glue client not initialized")

            response = self.glue_client.get_column_statistics_for_table(
                DatabaseName=database_name,
                TableName=table_name,
                ColumnNames=column_names
            )

            column_statistics = []
            for stat in response.get('ColumnStatisticsList', []):
                column_statistics.append({
                    "column_name": stat.get("ColumnName"),
                    "column_type": stat.get("ColumnType"),
                    "analyzed_time": stat.get("AnalyzedTime").isoformat() if stat.get("AnalyzedTime") else None,
                    "statistics_data": stat.get("StatisticsData", {})
                })

            return {
                "database": database_name,
                "table": table_name,
                "column_statistics": column_statistics,
                "count": len(column_statistics),
                "errors": response.get('Errors', [])
            }

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error getting column statistics for {database_name}.{table_name}: {e}")
            return {"error": str(e)}

    async def get_column_statistics_for_partition(
        self,
        database_name: str,
        table_name: str,
        partition_values: List[str],
        column_names: List[str]
    ) -> Dict[str, Any]:
        """
        Get column statistics for specified columns in a partition.

        Args:
            database_name: Database name
            table_name: Table name
            partition_values: List of partition values identifying the partition
            column_names: List of column names to get statistics for

        Returns:
            Dictionary with column statistics for the partition
        """
        try:
            if not self.glue_client:
                raise RuntimeError("Glue client not initialized")

            response = self.glue_client.get_column_statistics_for_partition(
                DatabaseName=database_name,
                TableName=table_name,
                PartitionValues=partition_values,
                ColumnNames=column_names
            )

            column_statistics = []
            for stat in response.get('ColumnStatisticsList', []):
                column_statistics.append({
                    "column_name": stat.get("ColumnName"),
                    "column_type": stat.get("ColumnType"),
                    "analyzed_time": stat.get("AnalyzedTime").isoformat() if stat.get("AnalyzedTime") else None,
                    "statistics_data": stat.get("StatisticsData", {})
                })

            return {
                "database": database_name,
                "table": table_name,
                "partition_values": partition_values,
                "column_statistics": column_statistics,
                "count": len(column_statistics),
                "errors": response.get('Errors', [])
            }

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error getting column statistics for partition in {database_name}.{table_name}: {e}")
            return {"error": str(e)}

    async def update_column_statistics_for_table(
        self,
        database_name: str,
        table_name: str,
        column_statistics_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Update column statistics for a table.

        Args:
            database_name: Database name
            table_name: Table name
            column_statistics_list: List of column statistics to update

        Returns:
            Dictionary with update result
        """
        try:
            if not self.glue_client:
                raise RuntimeError("Glue client not initialized")

            response = self.glue_client.update_column_statistics_for_table(
                DatabaseName=database_name,
                TableName=table_name,
                ColumnStatisticsList=column_statistics_list
            )

            return {
                "database": database_name,
                "table": table_name,
                "status": "updated",
                "errors": response.get('Errors', [])
            }

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error updating column statistics for {database_name}.{table_name}: {e}")
            return {"error": str(e)}

    async def update_column_statistics_for_partition(
        self,
        database_name: str,
        table_name: str,
        partition_values: List[str],
        column_statistics_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Update column statistics for a partition.

        Args:
            database_name: Database name
            table_name: Table name
            partition_values: List of partition values identifying the partition
            column_statistics_list: List of column statistics to update

        Returns:
            Dictionary with update result
        """
        try:
            if not self.glue_client:
                raise RuntimeError("Glue client not initialized")

            response = self.glue_client.update_column_statistics_for_partition(
                DatabaseName=database_name,
                TableName=table_name,
                PartitionValues=partition_values,
                ColumnStatisticsList=column_statistics_list
            )

            return {
                "database": database_name,
                "table": table_name,
                "partition_values": partition_values,
                "status": "updated",
                "errors": response.get('Errors', [])
            }

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error updating column statistics for partition in {database_name}.{table_name}: {e}")
            return {"error": str(e)}

    async def delete_column_statistics_for_table(
        self,
        database_name: str,
        table_name: str,
        column_name: str
    ) -> Dict[str, Any]:
        """
        Delete column statistics for a table column.

        Args:
            database_name: Database name
            table_name: Table name
            column_name: Column name

        Returns:
            Dictionary with deletion result
        """
        try:
            if not self.glue_client:
                raise RuntimeError("Glue client not initialized")

            self.glue_client.delete_column_statistics_for_table(
                DatabaseName=database_name,
                TableName=table_name,
                ColumnName=column_name
            )

            return {
                "database": database_name,
                "table": table_name,
                "column_name": column_name,
                "status": "deleted"
            }

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error deleting column statistics for {database_name}.{table_name}.{column_name}: {e}")
            return {"error": str(e)}

    async def delete_column_statistics_for_partition(
        self,
        database_name: str,
        table_name: str,
        partition_values: List[str],
        column_name: str
    ) -> Dict[str, Any]:
        """
        Delete column statistics for a partition column.

        Args:
            database_name: Database name
            table_name: Table name
            partition_values: List of partition values identifying the partition
            column_name: Column name

        Returns:
            Dictionary with deletion result
        """
        try:
            if not self.glue_client:
                raise RuntimeError("Glue client not initialized")

            self.glue_client.delete_column_statistics_for_partition(
                DatabaseName=database_name,
                TableName=table_name,
                PartitionValues=partition_values,
                ColumnName=column_name
            )

            return {
                "database": database_name,
                "table": table_name,
                "partition_values": partition_values,
                "column_name": column_name,
                "status": "deleted"
            }

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error deleting column statistics for partition in {database_name}.{table_name}: {e}")
            return {"error": str(e)}

    # Athena Workgroup Operations
    async def athena_create_work_group(
        self,
        name: str,
        description: Optional[str] = None,
        configuration: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Create an Athena workgroup.

        Args:
            name: Name of the workgroup
            description: Optional description
            configuration: Optional workgroup configuration
            tags: Optional tags for the workgroup

        Returns:
            Dictionary with workgroup creation result
        """
        try:
            if not self.athena_client:
                raise RuntimeError("Athena client not initialized")

            params = {"Name": name}

            if description:
                params["Description"] = description
            if configuration:
                params["Configuration"] = configuration
            if tags:
                params["Tags"] = [{"Key": k, "Value": v} for k, v in tags.items()]

            self.athena_client.create_work_group(**params)

            return {
                "name": name,
                "status": "created"
            }

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error creating Athena workgroup {name}: {e}")
            return {"error": str(e)}

    async def athena_list_work_groups(self, max_results: int = 25) -> Dict[str, Any]:
        """
        List Athena workgroups.

        Args:
            max_results: Maximum number of workgroups to return

        Returns:
            Dictionary with list of workgroups
        """
        try:
            if not self.athena_client:
                raise RuntimeError("Athena client not initialized")

            workgroups = []
            paginator = self.athena_client.get_paginator('list_work_groups')

            for page in paginator.paginate(PaginationConfig={'MaxItems': max_results}):
                for wg in page.get('WorkGroups', []):
                    workgroups.append({
                        "name": wg.get("Name"),
                        "state": wg.get("State"),
                        "description": wg.get("Description", ""),
                        "creation_time": wg.get("CreationTime").isoformat() if wg.get("CreationTime") else None
                    })

            return {
                "workgroups": workgroups,
                "count": len(workgroups)
            }

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error listing Athena workgroups: {e}")
            return {"error": str(e)}

    async def athena_get_work_group(self, name: str) -> Dict[str, Any]:
        """
        Get details of an Athena workgroup.

        Args:
            name: Name of the workgroup

        Returns:
            Dictionary with workgroup details
        """
        try:
            if not self.athena_client:
                raise RuntimeError("Athena client not initialized")

            response = self.athena_client.get_work_group(WorkGroup=name)
            wg = response.get("WorkGroup", {})

            return {
                "name": wg.get("Name"),
                "state": wg.get("State"),
                "description": wg.get("Description", ""),
                "configuration": wg.get("Configuration", {}),
                "creation_time": wg.get("CreationTime").isoformat() if wg.get("CreationTime") else None
            }

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error getting Athena workgroup {name}: {e}")
            return {"error": str(e)}

    async def athena_update_work_group(
        self,
        name: str,
        description: Optional[str] = None,
        configuration_updates: Optional[Dict[str, Any]] = None,
        state: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update an Athena workgroup.

        Args:
            name: Name of the workgroup
            description: Updated description
            configuration_updates: Configuration updates
            state: Updated state (ENABLED or DISABLED)

        Returns:
            Dictionary with update result
        """
        try:
            if not self.athena_client:
                raise RuntimeError("Athena client not initialized")

            params = {"WorkGroup": name}

            if description:
                params["Description"] = description
            if configuration_updates:
                params["ConfigurationUpdates"] = configuration_updates
            if state:
                params["State"] = state

            self.athena_client.update_work_group(**params)

            return {
                "name": name,
                "status": "updated"
            }

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error updating Athena workgroup {name}: {e}")
            return {"error": str(e)}

    async def athena_delete_work_group(
        self,
        name: str,
        recursive_delete_option: bool = False
    ) -> Dict[str, Any]:
        """
        Delete an Athena workgroup.

        Args:
            name: Name of the workgroup
            recursive_delete_option: If true, deletes the workgroup and its contents

        Returns:
            Dictionary with deletion result
        """
        try:
            if not self.athena_client:
                raise RuntimeError("Athena client not initialized")

            self.athena_client.delete_work_group(
                WorkGroup=name,
                RecursiveDeleteOption=recursive_delete_option
            )

            return {
                "name": name,
                "status": "deleted"
            }

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error deleting Athena workgroup {name}: {e}")
            return {"error": str(e)}

    # Athena Data Catalog Operations
    async def athena_get_data_catalog(self, name: str) -> Dict[str, Any]:
        """
        Get details of an Athena data catalog.

        Args:
            name: Name of the data catalog

        Returns:
            Dictionary with data catalog details
        """
        try:
            if not self.athena_client:
                raise RuntimeError("Athena client not initialized")

            response = self.athena_client.get_data_catalog(Name=name)
            catalog = response.get("DataCatalog", {})

            return {
                "name": catalog.get("Name"),
                "description": catalog.get("Description", ""),
                "type": catalog.get("Type"),
                "parameters": catalog.get("Parameters", {})
            }

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error getting Athena data catalog {name}: {e}")
            return {"error": str(e)}

    async def athena_list_data_catalogs(self, max_results: int = 25) -> Dict[str, Any]:
        """
        List Athena data catalogs.

        Args:
            max_results: Maximum number of catalogs to return

        Returns:
            Dictionary with list of data catalogs
        """
        try:
            if not self.athena_client:
                raise RuntimeError("Athena client not initialized")

            catalogs = []
            paginator = self.athena_client.get_paginator('list_data_catalogs')

            for page in paginator.paginate(PaginationConfig={'MaxItems': max_results}):
                for catalog in page.get('DataCatalogsSummary', []):
                    catalogs.append({
                        "catalog_name": catalog.get("CatalogName"),
                        "type": catalog.get("Type")
                    })

            return {
                "catalogs": catalogs,
                "count": len(catalogs)
            }

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error listing Athena data catalogs: {e}")
            return {"error": str(e)}

    async def athena_update_data_catalog(
        self,
        name: str,
        type: str,
        description: Optional[str] = None,
        parameters: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Update an Athena data catalog.

        Args:
            name: Name of the data catalog
            type: Type of the data catalog (GLUE, LAMBDA, HIVE)
            description: Optional description
            parameters: Optional parameters for the catalog

        Returns:
            Dictionary with update result
        """
        try:
            if not self.athena_client:
                raise RuntimeError("Athena client not initialized")

            params = {
                "Name": name,
                "Type": type
            }

            if description:
                params["Description"] = description
            if parameters:
                params["Parameters"] = parameters

            self.athena_client.update_data_catalog(**params)

            return {
                "name": name,
                "status": "updated"
            }

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error updating Athena data catalog {name}: {e}")
            return {"error": str(e)}

    # Athena Query Execution Operations
    async def athena_start_query_execution(
        self,
        query_string: str,
        database: Optional[str] = None,
        output_location: Optional[str] = None,
        work_group: Optional[str] = None,
        query_execution_context: Optional[Dict[str, Any]] = None,
        result_configuration: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Start an Athena query execution.

        Args:
            query_string: SQL query string to execute
            database: Optional database name
            output_location: Optional S3 output location
            work_group: Optional workgroup name
            query_execution_context: Optional query execution context
            result_configuration: Optional result configuration

        Returns:
            Dictionary with query execution ID
        """
        try:
            if not self.athena_client:
                raise RuntimeError("Athena client not initialized")

            params = {"QueryString": query_string}

            if query_execution_context:
                params["QueryExecutionContext"] = query_execution_context
            elif database:
                params["QueryExecutionContext"] = {"Database": database}

            if result_configuration:
                params["ResultConfiguration"] = result_configuration
            elif output_location:
                params["ResultConfiguration"] = {"OutputLocation": output_location}

            if work_group:
                params["WorkGroup"] = work_group

            response = self.athena_client.start_query_execution(**params)

            return {
                "query_execution_id": response.get("QueryExecutionId"),
                "status": "started"
            }

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error starting Athena query execution: {e}")
            return {"error": str(e)}

    async def athena_get_query_execution(self, query_execution_id: str) -> Dict[str, Any]:
        """
        Get details of an Athena query execution.

        Args:
            query_execution_id: Query execution ID

        Returns:
            Dictionary with query execution details
        """
        try:
            if not self.athena_client:
                raise RuntimeError("Athena client not initialized")

            response = self.athena_client.get_query_execution(QueryExecutionId=query_execution_id)
            qe = response.get("QueryExecution", {})

            return {
                "query_execution_id": qe.get("QueryExecutionId"),
                "query": qe.get("Query"),
                "state": qe.get("Status", {}).get("State"),
                "state_change_reason": qe.get("Status", {}).get("StateChangeReason", ""),
                "submission_date_time": qe.get("Status", {}).get("SubmissionDateTime").isoformat() if qe.get("Status", {}).get("SubmissionDateTime") else None,
                "completion_date_time": qe.get("Status", {}).get("CompletionDateTime").isoformat() if qe.get("Status", {}).get("CompletionDateTime") else None,
                "query_execution_context": qe.get("QueryExecutionContext", {}),
                "result_configuration": qe.get("ResultConfiguration", {}),
                "statistics": qe.get("Statistics", {}),
                "work_group": qe.get("WorkGroup", "")
            }

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error getting Athena query execution {query_execution_id}: {e}")
            return {"error": str(e)}

    async def athena_stop_query_execution(self, query_execution_id: str) -> Dict[str, Any]:
        """
        Stop an Athena query execution.

        Args:
            query_execution_id: Query execution ID

        Returns:
            Dictionary with stop result
        """
        try:
            if not self.athena_client:
                raise RuntimeError("Athena client not initialized")

            self.athena_client.stop_query_execution(QueryExecutionId=query_execution_id)

            return {
                "query_execution_id": query_execution_id,
                "status": "stopped"
            }

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error stopping Athena query execution {query_execution_id}: {e}")
            return {"error": str(e)}

    async def athena_get_query_results(
        self,
        query_execution_id: str,
        max_results: int = 1000
    ) -> Dict[str, Any]:
        """
        Get results of an Athena query execution.

        Args:
            query_execution_id: Query execution ID
            max_results: Maximum number of results to return

        Returns:
            Dictionary with query results
        """
        try:
            if not self.athena_client:
                raise RuntimeError("Athena client not initialized")

            rows = []
            paginator = self.athena_client.get_paginator('get_query_results')

            for page in paginator.paginate(
                QueryExecutionId=query_execution_id,
                PaginationConfig={'MaxItems': max_results}
            ):
                result_set = page.get('ResultSet', {})

                # Get column info from first page
                if not rows and result_set.get('ResultSetMetadata'):
                    column_info = result_set['ResultSetMetadata'].get('ColumnInfo', [])

                # Process rows
                for row in result_set.get('Rows', []):
                    row_data = []
                    for data in row.get('Data', []):
                        row_data.append(data.get('VarCharValue', ''))
                    rows.append(row_data)

            return {
                "query_execution_id": query_execution_id,
                "rows": rows,
                "row_count": len(rows),
                "column_info": column_info if 'column_info' in locals() else []
            }

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error getting Athena query results {query_execution_id}: {e}")
            return {"error": str(e)}

    async def athena_list_query_executions(
        self,
        work_group: Optional[str] = None,
        max_results: int = 25
    ) -> Dict[str, Any]:
        """
        List Athena query executions.

        Args:
            work_group: Optional workgroup name to filter by
            max_results: Maximum number of query executions to return

        Returns:
            Dictionary with list of query execution IDs
        """
        try:
            if not self.athena_client:
                raise RuntimeError("Athena client not initialized")

            params = {}
            if work_group:
                params["WorkGroup"] = work_group

            query_execution_ids = []
            paginator = self.athena_client.get_paginator('list_query_executions')

            for page in paginator.paginate(**params, PaginationConfig={'MaxItems': max_results}):
                query_execution_ids.extend(page.get('QueryExecutionIds', []))

            return {
                "query_execution_ids": query_execution_ids,
                "count": len(query_execution_ids)
            }

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error listing Athena query executions: {e}")
            return {"error": str(e)}

    async def athena_batch_get_query_execution(
        self,
        query_execution_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Batch get details of multiple Athena query executions.

        Args:
            query_execution_ids: List of query execution IDs

        Returns:
            Dictionary with query execution details
        """
        try:
            if not self.athena_client:
                raise RuntimeError("Athena client not initialized")

            response = self.athena_client.batch_get_query_execution(
                QueryExecutionIds=query_execution_ids
            )

            query_executions = []
            for qe in response.get('QueryExecutions', []):
                query_executions.append({
                    "query_execution_id": qe.get("QueryExecutionId"),
                    "query": qe.get("Query"),
                    "state": qe.get("Status", {}).get("State"),
                    "state_change_reason": qe.get("Status", {}).get("StateChangeReason", ""),
                    "submission_date_time": qe.get("Status", {}).get("SubmissionDateTime").isoformat() if qe.get("Status", {}).get("SubmissionDateTime") else None,
                    "completion_date_time": qe.get("Status", {}).get("CompletionDateTime").isoformat() if qe.get("Status", {}).get("CompletionDateTime") else None,
                    "work_group": qe.get("WorkGroup", "")
                })

            return {
                "query_executions": query_executions,
                "count": len(query_executions),
                "unprocessed_query_execution_ids": response.get('UnprocessedQueryExecutionIds', [])
            }

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error batch getting Athena query executions: {e}")
            return {"error": str(e)}
