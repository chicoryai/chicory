import decimal
import json
import subprocess

from lxml import etree
from decimal import Decimal

import msgpack
import pyarrow.parquet as pq
import sqlite3
import re
import yaml

import zipfile
import gzip
import shutil
import os
import pandas as pd
import numpy as np
import ssl

from bs4 import BeautifulSoup
from datetime import datetime, UTC

from services.integration.sqlalchemy_engine import run_query
from services.utils.dtd2xml import parse_dtd_to_xml
from services.utils.logger import logger

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# Document loaders - using worker-common package (replaces LangChain)
from chicory_worker_common.loaders import (
    Document,
    BaseLoader,
    TextLoader,
    CSVLoader,
    PythonLoader,
    JSONLoader,
    PDFLoader,
    UnstructuredLoader,
    MarkdownLoader,
    RSTLoader,
    WebLoader,
    AsyncWebLoader,
    RawHtmlLoader,
    BeautifulSoupTransformer,
)
from typing import Dict, Any, List, Protocol
from urllib.parse import urlparse


# Backwards compatibility aliases
UnstructuredPowerPointLoader = UnstructuredLoader
UnstructuredExcelLoader = UnstructuredLoader
UnstructuredMarkdownLoader = MarkdownLoader
UnstructuredRSTLoader = RSTLoader
WebBaseLoader = WebLoader
AsyncHtmlLoader = AsyncWebLoader
PyPDFLoader = PDFLoader


class GraphTextLoader(BaseLoader):
    def __init__(self, graph_text: str):
        self.graph_text = graph_text

    def load(self) -> list[Document]:
        return [Document(page_content=self.graph_text, metadata={"source": "graph_conversion"})]


class ContentTextLoader(BaseLoader):
    def __init__(self, text: str):
        self.text = text

    def load(self) -> list[Document]:
        return [Document(page_content=self.text, metadata={"source": "text"})]


class YamlLoader(BaseLoader):
    """Custom loader to load YAML files and convert them into LangChain documents."""

    def __init__(self, file_path: str):
        self.file_path = file_path

    def load(self) -> list[Document]:
        """Load YAML file and return it as a LangChain document."""
        with open(self.file_path, 'r') as file:
            yaml_content = yaml.safe_load(file)

        # Convert YAML content into a string representation
        yaml_str = yaml.dump(yaml_content)

        # Wrap it in a LangChain Document
        document = Document(page_content=yaml_str)

        return [document]


class MessagePackLoader(BaseLoader):
    def __init__(self, file_path: str):
        self.file_path = file_path

    def load(self) -> list[Document]:
        with open(self.file_path, "rb") as file:
            data = msgpack.unpack(file)

        # Assuming the MessagePack file contains a dictionary or a list of dictionaries
        if isinstance(data, dict):
            return [Document(page_content=str(data), metadata={"source": self.file_path})]
        elif isinstance(data, list):
            return [Document(page_content=str(item), metadata={"source": self.file_path}) for item in data]
        else:
            raise ValueError("Unsupported MessagePack structure")


# def DocxLoader(file_path):
#     # Load the .docx file
#     doc = docx.Document(file_path)
#
#     # Extract text from each paragraph in the document
#     text = [paragraph.text for paragraph in doc.paragraphs]
#
#     # Combine the text into a single string, separating paragraphs with newlines
#     combined_text = '\n'.join(text)
#
#     return combined_text

# Function to check if the given path is a URL
def is_url(path):
    try:
        result = urlparse(path)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


async def url_loader_async(url_list) -> Any:
    """Load URLs asynchronously using aiohttp."""
    loader = AsyncWebLoader(url_list)
    docs = await loader.aload()
    return docs


def add_line_breaks(text):
    # Add line breaks after block-level tags to preserve structure
    text = re.sub(r'(<\/(p|h[1-6]|li|div|br|hr)>)', r'\1\n', text)
    text = re.sub(r'\n{2,}', '\n', text)  # Remove extra newlines if any
    return text


async def url_loader_chrom(url_list) -> Any:
    """
    Load URLs asynchronously.

    NOTE: Previously used Chromium for JavaScript rendering (LangChain AsyncChromiumLoader).
    Now uses aiohttp which does not render JavaScript. For JS-heavy pages,
    consider using a browser automation tool like Playwright directly.
    """
    logger.warning(
        "url_loader_chrom now uses aiohttp instead of Chromium. "
        "JavaScript-rendered content will not be captured."
    )
    loader = RawHtmlLoader(url_list)
    return await loader.aload()


def url_loader(url_list) -> Any:
    """Load URLs synchronously using requests."""
    docs = []
    for url in url_list:
        if is_url(url):
            loader = WebLoader(url, verify_ssl=False)
            int_docs = loader.load()
            docs.append(int_docs)
    return docs


def save_to_txt(url: str, document: str, dest: str) -> None:
    # Create a file name based on the URL
    file_name = url.replace("http://", "").replace("https://", "").replace("/", "_") + ".txt"
    file_path = os.path.join(dest, file_name)  # Save in the "output_docs" directory

    # Ensure the output directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Save the document content into the text file
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(document)

    logger.debug(f"Document saved to {file_path}")


def fetch_url_list_from_file(file_name):
    """
    Read URLs from a file and return them as a list.
    Each URL should be on a separate line in the file.

    Args:
        file_name (str): Path to the file containing URLs

    Returns:
        list: List of URLs read from the file
    """
    if os.path.exists(file_name):
        with open(file_name, 'r') as file:
            # Strip whitespace and newlines from each line
            url_list = [line.strip() for line in file if line.strip()]

    return url_list if url_list else []


def process_sqlite_db(db_path):
    if os.path.isdir(db_path):
        for root, _, files in os.walk(db_path):
            for file in files:
                if file.endswith(('.sqlite')):
                    db_path = os.path.join(db_path, file)
                    break

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get database name
    cursor.execute("SELECT name FROM sqlite_master WHERE type='database'")
    # db_name = cursor.fetchone()[0]

    # Get table names and columns
    tables = []
    table_names = []
    table_names_original = []
    column_names = []
    column_names_original = []
    column_types = []
    foreign_keys_candidates = []
    foreign_keys = []
    primary_keys = []

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    table_names_original = [row[0] for row in cursor.fetchall()]

    column_names.insert(0, [-1, "*"])
    column_names_original.insert(0, [-1, "*"])
    column_types.insert(0, "TEXT")
    table_col_dict = {}
    overall_col_counter = 1
    total_column_count = 0
    max_column_count = 0

    for i, table_name in enumerate(table_names_original):
        try:
            table_names.append(table_name.lower().replace('_', ' '))
            columns = []
            columns_original = []
            cursor.execute(f"PRAGMA table_info('{table_name}')")
            column_count = 0

            for j, row in enumerate(cursor.fetchall()):
                column_name = row[1]
                column_type = row[2]
                is_primary_key = row[5]

                columns.append([overall_col_counter, column_name])
                columns_original.append([overall_col_counter, column_name])
                column_names.append([i, column_name.lower().replace('_', ' ')])
                column_names_original.append([i, column_name])
                column_types.append(column_type)
                if is_primary_key:
                    primary_keys.append(overall_col_counter)
                table_col_dict[f"{table_name}.{column_name}"] = overall_col_counter
                overall_col_counter += 1
                column_count += 1

            total_column_count += column_count
            if column_count > max_column_count:
                max_column_count = column_count

            cursor.execute(f"PRAGMA foreign_key_list('{table_name}')")
            for row in cursor.fetchall():
                foreign_key = [f"{table_name}.{row[3]}", f"{row[2]}.{row[4]}"]
                foreign_keys_candidates.append(foreign_key)
        except Exception as e:
            logger.error(f"Failed to process table {table_name}: {e}", exc_info=True)

    for foreign_keys_candidate in foreign_keys_candidates:
        try:
            (from_var, to_var) = foreign_keys_candidate
            from_var_index = table_col_dict[from_var]
            to_var_index = table_col_dict[to_var]
            foreign_keys.append([from_var_index, to_var_index])
        except Exception as e:
            logger.warning(f"Failed to fk candidate {foreign_keys_candidate}: {e}", exc_info=True)

    conn.close()

    table_count = len(table_names_original)
    avg_column_count = total_column_count / table_count if table_count else 0

    return {
        "table_names": table_names,
        "table_names_original": table_names_original,
        "column_names": column_names,
        "column_names_original": column_names_original,
        "column_types": column_types,
        "foreign_keys": foreign_keys,
        "primary_keys": primary_keys,
        "table_count": table_count,
        "max_column_count": max_column_count,
        "total_column_count": total_column_count,
        "avg_column_count": avg_column_count,
        "table_col_dict": table_col_dict
    }


def process_csv_xlsx_folder(folder_path):
    tables = []
    table_names = []
    table_names_original = []
    column_names = []
    column_names_original = []
    column_types = []

    total_column_count = 0
    max_column_count = 0

    for file in os.listdir(folder_path):
        if file.endswith('.csv') or file.endswith('.xlsx') or file.endswith('.xls'):
            logger.debug("Processing: " + file)
            table_name = os.path.splitext(file)[0]
            table_names.append(len(table_names))
            table_names_original.append(table_name)

            if file.endswith('.csv'):
                df = pd.read_csv(os.path.join(folder_path, file))
            elif file.endswith('.xlsx') or file.endswith('.xls'):
                df = pd.read_excel(os.path.join(folder_path, file))

            columns = []
            columns_original = []
            column_count = 0
            for i, column in enumerate(df.columns):
                columns.append([i, column])
                columns_original.append([i, column])
                column_names.append([len(table_names) - 1, column.lower().replace('_', ' ')])
                column_names_original.append([len(table_names) - 1, column])
                column_types.append(str(df[column].dtype))
                column_count += 1

            total_column_count += column_count
            if column_count > max_column_count:
                max_column_count = column_count

            tables.append({
                "table_name": len(table_names) - 1,
                "columns": columns,
                "columns_original": columns_original
            })

    column_names.insert(0, [-1, "*"])
    column_names_original.insert(0, [-1, "*"])

    table_count = len(table_names_original)
    avg_column_count = total_column_count / table_count if table_count else 0

    return {
        "table_names": table_names,
        "table_names_original": table_names_original,
        "column_names": column_names,
        "column_names_original": column_names_original,
        "column_types": column_types,
        "tables": tables,
        "foreign_keys": [],
        "primary_keys": [],
        "table_count": table_count,
        "max_column_count": max_column_count,
        "total_column_count": total_column_count,
        "avg_column_count": avg_column_count
    }


def create_tables_json(project, input_path, output_file, database_type="", database=None):
    """
        Create a JSON file describing the schema of tables from SQLite, CSV, Excel, or Databricks.
        """
    tables_jsons = []
    tables_json = {}

    if database_type == "databricks":
        if not database:
            logger.debug("Database name must be specified for Databricks. Not creating tables index. Not writing to file.")
            return
        try:
            tables_json = process_database(project, database, "databricks")
            if tables_json:
                if not tables_json['table_names']:
                    logger.error("No tables found in database or access issue.", exc_info=True)
        except Exception as e:
            logger.error(e, exc_info=True)
        tables_jsons.append(tables_json)
    elif database_type == "oracle":
        if not database:
            logger.debug("Database name must be specified for Oracle. Not creating tables index. Not writing to file.")
            return
        try:
            tables_json = process_database(project, database, "oracle")
            if tables_json:
                if not tables_json['table_names']:
                    logger.error("No tables found in database or access issue.", exc_info=True)
        except Exception as e:
            logger.error(e, exc_info=True)
        tables_jsons.append(tables_json)
    elif os.path.isdir(input_path):
        if os.path.exists(os.path.join(input_path, "database.sqlite")):
            tables_json = process_sqlite_db(os.path.join(input_path, "database.sqlite"))
            tables_jsons.append(tables_json)
        elif any(file.endswith('.sqlite') for file in os.listdir(input_path)):
            tables_json = process_sqlite_db(input_path)
            tables_jsons.append(tables_json)
        elif any(file.endswith(('.csv', '.xlsx', '.xls')) for file in os.listdir(input_path)):
            tables_json = process_csv_xlsx_folder(input_path)
            tables_jsons.append(tables_json)
    else:
        logger.debug("Invalid input path or format. Not creating tables index. Not writing to file.")
        return

    # Check if tables_jsons is empty
    if not any(tables_jsons):  # This ensures the check accounts for empty dictionaries as well
        logger.debug("No valid tables were processed. Not writing to file.")
        return

    parent_dir = os.path.dirname(output_file)
    os.makedirs(parent_dir, exist_ok=True)
    try:
        # Write the JSON file
        with open(output_file, "w") as f:
            json.dump(tables_jsons, f, indent=4)

        # Validate that the file is written correctly
        with open(output_file, "r") as f:
            try:
                loaded_data = json.load(f)
                if loaded_data == tables_jsons:
                    logger.debug("File written and validated successfully.")
                else:
                    logger.warning("File content does not match the data written.")
            except json.JSONDecodeError as e:
                logger.error("Failed to validate JSON file: Invalid JSON format.", exc_info=True)
    except Exception as e:
        logger.error(f"Failed to write or validate the JSON file: {e}", exc_info=True)

    return tables_jsons


def process_database(project, database, db_type):
    """
    Process a database and return schema details for all tables.
    Works for both Databricks and Oracle.
    """
    if db_type == "databricks":
        query = f"SHOW TABLES IN {database}"
        tables_df = run_query(query, db_type, project)
        table_names = tables_df['tableName'].tolist()
    elif db_type == "oracle":
        query = f"""
        SELECT table_name
        FROM all_tables
        WHERE owner = '{database.upper()}'
        """
        tables_df = run_query(query, db_type, project)
        table_names = tables_df['TABLE_NAME'].tolist()
    elif db_type == "snowflake" or db_type == "snowflake-connector":
        query = f"SHOW TABLES IN SCHEMA {database}"
        tables_df = run_query(query, db_type, project)
        table_names = tables_df['name'].tolist()
    else:
        raise ValueError(f"Unsupported database type: {db_type}")

    table_names_original = table_names.copy()
    column_names = []
    column_names_original = []
    column_types = []
    foreign_keys = []
    primary_keys = []
    table_col_dict = {}
    overall_col_counter = 1

    for i, table_name in enumerate(table_names_original):
        if db_type == "databricks" or db_type == "snowflake" or db_type == "snowflake-connector":
            query = f"DESCRIBE TABLE {database}.{table_name}"
        elif db_type == "oracle":
            query = f"""
            SELECT column_name, data_type
            FROM all_tab_columns
            WHERE table_name = '{table_name.upper()}'
            AND owner = '{database.upper()}'
            """

        schema_df = run_query(query, db_type, project)

        # Extract columns
        for _, row in schema_df.iterrows():
            if db_type == "databricks":
                column_name = row['col_name']
                column_type = row['data_type']
            elif db_type == "oracle":
                column_name = row['COLUMN_NAME']
                column_type = row['DATA_TYPE']
            elif db_type == "snowflake" or db_type == "snowflake-connector":
                column_name = row['name']
                column_type = row['type']

            column_names.append([i, column_name.lower().replace('_', ' ')])
            column_names_original.append([i, column_name])
            column_types.append(column_type)
            table_col_dict[f"{table_name}.{column_name}"] = overall_col_counter
            overall_col_counter += 1

        # Extract PKs
        if db_type == "databricks":
            query = f"""
                SHOW CREATE TABLE {database}.{table_name}
                """
            ddl_df = run_query(query, db_type, project)
            ddl = ddl_df.iloc[0, 0]
            for col in column_names_original:
                if col[0] == i and f"PRIMARY KEY ({col[1]})" in ddl:
                    primary_keys.append(table_col_dict[f"{table_name}.{col[1]}"])

        elif db_type == "oracle":
            query = f"""
                SELECT cols.column_name
                FROM all_constraints cons
                JOIN all_cons_columns cols
                ON cons.constraint_name = cols.constraint_name
                AND cons.owner = cols.owner
                WHERE cons.constraint_type = 'P'
                AND cons.owner = '{database.upper()}'
                AND cols.table_name = '{table_name.upper()}'
                """
            pk_df = run_query(query, db_type, project)
            for _, row in pk_df.iterrows():
                col_name = row['COLUMN_NAME']
                primary_keys.append(table_col_dict[f"{table_name}.{col_name}"])

        elif db_type == "snowflake" or db_type == "snowflake-connector":
            query = f"""
            SELECT kcu.COLUMN_NAME
            FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
            JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
            ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
            WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
            AND tc.TABLE_SCHEMA = '{database.split('.')[1]}' -- schema part
            AND tc.TABLE_NAME = '{table_name.upper()}'
            """
            pk_df = run_query(query, db_type, project)
            for _, row in pk_df.iterrows():
                col_name = row['COLUMN_NAME']
                primary_keys.append(table_col_dict[f"{table_name}.{col_name}"])

        # Extract FKs
        if db_type == "databricks":
            # Databricks doesn't natively enforce FK constraints, so fallback logic:
            # Look for FK hints in comments or naming convention (optional)
            pass  # You can optionally enhance this with metadata tables if available.
        elif db_type == "oracle":
            query = f"""
                SELECT a.column_name AS fk_column,
                       c_pk.table_name AS referenced_table,
                       b.column_name AS referenced_column
                FROM all_constraints c
                JOIN all_cons_columns a ON c.constraint_name = a.constraint_name
                JOIN all_constraints c_pk ON c.r_constraint_name = c_pk.constraint_name
                JOIN all_cons_columns b ON c_pk.constraint_name = b.constraint_name AND a.position = b.position
                WHERE c.constraint_type = 'R'
                AND c.owner = '{database.upper()}'
                AND c.table_name = '{table_name.upper()}'
                """
            fk_df = run_query(query, db_type, project)
            for _, row in fk_df.iterrows():
                fk_col = row['FK_COLUMN']
                ref_table = row['REFERENCED_TABLE']
                ref_col = row['REFERENCED_COLUMN']
                from_var_index = table_col_dict.get(f"{table_name}.{fk_col}")
                to_var_index = table_col_dict.get(f"{ref_table}.{ref_col}")
                if from_var_index and to_var_index:
                    foreign_keys.append([from_var_index, to_var_index])
        elif db_type == "snowflake" or db_type == "snowflake-connector":
            query = f"""
            SELECT
                kcu.COLUMN_NAME AS fk_column,
                kcu.REFERENCED_TABLE_NAME AS referenced_table,
                kcu.REFERENCED_COLUMN_NAME AS referenced_column
            FROM
                INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc
            JOIN
                INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
            ON
                rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
            WHERE
                rc.CONSTRAINT_SCHEMA = '{database.split('.')[1]}' -- schema
                AND rc.UNIQUE_CONSTRAINT_SCHEMA = '{database.split('.')[1]}'
                AND kcu.TABLE_NAME = '{table_name.upper()}'
            """
            fk_df = run_query(query, db_type, project)
            for _, row in fk_df.iterrows():
                fk_col = row['FK_COLUMN']
                ref_table = row['REFERENCED_TABLE']
                ref_col = row['REFERENCED_COLUMN']
                from_var_index = table_col_dict.get(f"{table_name}.{fk_col}")
                to_var_index = table_col_dict.get(f"{ref_table}.{ref_col}")
                if from_var_index and to_var_index:
                    foreign_keys.append([from_var_index, to_var_index])

    table_count = len(table_names_original)
    total_column_count = len(column_names_original)
    max_column_count = max(
        [len([c for c in column_names if c[0] == i]) for i in range(len(table_names_original))]
    )
    avg_column_count = total_column_count / table_count if table_count else 0

    return {
        "table_names": table_names,
        "table_names_original": table_names_original,
        "column_names": column_names,
        "column_names_original": column_names_original,
        "column_types": column_types,
        "foreign_keys": foreign_keys,
        "primary_keys": primary_keys,
        "table_count": table_count,
        "max_column_count": max_column_count,
        "total_column_count": total_column_count,
        "avg_column_count": avg_column_count,
        "table_col_dict": table_col_dict
    }

# Function to convert parquet file to a pandas DataFrame
def parquet_to_dataframe(parquet_file):
    table = pq.read_table(parquet_file)
    return table.to_pandas()


# Function to handle decimal.Decimal types in a DataFrame
def convert_decimal_to_float(df):
    for col in df.columns:
        if df[col].dtype == 'object':
            # Check if the column contains decimal.Decimal types
            if any(isinstance(val, decimal.Decimal) for val in df[col]):
                df[col] = df[col].apply(lambda x: float(x) if isinstance(x, decimal.Decimal) else x)
    return df


# Function to convert a DataFrame to a SQLite table
def dataframe_to_sqlite(df, table_name, sqlite_db_path):
    """Converts a DataFrame into SQLite, ensuring compatible data types."""

    os.makedirs(os.path.dirname(sqlite_db_path), exist_ok=True)
    # Create the SQLite database file if it doesn't exist
    if not os.path.exists(sqlite_db_path):
        open(sqlite_db_path, 'w').close()

    # Convert Decimal to Float (SQLite does not support Decimal)
    def convert_decimal(value):
        if isinstance(value, Decimal):
            return float(value)
        return value

    df = df.applymap(convert_decimal)

    # Ensure all columns are SQLite-compatible
    for col in df.columns:
        if df[col].dtype == 'object':  # Check if object type column
            df[col] = df[col].astype(str)  # Convert to string
        elif df[col].dtype == 'bool':  # SQLite doesn't support boolean
            df[col] = df[col].astype(int)  # Convert to 0/1
        elif np.issubdtype(df[col].dtype, np.datetime64):  # Convert datetime
            df[col] = df[col].astype(str)  # Store as text

    # Ensure no function or method references are in the DataFrame
    df = df.applymap(lambda x: x if not callable(x) else str(x))

    # Connect to SQLite and insert DataFrame
    conn = sqlite3.connect(sqlite_db_path)
    try:
        df.to_sql(table_name, conn, if_exists='append', index=False)
    except Exception as e:
        logger.error(f"❌ Error inserting into SQLite: {e}")
    finally:
        conn.close()


def sanitize_table_name(name):
    """Sanitize table name by replacing invalid SQLite characters."""
    return name.replace(".", "_").replace("-", "_").replace(" ", "_").replace("(", "_").replace(")", "_").lower()


def sanitize_column_names(df):
    """Sanitize column names by replacing invalid characters and converting to lowercase."""
    df.columns = [col.replace(".", "_").replace("-", "_").replace(" ", "_").replace("(", "_").replace(")", "_").lower() for col in df.columns]
    return df

def traverse_xml(elem, parent_path=""):
    """
    Recursively traverses the XML element and returns a list of dictionaries,
    each representing an element with its tag, text, attributes, full path, and depth.
    """
    rows = []
    # Build current element path
    current_path = f"{parent_path}/{elem.tag}" if parent_path else elem.tag
    # Create a row for the current element
    row = {
        "tag": elem.tag,
        "text": elem.text.strip() if elem.text and elem.text.strip() != "" else None,
        "attributes": elem.attrib if elem.attrib else None,
        "path": current_path,
        "level": current_path.count("/")
    }
    rows.append(row)
    # Recurse for each child element
    for child in elem:
        rows.extend(traverse_xml(child, current_path))
    return rows

def extract_tables_from_xml(xml_file):
    """Extracts a flattened table structure from an XML file and returns a pandas DataFrame."""
    try:
        tree = etree.parse(xml_file)
        root = tree.getroot()
        rows = traverse_xml(root)
        return pd.DataFrame(rows)
    except Exception as e:
        print(f"Error parsing {xml_file}: {e}")
        return None

def export_table_ddls_from_schema(schema_metadata, output_file="database_schema_dump.sql"):
    ddl_statements = []
    table_names_original = schema_metadata['table_names_original']
    column_names_original = schema_metadata['column_names_original']
    column_types = schema_metadata['column_types']
    primary_keys = schema_metadata['primary_keys']
    table_col_dict = schema_metadata['table_col_dict']

    for i, table in enumerate(table_names_original):
        column_lines = []
        for idx, col in enumerate(column_names_original):
            if col[0] == i:
                col_name = col[1]
                col_type = column_types[idx]
                col_key = f"{table}.{col_name}"
                col_index = table_col_dict[col_key]
                pk_suffix = "NOT NULL" if col_index in primary_keys else "NULL"
                column_lines.append(f"    {col_name} {col_type} {pk_suffix}")

        # Compose CREATE TABLE
        ddl = f"CREATE TABLE {table} (\n" + ",\n".join(column_lines)

        # Add PK constraint block
        pk_cols = []
        for idx, col in enumerate(column_names_original):
            if col[0] == i:
                col_name = col[1]
                col_key = f"{table}.{col_name}"
                col_index = table_col_dict[col_key]
                if col_index in primary_keys:
                    pk_cols.append(col_name)

        if pk_cols:
            ddl += f",\n    CONSTRAINT PK_{table} PRIMARY KEY ({', '.join(pk_cols)})"

        ddl += "\n);"
        ddl_statements.append(ddl)

    # Write to SQL file
    with open(output_file, "w") as ddl_file:
        for ddl in ddl_statements:
            ddl_file.write(ddl + "\n\n")

    logger.debug(f"[INFO] CREATE TABLE statements written to {output_file}")


def generate_erd(schema_metadata, erd_output_file="database_erd.png"):
    eralchemy_input_file = "schema_for_erd.er"

    with open(eralchemy_input_file, "w") as er_file:
        # Write tables with columns + PKs
        for i, table in enumerate(schema_metadata['table_names_original']):
            er_file.write(f"[{table}]\n")
            for idx, col in enumerate(schema_metadata['column_names_original']):
                if col[0] == i:
                    col_name = col[1]
                    col_type = schema_metadata['column_types'][idx]

                    # Get correct column index for PK check
                    col_key = f"{table}.{col_name}"
                    col_index = schema_metadata['table_col_dict'][col_key]

                    # Mark PK if found
                    pk_suffix = " PK" if col_index in schema_metadata['primary_keys'] else ""
                    er_file.write(f"{col_name} {col_type}{pk_suffix}\n")
            er_file.write("\n")

        # Write foreign key relationships
        if schema_metadata['foreign_keys']:
            for fk_pair in schema_metadata['foreign_keys']:
                from_idx, to_idx = fk_pair
                from_col = _get_col_name_from_idx(schema_metadata, from_idx)
                to_col = _get_col_name_from_idx(schema_metadata, to_idx)
                er_file.write(f"{from_col} *-- {to_col}\n")

    try:
        subprocess.run([
            "eralchemy", "-i", eralchemy_input_file, "-o", erd_output_file
        ], check=True)
        logger.debug(f"[INFO] ERD exported to {erd_output_file}")
    except subprocess.CalledProcessError as e:
        logger.error(f"[ERROR] ERAlchemy failed: {e}")

    os.remove(eralchemy_input_file)


def _get_col_name_from_idx(schema_metadata, idx):
    for col_key, value in schema_metadata['table_col_dict'].items():
        if value == idx:
            table, col = col_key.split('.')
            return f"{table}.{col}"
    return f"unknown_col_{idx}"


def register_source_database(conn, db_name, db_path, db_size, table_count):
    """Register a source database in the metadata"""

    # Create source databases metadata table if it doesn't exist
    conn.execute('''
    CREATE TABLE IF NOT EXISTS metadata_source_databases (
        database_name TEXT PRIMARY KEY,
        file_path TEXT,
        file_size_bytes INTEGER,
        table_count INTEGER,
        import_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Insert or update the database record
    conn.execute('''
    INSERT OR REPLACE INTO metadata_source_databases 
    (database_name, file_path, file_size_bytes, table_count)
    VALUES (?, ?, ?, ?)
    ''', (db_name, db_path, db_size, table_count))


def register_table_metadata(conn, table_name, source_db_name, original_table_name, row_count, column_count):
    """Register detailed table metadata"""

    # Create detailed table metadata if it doesn't exist
    conn.execute('''
    CREATE TABLE IF NOT EXISTS metadata_tables (
        table_name TEXT PRIMARY KEY,
        source_database TEXT,
        original_table_name TEXT,
        row_count INTEGER,
        column_count INTEGER,
        merge_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (source_database) REFERENCES metadata_source_databases(database_name)
    )
    ''')

    # Insert table metadata
    conn.execute('''
    INSERT OR REPLACE INTO metadata_tables 
    (table_name, source_database, original_table_name, row_count, column_count)
    VALUES (?, ?, ?, ?, ?)
    ''', (table_name, source_db_name, original_table_name, row_count, column_count))


def merge_sqlite_file(source_file, output_path):
    """
    Merge a single SQLite database file into a target database with enhanced metadata tracking.

    Args:
        source_file (str): Path to source SQLite database file
        output_path (str): Path to the target SQLite database

    Returns:
        dict: Summary of tables merged from this source file
    """
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Create output database if it doesn't exist
    if not os.path.exists(output_path):
        open(output_path, 'a').close()

    # Dictionary to track merged tables from this source
    merged_tables = {}

    try:
        logger.info(f"Processing database: {source_file}")

        # Extract database details
        db_name = os.path.basename(source_file)
        db_path = os.path.abspath(source_file)
        db_size = os.path.getsize(source_file)
        db_cleaned_name = db_name.replace('.sqlite', '').replace('.db', '').replace('.sqlite3', '').replace(' ',
                                                                                                            '_').replace(
            '-', '_')

        # Connect to databases
        source_conn = sqlite3.connect(source_file)
        output_conn = sqlite3.connect(output_path)

        source_cursor = source_conn.cursor()

        # Get list of tables from source
        source_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = source_cursor.fetchall()

        # Register the source database in metadata
        register_source_database(output_conn, db_name, db_path, db_size, len(tables))

        logger.info(f"Found {len(tables)} tables in {source_file}")

        # Process each table
        for table_tuple in tables:
            table_name = table_tuple[0]
            table_name = f"{table_name}_{db_cleaned_name}"

            # Get table schema
            source_cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name=?;", (table_tuple[0],))
            schema_sql = source_cursor.fetchone()[0]

            # Modify schema to use the new table name
            if table_name != table_tuple[0]:
                schema_sql = schema_sql.replace(f'TABLE "{table_tuple[0]}"', f'TABLE "{table_name}"')
                schema_sql = schema_sql.replace(f"TABLE '{table_tuple[0]}'", f"TABLE '{table_name}'")
                schema_sql = re.sub(r"CREATE TABLE\s+([^\s\"\']+)", f"CREATE TABLE {table_name}", schema_sql)

                # Fix malformed CREATE TABLE statements
                if "CREATE TABLE" in schema_sql:
                    # Check if there's a missing opening parenthesis after table name
                    table_pattern = r'CREATE TABLE\s+([^\s(]+)\s+'
                    match = re.search(table_pattern, schema_sql)
                    if match and '(' not in schema_sql.split(match.group(0))[1].strip()[:1]:
                        # Add the missing opening parenthesis after the table name
                        table_part = match.group(0)
                        schema_sql = schema_sql.replace(table_part, table_part + '(')

                    # Make sure there's a closing parenthesis at the end
                    if not schema_sql.rstrip().endswith(')'):
                        schema_sql = schema_sql.rstrip() + ')'

                if 'CONSTRAINT' in schema_sql:
                    schema_sql = schema_sql.replace(f'PK_{table_tuple[0]}', f'PK_{table_name}')

                # Find and update foreign key references
                source_cursor.execute(f"PRAGMA foreign_key_list(\"{table_tuple[0]}\");")
                foreign_keys = source_cursor.fetchall()
                for fk in foreign_keys:
                    _, _, ref_table, _, _, _, _, _ = fk
                    # Update references to point to renamed tables
                    ref_table_new = f"{ref_table}_{db_cleaned_name}"
                    schema_sql = schema_sql.replace(f'REFERENCES "{ref_table}"', f'REFERENCES "{ref_table_new}"')
                    schema_sql = schema_sql.replace(f"REFERENCES '{ref_table}'", f"REFERENCES '{ref_table_new}'")
                    schema_sql = schema_sql.replace(f"REFERENCES `{ref_table}`", f"REFERENCES `{ref_table_new}`")
                    schema_sql = schema_sql.replace(f"REFERENCES {ref_table} ", f"REFERENCES {ref_table_new} ")
                    schema_sql = schema_sql.replace(f"REFERENCES {ref_table}(", f"REFERENCES {ref_table_new}(")
                    schema_sql = schema_sql.replace(f"REFERENCES [{ref_table}]", f"REFERENCES [{ref_table_new}]")


            # Create table in output database
            output_conn.execute(schema_sql)

            # Copy data
            source_cursor.execute(f"SELECT * FROM \"{table_tuple[0]}\";")
            rows = source_cursor.fetchall()

            if rows:
                # Get column names
                column_info = source_cursor.description
                column_names = [column[0] for column in column_info]

                # Get information about generated columns
                output_cursor = output_conn.cursor()
                output_cursor.execute(f"PRAGMA table_info(\"{table_name}\");")
                table_info = output_cursor.fetchall()

                # For debugging
                logger.debug(f"Table info for {table_name}: {table_info}")

                # In SQLite, identify generated columns more precisely
                generated_columns = set()
                for col_info in table_info:
                    # Check specifically for generated column syntax
                    # col_info structure: (cid, name, type, notnull, dflt_value, pk)
                    # For generated columns, we need to look at the type or the full schema
                    if "GENERATED" in str(col_info).upper() or " AS " in str(col_info).upper():
                        generated_columns.add(col_info[1])  # col_info[1] is the column name
                        logger.info(f"Identified generated column: {col_info[1]} in {table_name}")

                # If we didn't find any generated columns with the PRAGMA approach,
                # Try looking at the full schema as a fallback
                if not generated_columns:
                    output_cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name=?;",
                                          (table_name,))
                    schema_sql = output_cursor.fetchone()[0]

                    # Look for "GENERATED ALWAYS AS" or "AS (expression)" patterns in the schema
                    for col in column_names:
                        # Escape the column name for regex
                        col_escaped = re.escape(col)
                        if re.search(
                                rf'"{col_escaped}"|{col_escaped}\s+\w+(?:\(\d+\))?\s+(?:GENERATED\s+ALWAYS\s+)?AS\s+\(',
                                schema_sql, re.IGNORECASE):
                            generated_columns.add(col)
                            logger.info(f"Identified generated column from schema: {col} in {table_name}")

                # Filter out generated columns
                non_generated_columns = [col for col in column_names if col not in generated_columns]

                logger.debug(f"Columns in source: {column_names}")
                logger.debug(f"Generated columns identified: {generated_columns}")
                logger.debug(f"Non-generated columns to insert: {non_generated_columns}")

                # Prepare INSERT statement with only non-generated columns
                if non_generated_columns:  # Make sure we have columns to insert
                    placeholders = ", ".join(["?" for _ in non_generated_columns])
                    columns_str = ", ".join([f'"{col}"' for col in non_generated_columns])
                    insert_sql = f'INSERT INTO "{table_name}" ({columns_str}) VALUES ({placeholders})'

                    # Extract only the non-generated column values from rows
                    # Create a mapping of column index to include
                    col_indices = [column_names.index(col) for col in non_generated_columns]
                    filtered_rows = []
                    for row in rows:
                        filtered_row = tuple(row[i] for i in col_indices)
                        filtered_rows.append(filtered_row)

                    # Execute batch insert with filtered data
                    output_conn.executemany(insert_sql, filtered_rows)

            # Copy indexes
            source_cursor.execute("SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name=?;", (table_tuple[0],))
            index_sqls = source_cursor.fetchall()

            for index_sql_tuple in index_sqls:
                if index_sql_tuple[0] is not None:  # Skip internal indexes (NULL sql)
                    index_sql = index_sql_tuple[0]

                    # Replace old table name with new table name
                    if table_name != table_tuple[0]:

                        # First, check if there's an ON keyword in the index SQL
                        has_on_keyword = " ON " in index_sql

                        if has_on_keyword:
                            # If it has ON keyword, replace the table name after ON
                            index_sql = re.sub(
                                r'ON\s+["\']?(' + re.escape(table_tuple[0]) + r')["\']?',
                                f'ON "{table_name}"',
                                index_sql
                            )
                        else:
                            # If it doesn't have ON keyword, insert it with the new table name
                            index_sql = re.sub(
                                r'CREATE\s+INDEX\s+([^\s]+)\s+["\']?(' + re.escape(table_tuple[0]) + r')["\']?',
                                f'CREATE INDEX idx_{table_name.lower()}_index ON "{table_name}"',
                                index_sql
                            )

                        # Handle any remaining references to the old table name
                        index_sql = index_sql.replace(f'"{table_tuple[0]}"', f'"{table_name}"')
                        index_sql = index_sql.replace(f"'{table_tuple[0]}'", f"'{table_name}'")
                        index_sql = index_sql.replace(f" {table_tuple[0]} ", f" {table_name} ")
                        index_sql = index_sql.replace(f"idx_fk", f"idx_fk_{db_cleaned_name}")
                        index_sql = index_sql.replace(f"IPK_{table_tuple[0]}", f"IPK_{table_name}")
                        index_sql = index_sql.replace(f"IFK_{table_tuple[0]}", f"IFK_{table_name}")
                        index_sql = index_sql.replace(f"[{table_tuple[0]}]", f"[{table_name}]")
                        index_sql = index_sql.replace(f"idx_{table_tuple[0]}", f"idx_{table_name}")

                        # Fix spaces between ON and table name
                        index_sql = re.sub(r'ON\s+"([^"]+)"\s+', r'ON "\1" ', index_sql)

                        # Final check to remove duplicate table names (your specific issue)
                        index_sql = re.sub(
                            r'ON\s+["\']?(' + re.escape(table_name) + r')["\']?\s+["\']?(' + re.escape(
                                table_name) + r')["\']?',
                            f'ON "{table_name}"',
                            index_sql
                        )

                    try:
                        output_conn.execute(index_sql)
                    except sqlite3.OperationalError as e:
                        logger.warning(f"Could not create index for {table_name}: {e}", exc_info=e)

            # Get table structure and size
            source_cursor.execute(f"PRAGMA table_info(\"{table_tuple[0]}\");")
            columns_info = source_cursor.fetchall()
            column_count = len(columns_info)
            row_count = len(rows)

            # Track the merged table with enhanced metadata
            merged_tables[table_name] = {
                'source_database': db_name,
                'source_path': db_path,
                'original_table_name': table_tuple[0],
                'rows_copied': row_count,
                'column_count': column_count
            }

            # Register table in metadata
            register_table_metadata(output_conn, table_name, db_name, table_tuple[0], row_count, column_count)

            logger.info(
                f"Merged table '{table_tuple[0]}' from {db_name} to '{table_name}' in output database ({row_count} rows)")
    except Exception as e:
        logger.error(f"Error processing database {source_file}: {e}", exc_info=e)
        return {}
    finally:
        # Commit changes and close connections
        if source_conn:
            source_conn.close()
        if output_conn:
            output_conn.commit()
            output_conn.close()

        return merged_tables


def update_metadata(connection, merged_tables):
    """Update the metadata table in the target database"""

    # Create metadata table if it doesn't exist
    connection.execute('''
    CREATE TABLE IF NOT EXISTS metadata_merged_tables (
        table_name TEXT PRIMARY KEY,
        source_database TEXT,
        original_table_name TEXT,
        rows_copied INTEGER,
        merge_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Insert metadata records
    for table_name, info in merged_tables.items():
        connection.execute('''
        INSERT OR REPLACE INTO metadata_merged_tables 
        (table_name, source_database, original_table_name, rows_copied)
        VALUES (?, ?, ?, ?)
        ''', (
            table_name,
            info['source_database'],
            info['original_table_name'],
            info['rows_copied']
        ))


def to_sqlite(base_dir, dest_folder):
    sqlite_db_path = f'{dest_folder}/database.sqlite'

    # Walk through all folders in the directory
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            try:
                file_path = os.path.join(root, file)
                file_name, file_ext = os.path.splitext(file)

                if file.endswith(('.sqlite', '.db', '.sqlite3')):
                    if file_name == 'database':
                        continue
                    # merge_sqlite_file(file_path, sqlite_db_path)
                    logger.debug(f"Skipped appending {file_path} to {sqlite_db_path} in SQLite database.")
                elif file.endswith('.parquet'):
                    table_name = sanitize_table_name(root.replace(base_dir + "/", "").replace(".parquet", "").replace("\\",
                                                                                                  "_"))
                    df = parquet_to_dataframe(file_path)
                    dataframe_to_sqlite(df, table_name, sqlite_db_path)
                    logger.debug(f"Converted {file_path} to {table_name} in SQLite database.")
                elif file.endswith('.csv'):
                    table_name = sanitize_table_name(file_name)
                    # Process CSV files
                    df = pd.read_csv(file_path, engine="python")
                    dataframe_to_sqlite(df, table_name, sqlite_db_path)
                    logger.debug(f"Converted {file_path} to {table_name} in SQLite database.")
                elif file_ext in ['.xlsx', '.xls']:
                    df = pd.read_excel(file_path, sheet_name=None)  # Read all sheets
                    for sheet_name, sheet_df in df.items():
                        sheet_table_name = sanitize_table_name(f"{file_name}_{sheet_name}") # Append sheet name to table name
                        sheet_df = sanitize_column_names(sheet_df)  # Sanitize column names
                        dataframe_to_sqlite(sheet_df, sheet_table_name, sqlite_db_path)
                        logger.debug(
                            f"Converted {file_path} (Sheet: {sheet_name}) to {sheet_table_name} in SQLite database.")
                elif file.endswith('.dtd'):
                    dummy_xml_file = os.path.join(os.path.dirname(file_path), "dummy.xml")
                    copy_path = os.path.join(os.path.dirname(file_path), "dummy-bk.xml")
                    parse_dtd_to_xml(file_path, dummy_xml_file)
                    if os.path.exists(dummy_xml_file):
                        shutil.copy(dummy_xml_file, copy_path)
                        df = extract_tables_from_xml(dummy_xml_file)
                        if df is not None:
                            table_name = sanitize_table_name(file_name)
                            dataframe_to_sqlite(df, table_name, sqlite_db_path)
                            print(f"Converted {dummy_xml_file} to {table_name} in SQLite.")
                else:
                    continue  # Skip unsupported file types
            except Exception as e:
                logger.error(f"Error: {e} for {file_path}", exc_info=True)
                continue


def parquet_to_csv(base_dir):
    # Loop through each folder in the base directory
    for folder_name in os.listdir(base_dir):
        folder_path = os.path.join(base_dir, folder_name)

        # Skip if it's not a directory
        if not os.path.isdir(folder_path):
            continue

        # Loop through each file in the folder
        for file_name in os.listdir(folder_path):
            if file_name.endswith('.parquet'):
                file_path = os.path.join(folder_path, file_name)

                # Read the Parquet file into a DataFrame
                df = pd.read_parquet(file_path, engine='pyarrow')

                # Define the CSV file name and path
                csv_file_name = folder_name.replace('.parquet', '.csv')
                csv_file_path = os.path.join(base_dir, csv_file_name)

                # Save the DataFrame to a CSV file
                df.to_csv(csv_file_path, index=False)
                logger.debug(f'Converted {file_path} to {csv_file_path}')


# def convert_docx_to_txt(file_path):
#     doc = docx.Document(file_path)
#     return '\n'.join([para.text for para in doc.paragraphs])

# def convert_pdf_to_txt(file_path):
#     with open(file_path, 'rb') as file:
#         reader = PyPDF2.PdfReader(file)
#         text = ""
#         for page_num in range(len(reader.pages)):
#             page = reader.pages[page_num]
#             text += page.extract_text()
#         text += "\n\n"
#         return text

def convert_xlsx_to_txt(file_path):
    df = pd.read_excel(file_path, sheet_name=None)  # Read all sheets
    content = ""
    for sheet_name, data in df.items():
        content += f"Sheet: {sheet_name}\n"
        content += data.to_csv(index=False)
    return content


def convert_zip_to_txt(file_path, dest_folder):
    with zipfile.ZipFile(file_path, 'r') as zip_ref:
        zip_ref.extractall(dest_folder)
    return "Extracted ZIP file contents."


def convert_gz_to_txt(file_path, dest_folder):
    with gzip.open(file_path, 'rb') as f_in:
        with open(os.path.join(dest_folder, os.path.basename(file_path).replace('.gz', '')), 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    return "Extracted GZ file contents."


def fix_pypdfloader_output(pdf_path):
    loader = PyPDFLoader(pdf_path)
    documents = loader.load()

    # Post-process the extracted text to remove excessive newlines, but keep meaningful breaks
    for document in documents:
        text = document.page_content
        # Collapse multiple newlines into a single newline to preserve structure
        fixed_text = re.sub(r'\n{2,}', '\n\n', text)  # Keeps double newlines for section breaks
        # fixed_text = " ".join(line.strip() for line in fixed_text.splitlines())

        document.page_content = fixed_text  # Update the document with cleaned content

    return documents


def fix_ref_paths(src_folder):
    logger.debug("Fixing reference paths in OpenAPI spec...")

    for root, dirs, files in os.walk(src_folder):
        for file_name in files:
            file_ext = os.path.splitext(file_name)[1].lower()
            file_path = os.path.join(root, file_name)

            if file_ext == ".yml":
                with open(file_path, "r") as file:
                    openapi_spec = yaml.safe_load(file)

                if openapi_spec:
                    try:
                        # Extract schemas
                        components = openapi_spec.setdefault("components", {})
                        schemas = components.setdefault("schemas", {})

                        # Step 1: Fix schema names by removing leading `#`
                        updated_schemas = {}
                        schema_name_map = {}

                        for key in schemas:
                            new_key = key.lstrip("#")  # Remove leading `#`
                            schema_name_map[key] = new_key
                            updated_schemas[new_key] = schemas[key]

                        # Replace old schemas with updated ones
                        openapi_spec["components"]["schemas"] = updated_schemas

                        # Step 2: Collect all $ref values
                        referenced_schemas = set()

                        def collect_refs(node):
                            """ Collects referenced schemas to check if they exist """
                            if isinstance(node, dict):
                                for key, value in node.items():
                                    if key == "$ref" and isinstance(value, str) and value.startswith("#/components/schemas/"):
                                        ref_schema = value.split("/")[-1]  # Extract schema name
                                        referenced_schemas.add(ref_schema)
                                    else:
                                        collect_refs(value)
                            elif isinstance(node, list):
                                for item in node:
                                    collect_refs(item)

                        collect_refs(openapi_spec)

                        # Step 3: Fix all $ref values
                        def fix_ref_paths(node):
                            """ Recursively fixes incorrect $ref paths """
                            if isinstance(node, dict):
                                for key, value in node.items():
                                    if key == "$ref" and isinstance(value, str):
                                        for old_name, new_name in schema_name_map.items():
                                            if value == f"#/{old_name}":
                                                corrected_value = f"#/components/schemas/{new_name}"
                                                logger.debug(f"Fixing $ref: {value} → {corrected_value}")
                                                node[key] = corrected_value
                                    else:
                                        fix_ref_paths(value)
                            elif isinstance(node, list):
                                for item in node:
                                    fix_ref_paths(item)

                        fix_ref_paths(openapi_spec)

                        # Step 4: Add missing schemas with dummy placeholders
                        for ref_schema in referenced_schemas:
                            if ref_schema not in updated_schemas:
                                logger.warning(f"Adding missing schema: {ref_schema}")
                                updated_schemas[ref_schema] = {
                                    "description": f"Placeholder for {ref_schema}.",
                                    "type": "object",
                                    "properties": {}
                                }

                        # Save the corrected OpenAPI YAML file
                        with open(file_path, "w") as file:
                            yaml.dump(openapi_spec, file, default_flow_style=False)

                    except Exception as e:
                        logger.error(f"Error processing {file_path}: {e}", exc_info=True)
                        continue

def extract_world_info(message_dict: dict):
    info_dict = {}
    info_dict['db_id'] = message_dict['db_id']
    info_dict['query'] = message_dict['query']
    info_dict['evidence'] = message_dict.get('evidence', '')
    info_dict['difficulty'] = message_dict.get('difficulty', '')
    info_dict['ground_truth'] = message_dict.get('ground_truth', '')
    info_dict['send_to'] = message_dict.get('send_to', '')
    return info_dict


def is_email(string):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    match = re.match(pattern, string)
    if match:
        return True
    else:
        return False


def is_valid_date(date_str):
    if (not isinstance(date_str, str)):
        return False
    date_str = date_str.split()[0]
    if len(date_str) != 10:
        return False
    pattern = r'^\d{4}-\d{2}-\d{2}$'
    if re.match(pattern, date_str):
        year, month, day = map(int, date_str.split('-'))
        if year < 1 or month < 1 or month > 12 or day < 1 or day > 31:
            return False
        else:
            return True
    else:
        return False


def is_valid_date_column(col_value_lst):
    for col_value in col_value_lst:
        if not is_valid_date(col_value):
            return False
    return True


# check if valid format
def check_selector_response(json_data: Dict) -> bool:
    FLAGS = ['keep_all', 'drop_all']
    for k, v in json_data.items():
        if isinstance(v, str):
            if v not in FLAGS:
                logger.error(f"error: invalid table flag: {v}\n", exc_info=True)
                logger.debug(f"json_data: {json_data}\n\n")
                return False
        elif isinstance(v, list):
            pass
        else:
            logger.error(f"error: invalid flag type: {v}\n", exc_info=True)
            logger.debug(f"json_data: {json_data}\n\n")
            return False
    return True


def parse_json(text: str, validate: bool = True) -> dict:
    # Find JSON chunks in a string
    start = text.find("```json")
    end = text.find("```", start + 7)

    # If JSON chunk found
    if start != -1 and end != -1:
        json_string = text[start + 7: end]

        try:
            # 解析 JSON 字符串
            json_data = json.loads(json_string)
            if validate:
                valid = check_selector_response(json_data)
                if valid:
                    return json_data
                else:
                    return {}
            else:
                return json_data
        except:
            logger.error(f"error: parse json error!\n", exc_info=True)
            logger.debug(f"json_string: {json_string}\n")
            logger.debug(f"original_string: {text}\n\n")
            pass

    return {}


def load_json_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        logger.debug(f"load json file from {path}")
        return json.load(f)

def extract_json_from_response(response: str) -> Dict:
    """
    Extract and parse JSON from a response that might contain markdown code blocks.

    Args:
        response: String response that might contain ```json blocks

    Returns:
        Dict containing the parsed JSON
    """
    # Ensure response is a string, in case it's passed as a tuple or other non-string type
    if isinstance(response, tuple):
        response = response[0]  # Get the string from the tuple

    try:
        # Try to parse as pure JSON first
        return json.loads(response)
    except json.JSONDecodeError:
        # Look for ```json blocks
        json_pattern = r'```json\s*(.*?)\s*```'
        matches = re.findall(json_pattern, response, re.DOTALL)

        if matches:
            # Try to parse the content of the first json block
            try:
                return json.loads(matches[0])
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON block: {e}")

        # If no JSON blocks found, try to extract anything that looks like JSON
        json_pattern = r'\{[^}]+\}'
        matches = re.findall(json_pattern, response, re.DOTALL)

        if matches:
            try:
                return json.loads(matches[0])
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON-like content: {e}")

        logger.error("No valid JSON found in response")
        return ""

async def run_rag(app, question: str, breakdown: bool, load_data: bool, concise_response: bool, global_flag: bool, project: str):
    # Run
    inputs = {
        "question": question,
        "breakdown": breakdown,
        "load_data": load_data,
        "concise": concise_response,
        "global_flag": global_flag
    }
    config = {
        "recursion_limit": 50,
        "configurable": {
            "thread_id": "chicory-ui-discovery",
            "thread_ts": datetime.now(UTC).isoformat(),
            "client": "slack-api",
            "user": "slack-bot",
            "project": project,
        }
    }
    try:
        async for event in app.astream(inputs, config=config):
            for key, value in event.items():
                logger.debug(f"Node '{key}':")
        if 'generation' in value:
            return value["generation"]
        elif 'data_summary' in value:
            return value["data_summary"]
        else:
            return value
    except Exception as e:
        logger.error(e)
        return f"Not found. {str(e)}"


class CustomBeautifulSoupTransformer(BeautifulSoupTransformer):
    def transform_documents(self, documents, **kwargs):
        transformed_documents = []
        for doc in documents:
            soup = BeautifulSoup(doc.page_content, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Get text while preserving some structure
            text = soup.get_text(separator='\n', strip=True)

            # Remove excessive newlines
            lines = (line.strip() for line in text.splitlines())
            text = '\n'.join(line for line in lines if line)

            doc.page_content = text
            transformed_documents.append(doc)
        return transformed_documents
