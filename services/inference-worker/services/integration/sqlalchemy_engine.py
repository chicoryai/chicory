import os
import pandas as pd
import time
from typing import Optional, Dict, Any, List
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, Engine
from functools import wraps
import threading

# Connection pool
_connection_pool = []
_pool_lock = threading.Lock()
MAX_POOL_SIZE = 5
POOL_TIMEOUT = 30  # seconds


def get_connection_from_pool(db_type: str) -> Optional[Any]:
    """Get an existing connection from the pool or create a new one if needed."""
    with _pool_lock:
        while _connection_pool:
            conn = _connection_pool.pop()
            try:
                if db_type == "oracle":
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1 FROM DUAL")
                    cursor.close()
                elif db_type == "databricks":
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT 1")
                return conn
            except Exception:
                try:
                    conn.close()
                except:
                    pass
        return None


def return_connection_to_pool(conn: Any):
    """Return a connection to the pool if there's space."""
    with _pool_lock:
        if len(_connection_pool) < MAX_POOL_SIZE:
            _connection_pool.append(conn)
        else:
            try:
                conn.close()
            except:
                pass


def with_retry(max_retries=3, initial_delay=1):
    """Decorator for functions that need retry logic."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    print(f"Error on attempt {attempt + 1}/{max_retries}: {str(e)}")

                    if attempt < max_retries - 1:
                        time.sleep(delay)
                        delay *= 2  # Exponential backoff

            raise last_exception

        return wrapper

    return decorator


def _validate_env(db_type: str, project: str) -> tuple:
    """Validate and return required environment variables"""
    if db_type == "oracle":
        username = os.getenv(f"{project.upper()}_ORACLE_USERNAME", os.getenv("ORACLE_USERNAME", None))
        password = os.getenv(f"{project.upper()}_ORACLE_PASSWORD", os.getenv("ORACLE_PASSWORD", None))
        dsn = os.getenv(f"{project.upper()}_ORACLE_DSN", os.getenv("ORACLE_DSN", None))
        if not all([username, password, dsn]):
            raise ValueError("Missing required Oracle environment variables")
        return username, password, dsn
    elif db_type == "databricks":
        host = os.getenv(f"{project.upper()}_DATABRICKS_HOST", os.getenv("DATABRICKS_HOST", None))
        http_path = os.getenv(f"{project.upper()}_DATABRICKS_HTTP_PATH", os.getenv("DATABRICKS_HTTP_PATH", None))
        access_token = os.getenv(f"{project.upper()}_DATABRICKS_ACCESS_TOKEN",
                                 os.getenv("DATABRICKS_ACCESS_TOKEN", None))
        catalog = os.getenv(f"{project.upper()}_DATABRICKS_CATALOG", os.getenv("DATABRICKS_CATALOG", None))
        schema = os.getenv(f"{project.upper()}_DATABRICKS_SCHEMA", os.getenv("DATABRICKS_SCHEMA", None))
        if not all([host, http_path, access_token, catalog, schema]):
            raise ValueError("Missing required Databricks environment variables")
        return host, http_path, access_token, catalog, schema
    elif db_type == "snowflake":
        account = os.getenv(f"{project.upper()}_SNOWFLAKE_ACCOUNT", os.getenv("SNOWFLAKE_ACCOUNT", None))
        username = os.getenv(f"{project.upper()}_SNOWFLAKE_USERNAME", os.getenv("SNOWFLAKE_USERNAME", None))
        password = os.getenv(f"{project.upper()}_SNOWFLAKE_PASSWORD", os.getenv("SNOWFLAKE_PASSWORD", None))
        warehouse = os.getenv(f"{project.upper()}SNOWFLAKE_WAREHOUSE", os.getenv("SNOWFLAKE_WAREHOUSE", None))
        database = os.getenv(f"{project.upper()}SNOWFLAKE_DATABASE", os.getenv("SNOWFLAKE_DATABASE", "PUBLIC"))
        schema = os.getenv(f"{project.upper()}SNOWFLAKE_SCHEMA", os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC"))
        if not all([account, username, password, warehouse, database, schema]):
            raise ValueError("Missing required Snowflake environment variables")
        return username, password, account, warehouse, database, schema
    else:
        raise ValueError("Unsupported database type")


def get_connection(db_type: str, project: str) -> Any:
    """Establish a connection to the database with retry logic"""
    conn = get_connection_from_pool(db_type)
    if conn:
        return conn

    try:
        if db_type == "oracle":
            import oracledb
            username, password, dsn = _validate_env(db_type, project)
            connection = oracledb.connect(user=username, password=password, dsn=dsn)
        elif db_type == "databricks":
            from databricks import sql
            host, http_path, access_token, _, _ = _validate_env(db_type, project)
            connection = sql.connect(
                server_hostname=host,
                http_path=http_path,
                access_token=access_token,
                connect_timeout=30
            )
        elif db_type == "snowflake" or db_type == "snowflake-connector":
            import snowflake.connector
            username, password, account, _, _, _ = _validate_env(db_type, project)
            connection = snowflake.connector.connect(
                user=username,
                password=password,
                account=account,
            )
        return connection
    except Exception as e:
        print(f"Failed to create new {db_type} connection: {e}")
        raise


@with_retry(max_retries=3, initial_delay=1)
def run_query(query: str, db_type: str, project: str) -> pd.DataFrame:
    """Execute a query with proper connection handling and retries"""
    print(f"Running query: {query}")
    connection = None

    try:
        connection = get_connection(db_type, project)
        df = pd.read_sql(query, connection)
        return df
    except Exception as e:
        print(f"Error executing query: {str(e)}")
        if connection:
            try:
                connection.close()
            except:
                pass
        raise
    else:
        return_connection_to_pool(connection)


def fetch_table_schema(database: str, table: str, db_type: str) -> List[Dict[str, Any]]:
    """Fetch table schema information"""
    if db_type == "oracle":
        query = f"""
        SELECT column_name, data_type, data_length, nullable
        FROM all_tab_columns
        WHERE table_name = '{table.upper()}'
        AND owner = '{database.upper()}'
        """
    elif db_type == "databricks":
        query = f"DESCRIBE TABLE {database}.{table}"
    else:
        raise ValueError("Unsupported database type")

    try:
        df = run_query(query, db_type)
        return df.to_dict('records')
    except Exception as e:
        print(f"Error fetching schema for {database}.{table}: {str(e)}")
        raise


def fetch_table_metadata(database: str, table: str, db_type: str) -> Dict[str, Any]:
    """Fetch table metadata including sample data"""
    if db_type == "oracle":
        sample_query = f"SELECT * FROM {database}.{table} WHERE ROWNUM <= 5"
        count_query = f"SELECT COUNT(*) as row_count FROM {database}.{table}"
    elif db_type == "databricks":
        sample_query = f"SELECT * FROM {database}.{table} LIMIT 5"
        count_query = f"SELECT COUNT(*) as row_count FROM {database}.{table}"
    else:
        raise ValueError("Unsupported database type")

    try:
        sample_df = run_query(sample_query, db_type)
        count_df = run_query(count_query, db_type)
        return {
            "sample_data": sample_df.to_dict('records'),
            "row_count": count_df['row_count'].iloc[0]
        }
    except Exception as e:
        print(f"Error fetching metadata for {database}.{table}: {str(e)}")
        raise


def fetch_all_databases(db_type: str) -> List[str]:
    """Fetch list of all available databases"""
    if db_type == "oracle":
        query = "SELECT username FROM all_users ORDER BY username"
    elif db_type == "databricks":
        query = "SHOW DATABASES"
    else:
        raise ValueError("Unsupported database type")

    try:
        df = run_query(query, db_type)
        if db_type == "oracle":
            return df['USERNAME'].tolist()
        else:  # databricks
            return df['databaseName'].tolist() if 'databaseName' in df.columns else []
    except Exception as e:
        print(f"Error fetching databases: {str(e)}")
        raise


def get_connection_string(db_type: str, project: str, conn_info=None) -> str:
    if conn_info is None:
        username, password, dsn = _validate_env(db_type, project)
    else:
        username, password, dsn = conn_info
    connection_string = f"oracle+oracledb://{username}:{password}@{dsn}"
    return connection_string


def get_sqlalchemy_engine(db_type: str, project: str, conn_info=None) -> Engine:
    """Create and return a SQLAlchemy engine for the specified database type"""

    if db_type == "oracle":
        if conn_info is None:
            username, password, dsn = _validate_env(db_type, project)
        else:
            username, password, dsn = conn_info
        connection_url = URL.create(
            "oracle+cx_oracle",
            username=username,
            password=password,
            host=dsn,
        )
    elif db_type == "databricks":
        if conn_info is None:
            host, http_path, access_token, catalog, schema = _validate_env(db_type, project)
        else:
            host, http_path, access_token, catalog, schema = conn_info
        connection_url = URL.create(
            "databricks",
            username="token",
            password=access_token,
            host=host.replace("https://", ""),
            port=443,
            database=f"{catalog}.{schema}",
            query={
                "http_path": http_path,
                "catalog": catalog,
                "schema": schema
            }
        )
    elif db_type == "snowflake":
        if conn_info is None:
            username, password, account, warehouse, database, schema = _validate_env(db_type, project)
        else:
            username, password, account, warehouse, database, schema = conn_info
        connection_url = URL.create(
            "snowflake",
            username=username,
            password=password,
            query={
                "account": account,
                "warehouse": warehouse,
                "database": database,
                "schema": schema
            }
        )
    else:
        raise ValueError("Unsupported database type")

    if db_type == "snowflake":
        connect_args = {
            "connect_timeout": 600,  # 10 minutes
            "network_timeout": 300,  # 5 minutes
            "socket_timeout": 300,  # 5 minutes
        }
    else:
        connect_args = {"connect_timeout": 300}

    return create_engine(
        connection_url,
        connect_args=connect_args,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=5,
        max_overflow=2
    )
