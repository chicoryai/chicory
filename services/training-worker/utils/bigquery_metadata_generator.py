import json
import os
import datetime
import hashlib
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from services.utils.logger import logger

# Try to import BigQuery client library directly
try:
    from google.cloud import bigquery
    from google.oauth2 import service_account

    BIGQUERY_AVAILABLE = True
except ImportError:
    logger.warning("Google BigQuery client library not available. Install with: pip install google-cloud-bigquery")
    BIGQUERY_AVAILABLE = False


def setup_bigquery_client(service_account_info):
    """
    Set up BigQuery client from service account info

    Args:
        service_account_info: Dictionary containing service account credentials

    Returns:
        BigQuery client instance
    """
    if not BIGQUERY_AVAILABLE:
        raise ImportError("Google BigQuery client library not installed")

    if not service_account_info:
        return None

    try:
        # Ensure we have all required fields for a complete service account JSON
        required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email', 'client_id']
        missing_fields = [field for field in required_fields if not service_account_info.get(field)]

        if missing_fields:
            logger.error(f"Missing required service account fields: {missing_fields}")
            return None

        # Create credentials from service account info
        credentials = service_account.Credentials.from_service_account_info(service_account_info)

        # Create BigQuery client
        client = bigquery.Client(
            credentials=credentials,
            project=service_account_info["project_id"]
        )

        logger.info(f"BigQuery client created for project: {service_account_info['project_id']}")
        return client

    except Exception as e:
        logger.error(f"Failed to create BigQuery client: {e}")
        return None


def setup_bigquery_credentials(service_account_info):
    """
    Set up BigQuery credentials from service account info (fallback method)

    Args:
        service_account_info: Dictionary containing service account credentials

    Returns:
        Path to temporary credentials file
    """
    if not service_account_info:
        return None

    try:
        # Ensure we have all required fields for a complete service account JSON
        required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email', 'client_id']
        missing_fields = [field for field in required_fields if not service_account_info.get(field)]

        if missing_fields:
            logger.error(f"Missing required service account fields: {missing_fields}")
            return None

        # Create a complete service account credentials dictionary
        credentials_dict = {
            "type": "service_account",
            "project_id": service_account_info["project_id"],
            "private_key_id": service_account_info["private_key_id"],
            "private_key": service_account_info["private_key"].replace('\\n', '\n'),  # Handle escaped newlines
            "client_email": service_account_info["client_email"],
            "client_id": service_account_info["client_id"],
            "auth_uri": service_account_info.get("auth_uri", "https://accounts.google.com/o/oauth2/auth"),
            "token_uri": service_account_info.get("token_uri", "https://oauth2.googleapis.com/token"),
            "auth_provider_x509_cert_url": service_account_info.get("auth_provider_x509_cert_url",
                                                                    "https://www.googleapis.com/oauth2/v1/certs")
        }

        # Add optional fields if present
        if service_account_info.get("client_x509_cert_url"):
            credentials_dict["client_x509_cert_url"] = service_account_info["client_x509_cert_url"]
        if service_account_info.get("universe_domain"):
            credentials_dict["universe_domain"] = service_account_info["universe_domain"]

        # Create a temporary file for the service account credentials
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(credentials_dict, temp_file, indent=2)
        temp_file.close()

        # Set the environment variable for BigQuery authentication
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_file.name
        logger.info(
            f"BigQuery credentials configured from service account info for project: {credentials_dict['project_id']}")

        return temp_file.name

    except Exception as e:
        logger.error(f"Failed to setup BigQuery credentials: {e}")
        return None


def test_bigquery_connection(client, project_id):
    """
    Test BigQuery connection with a simple query

    Args:
        client: BigQuery client instance
        project_id: Project ID for testing

    Returns:
        True if connection successful, False otherwise
    """
    try:
        # Simple test query
        query = f"SELECT '{project_id}' as project_id, 'US' as location"
        query_job = client.query(query)
        results = query_job.result()

        # Check if we got results
        row_count = 0
        for row in results:
            row_count += 1
            break  # We only need to verify we can get one row

        if row_count > 0:
            logger.info("BigQuery connection test successful")
            return True
        else:
            logger.error("BigQuery connection test failed - no results returned")
            return False

    except Exception as e:
        logger.error(f"BigQuery connection test failed: {str(e)}")
        error_msg = str(e).lower()

        if "authentication" in error_msg or "credentials" in error_msg:
            logger.error("Authentication issue detected. Please verify:")
            logger.error("1. Service account credentials are correct")
            logger.error("2. Service account has BigQuery permissions")
            logger.error("3. BigQuery API is enabled for the project")
        elif "permission" in error_msg or "access" in error_msg:
            logger.error("Permission issue detected. Please verify:")
            logger.error("1. Service account has BigQuery Data Viewer role")
            logger.error("2. Service account has BigQuery Job User role")
            logger.error("3. Project permissions are correctly configured")
        elif "not found" in error_msg:
            logger.error("Resource not found. Please verify:")
            logger.error("1. Project ID is correct")
            logger.error("2. BigQuery API is enabled")
            logger.error("3. Project exists and is accessible")

        return False


def get_datasets_using_client(client, project_id, target_datasets=None):
    """
    Get datasets using BigQuery client

    Args:
        client: BigQuery client instance
        project_id: Project ID
        target_datasets: Optional list of specific dataset names to process

    Returns:
        List of dataset information
    """
    try:
        datasets = []

        # List all datasets in the project
        dataset_list = client.list_datasets(project=project_id)

        for dataset in dataset_list:
            dataset_id = dataset.dataset_id

            # Filter datasets if target_datasets is provided
            if target_datasets and dataset_id not in target_datasets:
                continue

            # Get full dataset information
            dataset_ref = client.get_dataset(dataset.reference)

            dataset_info = {
                "dataset_name": dataset_id,
                "location": dataset_ref.location or "US",
                "creation_time": dataset_ref.created,
                "description": dataset_ref.description or ""
            }

            datasets.append(dataset_info)

        logger.info(f"Found {len(datasets)} datasets in project {project_id}")
        return datasets

    except Exception as e:
        logger.error(f"Error getting datasets: {str(e)}")
        return []


def get_tables_using_client(client, project_id, dataset_id, max_tables=100):
    """
    Get tables and views in a dataset using BigQuery client

    Args:
        client: BigQuery client instance
        project_id: Project ID
        dataset_id: Dataset ID
        max_tables: Maximum number of tables to process

    Returns:
        List of table and view information
    """
    try:
        tables = []

        # Get dataset reference
        dataset_ref = bigquery.DatasetReference(project_id, dataset_id)

        # List tables and views in the dataset
        table_list = client.list_tables(dataset_ref, max_results=max_tables)

        for table in table_list:
            try:
                # Get full table information
                table_ref = client.get_table(table.reference)

                # Get column information
                columns = []
                for field in table_ref.schema:
                    column_info = {
                        "name": field.name,
                        "data_type": field.field_type,
                        "nullable": field.mode != "REQUIRED",
                        "description": field.description or ""
                    }
                    columns.append(column_info)

                # Determine table type (TABLE, VIEW, MATERIALIZED_VIEW, EXTERNAL)
                table_type = table.table_type if hasattr(table, 'table_type') else "TABLE"
                if table_type is None:
                    table_type = "TABLE"

                table_info = {
                    "table_name": table.table_id,
                    "table_type": table_type,
                    "creation_time": table_ref.created,
                    "row_count": table_ref.num_rows or 0 if table_type != "VIEW" else 0,
                    "size_bytes": table_ref.num_bytes or 0 if table_type != "VIEW" else 0,
                    "columns": columns,
                    "description": table_ref.description or ""
                }

                tables.append(table_info)
            except Exception as e:
                logger.warning(f"Could not process table/view {table.table_id} in dataset {dataset_id}: {e}")
                continue

        logger.info(f"Found {len(tables)} tables/views in dataset {dataset_id}")
        return tables

    except Exception as e:
        logger.error(f"Error getting tables/views for dataset {dataset_id}: {str(e)}")
        return []


def generate_bigquery_overview(base_dir, project, dest_folder, target_datasets=None,
                               service_account_info=None, output_format="json"):
    """
    Generate comprehensive BigQuery database and table metadata files

    Args:
        base_dir: Base directory path
        project: Project configuration
        dest_folder: Destination folder for output files
        target_datasets: Optional list of specific dataset names to process. If None, processes all datasets.
        service_account_info: Dictionary containing service account credentials
        output_format: Format of output files. Options: "json" (default), "text" (human-readable for RAG), or "both".
    """
    try:
        logger.info("Starting generation of BigQuery metadata...")

        # Create directory structure
        metadata_dir = os.path.join(dest_folder, "database_metadata")
        providers_dir = os.path.join(metadata_dir, "providers", "bigquery")
        tables_dir = os.path.join(providers_dir, "tables")

        os.makedirs(metadata_dir, exist_ok=True)
        os.makedirs(providers_dir, exist_ok=True)
        os.makedirs(tables_dir, exist_ok=True)

        # Process datasets and tables
        process_bigquery_datasets_and_tables(
            project,
            metadata_dir,
            providers_dir,
            tables_dir,
            target_datasets=target_datasets,
            service_account_info=service_account_info,
            output_format=output_format
        )

        logger.info("Successfully generated all BigQuery metadata files")

    except Exception as e:
        logger.error(f"Error generating BigQuery metadata: {str(e)}", exc_info=True)
        raise


def format_bigquery_table_card(table_data, project_id, location):
    """
    Format table metadata according to the schema card specification for BigQuery
    Only includes factual information from the database
    """
    props = table_data["properties"]
    basic_info = props.get("basic_info", {})
    columns = props.get("columns", [])
    dataset_name = props.get("location", {}).get("dataset", "")
    table_name = props.get("name", "")

    # Create FQTN (Fully Qualified Table Name)
    fqtn = f"bigquery://{project_id}/{dataset_name}/{table_name}"

    # Format columns with only factual information
    formatted_columns = []
    for col in columns:
        formatted_col = {
            "name": col.get("name", ""),
            "type": col.get("data_type", "STRING"),
            "nullable": col.get("nullable", True),
            "description": col.get("description", "")
        }
        formatted_columns.append(formatted_col)

    # Create the schema card with only factual data
    card = {
        "version": "1.0",
        "provider": "bigquery",
        "dialect": "bigquery",
        "address": {
            "account": None,
            "region": location,
            "database": None,
            "schema": None,
            "catalog": None,
            "project": project_id,
            "dataset": dataset_name
        },
        "fqtn": fqtn,
        "kind": basic_info.get("table_type", "table").lower(),
        "row_count": basic_info.get("row_count", 0),
        "size_bytes": basic_info.get("size_bytes", 0),
        "created_date": basic_info.get("created_date"),
        "description": basic_info.get("comment", ""),
        "columns": formatted_columns
    }

    return card


def process_bigquery_datasets_and_tables(project, metadata_dir, providers_dir, tables_dir,
                                         max_tables_per_dataset=100, target_datasets=None, service_account_info=None,
                                         output_format="json"):
    """
    Process BigQuery datasets and tables to generate metadata files using native BigQuery client

    Args:
        project: Project configuration
        metadata_dir: Base metadata directory
        providers_dir: Provider-specific directory
        tables_dir: Tables directory
        max_tables_per_dataset: Maximum number of tables to process per dataset
        target_datasets: Optional list of specific dataset names to process
        service_account_info: Dictionary containing service account credentials
        output_format: Format of output files
    """
    try:
        if not BIGQUERY_AVAILABLE:
            logger.error("BigQuery client library not available. Cannot process BigQuery metadata.")
            return

        # Get project information from service account info
        if not service_account_info:
            logger.error("No service account information provided for BigQuery")
            return

        project_id = service_account_info["project_id"]
        location = "US"  # Default location

        logger.info(f"Processing BigQuery project: {project_id} in location: {location}")

        # Create BigQuery client
        client = setup_bigquery_client(service_account_info)
        if not client:
            logger.error("Failed to create BigQuery client")
            return

        # Test BigQuery connection
        if not test_bigquery_connection(client, project_id):
            logger.error("BigQuery connection test failed")
            return

        # Get all datasets using BigQuery client
        datasets = get_datasets_using_client(client, project_id, target_datasets)

        if not datasets:
            logger.warning("No datasets found to process")
            return

        total_datasets = len(datasets)
        logger.info(f"Found {total_datasets} datasets to process")

        # Create provider overview
        provider_overview = {
            "version": "1.0",
            "provider": "bigquery",
            "project_id": project_id,
            "location": location,
            "total_datasets": total_datasets,
            "connection_info": {
                "authentication": "service_account",
                "location": location
            },
            "capabilities": {
                "standard_sql": True,
                "ml": True,
                "streaming": True,
                "cross_region_queries": True
            },
            "generated_at": datetime.datetime.now().isoformat()
        }

        # Write provider overview
        with open(os.path.join(providers_dir, "provider_overview.json"), 'w') as f:
            json.dump(provider_overview, f, indent=2, default=str)

        # Process datasets and tables
        all_table_cards = []
        manifest_entries = []
        total_tables_processed = 0

        max_workers = min(3, total_datasets)  # Limit concurrent workers for BigQuery

        def process_dataset(dataset_info):
            """Process a single dataset and its tables"""
            try:
                dataset_name = dataset_info["dataset_name"]
                logger.info(f"Processing dataset: {dataset_name}")

                # Create dataset directory
                dataset_dir = os.path.join(tables_dir, project_id, dataset_name)
                os.makedirs(dataset_dir, exist_ok=True)

                # Get tables in dataset using BigQuery client
                tables = get_tables_using_client(client, project_id, dataset_name, max_tables_per_dataset)

                dataset_cards = []
                tables_processed_in_dataset = 0

                for table_info in tables:
                    table_name = table_info["table_name"]

                    try:
                        # Build table data structure
                        table_data = {
                            "entity": "table",
                            "properties": {
                                "name": table_name,
                                "full_name": f"{project_id}.{dataset_name}.{table_name}",
                                "location": {
                                    "project": project_id,
                                    "dataset": dataset_name
                                },
                                "basic_info": {
                                    "table_type": table_info.get("table_type", "BASE TABLE"),
                                    "created_date": table_info["creation_time"].strftime("%Y-%m-%d") if table_info[
                                        "creation_time"] else None,
                                    "comment": table_info.get("description", ""),
                                    "row_count": table_info.get("row_count", 0),
                                    "size_bytes": table_info.get("size_bytes", 0)
                                },
                                "columns": table_info.get("columns", [])
                            }
                        }

                        # Generate schema card
                        table_card = format_bigquery_table_card(table_data, project_id, location)

                        # Write individual table card
                        table_file = os.path.join(dataset_dir, f"{table_name}.json")
                        with open(table_file, 'w') as f:
                            json.dump(table_card, f, indent=2, default=str)

                        # Calculate file size and hash
                        file_stats = os.stat(table_file)
                        with open(table_file, 'rb') as f:
                            file_hash = hashlib.sha256(f.read()).hexdigest()

                        # Add to manifest
                        manifest_entry = {
                            "fqtn": table_card["fqtn"],
                            "provider": "bigquery",
                            "dialect": "bigquery",
                            "path": os.path.relpath(table_file, metadata_dir),
                            "size_bytes": file_stats.st_size,
                            "hash": f"sha256:{file_hash}",
                            "row_count": table_card["row_count"]
                        }

                        dataset_cards.append(table_card)
                        manifest_entries.append(manifest_entry)
                        tables_processed_in_dataset += 1

                        logger.debug(f"  Processed table {table_name}")

                    except Exception as e:
                        logger.warning(f"Could not process table {table_name} in dataset {dataset_name}: {e}")
                        continue

                logger.info(f"✓ Completed dataset {dataset_name}: {tables_processed_in_dataset} tables processed")
                return dataset_cards, tables_processed_in_dataset

            except Exception as e:
                logger.error(f"✗ Failed to process dataset {dataset_name}: {e}")
                return [], 0

        # Execute parallel processing
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_dataset = {
                executor.submit(process_dataset, dataset_info): dataset_info["dataset_name"]
                for dataset_info in datasets
            }

            for future in as_completed(future_to_dataset):
                dataset_name = future_to_dataset[future]
                try:
                    dataset_cards, tables_count = future.result()
                    all_table_cards.extend(dataset_cards)
                    total_tables_processed += tables_count
                except Exception as e:
                    logger.error(f"Dataset {dataset_name} generated an exception: {e}")

        # Write manifest.json
        manifest = {
            "version": "1.0",
            "tables": manifest_entries
        }

        with open(os.path.join(providers_dir, "manifest.json"), 'w') as f:
            json.dump(manifest, f, indent=2, default=str)

        # Write database_overview.json
        database_overview = {
            "version": "1.0",
            "providers": {
                "bigquery": {
                    "project_count": 1,
                    "dataset_count": total_datasets,
                    "table_count": total_tables_processed,
                    "regions": [location]
                }
            },
            "total_tables": total_tables_processed,
            "generated_at": datetime.datetime.now().isoformat()
        }

        with open(os.path.join(metadata_dir, "database_overview.json"), 'w') as f:
            json.dump(database_overview, f, indent=2, default=str)

        # Write generatedat timestamp
        with open(os.path.join(metadata_dir, "generatedat"), 'w') as f:
            f.write(datetime.datetime.now().isoformat())

        logger.info(
            f"BigQuery metadata generation completed! Processed {total_datasets} datasets with {total_tables_processed} total tables")
        logger.info(f"Files saved to: {metadata_dir}")

    except Exception as e:
        logger.error(f"Error processing BigQuery datasets and tables: {str(e)}", exc_info=True)
        raise
