import json
import os
import datetime
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from services.utils.logger import logger

# Try to import AWS Glue/boto3 client library
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    GLUE_AVAILABLE = True
except ImportError:
    logger.warning("AWS boto3 library not available. Install with: pip install boto3")
    GLUE_AVAILABLE = False


def setup_glue_client(iam_role_config):
    """
    Set up AWS Glue client using IAM role assumption

    Args:
        iam_role_config: Dictionary containing IAM role configuration
            - customer_account_id: AWS account ID to assume role in
            - role_name: Name of the IAM role to assume
            - external_id: External ID for role assumption
            - region: AWS region for Glue service

    Returns:
        Glue client instance
    """
    if not GLUE_AVAILABLE:
        raise ImportError("AWS boto3 library not installed")

    if not iam_role_config:
        return None

    try:
        # Extract configuration
        customer_account_id = iam_role_config.get("customer_account_id")
        role_name = iam_role_config.get("role_name")
        external_id = iam_role_config.get("external_id")
        region = iam_role_config.get("region", "us-east-1")

        # Validate required fields
        required_fields = ['customer_account_id', 'role_name', 'external_id']
        missing_fields = [field for field in required_fields if not iam_role_config.get(field)]

        if missing_fields:
            logger.error(f"Missing required IAM role fields: {missing_fields}")
            return None

        # Construct role ARN
        role_arn = f"arn:aws:iam::{customer_account_id}:role/{role_name}"

        # Create STS client to assume role
        sts_client = boto3.client('sts')

        # Assume the role
        assumed_role = sts_client.assume_role(
            RoleArn=role_arn,
            RoleSessionName='BrewSearchGlueScanning',
            ExternalId=external_id
        )

        # Extract temporary credentials
        credentials = assumed_role['Credentials']

        # Create Glue client with assumed role credentials
        glue_client = boto3.client(
            'glue',
            region_name=region,
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken']
        )

        logger.info(f"AWS Glue client created for account: {customer_account_id}, region: {region}")
        return glue_client

    except ClientError as e:
        logger.error(f"Failed to assume role for AWS Glue: {e}")
        return None
    except NoCredentialsError as e:
        logger.error(f"AWS credentials not found: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to create AWS Glue client: {e}")
        return None


def test_glue_connection(client):
    """
    Test AWS Glue connection by listing databases

    Args:
        client: Glue client instance

    Returns:
        True if connection successful, False otherwise
    """
    try:
        # Simple test - list databases
        response = client.get_databases(MaxResults=1)

        if 'DatabaseList' in response:
            logger.info("AWS Glue connection test successful")
            return True
        else:
            logger.error("AWS Glue connection test failed - unexpected response")
            return False

    except ClientError as e:
        logger.error(f"AWS Glue connection test failed: {e}")
        return False
    except Exception as e:
        logger.error(f"AWS Glue connection test error: {e}")
        return False


def get_database_list(client, target_databases=None):
    """
    Get list of databases from AWS Glue

    Args:
        client: Glue client instance
        target_databases: Optional list of specific database names to fetch

    Returns:
        List of database objects
    """
    try:
        databases = []

        if target_databases:
            # Fetch specific databases
            for db_name in target_databases:
                try:
                    response = client.get_database(Name=db_name)
                    if 'Database' in response:
                        databases.append(response['Database'])
                except ClientError as e:
                    logger.warning(f"Failed to get database {db_name}: {e}")
        else:
            # Fetch all databases with pagination
            paginator = client.get_paginator('get_databases')
            for page in paginator.paginate():
                databases.extend(page.get('DatabaseList', []))

        logger.info(f"Retrieved {len(databases)} databases from AWS Glue")
        return databases

    except Exception as e:
        logger.error(f"Failed to get database list: {e}")
        return []


def get_table_metadata(client, database_name, table_name):
    """
    Get detailed metadata for a specific table

    Args:
        client: Glue client instance
        database_name: Name of the database
        table_name: Name of the table

    Returns:
        Dictionary containing table metadata
    """
    try:
        response = client.get_table(DatabaseName=database_name, Name=table_name)
        table = response.get('Table', {})

        # Extract relevant metadata
        metadata = {
            "table_name": table_name,
            "database_name": database_name,
            "description": table.get('Description', ''),
            "owner": table.get('Owner', ''),
            "create_time": str(table.get('CreateTime', '')),
            "update_time": str(table.get('UpdateTime', '')),
            "last_access_time": str(table.get('LastAccessTime', '')),
            "retention": table.get('Retention', 0),
            "storage_descriptor": table.get('StorageDescriptor', {}),
            "partition_keys": table.get('PartitionKeys', []),
            "table_type": table.get('TableType', ''),
            "parameters": table.get('Parameters', {})
        }

        return metadata

    except ClientError as e:
        logger.error(f"Failed to get table metadata for {database_name}.{table_name}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error getting table metadata: {e}")
        return None


def generate_glue_overview(base_dir, project, dest_folder, target_databases=None,
                           iam_role_config=None, output_format="both"):
    """
    Generate AWS Glue metadata overview

    Args:
        base_dir: Base directory for project data
        project: Project identifier
        dest_folder: Destination folder for metadata files
        target_databases: Optional list of specific databases to scan
        iam_role_config: IAM role configuration for authentication
        output_format: Output format - "json", "text", or "both"
    """
    if not GLUE_AVAILABLE:
        logger.error("AWS boto3 library not available. Cannot generate Glue overview.")
        return

    try:
        # Setup Glue client
        client = setup_glue_client(iam_role_config)
        if not client:
            logger.error("Failed to setup AWS Glue client")
            return

        # Test connection
        if not test_glue_connection(client):
            logger.error("AWS Glue connection test failed")
            return

        # Create metadata directory structure
        metadata_base = os.path.join(dest_folder, "database_metadata")
        provider_dir = os.path.join(metadata_base, "providers", "glue")
        tables_dir = os.path.join(provider_dir, "tables")
        os.makedirs(tables_dir, exist_ok=True)

        # Get databases
        databases = get_database_list(client, target_databases)

        if not databases:
            logger.warning("No databases found in AWS Glue")
            return

        logger.info(f"Processing {len(databases)} databases...")

        # Track overall statistics
        total_tables = 0
        manifest_entries = []

        # Process each database
        for database in databases:
            db_name = database.get('Name')
            logger.info(f"Processing database: {db_name}")

            try:
                # Get tables and views in database
                paginator = client.get_paginator('get_tables')
                for page in paginator.paginate(DatabaseName=db_name):
                    tables = page.get('TableList', [])

                    # Process each table/view
                    for table in tables:
                        table_name = table.get('Name')
                        table_type = table.get('TableType', 'TABLE')

                        try:
                            # Create table metadata file
                            table_metadata = get_table_metadata(client, db_name, table_name)
                            if table_metadata:
                                # Add table_type to metadata
                                table_metadata['table_type'] = table_type

                                # Save table metadata
                                table_file_path = os.path.join(tables_dir, db_name, f"{table_name}.json")
                                os.makedirs(os.path.dirname(table_file_path), exist_ok=True)

                                with open(table_file_path, 'w') as f:
                                    json.dump(table_metadata, f, indent=2, default=str)

                                # Add to manifest
                                manifest_entries.append({
                                    "fqtn": f"glue://{iam_role_config.get('customer_account_id')}/{db_name}/{table_name}",
                                    "provider": "glue",
                                    "database": db_name,
                                    "table": table_name,
                                    "table_type": table_type,
                                    "file_path": f"providers/glue/tables/{db_name}/{table_name}.json"
                                })
                                total_tables += 1
                        except Exception as e:
                            logger.warning(f"Could not process table/view {db_name}.{table_name}: {e}")
                            continue

            except Exception as e:
                logger.error(f"Failed to process database {db_name}: {e}")

        # Create provider overview
        provider_overview = {
            "provider": "glue",
            "account_id": iam_role_config.get('customer_account_id'),
            "region": iam_role_config.get('region', 'us-east-1'),
            "total_databases": len(databases),
            "total_tables": total_tables,
            "scanned_at": datetime.datetime.now().isoformat()
        }

        with open(os.path.join(provider_dir, "provider_overview.json"), 'w') as f:
            json.dump(provider_overview, f, indent=2, default=str)

        # Create manifest
        manifest = {
            "version": "1.0",
            "provider": "glue",
            "tables": manifest_entries
        }

        with open(os.path.join(provider_dir, "manifest.json"), 'w') as f:
            json.dump(manifest, f, indent=2, default=str)

        logger.info(f"AWS Glue metadata generation completed: {total_tables} tables from {len(databases)} databases")

    except Exception as e:
        logger.error(f"Failed to generate AWS Glue overview: {e}", exc_info=True)
