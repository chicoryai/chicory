import json
import os
import datetime
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from services.utils.logger import logger
import logging

# Configure Snowflake logging to reduce verbosity
logging.getLogger('snowflake.connector').setLevel(logging.WARNING)
logging.getLogger('snowflake.connector.network').setLevel(logging.WARNING)
logging.getLogger('snowflake.connector.ocsp_snowflake').setLevel(logging.WARNING)

# Try to import Snowflake connector library directly
try:
    import snowflake.connector
    from snowflake.connector import connect
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    SNOWFLAKE_AVAILABLE = True
except ImportError:
    logger.warning("Snowflake connector library not available. Install with: pip install snowflake-connector-python")
    SNOWFLAKE_AVAILABLE = False


def setup_snowflake_client(snowflake_config):
    """
    Set up Snowflake client from configuration

    Args:
        snowflake_config: Dictionary containing Snowflake connection configuration

    Returns:
        Snowflake connection instance
    """
    if not SNOWFLAKE_AVAILABLE:
        raise ImportError("Snowflake connector library not installed")

    if not snowflake_config:
        return None

    try:
        # Ensure we have all required fields for Snowflake connection
        required_fields = ['account', 'user', 'warehouse']
        missing_fields = [field for field in required_fields if not snowflake_config.get(field)]

        if missing_fields:
            logger.error(f"Missing required Snowflake config fields: {missing_fields}")
            return None

        # Set up connection parameters
        conn_params = {
            'account': snowflake_config['account'],
            'user': snowflake_config['user'],
            'warehouse': snowflake_config.get('warehouse'),
            'database': snowflake_config.get('database', 'INFORMATION_SCHEMA'),
            'schema': snowflake_config.get('schema', 'PUBLIC')
        }

        # Handle authentication - support both password and key pair
        if snowflake_config.get('password'):
            conn_params['password'] = snowflake_config['password']
        elif snowflake_config.get('private_key'):
            # Handle private key authentication
            try:
                private_key_content = snowflake_config['private_key']

                # If the key is stored as a single line with \n escaped, convert it back
                if isinstance(private_key_content, str):
                    # Replace literal \n with actual newlines
                    private_key_content = private_key_content.replace('\\n', '\n')
                    private_key_content = private_key_content.encode('utf-8')

                # Handle passphrase
                passphrase = None
                if snowflake_config.get('private_key_passphrase'):
                    passphrase = snowflake_config['private_key_passphrase'].encode('utf-8')

                # Load the private key
                private_key = load_pem_private_key(
                    private_key_content,
                    password=passphrase
                )

                # Convert to DER format for Snowflake connector
                pkb = private_key.private_bytes(
                    encoding=serialization.Encoding.DER,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                )
                conn_params['private_key'] = pkb
                logger.info("Private key authentication configured successfully")

            except Exception as e:
                logger.error(f"Failed to process private key: {e}")
                logger.error("Ensure private key is in valid PEM format. For .env files, use format: '-----BEGIN PRIVATE KEY-----\\nMII...\\n-----END PRIVATE KEY-----'")
                return None
        else:
            logger.error("No authentication method provided (password or private_key)")
            return None

        # Add optional parameters
        if snowflake_config.get('role'):
            conn_params['role'] = snowflake_config['role']

        # Add query tag for monitoring
        conn_params['session_parameters'] = {
            'QUERY_TAG': "Chicory-Scan"
        }

        # Create Snowflake connection
        conn = connect(**conn_params)
        
        logger.info(f"Snowflake client created for account: {snowflake_config['account']}")
        return conn

    except Exception as e:
        logger.error(f"Failed to create Snowflake client: {e}")
        return None


def test_snowflake_connection(conn, account_name):
    """
    Test Snowflake connection with a simple query

    Args:
        conn: Snowflake connection instance
        account_name: Account name for testing

    Returns:
        True if connection successful, False otherwise
    """
    try:
        # Simple test query
        cursor = conn.cursor()
        cursor.execute("SELECT CURRENT_ACCOUNT(), CURRENT_REGION()")
        results = cursor.fetchall()
        cursor.close()

        if results and len(results) > 0:
            logger.info("Snowflake connection test successful")
            return True
        else:
            logger.error("Snowflake connection test failed - no results returned")
            return False

    except Exception as e:
        logger.error(f"Snowflake connection test failed: {str(e)}")
        error_msg = str(e).lower()

        if "authentication" in error_msg or "invalid" in error_msg:
            logger.error("Authentication issue detected. Please verify:")
            logger.error("1. Account name, user, and credentials are correct")
            logger.error("2. User has appropriate permissions")
            logger.error("3. Private key format is correct (if using key pair auth)")
        elif "permission" in error_msg or "access" in error_msg:
            logger.error("Permission issue detected. Please verify:")
            logger.error("1. User has required roles and permissions")
            logger.error("2. Warehouse access is granted")
            logger.error("3. Database and schema permissions are correct")
        elif "not found" in error_msg or "does not exist" in error_msg:
            logger.error("Resource not found. Please verify:")
            logger.error("1. Account name is correct")
            logger.error("2. Warehouse, database, and schema exist")
            logger.error("3. Resources are accessible to the user")

        return False


def get_databases_using_client(conn, target_databases=None):
    """
    Get databases using Snowflake client

    Args:
        conn: Snowflake connection instance
        target_databases: Optional list of specific database names to process

    Returns:
        List of database information
    """
    try:
        databases = []
        cursor = conn.cursor()
        
        # Get all databases
        cursor.execute("SHOW DATABASES")
        results = cursor.fetchall()
        
        for row in results:
            # Snowflake SHOW DATABASES returns: name, created_on, is_default, is_current, database_owner, comment, options, retention_time
            database_name = row[1]
            
            # Filter databases if target_databases is provided
            if target_databases and database_name.upper() not in [db.upper() for db in target_databases]:
                continue
            
            database_info = {
                "database_name": database_name,
                "created_on": row[0] if len(row) > 1 else None,
                "role": row[5] if len(row) > 4 else ""
            }
            
            databases.append(database_info)
        
        cursor.close()
        logger.info(f"Found {len(databases)} databases")
        return databases

    except Exception as e:
        logger.error(f"Error getting databases: {str(e)}")
        return []


def get_schemas_using_client(conn, database_name, target_schemas=None):
    """
    Get schemas in a database using Snowflake client

    Args:
        conn: Snowflake connection instance
        database_name: Database name
        target_schemas: Optional list of specific schema names to process

    Returns:
        List of schema information
    """
    try:
        schemas = []
        cursor = conn.cursor()
        
        # Get schemas in database
        cursor.execute(f"SHOW SCHEMAS IN DATABASE {database_name}")
        results = cursor.fetchall()
        
        for row in results:
            schema_name = row[1]  # Schema name is in the second column
            
            # Skip system schemas
            if schema_name.upper() in ['INFORMATION_SCHEMA']:
                continue
                
            # Filter schemas if target_schemas is provided
            if target_schemas and schema_name.upper() not in [s.upper() for s in target_schemas]:
                continue
            
            schema_info = {
                "schema_name": schema_name,
                "created_on": row[0] if len(row) > 0 else None,
                "database_name": row[4] if len(row) > 3 else "",
                "role": row[5] if len(row) > 3 else "",
            }
            
            schemas.append(schema_info)
        
        cursor.close()
        logger.info(f"Found {len(schemas)} schemas in database {database_name}")
        return schemas

    except Exception as e:
        logger.error(f"Error getting schemas for database {database_name}: {str(e)}")
        return []


def get_tables_using_client(conn, database_name, schema_name, max_tables=100):
    """
    Get tables and views in a schema using Snowflake client

    Args:
        conn: Snowflake connection instance
        database_name: Database name
        schema_name: Schema name
        max_tables: Maximum number of tables to process

    Returns:
        List of table and view information
    """
    try:
        tables = []
        cursor = conn.cursor()

        # Get tables in schema
        cursor.execute(f"SHOW TABLES IN SCHEMA {database_name}.{schema_name}")
        table_results = cursor.fetchall()

        # Get views in schema
        try:
            cursor.execute(f"SHOW VIEWS IN SCHEMA {database_name}.{schema_name}")
            view_results = cursor.fetchall()
        except Exception as e:
            logger.warning(f"Could not fetch views for schema {database_name}.{schema_name}: {e}")
            view_results = []

        # Combine tables and views
        all_results = [(row, "TABLE") for row in table_results] + [(row, "VIEW") for row in view_results]

        processed_items = 0
        for row, object_type in all_results:
            if processed_items >= max_tables:
                break

            object_name = row[1]  # Object name is in the second column
            full_object_name = f"{database_name}.{schema_name}.{object_name}"

            try:
                # Get object columns
                cursor.execute(f"DESCRIBE {'VIEW' if object_type == 'VIEW' else 'TABLE'} {full_object_name}")
                columns_results = cursor.fetchall()

                columns = []
                for col_row in columns_results:
                    column_info = {
                        "name": col_row[0],
                        "data_type": col_row[1],
                        "nullable": col_row[3] == "Y",
                        "primary_key": col_row[5] == "Y" if len(col_row) > 5 and object_type != "VIEW" else False,
                        "unique_key": col_row[6] == "Y" if len(col_row) > 6 and object_type != "VIEW" else False,
                        "description": col_row[9] if len(col_row) > 9 and col_row[9] else "",
                    }
                    columns.append(column_info)

                table_info = {
                    "table_name": object_name,
                    "table_type": object_type,
                    "created_on": row[0] if len(row) > 0 else None,
                    "row_count": row[7] if len(row) > 7 and row[7] is not None and object_type != "VIEW" else 0,
                    "role": row[9] if len(row) > 6 else "",
                    "columns": columns
                }

                tables.append(table_info)
                processed_items += 1
            except Exception as e:
                logger.warning(f"Could not process {object_type.lower()} {full_object_name}: {e}")
                continue

        cursor.close()
        logger.info(f"Found {len(tables)} tables/views in schema {database_name}.{schema_name}")
        return tables

    except Exception as e:
        logger.error(f"Error getting tables/views for schema {database_name}.{schema_name}: {str(e)}")
        return []


def generate_snowflake_overview(base_dir, project, dest_folder, snowflake_config, target_databases=None,
                                target_schemas=None, output_format="json"):
    """
    Generate comprehensive Snowflake database and table metadata files using the unified schema card format

    Args:
        base_dir: Base directory path
        project: Project configuration (project name string)
        dest_folder: Destination folder for output files
        snowflake_config: Snowflake Configuration
        target_databases: Optional list of specific database names to process. If None, processes all databases.
        target_schemas: Optional list of specific schema names to process. If None, processes all schemas.
        output_format: Format of output files. Options: "json" (default), "text" (human-readable for RAG), or "both".
    """
    try:
        logger.info("Starting generation of Snowflake metadata...")

        # Create directory structure
        metadata_dir = os.path.join(dest_folder, "database_metadata")
        providers_dir = os.path.join(metadata_dir, "providers", "snowflake")
        tables_dir = os.path.join(providers_dir, "tables")

        os.makedirs(metadata_dir, exist_ok=True)
        os.makedirs(providers_dir, exist_ok=True)
        os.makedirs(tables_dir, exist_ok=True)

        # Process databases and tables
        process_snowflake_databases_and_tables(
            project,
            metadata_dir,
            providers_dir,
            tables_dir,
            target_databases=target_databases,
            target_schemas=target_schemas,
            snowflake_config=snowflake_config,
            output_format=output_format
        )

        logger.info("Successfully generated all Snowflake metadata files")

    except Exception as e:
        logger.error(f"Error generating Snowflake metadata: {str(e)}", exc_info=True)
        raise


def format_snowflake_table_card(table_data, account_name, region):
    """
    Format table metadata according to the schema card specification for Snowflake

    Args:
        table_data: Dictionary containing table metadata
        account_name: Snowflake account name
        region: Snowflake region

    Returns:
        Formatted table card dictionary
    """
    props = table_data["properties"]
    basic_info = props.get("basic_info", {})
    columns = props.get("columns", [])
    location = props.get("location", {})
    database_name = location.get("database", "")
    schema_name = location.get("schema", "")
    table_name = props.get("name", "")

    # Create FQTN (Fully Qualified Table Name)
    fqtn = f"snowflake://{account_name}/{database_name}/{schema_name}/{table_name}"

    # Extract primary key and foreign keys from columns
    primary_key = []
    foreign_keys = []

    formatted_columns = []
    for col in columns:
        col_name = col.get("name", "")
        col_type = col.get("data_type", "STRING")
        nullable = col.get("nullable", True)
        description = col.get("description", "")
        is_pk = col.get("primary_key", False)
        is_uk = col.get("unique_key", False)

        formatted_col = {
            "name": col_name,
            "type": col_type,
            "nullable": nullable,
            "description": description
        }

        # Add quality checks for numeric columns
        if any(numeric_type in col_type.upper() for numeric_type in
               ['NUMBER', 'DECIMAL', 'DOUBLE', 'FLOAT', 'INTEGER']):
            if "amount" in col_name.lower() or "price" in col_name.lower():
                formatted_col["quality"] = ["non_negative"]

        formatted_columns.append(formatted_col)

        # Track primary keys
        if is_pk:
            primary_key.append(col_name)

        # Simple heuristic for foreign key detection
        if col_name.lower().endswith("_id") and not is_pk:
            # Guess the referenced table
            ref_table = col_name.lower().replace("_id", "s")  # customer_id -> customers
            foreign_keys.append({
                "columns": [col_name],
                "ref": f"snowflake://{account_name}/{database_name}/{schema_name}/{ref_table}({col_name})"
            })

    # Create the schema card
    card = {
        "version": "1.0",
        "provider": "snowflake",
        "dialect": "snowflake",
        "address": {
            "account": account_name,
            "region": region,
            "database": database_name,
            "schema": schema_name,
            "catalog": None,
            "project": None,
            "dataset": None
        },
        "fqtn": fqtn,
        "kind": basic_info.get("table_type", "table").lower(),
        "owner": basic_info.get("owner", "unknown@company.com"),
        "freshness_hours": 24,  # Default assumption
        "row_count": basic_info.get("row_count", 0),
        "primary_key": primary_key,
        "foreign_keys": foreign_keys,
        "columns": formatted_columns,
        "join_hints": [],  # Will be populated if we detect relationships
        "semantics": {
            "grain": primary_key if primary_key else [formatted_columns[0]["name"]] if formatted_columns else [],
            "dimensions": [col["name"] for col in formatted_columns if col["name"] not in primary_key and not any(
                kw in col["name"].lower() for kw in ['amount', 'count', 'total'])],
            "measures": []
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


def process_snowflake_databases_and_tables(project, metadata_dir, providers_dir, tables_dir,
                                           max_tables_per_database=100, target_databases=None, target_schemas=None,
                                           snowflake_config=None, output_format="json"):
    """
    Process Snowflake databases and tables to generate metadata files using native Snowflake client

    Args:
        project: Project configuration
        metadata_dir: Base metadata directory
        providers_dir: Provider-specific directory
        tables_dir: Tables directory
        max_tables_per_database: Maximum number of tables to process per database
        target_databases: Optional list of specific database names to process
        target_schemas: Optional list of specific schema names to process
        snowflake_config: Dictionary containing Snowflake connection configuration
        output_format: Format of output files
    """
    try:
        if not SNOWFLAKE_AVAILABLE:
            logger.error("Snowflake connector library not available. Cannot process Snowflake metadata.")
            return

        # Get connection configuration
        if not snowflake_config:
            logger.error("No Snowflake connection configuration provided")
            return

        logger.info(f"Processing Snowflake account: {snowflake_config.get('account', 'unknown')}")

        # Create Snowflake client
        conn = setup_snowflake_client(snowflake_config)
        if not conn:
            logger.error("Failed to create Snowflake client")
            return

        # Test Snowflake connection
        if not test_snowflake_connection(conn, snowflake_config.get('account', 'unknown')):
            logger.error("Snowflake connection test failed")
            conn.close()
            return

        # Get account information using the connection
        cursor = conn.cursor()
        cursor.execute("SELECT CURRENT_ACCOUNT(), CURRENT_REGION()")
        account_result = cursor.fetchone()
        cursor.close()
        
        if not account_result:
            logger.error("Could not retrieve Snowflake account information")
            conn.close()
            return

        account_name = account_result[0]
        region = account_result[1]
        logger.info(f"Connected to Snowflake account: {account_name} in region: {region}")

        # Get all databases using Snowflake client
        databases = get_databases_using_client(conn, target_databases)

        if not databases:
            logger.warning("No databases found to process")
            conn.close()
            return

        total_databases = len(databases)
        logger.info(f"Found {total_databases} databases to process")

        # Create provider overview
        provider_overview = {
            "version": "1.0",
            "provider": "snowflake",
            "account_name": account_name,
            "region": region,
            "total_databases": total_databases,
            "connection_info": {
                "authentication": "key_pair",
                "warehouse_type": "standard"
            },
            "capabilities": {
                "time_travel": True,
                "zero_copy_cloning": True,
                "auto_scaling": True,
                "secure_views": True,
                "data_sharing": True
            },
            "generated_at": datetime.datetime.now().isoformat()
        }

        # Write provider overview
        with open(os.path.join(providers_dir, "provider_overview.json"), 'w') as f:
            json.dump(provider_overview, f, indent=2, default=str)

        # Process databases and tables
        all_table_cards = []
        manifest_entries = []
        total_tables_processed = 0

        max_workers = min(5, total_databases)  # Limit concurrent workers for Snowflake

        def process_database(database_info):
            """Process a single database and its schemas/tables"""
            try:
                database_name = database_info["database_name"]
                logger.info(f"Processing database: {database_name}")

                # Get schemas in this database using Snowflake client
                schemas = get_schemas_using_client(conn, database_name, target_schemas)

                database_cards = []
                tables_processed_in_database = 0

                for schema_info in schemas:
                    schema_name = schema_info["schema_name"]

                    try:
                        # Create schema directory
                        schema_dir = os.path.join(tables_dir, account_name, database_name, schema_name)
                        os.makedirs(schema_dir, exist_ok=True)

                        # Get tables in schema using Snowflake client
                        tables = get_tables_using_client(conn, database_name, schema_name, max_tables_per_database - tables_processed_in_database)

                        schema_table_count = 0
                        for table_info in tables:
                            if tables_processed_in_database >= max_tables_per_database:
                                break

                            table_name = table_info["table_name"]
                            full_table_name = f"{database_name}.{schema_name}.{table_name}"

                            try:
                                # Build table data structure using the data from get_tables_using_client
                                table_data = {
                                    "entity": "table",
                                    "properties": {
                                        "name": table_name,
                                        "full_name": full_table_name,
                                        "location": {
                                            "account": account_name,
                                            "database": database_name,
                                            "schema": schema_name
                                        },
                                        "basic_info": {
                                            "table_type": table_info.get("table_type", "TABLE"),
                                            "created_date": table_info["created_on"].strftime(
                                                "%Y-%m-%d") if table_info.get("created_on") else None,
                                            "role": table_info.get("role", ""),
                                            "row_count": table_info.get("row_count", 0)
                                        },
                                        "columns": table_info.get("columns", [])
                                    }
                                }

                                # Generate schema card
                                table_card = format_snowflake_table_card(table_data, account_name, region)

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
                                    "provider": "snowflake",
                                    "dialect": "snowflake",
                                    "path": os.path.relpath(table_file, metadata_dir),
                                    "size_bytes": file_stats.st_size,
                                    "hash": f"sha256:{file_hash}",
                                    "row_count": table_card["row_count"],
                                }

                                database_cards.append(table_card)
                                manifest_entries.append(manifest_entry)
                                schema_table_count += 1
                                tables_processed_in_database += 1

                                logger.debug(f"  Processed table {full_table_name}")

                            except Exception as e:
                                logger.warning(f"Could not process table {full_table_name}: {e}")
                                continue

                        logger.info(f"  Schema {schema_name}: {schema_table_count} tables processed")

                    except Exception as e:
                        logger.warning(f"Could not process schema {schema_name} in database {database_name}: {e}")
                        continue

                logger.info(f"Completed database {database_name}: {tables_processed_in_database} tables processed")
                return database_cards, tables_processed_in_database

            except Exception as e:
                logger.error(f"Failed to process database {database_name}: {e}")
                return [], 0

        # Execute parallel processing
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_database = {
                executor.submit(process_database, database_info): database_info["database_name"]
                for database_info in databases
            }

            for future in as_completed(future_to_database):
                database_name = future_to_database[future]
                try:
                    database_cards, tables_count = future.result()
                    all_table_cards.extend(database_cards)
                    total_tables_processed += tables_count
                except Exception as e:
                    logger.error(f"Database {database_name} generated an exception: {e}")

        # Close the connection
        conn.close()

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
                "snowflake": {
                    "account_count": 1,
                    "database_count": total_databases,
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

        logger.info(
            f"Snowflake metadata generation completed! Processed {total_databases} databases with {total_tables_processed} total tables")
        logger.info(f"Files saved to: {metadata_dir}")

    except Exception as e:
        logger.error(f"Error processing Snowflake databases and tables: {str(e)}", exc_info=True)
        raise
