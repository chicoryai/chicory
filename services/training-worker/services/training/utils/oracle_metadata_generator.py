import json
import os
import datetime
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from services.integration.sqlalchemy_engine import run_query
from services.utils.logger import logger


def generate_oracle_overview(base_dir, project, dest_folder, oracle_schemas, target_schemas=None, output_format="json"):
    """
    Generate comprehensive Oracle database and table metadata files
    
    Args:
        base_dir: Base directory path
        project: Project configuration
        dest_folder: Destination folder for output files
        oracle_schemas: Oracle schemas configuration
        target_schemas: Optional list of specific schema names to process. If None, processes all schemas.
        output_format: Format of output files. Options: "json" (default), "text" (human-readable for RAG), or "both".
    """
    try:
        logger.info("Starting generation of Oracle metadata...")
        
        # Create directory structure
        metadata_dir = os.path.join(dest_folder, "database_metadata")
        providers_dir = os.path.join(metadata_dir, "providers", "oracle")
        tables_dir = os.path.join(providers_dir, "tables")
        
        os.makedirs(metadata_dir, exist_ok=True)
        os.makedirs(providers_dir, exist_ok=True)
        os.makedirs(tables_dir, exist_ok=True)
        
        # Process schemas and tables
        process_oracle_schemas_and_tables(
            project, 
            metadata_dir, 
            providers_dir, 
            tables_dir,
            oracle_schemas, 
            target_schemas=target_schemas, 
            output_format=output_format
        )
        
        logger.info("Successfully generated all Oracle metadata files")

    except Exception as e:
        logger.error(f"Error generating Oracle metadata: {str(e)}", exc_info=True)
        raise


def format_oracle_table_card(table_data, instance_name, region):
    """
    Format table metadata according to the schema card specification for Oracle
    
    Args:
        table_data: Dictionary containing table metadata
        instance_name: Oracle instance/SID name
        region: Oracle region/location
        
    Returns:
        Formatted table card dictionary
    """
    props = table_data["properties"]
    basic_info = props.get("basic_info", {})
    columns = props.get("columns", [])
    location = props.get("location", {})
    schema_name = location.get("schema", "")
    table_name = props.get("name", "")
    
    # Create FQTN (Fully Qualified Table Name)
    fqtn = f"oracle://{instance_name}/{schema_name}/{table_name}"
    
    # Extract primary key and foreign keys from columns
    primary_key = []
    foreign_keys = []
    pii_columns = []
    
    formatted_columns = []
    for col in columns:
        col_name = col.get("name", "")
        col_type = col.get("data_type", "VARCHAR2")
        nullable = col.get("nullable", True)
        description = col.get("description", "")
        is_pk = col.get("primary_key", False)
        
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
        if any(numeric_type in col_type.upper() for numeric_type in ['NUMBER', 'DECIMAL', 'FLOAT', 'INTEGER']):
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
                "ref": f"oracle://{instance_name}/{schema_name}/{ref_table}({col_name})"
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
        "provider": "oracle",
        "dialect": "oracle",
        "address": {
            "account": instance_name,
            "region": region,
            "database": instance_name,
            "schema": schema_name,
            "catalog": None,
            "project": None,
            "dataset": None
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


def process_oracle_schemas_and_tables(project, metadata_dir, providers_dir, tables_dir, oracle_schemas, max_tables_per_schema=100, target_schemas=None, output_format="json"):
    """
    Process Oracle schemas and tables to generate metadata files
    
    Args:
        project: Project configuration
        metadata_dir: Base metadata directory
        providers_dir: Provider-specific directory
        tables_dir: Tables directory
        oracle_schemas: Oracle schemas configuration
        max_tables_per_schema: Maximum number of tables to process per schema
        target_schemas: Optional list of specific schema names to process
        output_format: Format of output files
    """
    try:
        # Get instance information
        instance_query = """
        SELECT 
            instance_name,
            host_name,
            version
        FROM 
            v$instance
        """
        
        instance_info = run_query(instance_query, "oracle", project)
        if instance_info.empty:
            logger.error("Could not retrieve Oracle instance information")
            return
            
        instance_name = instance_info.iloc[0]["instance_name"]
        host_name = instance_info.iloc[0]["host_name"]
        version = instance_info.iloc[0]["version"]
        
        # Use environment variable for region or default
        region = os.getenv("ORACLE_REGION", "us-east-1")
        
        logger.info(f"Processing Oracle instance: {instance_name} on {host_name} (version {version})")
        
        # Get all schemas (owners)
        schemas_query = """
        SELECT DISTINCT 
            owner as schema_name,
            created
        FROM 
            all_tables
        WHERE 
            owner NOT IN ('SYS', 'SYSTEM', 'DBSNMP', 'SYSMAN', 'OUTLN', 'MDSYS', 'ORDSYS', 'EXFSYS', 'DMSYS', 'WMSYS', 'CTXSYS', 'XDB', 'ANONYMOUS', 'XS$NULL', 'ORACLE_OCM', 'APPQOSSYS')
        ORDER BY 
            owner
        """
        
        schemas_df = run_query(schemas_query, "oracle", project)
        
        # Filter schemas if target_schemas is provided
        if target_schemas:
            target_schemas_upper = [schema.upper() for schema in target_schemas]
            schemas_df = schemas_df[schemas_df["schema_name"].str.upper().isin(target_schemas_upper)]
            logger.info(f"Filtering to process only specified schemas: {target_schemas}")
        
        total_schemas = len(schemas_df)
        logger.info(f"Found {total_schemas} schemas to process")
        
        if total_schemas == 0:
            logger.warning("No schemas found to process")
            return
        
        # Create provider overview
        provider_overview = {
            "version": "1.0",
            "provider": "oracle",
            "instance_name": instance_name,
            "host_name": host_name,
            "version": version,
            "region": region,
            "total_schemas": total_schemas,
            "connection_info": {
                "authentication": "username_password",
                "connection_type": "direct"
            },
            "capabilities": {
                "partitioning": True,
                "parallel_query": True,
                "materialized_views": True,
                "analytics": True,
                "json": "12c+" in version
            },
            "generated_at": datetime.datetime.now().isoformat()
        }
        
        # Write provider overview
        with open(os.path.join(providers_dir, "provider_overview.json"), 'w') as f:
            json.dump(provider_overview, f, indent=2, default=str)
        
        # Process schemas and tables
        all_table_cards = []
        manifest_entries = []
        total_tables_processed = 0
        
        max_workers = min(3, total_schemas)  # Limit concurrent workers for Oracle
        
        def process_schema(schema_row):
            """Process a single schema and its tables"""
            try:
                schema_name = schema_row["schema_name"]
                logger.info(f"Processing schema: {schema_name}")
                
                # Create schema directory
                schema_dir = os.path.join(tables_dir, instance_name, schema_name)
                os.makedirs(schema_dir, exist_ok=True)
                
                # Get tables in schema
                tables_query = f"""
                SELECT
                    table_name,
                    tablespace_name,
                    created,
                    num_rows,
                    blocks,
                    avg_row_len,
                    'TABLE' as object_type
                FROM
                    all_tables
                WHERE
                    owner = '{schema_name}'
                """

                # Get views in schema
                views_query = f"""
                SELECT
                    view_name as table_name,
                    NULL as tablespace_name,
                    NULL as created,
                    NULL as num_rows,
                    NULL as blocks,
                    NULL as avg_row_len,
                    'VIEW' as object_type
                FROM
                    all_views
                WHERE
                    owner = '{schema_name}'
                """

                # Combine tables and views
                combined_query = f"""
                ({tables_query})
                UNION ALL
                ({views_query})
                ORDER BY created DESC NULLS LAST
                FETCH FIRST {max_tables_per_schema} ROWS ONLY
                """

                try:
                    tables_df = run_query(combined_query, "oracle", project)
                except Exception as e:
                    logger.warning(f"Could not fetch views for schema {schema_name}, falling back to tables only: {e}")
                    # Fallback to tables only
                    tables_query_with_limit = tables_query + f" ORDER BY created DESC FETCH FIRST {max_tables_per_schema} ROWS ONLY"
                    tables_df = run_query(tables_query_with_limit, "oracle", project)

                schema_cards = []
                tables_processed_in_schema = 0

                for _, table_row in tables_df.iterrows():
                    table_name = table_row["table_name"]
                    object_type = table_row.get("object_type", "TABLE")
                    
                    try:
                        # Get column information
                        columns_query = f"""
                        SELECT 
                            c.column_name,
                            c.data_type,
                            c.data_length,
                            c.data_precision,
                            c.data_scale,
                            c.nullable,
                            c.data_default,
                            cc.comments as description,
                            CASE WHEN pk.column_name IS NOT NULL THEN 'Y' ELSE 'N' END as is_primary_key
                        FROM 
                            all_tab_columns c
                            LEFT JOIN all_col_comments cc ON c.owner = cc.owner AND c.table_name = cc.table_name AND c.column_name = cc.column_name
                            LEFT JOIN (
                                SELECT acc.owner, acc.table_name, acc.column_name
                                FROM all_cons_columns acc
                                JOIN all_constraints ac ON acc.owner = ac.owner AND acc.constraint_name = ac.constraint_name
                                WHERE ac.constraint_type = 'P'
                            ) pk ON c.owner = pk.owner AND c.table_name = pk.table_name AND c.column_name = pk.column_name
                        WHERE 
                            c.owner = '{schema_name}' 
                            AND c.table_name = '{table_name}'
                        ORDER BY 
                            c.column_id
                        """
                        
                        columns_df = run_query(columns_query, "oracle", project)
                        
                        columns = []
                        for _, col_row in columns_df.iterrows():
                            # Format Oracle data type
                            data_type = col_row["data_type"]
                            if col_row["data_precision"] and col_row["data_scale"] is not None:
                                data_type += f"({col_row['data_precision']},{col_row['data_scale']})"
                            elif col_row["data_length"] and data_type in ['VARCHAR2', 'CHAR', 'NVARCHAR2', 'NCHAR']:
                                data_type += f"({col_row['data_length']})"
                            
                            column_info = {
                                "name": col_row["column_name"],
                                "data_type": data_type,
                                "nullable": col_row["nullable"] == "Y",
                                "description": col_row.get("description", "") or "",
                                "primary_key": col_row["is_primary_key"] == "Y"
                            }
                            columns.append(column_info)
                        
                        # Get table comments
                        table_comment_query = f"""
                        SELECT comments
                        FROM all_tab_comments
                        WHERE owner = '{schema_name}' AND table_name = '{table_name}'
                        """
                        
                        table_comment_df = run_query(table_comment_query, "oracle", project)
                        table_comment = ""
                        if not table_comment_df.empty and table_comment_df.iloc[0]["comments"]:
                            table_comment = table_comment_df.iloc[0]["comments"]
                        
                        # Build table data structure
                        table_data = {
                            "entity": "table",
                            "properties": {
                                "name": table_name,
                                "full_name": f"{schema_name}.{table_name}",
                                "location": {
                                    "instance": instance_name,
                                    "schema": schema_name
                                },
                                "basic_info": {
                                    "table_type": object_type,
                                    "created_date": table_row["created"].strftime("%Y-%m-%d") if table_row.get("created") and table_row["created"] else None,
                                    "owner": schema_name,
                                    "comment": table_comment,
                                    "row_count": table_row.get("num_rows", 0) or 0 if object_type == "TABLE" else 0,
                                    "tablespace": table_row.get("tablespace_name", "") if object_type == "TABLE" else ""
                                },
                                "columns": columns
                            }
                        }
                        
                        # Generate schema card
                        table_card = format_oracle_table_card(table_data, instance_name, region)
                        
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
                            "provider": "oracle",
                            "dialect": "oracle",
                            "path": os.path.relpath(table_file, metadata_dir),
                            "size_bytes": file_stats.st_size,
                            "hash": f"sha256:{file_hash}",
                            "row_count": table_card["row_count"],
                            "freshness_hours": table_card["freshness_hours"],
                            "domain": table_card["domain"],
                            "tags": table_card["tags"]
                        }
                        
                        schema_cards.append(table_card)
                        manifest_entries.append(manifest_entry)
                        tables_processed_in_schema += 1
                        
                        logger.debug(f"  Processed table {table_name}")
                        
                    except Exception as e:
                        logger.warning(f"Could not process table {table_name} in schema {schema_name}: {e}")
                        continue
                
                logger.info(f"✓ Completed schema {schema_name}: {tables_processed_in_schema} tables processed")
                return schema_cards, tables_processed_in_schema
                
            except Exception as e:
                logger.error(f"✗ Failed to process schema {schema_name}: {e}")
                return [], 0
        
        # Execute parallel processing
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_schema = {
                executor.submit(process_schema, schema_row): schema_row["schema_name"]
                for _, schema_row in schemas_df.iterrows()
            }
            
            for future in as_completed(future_to_schema):
                schema_name = future_to_schema[future]
                try:
                    schema_cards, tables_count = future.result()
                    all_table_cards.extend(schema_cards)
                    total_tables_processed += tables_count
                except Exception as e:
                    logger.error(f"Schema {schema_name} generated an exception: {e}")
        
        # Write manifest.json
        manifest = {
            "version": "1.0",
            "tables": manifest_entries
        }
        
        with open(os.path.join(providers_dir, "manifest.json"), 'w') as f:
            json.dump(manifest, f, indent=2, default=str)
        
        # Generate relationships.json (basic version)
        relationships = {
            "version": "1.0",
            "edges": []
        }
        
        # Extract relationships from join hints
        for card in all_table_cards:
            for hint in card.get("join_hints", []):
                relationship = {
                    "from": card["fqtn"],
                    "to": hint["to"],
                    "on": hint["on"],
                    "cardinality": hint["cardinality"],
                    "confidence": 0.8,  # Heuristic confidence
                    "preferred": hint.get("preferred", False)
                }
                relationships["edges"].append(relationship)
        
        with open(os.path.join(metadata_dir, "relationships.json"), 'w') as f:
            json.dump(relationships, f, indent=2, default=str)
        
        # Write database_overview.json
        database_overview = {
            "version": "1.0",
            "providers": {
                "oracle": {
                    "instance_count": 1,
                    "schema_count": total_schemas,
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
        
        logger.info(f"Oracle metadata generation completed! Processed {total_schemas} schemas with {total_tables_processed} total tables")
        logger.info(f"Files saved to: {metadata_dir}")
        
    except Exception as e:
        logger.error(f"Error processing Oracle schemas and tables: {str(e)}", exc_info=True)
        raise