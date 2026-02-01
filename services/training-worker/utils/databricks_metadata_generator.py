import json
import os
import datetime
import hashlib
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from services.utils.logger import logger

# Try to import Databricks client library directly
try:
    from databricks import sql as databricks_sql
    DATABRICKS_AVAILABLE = True
except ImportError:
    logger.warning("Databricks SQL client library not available. Install with: pip install databricks-sql-connector")
    DATABRICKS_AVAILABLE = False


def setup_databricks_client(databricks_config):
    """
    Set up Databricks client from configuration

    Args:
        databricks_config: Dictionary containing Databricks connection info

    Returns:
        Databricks SQL connection instance
    """
    if not DATABRICKS_AVAILABLE:
        raise ImportError("Databricks SQL client library not installed")

    if not databricks_config:
        return None

    try:
        # Ensure we have all required fields for Databricks connection
        required_fields = ['access_token', 'server_hostname']
        missing_fields = [field for field in required_fields if not databricks_config.get(field)]

        if missing_fields:
            logger.error(f"Missing required Databricks connection fields: {missing_fields}")
            logger.error("Please ensure the following environment variables are set:")
            if 'access_token' in missing_fields:
                logger.error("- DATABRICKS_ACCESS_TOKEN or {PROJECT}_DATABRICKS_ACCESS_TOKEN")
            if 'server_hostname' in missing_fields:
                logger.error("- DATABRICKS_SERVER_HOSTNAME or {PROJECT}_DATABRICKS_SERVER_HOSTNAME")
            return None

        # Create Databricks SQL connection
        connection = databricks_sql.connect(
            server_hostname=databricks_config["server_hostname"],
            http_path=databricks_config.get("http_path", "/sql/1.0/warehouses/default"),
            access_token=databricks_config["access_token"]
        )

        logger.info(f"Databricks client created for hostname: {databricks_config['server_hostname']}")
        return connection

    except Exception as e:
        logger.error(f"Failed to create Databricks client: {e}")
        return None


def test_databricks_connection(connection):
    """
    Test Databricks connection with a simple query

    Args:
        connection: Databricks SQL connection instance

    Returns:
        True if connection successful, False otherwise
    """
    try:
        cursor = connection.cursor()
        
        # Simple test query
        cursor.execute("SELECT 'test' as test_column")
        result = cursor.fetchone()
        
        cursor.close()
        
        if result:
            logger.info("Databricks connection test successful")
            return True
        else:
            logger.error("Databricks connection test failed - no results returned")
            return False

    except Exception as e:
        logger.error(f"Databricks connection test failed: {str(e)}")
        error_msg = str(e).lower()

        if "authentication" in error_msg or "token" in error_msg:
            logger.error("Authentication issue detected. Please verify:")
            logger.error("1. Access token is correct and not expired")
            logger.error("2. Token has appropriate permissions")
        elif "hostname" in error_msg or "connection" in error_msg:
            logger.error("Connection issue detected. Please verify:")
            logger.error("1. Server hostname is correct")
            logger.error("2. HTTP path is correct")
            logger.error("3. Network connectivity to Databricks workspace")
        elif "permission" in error_msg or "access" in error_msg:
            logger.error("Permission issue detected. Please verify:")
            logger.error("1. User has appropriate workspace permissions")
            logger.error("2. Access token has required scopes")

        return False


def generate_databricks_overview(base_dir, project, dest_folder, target_catalogs=None, target_schemas=None, databricks_config=None, output_format="json"):
    """
    Generate comprehensive Databricks database and table metadata files
    
    Args:
        base_dir: Base directory path
        project: Project configuration
        dest_folder: Destination folder for output files
        target_catalogs: Optional list of specific catalog names to process. If None, processes all catalogs.
        target_schemas: Optional list of specific schema names to process. If None, processes all schemas.
        databricks_config: Dictionary containing Databricks connection credentials
        output_format: Format of output files. Options: "json" (default), "text" (human-readable for RAG), or "both".
    """
    try:
        logger.info("Starting generation of Databricks metadata...")
        
        # Create directory structure
        metadata_dir = os.path.join(dest_folder, "database_metadata")
        providers_dir = os.path.join(metadata_dir, "providers", "databricks")
        tables_dir = os.path.join(providers_dir, "tables")
        
        os.makedirs(metadata_dir, exist_ok=True)
        os.makedirs(providers_dir, exist_ok=True)
        os.makedirs(tables_dir, exist_ok=True)
        
        # Process catalogs and tables
        process_databricks_catalogs_and_tables(
            project, 
            metadata_dir, 
            providers_dir, 
            tables_dir,
            target_catalogs=target_catalogs,
            target_schemas=target_schemas,
            databricks_config=databricks_config,
            output_format=output_format
        )
        
        logger.info("Successfully generated all Databricks metadata files")

    except Exception as e:
        logger.error(f"Error generating Databricks metadata: {str(e)}", exc_info=True)
        raise


def format_databricks_table_card(table_data, workspace_id, region):
    """
    Format table metadata according to the schema card specification for Databricks
    
    Args:
        table_data: Dictionary containing table metadata
        workspace_id: Databricks workspace ID
        region: Databricks region
        
    Returns:
        Formatted table card dictionary
    """
    props = table_data["properties"]
    basic_info = props.get("basic_info", {})
    columns = props.get("columns", [])
    location = props.get("location", {})
    catalog_name = location.get("catalog", "")
    schema_name = location.get("schema", "")
    table_name = props.get("name", "")
    
    # Create FQTN (Fully Qualified Table Name)
    fqtn = f"databricks://{workspace_id}/{catalog_name}/{schema_name}/{table_name}"
    
    # Extract primary key and foreign keys from columns
    primary_key = []
    foreign_keys = []
    pii_columns = []
    
    formatted_columns = []
    for col in columns:
        col_name = col.get("name", "")
        col_type = col.get("data_type", "STRING")
        nullable = col.get("nullable", True)
        description = col.get("description", "")
        
        # Check for PII markers
        pii_type = None
        if any(keyword in col_name.lower() for keyword in ['email', 'phone', 'ssn', 'customer_id', 'user_id']):
            pii_type = "identifier"
            pii_columns.append(col_name)
        
        formatted_col = {
            "name": col_name,
            "type": col_type,
            "nullable": nullable,
            "description": description
        }
        
        if pii_type:
            formatted_col["pii"] = pii_type
            formatted_col["mask"] = "hash(token)"
        
        # Add quality checks for numeric columns
        if any(numeric_type in col_type.upper() for numeric_type in ['DECIMAL', 'DOUBLE', 'FLOAT', 'INT', 'BIGINT']):
            if "amount" in col_name.lower() or "price" in col_name.lower():
                formatted_col["quality"] = ["non_negative"]
        
        formatted_columns.append(formatted_col)
        
        # Simple heuristic for primary key detection
        if col_name.lower().endswith("_id") and not nullable:
            if table_name.lower() in col_name.lower():
                primary_key.append(col_name)
        
        # Simple heuristic for foreign key detection
        if col_name.lower().endswith("_id") and col_name not in primary_key:
            # Guess the referenced table
            ref_table = col_name.lower().replace("_id", "s")  # customer_id -> customers
            foreign_keys.append({
                "columns": [col_name],
                "ref": f"databricks://{workspace_id}/{catalog_name}/{schema_name}/{ref_table}({col_name})"
            })
    
    # Determine domain based on table name and columns
    domain = "general"
    table_lower = table_name.lower()
    if any(keyword in table_lower for keyword in ['order', 'sale', 'revenue', 'payment']):
        domain = "revenue"
    elif any(keyword in table_lower for keyword in ['customer', 'user', 'account']):
        domain = "customer"
    elif any(keyword in table_lower for keyword in ['product', 'inventory', 'catalog']):
        domain = "product"
    elif any(keyword in table_lower for keyword in ['log', 'event', 'audit']):
        domain = "analytics"
    
    # Generate tags based on table characteristics
    tags = []
    if len(foreign_keys) > 2:
        tags.append("fact")
    elif len(foreign_keys) <= 1:
        tags.append("dimension")
    
    if pii_columns:
        tags.append("pii-light")
    
    if domain != "general":
        tags.append(domain)
    
    # Create the schema card
    card = {
        "version": "1.0",
        "provider": "databricks",
        "dialect": "databricks",
        "address": {
            "account": None,
            "region": region,
            "database": None,
            "schema": schema_name,
            "catalog": catalog_name,
            "project": None,
            "dataset": None,
            "workspace": workspace_id
        },
        "fqtn": fqtn,
        "domain": domain,
        "kind": basic_info.get("table_type", "table").lower(),
        "owner": basic_info.get("owner", "unknown@company.com"),
        "freshness_hours": 24,  # Default assumption
        "row_count": basic_info.get("row_count", 0),
        "primary_key": primary_key,
        "foreign_keys": foreign_keys,
        "tags": tags,
        "columns": formatted_columns,
        "join_hints": [],  # Will be populated if we detect relationships
        "semantics": {
            "grain": primary_key if primary_key else [formatted_columns[0]["name"]] if formatted_columns else [],
            "dimensions": [col["name"] for col in formatted_columns if col["name"] not in primary_key and not any(kw in col["name"].lower() for kw in ['amount', 'count', 'total'])],
            "measures": []
        },
        "safety": {
            "pii_columns": pii_columns,
            "default_masking": len(pii_columns) > 0
        },
        "lineage": {
            "upstream": [],
            "downstream": []
        },
        "notes": []
    }
    
    # Add measures to semantics
    for col in formatted_columns:
        if any(kw in col["name"].lower() for kw in ['amount', 'total', 'count', 'sum', 'revenue']):
            measure_name = col["name"].replace("_", " ").title()
            card["semantics"]["measures"].append({
                "name": measure_name,
                "expr": f"SUM({col['name']})"
            })
    
    # Add join hints for foreign keys
    for fk in foreign_keys:
        ref_table = fk["ref"].split("(")[0]  # Extract table name from reference
        card["join_hints"].append({
            "to": ref_table,
            "on": [f"{fk['columns'][0]} = {ref_table.split('/')[-1]}.{fk['columns'][0]}"],
            "cardinality": "M:1",
            "preferred": True
        })
    
    return card


def process_databricks_catalogs_and_tables(project, metadata_dir, providers_dir, tables_dir, max_tables_per_schema=100, target_catalogs=None, target_schemas=None, databricks_config=None, output_format="json"):
    """
    Process Databricks catalogs, schemas and tables to generate metadata files using native Databricks client
    
    Args:
        project: Project configuration
        metadata_dir: Base metadata directory
        providers_dir: Provider-specific directory
        tables_dir: Tables directory
        max_tables_per_schema: Maximum number of tables to process per schema
        target_catalogs: Optional list of specific catalog names to process
        target_schemas: Optional list of specific schema names to process
        databricks_config: Dictionary containing Databricks connection credentials
        output_format: Format of output files
    """
    try:
        if not DATABRICKS_AVAILABLE:
            logger.error("Databricks SQL client library not available. Cannot process Databricks metadata.")
            return

        # Get workspace information from databricks_config
        if not databricks_config:
            logger.error("No Databricks configuration provided")
            return

        workspace_id = os.getenv("DATABRICKS_WORKSPACE_ID", "ws-prod")
        region = os.getenv("DATABRICKS_REGION", "us-west-2")
        
        logger.info(f"Processing Databricks workspace: {workspace_id} in region: {region}")
        
        # Create Databricks client
        connection = setup_databricks_client(databricks_config)
        if not connection:
            logger.error("Failed to create Databricks client")
            return

        # Test Databricks connection
        if not test_databricks_connection(connection):
            logger.error("Databricks connection test failed")
            connection.close()
            return

        # Get all catalogs using native Databricks client
        cursor = connection.cursor()
        cursor.execute("SHOW CATALOGS")
        catalog_rows = cursor.fetchall()
        
        catalogs = []
        for row in catalog_rows:
            catalog_name = row[0]  # First column is catalog name
            
            # Filter catalogs if target_catalogs is provided
            if target_catalogs and catalog_name not in target_catalogs:
                continue
            
            catalogs.append({"catalog": catalog_name})
        
        cursor.close()
        
        if not catalogs:
            logger.warning("No catalogs found to process")
            connection.close()
            return

        total_catalogs = len(catalogs)
        logger.info(f"Found {total_catalogs} catalogs to process")
        
        # Create provider overview
        provider_overview = {
            "version": "1.0",
            "provider": "databricks",
            "workspace_id": workspace_id,
            "region": region,
            "total_catalogs": total_catalogs,
            "connection_info": {
                "authentication": "token",
                "cluster_type": "interactive",
                "runtime_version": "13.3.x-scala2.12"
            },
            "capabilities": {
                "unity_catalog": True,
                "delta_lake": True,
                "ml": True,
                "streaming": True,
                "auto_loader": True
            },
            "generated_at": datetime.datetime.now().isoformat()
        }
        
        # Write provider overview
        with open(os.path.join(providers_dir, "provider_overview.json"), 'w') as f:
            json.dump(provider_overview, f, indent=2, default=str)
        
        # Process catalogs and tables
        all_table_cards = []
        manifest_entries = []
        total_tables_processed = 0
        
        max_workers = min(3, total_catalogs)  # Limit concurrent workers for Databricks
        
        def process_catalog(catalog_row):
            """Process a single catalog and its schemas/tables"""
            try:
                catalog_name = catalog_row["catalog"]
                logger.info(f"Processing catalog: {catalog_name}")
                
                # Create catalog directory
                catalog_dir = os.path.join(tables_dir, workspace_id, catalog_name)
                os.makedirs(catalog_dir, exist_ok=True)
                
                # Get schemas in this catalog using native client
                cursor = connection.cursor()
                cursor.execute(f"SHOW SCHEMAS IN {catalog_name}")
                schema_rows = cursor.fetchall()
                
                catalog_cards = []
                tables_processed_in_catalog = 0
                
                for schema_row in schema_rows:
                    schema_name = schema_row[0]  # First column is schema name
                    
                    # Filter schemas if target_schemas is provided
                    if target_schemas and schema_name not in target_schemas:
                        continue
                    
                    # Skip system schemas
                    if schema_name.lower() in ['information_schema', 'default']:
                        continue
                    
                    try:
                        # Create schema directory
                        schema_dir = os.path.join(catalog_dir, schema_name)
                        os.makedirs(schema_dir, exist_ok=True)

                        # Get tables in schema
                        cursor.execute(f"SHOW TABLES IN {catalog_name}.{schema_name}")
                        table_rows = cursor.fetchall()

                        # Get views in schema
                        view_rows = []
                        try:
                            cursor.execute(f"SHOW VIEWS IN {catalog_name}.{schema_name}")
                            view_rows = cursor.fetchall()
                        except Exception as e:
                            logger.warning(f"Could not fetch views for schema {catalog_name}.{schema_name}: {e}")

                        # Combine tables and views
                        all_rows = [(row, "TABLE") for row in table_rows] + [(row, "VIEW") for row in view_rows]

                        schema_table_count = 0
                        for table_row, object_type in all_rows:
                            if schema_table_count >= max_tables_per_schema:
                                break

                            table_name = table_row[1]  # Second column is table/view name
                            full_table_name = f"{catalog_name}.{schema_name}.{table_name}"
                            
                            try:
                                # Get table details
                                cursor.execute(f"DESCRIBE TABLE EXTENDED {full_table_name}")
                                table_detail_rows = cursor.fetchall()
                                
                                # Parse table details
                                columns = []
                                table_info = {}
                                
                                for detail_row in table_detail_rows:
                                    col_name = detail_row[0] if detail_row[0] else ""
                                    data_type = detail_row[1] if detail_row[1] else ""
                                    comment = detail_row[2] if len(detail_row) > 2 and detail_row[2] else ""
                                    
                                    # Skip metadata rows
                                    if col_name.startswith("#") or col_name == "":
                                        continue
                                    
                                    # Check if this is table metadata
                                    if col_name in ["Owner", "Created Time", "Last Access", "Type"]:
                                        table_info[col_name.lower().replace(" ", "_")] = data_type
                                        continue
                                    
                                    # This is a column
                                    column_info = {
                                        "name": col_name,
                                        "data_type": data_type,
                                        "nullable": True,  # Default assumption
                                        "description": comment or ""
                                    }
                                    columns.append(column_info)
                                
                                # Build table data structure
                                table_data = {
                                    "entity": "table",
                                    "properties": {
                                        "name": table_name,
                                        "full_name": full_table_name,
                                        "location": {
                                            "workspace": workspace_id,
                                            "catalog": catalog_name,
                                            "schema": schema_name
                                        },
                                        "basic_info": {
                                            "table_type": object_type,
                                            "created_date": table_info.get("created_time", ""),
                                            "owner": table_info.get("owner", ""),
                                            "comment": "",
                                            "row_count": 0 if object_type == "VIEW" else 0  # Would need separate query to get accurate count
                                        },
                                        "columns": columns
                                    }
                                }
                                
                                # Generate schema card
                                table_card = format_databricks_table_card(table_data, workspace_id, region)
                                
                                # Write individual table card
                                table_file = os.path.join(schema_dir, f"{table_name}.json")
                                with open(table_file, 'w') as f:
                                    json.dump(table_card, f, indent=2, default=str)
                                
                                # Calculate file size and hash
                                file_stats = os.stat(table_file)
                                with open(table_file, 'rb') as f:
                                    file_hash = hashlib.sha256(f.read()).hexdigest()
                                
                                # Add to manifest
                                manifest_entry = {
                                    "fqtn": table_card["fqtn"],
                                    "provider": "databricks",
                                    "dialect": "databricks",
                                    "path": os.path.relpath(table_file, metadata_dir),
                                    "size_bytes": file_stats.st_size,
                                    "hash": f"sha256:{file_hash}",
                                    "row_count": table_card["row_count"]
                                }
                                
                                catalog_cards.append(table_card)
                                manifest_entries.append(manifest_entry)
                                schema_table_count += 1
                                tables_processed_in_catalog += 1
                                
                                logger.debug(f"  Processed table {full_table_name}")
                                
                            except Exception as e:
                                logger.warning(f"Could not process table {full_table_name}: {e}")
                                continue
                        
                        logger.info(f"  Schema {schema_name}: {schema_table_count} tables processed")
                        
                    except Exception as e:
                        logger.warning(f"Could not process schema {schema_name} in catalog {catalog_name}: {e}")
                        continue
                
                cursor.close()
                logger.info(f"✓ Completed catalog {catalog_name}: {tables_processed_in_catalog} tables processed")
                return catalog_cards, tables_processed_in_catalog
                
            except Exception as e:
                logger.error(f"✗ Failed to process catalog {catalog_name}: {e}")
                return [], 0
        
        # Execute parallel processing
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_catalog = {
                executor.submit(process_catalog, catalog_row): catalog_row["catalog"]
                for catalog_row in catalogs
            }
            
            for future in as_completed(future_to_catalog):
                catalog_name = future_to_catalog[future]
                try:
                    catalog_cards, tables_count = future.result()
                    all_table_cards.extend(catalog_cards)
                    total_tables_processed += tables_count
                except Exception as e:
                    logger.error(f"Catalog {catalog_name} generated an exception: {e}")
        
        # Close Databricks connection
        connection.close()
        
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
                "databricks": {
                    "workspace_count": 1,
                    "catalog_count": total_catalogs,
                    "table_count": total_tables_processed,
                    "regions": [region]
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
        
        logger.info(f"Databricks metadata generation completed! Processed {total_catalogs} catalogs with {total_tables_processed} total tables")
        logger.info(f"Files saved to: {metadata_dir}")
        
    except Exception as e:
        logger.error(f"Error processing Databricks catalogs and tables: {str(e)}", exc_info=True)
        raise