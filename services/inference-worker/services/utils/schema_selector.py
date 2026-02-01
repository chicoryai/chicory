import json
import logging
from logging import getLogger

from typing import List
from copy import deepcopy

import sqlite3
import time
import sys
import os
import pandas as pd
from tqdm import trange

from langchain_core.documents import Document
from services.workflows.base import BaseAgent
from services.integration.sqlalchemy_engine import fetch_table_schema, \
    fetch_table_metadata, fetch_all_databases, run_query, get_connection
from services.utils.const import concise_template, features_template, SELECTOR_NAME, selector_template, \
    relationship_template
from services.utils.llm import safe_call_llm
from services.utils.tools import load_json_file, is_email, parse_json, extract_world_info, is_valid_date_column, \
    create_tables_json, generate_erd, export_table_ddls_from_schema

PLATFORM_QA_MODEL = os.getenv("MODEL", "gpt-4o")

logger = getLogger(__name__)
logging.getLogger('thrift_backend').setLevel(logging.INFO)

class Selector(BaseAgent):
    """
    Get database description and if need, extract relative tables & columns
    """
    name = SELECTOR_NAME
    description = "Get database description and if need, extract relative tables & columns"

    def __init__(self, data_path: str, tables_json_path: str, prompt_template: str, project: str, lazy: bool = False,
                 without_selector: bool = False, database_type="", database=None):
        super().__init__()
        # self.data_path = data_path.strip('/').strip('\\')
        self.data_path = data_path.strip('\\')
        self.tables_json_path = tables_json_path
        self.default_db_id = project
        self.db2infos = {}  # summary of db (stay in the memory during generating prompt)
        self.db2dbjsons = {}  # store all db to tables.json dict by tables_json_path
        self.init_db2jsons()
        if not lazy:
            self._load_all_db_info()
        self._message = {}
        self.without_selector = without_selector
        self.prompt_template = prompt_template
        self.database_type = database_type
        self.database_name = database

    def init_db2jsons(self):
        if not os.path.exists(self.tables_json_path):
            raise FileNotFoundError(f"tables.json not found in {self.tables_json_path}")
        data = load_json_file(self.tables_json_path)
        if not any(data):
            raise ValueError(f"The file 'tables.json' in {self.tables_json_path} is empty or contains no valid data.")
        for item in data:
            if not item:
                continue

            table_names = item['table_names']
            logger.debug(f"table_names: {table_names}")
            # Number of statistical tables
            item['table_count'] = len(table_names)

            column_count_lst = [0] * len(table_names)
            for tb_idx, col in item['column_names']:
                if tb_idx >= 0:
                    column_count_lst[tb_idx] += 1
            # Maximum number of column names
            item['max_column_count'] = max(column_count_lst)
            item['total_column_count'] = sum(column_count_lst)
            item['avg_column_count'] = sum(column_count_lst) // len(table_names)

            # print()
            # print(f"db_id: {db_id}")
            # print(f"table_count: {item['table_count']}")
            # print(f"max_column_count: {item['max_column_count']}")
            # print(f"total_column_count: {item['total_column_count']}")
            # print(f"avg_column_count: {item['avg_column_count']}")
            # time.sleep(0.2)
            self.db2dbjsons[self.default_db_id] = item

    def _get_column_attributes(self, cursor, table, df=None):
        column_names = []
        column_types = []
        if cursor:
            if self.database_type == "databricks":
                primary_keys = []
                columns = []
                try:
                    # Query column information
                    q1 = f"DESCRIBE TABLE {self.database_name}.{table}"
                    logger.debug(f"sql: {q1}")
                    cursor.execute(q1)
                    columns = cursor.fetchall()

                    # Query primary key information
                    q2 = f"""
                            SELECT column_name
                            FROM information_schema.key_column_usage
                            WHERE table_name = {table}
                              AND constraint_name IN (
                                  SELECT constraint_name
                                  FROM information_schema.table_constraints
                                  WHERE table_name = {table} AND constraint_type = 'PRIMARY KEY'
                              );
                        """
                    logger.debug(f"sql: {q2}")
                    cursor.execute(q2)
                    potential_pk = cursor.fetchall()
                    primary_keys = [row[0] for row in potential_pk]
                except Exception as e:
                    logger.debug(f"An error occurred: {e}", exc_info=True)
                # Construct column information
                columns_info = []
                for column in columns:
                    column_names.append(column[0])  # Column name
                    column_types.append(column[1])  # Data type
                    is_pk = column[0] in primary_keys
                    column_info = {
                        'name': column[0],
                        'type': column[1],
                        'not_null': None,  # Nullability not available in DESCRIBE TABLE
                        'primary_key': is_pk
                    }
                    columns_info.append(column_info)
            elif self.database_type == "oracle":
                primary_keys = []
                columns = []
                try:
                    # Query column information
                    q1 = f"""
                    SELECT column_name, data_type, nullable, data_length, data_precision, data_scale
                    FROM all_tab_columns
                    WHERE table_name = '{table.upper()}'
                    AND owner = '{self.database_name.upper()}'
                    """
                    logger.debug(f"sql: {q1}")
                    cursor.execute(q1)
                    columns = cursor.fetchall()

                    # Query primary key information
                    q2 = f"""
                    SELECT column_name
                    FROM all_cons_columns
                    WHERE constraint_name = (
                        SELECT constraint_name
                        FROM all_constraints
                        WHERE table_name = '{table.upper()}'
                        AND owner = '{self.database_name.upper()}'
                        AND constraint_type = 'P'
                    )
                    """
                    logger.debug(f"sql: {q2}")
                    cursor.execute(q2)
                    potential_pk = cursor.fetchall()
                    primary_keys = [row[0] for row in potential_pk]
                except Exception as e:
                    logger.debug(f"An error occurred: {e}", exc_info=True)

                # Construct column information
                columns_info = []
                for column in columns:
                    column_name = column[0]
                    data_type = column[1]
                    nullable = column[2]
                    data_length = column[3]
                    data_precision = column[4]
                    data_scale = column[5]

                    column_names.append(column_name)

                    # Construct the full data type string
                    if data_type in ('NUMBER', 'FLOAT'):
                        if data_precision is not None and data_scale is not None:
                            full_data_type = f"{data_type}({data_precision},{data_scale})"
                        elif data_precision is not None:
                            full_data_type = f"{data_type}({data_precision})"
                        else:
                            full_data_type = data_type
                    elif data_type in ('CHAR', 'VARCHAR2', 'NCHAR', 'NVARCHAR2'):
                        full_data_type = f"{data_type}({data_length})"
                    else:
                        full_data_type = data_type

                    column_types.append(full_data_type)

                    is_pk = column_name in primary_keys
                    column_info = {
                        'name': column_name,
                        'type': full_data_type,
                        'not_null': nullable == 'N',  # 'N' means Not Null
                        'primary_key': is_pk
                    }
                    columns_info.append(column_info)
            else:
                # Query table column attribute information
                cursor.execute(f"PRAGMA table_info(`{table}`)")
                columns = cursor.fetchall()

                # Construct a dictionary list of column attribute information
                columns_info = []
                primary_keys = []
                for column in columns:
                    column_names.append(column[1])
                    column_types.append(column[2])
                    is_pk = bool(column[5])
                    if is_pk:
                        primary_keys.append(column[1])
                    column_info = {
                        'name': column[1],  # List
                        'type': column[2],  # type of data
                        'not_null': bool(column[3]),  # Whether to allow empty
                        'primary_key': bool(column[5])  # Is it a primary key?
                    }
                    columns_info.append(column_info)
        elif df is not None:
            # For DataFrame, get column attribute information
            columns_info = []
            primary_keys = []  # Assuming no primary key information in CSV/XLSX
            column_names = df.columns.tolist()
            column_types = [str(df[col].dtype) for col in df.columns]
            for col_name, col_type in zip(column_names, column_types):
                column_info = {
                    'name': col_name,  # List
                    'type': col_type,  # type of data
                    'not_null': not df[col_name].isnull().any(),  # Whether to allow empty
                    'primary_key': False  # Assuming no primary key information
                }
                columns_info.append(column_info)
        else:
            raise ValueError("Either cursor or df must be provided")

        return column_names, column_types

    def _get_unique_column_values_str(self, cursor, table, column_names, column_types,
                                      json_column_names, is_key_column_lst, df=None):

        col_to_values_str_lst = []
        col_to_values_str_dict = {}

        key_col_list = [json_column_names[i] for i, flag in enumerate(is_key_column_lst) if flag]

        len_column_names = len(column_names)
        sample_percent = 1  # safest sample

        if self.database_type == "databricks":
            # Step 1: Estimate the number of rows in the table
            try:
                count_sql = f"SELECT COALESCE(COUNT(*), 0) FROM {self.database_name}.{table}"
                logger.debug(f"Counting rows: sql: {count_sql}")
                cursor.execute(count_sql)
                results = cursor.fetchall_arrow()
                df = results.to_pandas()
                # Extract the total row count from the DataFrame
                total_rows = df.iloc[0, 0]  # First row, first column
                logger.debug(f"Table: {self.database_name}.{table}; Total rows: {total_rows}")

                # Step 2: Dynamically determine the sampling percentage
                # Adjust based on the total number of rows
                if total_rows >= 100_000_000:  # For very large tables, sample 1%
                    sample_percent = 1
                elif total_rows >= 10_000_000:  # For medium-sized tables, sample 5%
                    sample_percent = 5
                else:  # For smaller tables, sample 10%
                    sample_percent = 10
            except Exception as e:
                logger.debug(f"An error occurred: {e}", exc_info=True)
        elif self.database_type == "oracle":
            # Step 1: Estimate the number of rows in the table
            try:
                count_sql = f"""
                SELECT COALESCE(num_rows, 0) as row_count
                FROM all_tables
                WHERE table_name = '{table.upper()}'
                AND owner = '{self.database_name.upper()}'
                """
                logger.debug(f"Estimating rows: sql: {count_sql}")
                cursor.execute(count_sql)
                result = cursor.fetchone()
                total_rows = result[0] if result else 0
                logger.debug(f"Table: {self.database_name}.{table}; Estimated rows: {total_rows}")

                # Step 2: Dynamically determine the sampling percentage
                # Adjust based on the total number of rows
                if total_rows >= 100_000_000:  # For very large tables, sample 1%
                    sample_percent = 1
                elif total_rows >= 10_000_000:  # For medium-sized tables, sample 5%
                    sample_percent = 5
                else:  # For smaller tables, sample 10%
                    sample_percent = 10
            except Exception as e:
                logger.debug(f"An error occurred: {e}", exc_info=True)
        elif self.database_type == "sqlite":
            # Step 1: Count rows in the table for SQLite
            try:
                count_sql = f"SELECT COUNT(*) FROM {table}"
                logger.debug(f"Counting rows: sql: {count_sql}")
                cursor.execute(count_sql)
                result = cursor.fetchone()
                total_rows = result[0] if result else 0
                logger.debug(f"Table: {table}; Total rows: {total_rows}")

                # Step 2: Dynamically determine the sampling percentage
                if total_rows >= 100_000_000:  # For very large tables, sample 1%
                    sample_percent = 1
                elif total_rows >= 10_000_000:  # For medium-sized tables, sample 5%
                    sample_percent = 5
                else:  # For smaller tables, sample 10%
                    sample_percent = 10
            except Exception as e:
                logger.debug(f"An error occurred: {e}", exc_info=True)

        # TODO: Skipping very big tables to avoid long query time
        if sample_percent > 1:
            for idx, column_name in enumerate(column_names):
                # Skip primary keys and foreign keys
                if column_name in key_col_list:
                    continue

                lower_column_name = column_name.lower()
                # If the column name ends with id, email, or url, use an empty string
                if lower_column_name.endswith('id') or lower_column_name.endswith('email') or lower_column_name.endswith(
                        'url'):
                    values_str = ''
                    col_to_values_str_dict[column_name] = values_str
                    continue

                if cursor:
                    values = []
                    try:
                        if self.database_type == "databricks":
                            # Step 3: Query based on the row size
                            if sample_percent == 1:
                                sql = f"""
                                       SELECT {column_name}
                                       FROM {self.database_name}.{table} TABLESAMPLE({sample_percent} PERCENT)
                                       WHERE {column_name} IS NOT NULL
                                       LIMIT 1000
                                    """
                            elif sample_percent == 5:
                                sql = f"""
                                       SELECT {column_name}
                                       FROM {self.database_name}.{table}
                                       WHERE MOD(HASH({column_name}), 100) < {sample_percent}
                                       GROUP BY {column_name}
                                       LIMIT 1000
                                    """
                            else:
                                sql = f"""
                                   WITH ranked_values AS (
                                        SELECT {column_name},
                                               approx_count_distinct({column_name}) as freq
                                        FROM {self.database_name}.{table} TABLESAMPLE({sample_percent} PERCENT)
                                        WHERE {column_name} IS NOT NULL
                                        GROUP BY {column_name}
                                        ORDER BY freq DESC
                                        LIMIT 1000
                                   )
                                   SELECT {column_name}
                                   FROM ranked_values
                                    """
                            logger.debug(f"Sampling column: {column_name}; sql: {sql}")
                            cursor.execute(sql)
                            results = cursor.fetchall_arrow()
                            df = results.to_pandas()
                            values = df[column_name].dropna().unique().tolist()
                        elif self.database_type == "oracle":
                            # Step 3: Query based on the row size
                            if sample_percent == 1:
                                sql = f"""
                                       SELECT DISTINCT {column_name}
                                       FROM (
                                           SELECT {column_name}
                                           FROM {self.database_name}.{table} SAMPLE({sample_percent})
                                           WHERE {column_name} IS NOT NULL
                                       )
                                       WHERE ROWNUM <= 1000
                                    """
                            elif sample_percent == 5:
                                sql = f"""
                                       SELECT DISTINCT {column_name}
                                       FROM (
                                           SELECT {column_name}
                                           FROM {self.database_name}.{table}
                                           WHERE MOD(ORA_HASH({column_name}), 100) < {sample_percent}
                                       )
                                       WHERE ROWNUM <= 1000
                                    """
                            else:
                                sql = f"""
                                   WITH ranked_values AS (
                                        SELECT {column_name},
                                               COUNT(*) as freq
                                        FROM (
                                            SELECT {column_name}
                                            FROM {self.database_name}.{table} SAMPLE({sample_percent})
                                            WHERE {column_name} IS NOT NULL
                                        )
                                        GROUP BY {column_name}
                                        ORDER BY freq DESC
                                   )
                                   SELECT {column_name}
                                   FROM ranked_values
                                   WHERE ROWNUM <= 1000
                                    """

                            logger.debug(f"Sampling column: {column_name}; sql: {sql}")
                            cursor.execute(sql)
                            results = cursor.fetchall()
                            values = [row[0] for row in results if row[0] is not None]
                        elif self.database_type == "sqlite":
                            # SQLite doesn't support TABLESAMPLE or similar features
                            # Use simple sampling based on RANDOM() function for larger tables
                            if total_rows > 10000:
                                if sample_percent <= 1:
                                    # For very large tables, use more aggressive sampling
                                    sql = f"""
                                        SELECT {column_name}
                                        FROM {table}
                                        WHERE {column_name} IS NOT NULL AND (ABS(RANDOM()) % 100) < {sample_percent}
                                        GROUP BY {column_name}
                                        ORDER BY COUNT(*) DESC
                                        LIMIT 1000
                                    """
                                elif sample_percent <= 5:
                                    # For medium-sized tables
                                    sql = f"""
                                        SELECT {column_name}
                                        FROM {table}
                                        WHERE {column_name} IS NOT NULL AND (ABS(RANDOM()) % 100) < {sample_percent}
                                        GROUP BY {column_name}
                                        ORDER BY COUNT(*) DESC
                                        LIMIT 1000
                                    """
                                else:
                                    # For smaller tables
                                    sql = f"""
                                        SELECT {column_name}
                                        FROM {table}
                                        WHERE {column_name} IS NOT NULL
                                        GROUP BY {column_name}
                                        ORDER BY COUNT(*) DESC
                                        LIMIT 1000
                                    """
                            else:
                                # For small tables, just get all distinct values
                                sql = f"""
                                    SELECT {column_name}
                                    FROM {table}
                                    WHERE {column_name} IS NOT NULL
                                    GROUP BY {column_name}
                                    ORDER BY COUNT(*) DESC
                                    LIMIT 1000
                                """

                            logger.debug(f"Sampling column: {column_name}; sql: {sql}")
                            cursor.execute(sql)
                            results = cursor.fetchall()
                            values = [row[0] for row in results if row[0] is not None]
                        else:
                            sql = f"SELECT {column_name} FROM {table} GROUP BY {column_name} ORDER BY COUNT(*) DESC LIMIT 1000"
                            logger.debug(f"Sampling column: {column_name}; sql: {sql}")
                            cursor.execute(sql)
                            values = cursor.fetchall()
                    except Exception as e:
                        logger.debug(f"Unexpected error occurred: {e}", exc_info=True)
                else:
                    values = df[column_name].dropna().unique().tolist()

                values_str = ''
                # Try to get value examples string, if exception, use an empty string
                try:
                    if values:
                        values_str = self._get_value_examples_str(values, column_types[idx])
                except Exception as e:
                    logger.error(f"\nerror: get_value_examples_str failed, Exception:\n{e}\n", exc_info=True)

                col_to_values_str_dict[column_name] = values_str

        for k, column_name in enumerate(json_column_names):
            values_str = ''
            is_key = is_key_column_lst[k]

            # Primary key or foreign key do not need value string
            if is_key:
                values_str = ''
            elif column_name in col_to_values_str_dict:
                values_str = col_to_values_str_dict[column_name]
            else:
                logger.debug(col_to_values_str_dict)
                time.sleep(3)
                logger.warning(f"WARNING: column_name: {column_name} not found in col_to_values_str_dict")

            col_to_values_str_lst.append([column_name, values_str])

        return col_to_values_str_lst

    def _get_value_examples_str(self, values: List[object], col_type: str):
        if not values:
            return ''
        if len(values) > 10 and col_type in ['INTEGER', 'REAL', 'NUMERIC', 'FLOAT', 'INT']:
            return ''

        vals = []
        has_null = False
        for v in values:
            if v is None:
                has_null = True
            else:
                tmp_v = str(v).strip()
                if tmp_v == '':
                    continue
                else:
                    vals.append(v)
        if not vals:
            return ''

        if col_type in ['TEXT', 'VARCHAR']:
            new_values = []
            for v in vals:
                if not isinstance(v, str):
                    new_values.append(v)
                else:
                    v = v.strip()
                    if v == '':  # exclude empty string
                        continue
                    elif ('https://' in v) or ('http://' in v):  # exclude url
                        return ''
                    elif is_email(v):  # exclude email
                        return ''
                    else:
                        new_values.append(v)
            vals = new_values
            tmp_vals = [len(str(a)) for a in vals]
            if not tmp_vals:
                return ''
            max_len = max(tmp_vals)
            if max_len > 50:
                return ''

        if not vals:
            return ''

        vals = vals[:6]

        is_date_column = is_valid_date_column(vals)
        if is_date_column:
            vals = vals[:1]

        if has_null:
            vals.insert(0, None)

        val_str = str(vals)
        return val_str

    # support databricks - not in use
    def _load_single_db_info(self, db_id: str, database: str) -> dict:
        table2coldescription = {}
        table2primary_keys = {}
        table_foreign_keys = {}
        table_unique_column_values = {}

        # Fetch table list from Databricks
        query = f"SHOW TABLES IN {database}"
        tables_df = run_query(query, "databricks", self.default_db_id)

        for _, row in tables_df.iterrows():
            table_name = row['tableName']
            logger.debug(f"Processing Table: {table_name}")
            try:
                # Fetch schema and metadata from Databricks
                schema = fetch_table_schema(database, table_name, "databricks")
                metadata = fetch_table_metadata(database, table_name, "databricks")
            except Exception as e:
                logger.error(f"Table {table_name} does not exist in database {database}: {e}", exc_info=True)
                continue

            columns_info = [
                {"name": col['col_name'], "type": col['data_type'], "not_null": False, "primary_key": False}
                for col in schema
            ]

            # Extract unique column values (if required)
            column_names = [col['col_name'] for col in schema]
            column_types = [col['data_type'] for col in schema]
            col_to_values_str_lst = [
                [col, metadata["sample_data"][0].get(col, "")] if col in metadata["sample_data"][0] else [col, ""]
                for col in column_names
            ]

            # Populate schema details
            table2coldescription[table_name] = [{"name": col['col_name'], "type": col['data_type']} for col in schema]
            table_unique_column_values[table_name] = col_to_values_str_lst

        result = {
            "desc_dict": table2coldescription,
            "value_dict": table_unique_column_values,
            "pk_dict": table2primary_keys,
            "fk_dict": table_foreign_keys,
        }
        return result

    def _load_single_db_info(self, db_id: str) -> dict:
        table2coldescription = {}  # Dict {table_name: [(column_name, full_column_name, column_description), ...]}
        table2primary_keys = {}  # DIct {table_name: [primary_key_column_name,...]}

        table_foreign_keys = {}  # Dict {table_name: [(from_col, to_table, to_col), ...]}
        table_unique_column_values = {}  # Dict {table_name: [(column_name, examples_values_str)]}

        db_dict = self.db2dbjsons[db_id] if self.db2dbjsons else {}

        # todo: gather all pk and fk id list
        important_key_id_lst = []
        keys = []
        if 'primary_keys' in db_dict:
            keys += db_dict['primary_keys']
        if 'foreign_keys' in db_dict:
            keys += db_dict['foreign_keys']
        for col_id in keys:
            if isinstance(col_id, list):
                important_key_id_lst.extend(col_id)
            else:
                important_key_id_lst.append(col_id)

        table_names_original_lst = db_dict['table_names_original']
        for tb_idx, tb_name in enumerate(table_names_original_lst):
            # Iterate over original column names
            all_column_names_original_lst = db_dict['column_names_original']

            all_column_names_full_lst = db_dict['column_names']
            col2dec_lst = []

            pure_column_names_original_lst = []
            is_key_column_lst = []
            for col_idx, (root_tb_idx, orig_col_name) in enumerate(all_column_names_original_lst):
                if root_tb_idx != tb_idx:
                    continue
                pure_column_names_original_lst.append(orig_col_name)
                if col_idx in important_key_id_lst:
                    is_key_column_lst.append(True)
                else:
                    is_key_column_lst.append(False)
                full_col_name: str = all_column_names_full_lst[col_idx][1]
                full_col_name = full_col_name.replace('_', ' ')
                cur_desc_obj = [orig_col_name, full_col_name, '']
                col2dec_lst.append(cur_desc_obj)
            table2coldescription[tb_name] = col2dec_lst

            table_foreign_keys[tb_name] = []
            table_unique_column_values[tb_name] = []
            table2primary_keys[tb_name] = []

            if os.path.exists(f"{self.data_path}/database.sqlite"):
                file_format = 'sqlite'
            elif os.path.exists(f"{self.data_path}/{tb_name}.csv"):
                file_format = 'csv'
            elif os.path.exists(f"{self.data_path}/{tb_name}.xlsx"):
                file_format = 'xlsx'
            elif os.path.exists(f"{self.data_path}/{tb_name}.xls"):
                file_format = 'xls'
            else:
                file_format = 'ni'

            if file_format == 'sqlite' or self.database_type == "databricks" or self.database_type == "oracle" or self.database_type == "sqlite":
                if self.database_type == "databricks" or self.database_type == "oracle":
                    try:
                        conn = get_connection(self.database_type, self.default_db_id)
                        cursor = conn.cursor()
                        logger.debug(f"Processing table: {tb_name}")
                        all_sqlite_column_names_lst, all_sqlite_column_types_lst = self._get_column_attributes(cursor,
                                                                                                               tb_name)
                        col_to_values_str_lst = self._get_unique_column_values_str(cursor, tb_name,
                                                                                   all_sqlite_column_names_lst,
                                                                                   all_sqlite_column_types_lst,
                                                                                   pure_column_names_original_lst,
                                                                                   is_key_column_lst)
                    except Exception as e:
                        logger.error(f"Error processing Databricks table {tb_name}: {str(e)}", exc_info=True)
                        # Return empty lists if there's an error
                        all_sqlite_column_names_lst, all_sqlite_column_types_lst = [], []
                        col_to_values_str_lst = []
                    finally:
                        if cursor:
                            cursor.close()
                        if conn:
                            conn.close()
                else:
                    # For file_format == 'sqlite' but no specific database_type
                    db_path = f"{self.data_path}/database.sqlite"
                    # db_path = f"{self.data_path}/{db_id}.sqlite"
                    logger.debug(f"db_path: {db_path}")
                    conn = sqlite3.connect(db_path)
                    conn.text_factory = lambda b: b.decode(
                        errors="ignore")  # avoid gbk/utf8 error, copied from sql-eval.exec_eval
                    cursor = conn.cursor()
                    logger.debug(f"Processing table: {tb_name}")
                    all_sqlite_column_names_lst, all_sqlite_column_types_lst = self._get_column_attributes(cursor,
                                                                                                           tb_name)
                    col_to_values_str_lst = self._get_unique_column_values_str(cursor, tb_name,
                                                                               all_sqlite_column_names_lst,
                                                                               all_sqlite_column_types_lst,
                                                                               pure_column_names_original_lst,
                                                                               is_key_column_lst)
                    if cursor:
                        cursor.close()
                    if conn:
                        conn.close()
            elif file_format == 'csv':
                csv_file = f"{self.data_path}/{tb_name}.csv"
                df = pd.read_csv(csv_file)
                all_sqlite_column_names_lst, all_sqlite_column_types_lst = self._get_column_attributes(None, tb_name,
                                                                                                       df)
                col_to_values_str_lst = self._get_unique_column_values_str(None, tb_name, all_sqlite_column_names_lst,
                                                                           all_sqlite_column_types_lst,
                                                                           pure_column_names_original_lst,
                                                                           is_key_column_lst, df)
            elif file_format == 'xlsx':
                xlsx_file = f"{self.data_path}/{tb_name}.xlsx"
                df = pd.read_excel(xlsx_file)
                all_sqlite_column_names_lst, all_sqlite_column_types_lst = self._get_column_attributes(None, tb_name,
                                                                                                       df)
                col_to_values_str_lst = self._get_unique_column_values_str(None, tb_name, all_sqlite_column_names_lst,
                                                                           all_sqlite_column_types_lst,
                                                                           pure_column_names_original_lst,
                                                                           is_key_column_lst, df)
            table_unique_column_values[tb_name] = col_to_values_str_lst

        if file_format == 'sqlite' or self.database_type == "databricks" or self.database_type == "oracle":
            foreign_keys_lst = db_dict['foreign_keys']
            for from_col_idx, to_col_idx in foreign_keys_lst:
                from_col_name = all_column_names_original_lst[from_col_idx][1]
                from_tb_idx = all_column_names_original_lst[from_col_idx][0]
                from_tb_name = table_names_original_lst[from_tb_idx]

                to_col_name = all_column_names_original_lst[to_col_idx][1]
                to_tb_idx = all_column_names_original_lst[to_col_idx][0]
                to_tb_name = table_names_original_lst[to_tb_idx]

                table_foreign_keys[from_tb_name].append((from_col_name, to_tb_name, to_col_name))

            if 'primary_keys' in db_dict:
                for pk_idx in db_dict['primary_keys']:
                    pk_idx_lst = []
                    if isinstance(pk_idx, int):
                        pk_idx_lst.append(pk_idx)
                    elif isinstance(pk_idx, list):
                        pk_idx_lst = pk_idx
                    else:
                        err_message = f"pk_idx: {pk_idx} is not int or list"
                        logger.error(err_message, exc_info=True)
                        raise Exception(err_message)
                    for cur_pk_idx in pk_idx_lst:
                        tb_idx = all_column_names_original_lst[cur_pk_idx][0]
                        col_name = all_column_names_original_lst[cur_pk_idx][1]
                        tb_name = table_names_original_lst[tb_idx]
                        table2primary_keys[tb_name].append(col_name)

        time.sleep(1)

        result = {
            "desc_dict": table2coldescription,
            "value_dict": table_unique_column_values,
            "pk_dict": table2primary_keys,
            "fk_dict": table_foreign_keys
        }
        return result

    def _get_unique_column_values_str_from_df(self, df: pd.DataFrame, column_names: list, is_key_column_lst: list):
        unique_values = []
        for col_name, is_key in zip(column_names, is_key_column_lst):
            if is_key:
                examples_values_str = ', '.join(map(str, df[col_name].unique()[:5]))
                unique_values.append((col_name, examples_values_str))
        return unique_values

    def _load_all_db_info(self):
        logger.debug("\nLoading all database info...", file=sys.stdout, flush=True)
        db_ids = [item for item in os.listdir(self.data_path)]
        for i in trange(len(db_ids)):
            db_id = db_ids[i]
            db_info = self._load_single_db_info(db_id)
            self.db2infos[db_id] = db_info

    def _build_table_schema_sqlite_str(self, table_name, new_columns_desc, new_columns_val):
        schema_desc_str = ''
        schema_desc_str += f"CREATE TABLE {table_name}\n"
        extracted_column_infos = []
        for (col_name, full_col_name, col_extra_desc), (_, col_values_str) in zip(new_columns_desc, new_columns_val):
            # district_id INTEGER PRIMARY KEY, -- location of branch
            col_line_text = ''
            col_extra_desc = 'And ' + str(col_extra_desc) if col_extra_desc != '' and str(
                col_extra_desc) != 'nan' else ''
            col_extra_desc = col_extra_desc[:100]
            col_line_text = ''
            col_line_text += f"  {col_name},  --"
            if full_col_name != '':
                full_col_name = full_col_name.strip()
                col_line_text += f" {full_col_name},"
            if col_values_str != '':
                col_line_text += f" Value examples: {col_values_str}."
            if col_extra_desc != '':
                col_line_text += f" {col_extra_desc}"
            extracted_column_infos.append(col_line_text)
        schema_desc_str += '{\n' + '\n'.join(extracted_column_infos) + '\n}' + '\n'
        return schema_desc_str

    def _build_table_schema_list_str(self, table_name, new_columns_desc, new_columns_val):
        schema_desc_str = ''
        schema_desc_str += f"# Table: {table_name}\n"
        # schema_desc_str += f"# Table: {table_name}\n"
        extracted_column_infos = []
        for (col_name, full_col_name, col_extra_desc), (_, col_values_str) in zip(new_columns_desc, new_columns_val):
            col_extra_desc = 'And ' + str(col_extra_desc) if col_extra_desc != '' and str(
                col_extra_desc) != 'nan' else ''
            col_extra_desc = col_extra_desc[:100]

            col_line_text = ''
            col_line_text += f'  ('
            col_line_text += f"{col_name},"

            if full_col_name != '':
                full_col_name = full_col_name.strip()
                col_line_text += f" {full_col_name}."
            if col_values_str != '':
                col_line_text += f" Value examples: {col_values_str}."
            if col_extra_desc != '':
                col_line_text += f" {col_extra_desc}"
            col_line_text += '),'
            extracted_column_infos.append(col_line_text)
        schema_desc_str += '[\n' + '\n'.join(extracted_column_infos).strip(',') + '\n]' + '\n'
        return schema_desc_str

    def _get_db_desc_str(self,
                         db_id: str,
                         extracted_schema: dict,
                         use_gold_schema: bool = False) -> List[str]:
        """
        Add foreign keys, and value descriptions of focused columns.
        :param db_id: name of sqlite database
        :param extracted_schema: {table_name: "keep_all" or "drop_all" or ['col_a', 'col_b']}
        :return: Detailed columns info of db; foreign keys info of db
        """
        if self.db2infos.get(db_id, {}) == {}:  # lazy load
            self.db2infos[db_id] = self._load_single_db_info(db_id)
        db_info = self.db2infos[db_id]
        desc_info = db_info[
            'desc_dict']  # table:str -> columns[(column_name, full_column_name, extra_column_desc): str]
        value_info = db_info['value_dict']  # table:str -> columns[(column_name, value_examples_str): str]
        pk_info = db_info['pk_dict']  # table:str -> primary keys[column_name: str]
        fk_info = db_info['fk_dict']  # table:str -> foreign keys[(column_name, to_table, to_column): str]
        tables_1, tables_2, tables_3 = desc_info.keys(), value_info.keys(), fk_info.keys()
        assert set(tables_1) == set(tables_2)
        assert set(tables_2) == set(tables_3)

        # print(f"desc_info: {desc_info}\n\n")

        # schema_desc_str = f"[db_id]: {db_id}\n"
        schema_desc_str = ''  # for concat
        db_fk_infos = []  # use list type for unique check in db

        # print(f"extracted_schema:\n")
        # pprint(extracted_schema)
        # print()

        logger.debug(f"db_id: {db_id}")
        # For selector recall and compression rate calculation
        chosen_db_schem_dict = {}  # {table_name: ['col_a', 'col_b'], ..}
        for (table_name, columns_desc), (_, columns_val), (_, fk_info), (_, pk_info) in \
                zip(desc_info.items(), value_info.items(), fk_info.items(), pk_info.items()):

            table_decision = extracted_schema.get(table_name, '')
            if table_decision == '' and use_gold_schema:
                continue

            # columns_desc = [(column_name, full_column_name, extra_column_desc): str]
            # columns_val = [(column_name, value_examples_str): str]
            # fk_info = [(column_name, to_table, to_column): str]
            # pk_info = [column_name: str]

            all_columns = [name for name, _, _ in columns_desc]
            primary_key_columns = [name for name in pk_info]
            foreign_key_columns = [name for name, _, _ in fk_info]

            important_keys = primary_key_columns + foreign_key_columns

            new_columns_desc = []
            new_columns_val = []

            logger.debug(f"table_name: {table_name}")
            if table_decision == "drop_all":
                new_columns_desc = deepcopy(columns_desc[:6])
                new_columns_val = deepcopy(columns_val[:6])
            elif table_decision == "keep_all" or table_decision == '':
                new_columns_desc = deepcopy(columns_desc)
                new_columns_val = deepcopy(columns_val)
            else:
                llm_chosen_columns = table_decision
                logger.debug(f"llm_chosen_columns: {llm_chosen_columns}")
                append_col_names = []
                for idx, col in enumerate(all_columns):
                    if col in important_keys:
                        new_columns_desc.append(columns_desc[idx])
                        new_columns_val.append(columns_val[idx])
                        append_col_names.append(col)
                    elif col in llm_chosen_columns:
                        new_columns_desc.append(columns_desc[idx])
                        new_columns_val.append(columns_val[idx])
                        append_col_names.append(col)
                    else:
                        pass

                # todo: check if len(new_columns_val) ≈ 6
                if len(all_columns) > 6 and len(new_columns_val) < 6:
                    for idx, col in enumerate(all_columns):
                        if len(append_col_names) >= 6:
                            break
                        if col not in append_col_names:
                            new_columns_desc.append(columns_desc[idx])
                            new_columns_val.append(columns_val[idx])
                            append_col_names.append(col)

            # Selector
            chosen_db_schem_dict[table_name] = [col_name for col_name, _, _ in new_columns_desc]

            # 1. Build schema part of prompt
            # schema_desc_str += self._build_bird_table_schema_sqlite_str(table_name, new_columns_desc, new_columns_val)
            schema_desc_str += self._build_table_schema_list_str(table_name, new_columns_desc, new_columns_val)

            # 2. Build foreign key part of prompt
            for col_name, to_table, to_col in fk_info:
                from_table = table_name
                if '`' not in str(col_name):
                    col_name = f"`{col_name}`"
                if '`' not in str(to_col):
                    to_col = f"`{to_col}`"
                fk_link_str = f"{from_table}.{col_name} = {to_table}.{to_col}"
                if fk_link_str not in db_fk_infos:
                    db_fk_infos.append(fk_link_str)
        fk_desc_str = '\n'.join(db_fk_infos)
        schema_desc_str = schema_desc_str.strip()
        fk_desc_str = fk_desc_str.strip()

        return schema_desc_str, fk_desc_str, chosen_db_schem_dict

    def _is_need_prune(self, db_id: str, db_schema: str):
        # encoder = tiktoken.get_encoding("cl100k_base")
        # tokens = encoder.encode(db_schema)
        # return len(tokens) >= 25000
        db_dict = self.db2dbjsons[db_id]
        avg_column_count = db_dict['avg_column_count']
        total_column_count = db_dict['total_column_count']
        if avg_column_count <= 6 and total_column_count <= 30:
            return False
        else:
            return True

    def _prune(self,
               query: str,
               db_schema: str,
               db_fk: str,
               evidence: str = None,
               ) -> dict:
        prompt = self.prompt_template.format(query=query, evidence=evidence, desc_str=db_schema,
                                             fk_str=db_fk)
        word_info = extract_world_info(self._message)
        reply = safe_call_llm(prompt, **word_info)
        extracted_schema_dict = parse_json(reply, True)
        return extracted_schema_dict

    def _concise(self,
                 query: str,
                 db_schema: str,
                 db_fk: str,
                 chosen_db_schem_dict: str,
                 evidence: str = None,
                 ) -> dict:
        prompt = concise_template.format(query=query, evidence=evidence, desc_str=db_schema,
                                             fk_str=db_fk, chosen_db_schem_dict=chosen_db_schem_dict)
        word_info = extract_world_info(self._message)
        if not word_info['evidence']:
            word_info['evidence'] = evidence
        reply = safe_call_llm(prompt, **word_info)
        # if "```json" in reply:
        #     reply = reply.replace("```json", "")
        #     reply = reply.replace("```", "")
        #     reply = "```json" + reply + "```"
        extracted_schema_dict = parse_json(reply, False)
        if not extracted_schema_dict:
            return str(reply)
        return extracted_schema_dict

    def _features(self,
                 query: str,
                 db_schema: str,
                 db_fk: str,
                 chosen_db_schem_dict: str,
                 evidence: str = None,
                 ) -> dict:
        prompt = features_template.format(query=query, evidence=evidence, desc_str=db_schema,
                                             fk_str=db_fk, chosen_db_schem_dict=chosen_db_schem_dict)
        word_info = extract_world_info(self._message)
        reply = safe_call_llm(prompt, **word_info)
        extracted_schema_dict = parse_json(reply, False)
        return extracted_schema_dict

    def _relation(self,
                 query: str,
                 db_schema: str,
                 db_fk: str,
                 chosen_db_schem_dict: str,
                 evidence: str = None,
                 ) -> dict:
        prompt = relationship_template.format(query=query, evidence=evidence, desc_str=db_schema,
                                             fk_str=db_fk, chosen_db_schem_dict=chosen_db_schem_dict)
        word_info = extract_world_info(self._message)
        reply = safe_call_llm(prompt, **word_info)
        extracted_schema_dict = parse_json(reply, False)
        return extracted_schema_dict

    def talk(self, message: dict):
        """
        :param message: {"db_id": database_name,
                         "query": user_query,
                         "evidence": extra_info,
                         "extracted_schema": None if no preprocessed result found}
        :return: extracted database schema {"desc_str": extracted_db_schema, "fk_str": foreign_keys_of_db}
        """
        if message['send_to'] != self.name: return
        self._message = message
        db_id, ext_sch, query, evidence = message.get('db_id'), \
            message.get('extracted_schema', {}), \
            message.get('query'), \
            message.get('evidence')
        use_gold_schema = False
        if ext_sch:
            use_gold_schema = True
        db_schema, db_fk, chosen_db_schem_dict = self._get_db_desc_str(db_id=db_id, extracted_schema=ext_sch,
                                                                       use_gold_schema=use_gold_schema)
        need_prune = self._is_need_prune(db_id, db_schema)
        if self.without_selector:
            need_prune = False

        if ext_sch == {} and need_prune:
            try:
                try:
                    raw_extracted_schema_dict = self._prune(query=query, db_schema=db_schema, db_fk=db_fk,
                                                            evidence=evidence)
                except Exception as e:
                    logger.error(e, exc_info=True)
                    raw_extracted_schema_dict = {}

            except Exception as e:
                logger.error(e, exc_info=True)
                raw_extracted_schema_dict = {}

            logger.debug(f"query: {message['query']}\n")
            db_schema_str, db_fk, chosen_db_schem_dict = self._get_db_desc_str(db_id=db_id,
                                                                               extracted_schema=raw_extracted_schema_dict)

            message['extracted_schema'] = raw_extracted_schema_dict
            message['chosen_db_schem_dict'] = chosen_db_schem_dict
            message['desc_str'] = db_schema_str
            message['fk_str'] = db_fk
            message['pruned'] = True
            message['send_to'] = SELECTOR_NAME
        else:
            message['chosen_db_schem_dict'] = chosen_db_schem_dict
            message['desc_str'] = db_schema
            message['fk_str'] = db_fk
            message['pruned'] = False
            message['send_to'] = SELECTOR_NAME

        if "metadata_flag" in message and message["metadata_flag"]:
            message['metadata'] = {}
            try:
                db_dict = self.db2dbjsons[db_id]
                for table in db_dict['table_names_original']:
                    metadata_tmp = self._concise(query=query, db_schema=db_schema, db_fk=db_fk,
                                                        chosen_db_schem_dict=chosen_db_schem_dict, evidence= evidence + f"""\nONLY PROVIDE metadata for table: {table}""")
                    message['metadata'][table] = metadata_tmp
            except Exception as e:
                logger.error(f"Metadata Generation Failed {e}", exc_info=True)
                message['metadata'] = {}

        if "feature_flag" in message and message["feature_flag"]:
            try:
                message['features'] = self._features(query=query, db_schema=db_schema, db_fk=db_fk,
                                                    chosen_db_schem_dict=chosen_db_schem_dict, evidence=evidence)
            except Exception as e:
                logger.error(e, exc_info=True)
                message['features'] = {}

        if "relationship_flag" in message and message["relationship_flag"]:
            try:
                message['relationship'] = self._relation(query=query, db_schema=db_schema, db_fk=db_fk,
                                                     chosen_db_schem_dict=chosen_db_schem_dict, evidence=evidence)
            except Exception as e:
                logger.error(e, exc_info=True)
                message['relationship'] = {}

        return message

    def invoke(self, message):
        response = self.talk(message)
        return response


def initialize_selector_agent(data_path,
                              tables_json_path,
                              prompt_template=selector_template,
                              lazy=False,
                              project="dataset001",
                              database_type="", database=None):
    data_retriever = Selector(data_path=data_path,
                              tables_json_path=tables_json_path, prompt_template=prompt_template, project=project, lazy=lazy,
                              database_type=database_type, database=database)
    return data_retriever


def summarize_tables(base_dir):
    tables_result, metadata_result, tables_summary = [], [], []

    for root, dirs, files in os.walk(base_dir):
        for file_name in files:
            # Get the file extension and path
            file_ext = os.path.splitext(file_name)[1]
            file_path = os.path.join(root, file_name)
            if file_ext != '.csv':
                continue

            try:
                df_table = pd.read_csv(file_path)
                df_table = df_table.apply(lambda x: x.astype(str).str.replace("\n", " ").replace("\xa0", " "))
                df_table = df_table.astype(str)
                df_table = df_table.applymap(lambda x: str(x) if isinstance(x, bool) else x)

                if not df_table.empty:
                    df_table = df_table.rename(columns=df_table.iloc[0]).drop(df_table.index[0]).reset_index(drop=True)

                if df_table.shape[0] <= 3 or df_table.eq("").all(axis=None):
                    continue

                metadata_table = {"source": file_path, "type": "row"}

                df_table["summary"] = df_table.apply(
                    lambda x: " ".join([f"{col}: {val}, " for col, val in x.items()]).replace("\xa0", " "),
                    axis=1
                )

                docs_summary = [Document(page_content=row["summary"].strip(), metadata=metadata_table) for _, row in
                                df_table.iterrows()]

                tables_result.append(df_table)
                metadata_result.append(metadata_table)
                tables_summary.extend(docs_summary)

                metadata_table = {"source": file_path, "type": "table"}
                tables_summary.append(Document(page_content=df_table.to_markdown(), metadata=metadata_table))
                metadata_result.append(metadata_table)
            except Exception as e:
                logger.error(e, exc_info=True)

    return tables_summary, metadata_result, tables_result

def generate_schema(base_dir, project, dest_folder, metadata_flag=True,
                    feature_flag=False, relationship_flag=False,
                    query='Summarize all the tables in the dataset.', database_type="", database=None):
    """
    Generate schema metadata and optionally features from Databricks or other sources.
    """
    logger.debug(f"Starting schema generation for project: {project}, database: {database}")

    # Ensure destination folder exists
    os.makedirs(dest_folder, exist_ok=True)

    tables_file = f"{dest_folder}/tables.json"
    metadata_file = f"{dest_folder}/metadata.json"
    schema_file = f"{dest_folder}/schema.json"
    feature_file = f"{dest_folder}/features.json"
    relationship_file = f"{dest_folder}/relation.json"

    try:
        # Step 1: Create Table JSON from Databricks or other sources
        dbs_json = create_tables_json(project, dest_folder, tables_file, database_type=database_type, database=database)
        # Verify tables.json was created and has content
        if not os.path.exists(tables_file) or os.path.getsize(tables_file) == 0:
            raise ValueError(f"tables.json at {tables_file} is empty or was not created")
        logger.debug(f"Created tables.json at {tables_file}")

        # Step 2: generate ddl/erd file
        for db in dbs_json:
            try:
                export_table_ddls_from_schema(db,
                                          os.path.join(base_dir, project, "raw", "code", f"{database}_ddl.sql"))
                generate_erd(db, os.path.join(base_dir, project, "raw", "code", f"{database}_erd.png"))
            except Exception as e:
                logger.error(e)

        # Step 3: Initialize selector agent
        selector_data_agent = initialize_selector_agent(
            data_path=dest_folder,
            tables_json_path=tables_file,
            prompt_template=selector_template,
            lazy=True,
            project=project,
            database_type=database_type,
            database=database
        )

        # Step 4: Prepare message for selector agent
        message = {
            "db_id": project,
            "extracted_schema": {},
            "evidence": "",
            "query": query,
            "send_to": SELECTOR_NAME,
            "metadata_flag": metadata_flag,
            "feature_flag": feature_flag,
            "relationship_flag": relationship_flag
        }

        # Step 5: Invoke selector agent and get response
        selector_data_chain_message = selector_data_agent.invoke(message)
        if not selector_data_chain_message:
            raise ValueError("Selector agent returned empty response")

        logger.debug(f"Selector agent response keys: {selector_data_chain_message.keys()}")

        # Step 6: Write schema file
        if "chosen_db_schem_dict" in selector_data_chain_message and "desc_str" in selector_data_chain_message:
            with open(schema_file, 'w') as json_file:
                dict_str = str(selector_data_chain_message["chosen_db_schem_dict"]).replace("{", "{{").replace("}","}}")
                json.dump(dict_str, json_file, indent=4)
                json_file.write("\n\n## Table Schema Description\n\n")
                json_file.write(selector_data_chain_message["desc_str"])
            logger.debug(f"Successfully wrote schema file to {schema_file}")
        else:
            logger.error("Missing required schema data in selector response")

        # Step 7: Write metadata file
        if metadata_flag:
            if "metadata" in selector_data_chain_message:
                logger.debug("Writing metadata to file...")
                with open(metadata_file, 'w') as json_file:
                    json.dump(selector_data_chain_message["metadata"], json_file, indent=4)
                # Verify metadata was written
                if os.path.getsize(metadata_file) > 0:
                    logger.debug(f"Successfully wrote metadata to {metadata_file}")
                else:
                    logger.error("Metadata file was created but is empty")
            else:
                logger.error("No metadata found in selector response")
                logger.debug(f"Available keys in response: {list(selector_data_chain_message.keys())}")

        # Step 8: Write features file
        if feature_flag and "features" in selector_data_chain_message:
            with open(feature_file, 'w') as json_file:
                json.dump(selector_data_chain_message["features"], json_file, indent=4)
            logger.debug(f"Successfully wrote features to {feature_file}")

        # Step 8: Write features file
        if relationship_flag and "relationship" in selector_data_chain_message:
            with open(relationship_file, 'w') as json_file:
                json.dump(selector_data_chain_message["relationship"], json_file, indent=4)
            logger.debug(f"Successfully wrote relationship to {relationship_file}")

        logger.debug("Schema generation completed successfully")
        return True

    except Exception as e:
        logger.error(f"Error during schema generation: {str(e)}", exc_info=True)
        # Clean up any partially written files
        for file_path in [tables_file, metadata_file, schema_file, feature_file]:
            if os.path.exists(file_path) and os.path.getsize(file_path) == 0:
                try:
                    os.remove(file_path)
                    logger.debug(f"Removed empty file: {file_path}")
                except Exception as cleanup_error:
                    logger.error(f"Error cleaning up file {file_path}: {str(cleanup_error)}")
        return False

def generate_schemas_for_all_databases(dest_folder, metadata_flag=True, feature_flag=False, query='Summarize all the tables in the dataset.'):
    """
    Generate schemas for all databases in Databricks.
    """
    databases = fetch_all_databases()
    logger.debug(f"Found {len(databases)} databases in Databricks.")

    for database in databases:
        logger.debug(f"Processing database: {database}")
        project = f"databricks_{database}"  # Use database name as project identifier
        database_dest_folder = os.path.join(dest_folder, database)

        # Ensure destination folder exists
        os.makedirs(database_dest_folder, exist_ok=True)

        generate_schema(
            base_dir="",  # Not used for Databricks
            project=project,
            dest_folder=database_dest_folder,
            metadata_flag=metadata_flag,
            feature_flag=feature_flag,
            query=query,
            database_type="databricks",
            database=database
        )

    logger.debug("Schema generation completed for all databases.")


# if __name__ == "__main__":
#     data_retriever = initialize_selector_agent(data_path="../../../data/datasets/spider/database",
#                                                tables_json_path="../../../data/datasets/spider/tables.json")
#     message = {
#         "db_id": "concert_singer",
#         "extracted_schema": {},
#         "evidence": "",
#         "query": 'How many singers do we have?',
#         "send_to": SELECTOR_NAME
#     }
#     selector_data_chain = data_retriever.invoke(message)
#     print(selector_data_chain)
