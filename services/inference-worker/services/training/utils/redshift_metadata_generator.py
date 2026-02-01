import json
import os
import datetime
from services.utils.logger import logger

# Try to import Redshift connector library
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    REDSHIFT_AVAILABLE = True
except ImportError:
    logger.warning("psycopg2 library not available. Install with: pip install psycopg2-binary")
    REDSHIFT_AVAILABLE = False


def setup_redshift_connection(connection_info):
    """
    Set up Redshift connection from connection info
    
    Args:
        connection_info: Dictionary containing connection details
        
    Returns:
        psycopg2 connection instance
    """
    if not REDSHIFT_AVAILABLE:
        raise ImportError("psycopg2 library not installed")
    
    if not connection_info:
        return None
    
    try:
        # Ensure we have all required fields for connection
        required_fields = ['host', 'port', 'database', 'user', 'password']
        missing_fields = [field for field in required_fields if not connection_info.get(field)]
        
        if missing_fields:
            logger.error(f"Missing required connection fields: {missing_fields}")
            return None
        
        # Create connection
        conn = psycopg2.connect(
            host=connection_info['host'],
            port=connection_info['port'],
            database=connection_info['database'],
            user=connection_info['user'],
            password=connection_info['password'],
            sslmode='prefer'
        )
        
        return conn
        
    except Exception as e:
        logger.error(f"Error creating Redshift connection: {str(e)}")
        return None


def get_schemas_using_connection(conn):
    """
    Get schemas in the database using Redshift connection
    
    Args:
        conn: psycopg2 connection instance
        
    Returns:
        List of schema information
    """
    try:
        schemas = []
        
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Query to get schema information
            cursor.execute("""
                SELECT schema_name, schema_owner
                FROM information_schema.schemata
                WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast', 'pg_temp_1', 'pg_toast_temp_1')
                ORDER BY schema_name
            """)
            
            rows = cursor.fetchall()
            
            for row in rows:
                schema_info = {
                    "schema_name": row['schema_name'],
                    "schema_owner": row['schema_owner']
                }
                schemas.append(schema_info)
        
        logger.info(f"Found {len(schemas)} schemas in database")
        return schemas
        
    except Exception as e:
        logger.error(f"Error getting schemas: {str(e)}")
        return []


def get_tables_using_connection(conn, schema_name, max_tables=100):
    """
    Get tables and views in a schema using Redshift connection

    Args:
        conn: psycopg2 connection instance
        schema_name: Schema name
        max_tables: Maximum number of tables/views to process

    Returns:
        List of table and view information
    """
    try:
        tables = []
        
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Query to get table information
            cursor.execute("""
                SELECT 
                    t.table_name,
                    t.table_type,
                    obj_description(c.oid) as table_comment
                FROM information_schema.tables t
                LEFT JOIN pg_class c ON c.relname = t.table_name
                WHERE t.table_schema = %s
                AND t.table_type IN ('BASE TABLE', 'VIEW')
                ORDER BY t.table_name
                LIMIT %s
            """, (schema_name, max_tables))
            
            table_rows = cursor.fetchall()
            
            for table_row in table_rows:
                table_name = table_row['table_name']
                
                # Get column information
                cursor.execute("""
                    SELECT 
                        column_name,
                        data_type,
                        is_nullable,
                        column_default,
                        character_maximum_length,
                        numeric_precision,
                        numeric_scale
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position
                """, (schema_name, table_name))
                
                column_rows = cursor.fetchall()
                
                columns = []
                for col_row in column_rows:
                    column_info = {
                        "name": col_row['column_name'],
                        "type": col_row['data_type'],
                        "nullable": col_row['is_nullable'] == 'YES',
                        "default": col_row['column_default']
                    }
                    
                    if col_row['character_maximum_length']:
                        column_info["max_length"] = col_row['character_maximum_length']
                    if col_row['numeric_precision']:
                        column_info["precision"] = col_row['numeric_precision']
                    if col_row['numeric_scale']:
                        column_info["scale"] = col_row['numeric_scale']
                    
                    columns.append(column_info)
                
                # Get row count estimate (skip for views as they can be expensive)
                row_count = None
                if table_row['table_type'] == 'BASE TABLE':
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM \"{schema_name}\".\"{table_name}\" LIMIT 1000000")
                        row_count = cursor.fetchone()[0]
                    except Exception as e:
                        logger.debug(f"Could not get row count for {schema_name}.{table_name}: {e}")
                        row_count = None
                
                table_info = {
                    "table_name": table_name,
                    "table_type": table_row['table_type'],
                    "description": table_row['table_comment'] or "",
                    "row_count": row_count,
                    "columns": columns
                }
                
                tables.append(table_info)
        
        logger.info(f"Found {len(tables)} tables/views in schema {schema_name}")
        return tables

    except Exception as e:
        logger.error(f"Error getting tables/views from schema {schema_name}: {str(e)}")
        return []


def generate_redshift_overview(base_dir, project, dest_folder, connection_info=None, output_format="both"):
    """
    Generate overview of Redshift database structure and save to files
    
    Args:
        base_dir: Base directory for output
        project: Project name
        dest_folder: Destination folder for output
        connection_info: Dictionary containing Redshift connection details
        output_format: Output format ("json", "txt", or "both")
    """
    if not REDSHIFT_AVAILABLE:
        logger.error("Redshift client library not available")
        return
    
    logger.info("Starting Redshift metadata generation...")
    
    # Ensure destination folder exists
    os.makedirs(dest_folder, exist_ok=True)
    
    # Setup Redshift connection
    conn = setup_redshift_connection(connection_info)
    if not conn:
        logger.error("Failed to setup Redshift connection")
        return
    
    try:
        # Get all schemas
        available_schemas = get_schemas_using_connection(conn)
        target_schemas = [schema['schema_name'] for schema in available_schemas]
        
        logger.info(f"Processing {len(target_schemas)} schemas: {target_schemas}")
        
        # Process each schema
        all_schemas_data = []
        for schema_name in target_schemas:
            logger.info(f"Processing schema: {schema_name}")
            
            tables = get_tables_using_connection(conn, schema_name)
            
            schema_data = {
                "schema_name": schema_name,
                "table_count": len(tables),
                "tables": tables,
                "generated_at": datetime.datetime.now().isoformat()
            }
            
            all_schemas_data.append(schema_data)
        
        # Generate metadata overview
        metadata = {
            "source_type": "redshift",
            "database": connection_info.get('database'),
            "host": connection_info.get('host'),
            "schemas": all_schemas_data,
            "total_schemas": len(all_schemas_data),
            "total_tables": sum(schema['table_count'] for schema in all_schemas_data),
            "generated_at": datetime.datetime.now().isoformat(),
            "project": project
        }
        
        # Save metadata to files
        if output_format in ["json", "both"]:
            json_filename = os.path.join(dest_folder, "redshift_metadata.json")
            with open(json_filename, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
            logger.info(f"Saved Redshift metadata to: {json_filename}")
        
        if output_format in ["txt", "both"]:
            txt_filename = os.path.join(dest_folder, "redshift_overview.txt")
            with open(txt_filename, 'w') as f:
                f.write(f"Redshift Database Overview\n")
                f.write(f"=" * 50 + "\n\n")
                f.write(f"Database: {metadata['database']}\n")
                f.write(f"Host: {metadata['host']}\n")
                f.write(f"Total Schemas: {metadata['total_schemas']}\n")
                f.write(f"Total Tables: {metadata['total_tables']}\n")
                f.write(f"Generated: {metadata['generated_at']}\n\n")
                
                for schema in all_schemas_data:
                    f.write(f"Schema: {schema['schema_name']}\n")
                    f.write(f"-" * 30 + "\n")
                    f.write(f"Tables: {schema['table_count']}\n\n")
                    
                    for table in schema['tables']:
                        f.write(f"  Table: {table['table_name']} ({table['table_type']})\n")
                        if table.get('description'):
                            f.write(f"    Description: {table['description']}\n")
                        if table.get('row_count') is not None:
                            f.write(f"    Rows: {table['row_count']}\n")
                        f.write(f"    Columns: {len(table['columns'])}\n")
                        
                        for col in table['columns']:
                            nullable_str = "NULL" if col['nullable'] else "NOT NULL"
                            f.write(f"      - {col['name']} ({col['type']}) {nullable_str}\n")
                        f.write("\n")
                    f.write("\n")
            
            logger.info(f"Saved Redshift overview to: {txt_filename}")
        
        logger.info("Redshift metadata generation completed successfully")
        
    except Exception as e:
        logger.error(f"Error generating Redshift overview: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()
