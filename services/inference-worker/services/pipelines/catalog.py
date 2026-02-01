import asyncio
import json
import os
import sys

import pandas as pd
import xml.etree.ElementTree as ET

from datetime import datetime

from services.customer.personalization import get_project_config
from services.integration.sqlalchemy_engine import get_connection
from services.utils.tools import run_rag, extract_json_from_response
from services.workflows.data_understanding.hybrid_rag.adaptive_rag_v4 import initialize_brewsearch_state_workflow


class CatalogProcessor:
    """Class to extract metadata from different sources (DB, Files) and create a harmonization catalog."""

    def __init__(self, source_type="oracle", rag_service=None, project=None, database=None, wd="."):
        self.source_type = source_type
        self.rag_service = rag_service  # RAG service for metadata enrichment
        self.project = project
        self.database = database
        self.catalog = []  # List to store catalog entries
        self.work_directory = wd

    def get_oracle_schema(self, connection):
        """Fetch schema details from Oracle Database."""
        query = f"""
        SELECT table_name, column_name, data_type, data_length, nullable, data_default 
        FROM all_tab_columns 
        WHERE owner = '{self.database.upper()}'
        """
        df = pd.read_sql(query, connection)
        return df

    def get_foreign_keys(self, connection):
        """Retrieve Foreign Key relationships."""

        if self.source_type == "oracle":
            fk_query = f"""
                    SELECT
                        a.table_name, a.column_name, c_pk.table_name AS ref_table, c_pk.column_name AS ref_column
                    FROM all_cons_columns a
                    JOIN all_constraints c ON a.constraint_name = c.constraint_name AND a.owner = c.owner
                    JOIN all_cons_columns c_pk ON c.r_constraint_name = c_pk.constraint_name AND c_pk.owner = c.owner
                    WHERE c.constraint_type = 'R' -- Foreign Key
                    AND c.owner = '{self.database.upper()}'
                    """
        else:
            fk_query = """
                    SELECT
                        a.table_name, a.column_name, c_pk.table_name AS ref_table, c_pk.column_name AS ref_column
                    FROM all_cons_columns a
                    JOIN all_constraints c ON a.constraint_name = c.constraint_name AND a.owner = c.owner
                    JOIN all_cons_columns c_pk ON c.r_constraint_name = c_pk.constraint_name AND c_pk.owner = c.owner
                    WHERE c.constraint_type = 'R' -- Foreign Key
                    """
        return pd.read_sql(fk_query, connection)

    async def enrich_with_rag(self, query):
        """Query RAG service to get additional metadata."""
        if self.rag_service:
            response = await run_rag(self.rag_service, query, True, True, True, False, self.project)
            return response if response else "No description available"
        return "No context available!"

    def get_primary_keys(self, connection):
        """Fetch primary key columns for each table."""

        if self.source_type == "oracle":
            query = f"""
                        SELECT cols.table_name, cols.column_name
                        FROM all_cons_columns cols
                        JOIN all_constraints cons
                        ON cols.constraint_name = cons.constraint_name
                        WHERE cons.constraint_type = 'P'
                        AND cols.owner = '{self.database.upper()}'
                        """
        else:
            query = """
                        SELECT cols.table_name, cols.column_name
                        FROM all_cons_columns cols
                        JOIN all_constraints cons
                        ON cols.constraint_name = cons.constraint_name
                        WHERE cons.constraint_type = 'P'
                        """
        return pd.read_sql(query, connection)

    async def process_oracle_catalog(self):
        """Process Oracle schema and generate metadata catalog."""
        connection = get_connection(self.source_type, self.project)
        schema_df = self.get_oracle_schema(connection)
        pk_df = self.get_primary_keys(connection)  # Fetch primary keys
        fk_df = self.get_foreign_keys(connection)  # Fetch foreign keys

        # Merge Primary Key info
        schema_df["is_primary_key"] = schema_df.apply(
            lambda row: True if ((row["TABLE_NAME"], row["COLUMN_NAME"]) in zip(pk_df["TABLE_NAME"],
                                                                                pk_df["COLUMN_NAME"])) else False,
            axis=1
        )

        # Merge Foreign Key details
        schema_df = schema_df.merge(fk_df, how="left", on=["TABLE_NAME", "COLUMN_NAME"])

        for _, row in schema_df.iterrows():
            enrich_question = f"Provide detailed information about the database column '{row["COLUMN_NAME"]}' in the table '{row["TABLE_NAME"]}'. Please return the response in json format:" \
"""
{
    "description": "Provide a detailed description for the database column. Explain its purpose, expected values, and how it is used within the system. If relevant, include examples of common values and their meanings.",
    "relation_other_attributes": "Provide relationships between the column and other attributes within the database. Specify if it serves as a primary key, foreign key, or is functionally dependent on other columns. List any known related attributes.",
    "sample_data": "Provide five representative sample values for the column. Include variations if applicable, and describe any formatting rules or constraints.",
    "validation_rules": "What are the validation rules for the column? Include constraints like data type, length restrictions, required fields, regex patterns, and business logic validations. Provide exact validation for syntax/semantic, and quality.",
    "usefulness": "How is the column useful? Explain its significance in reporting, decision-making, and operational processes. Include examples of how this attribute impacts business workflows.",
    "category": "One Word. Classify the column into one of the following categories: Identifier, Measurement, Date/Time, Categorical, Metadata, Reference. Explain the reason for the chosen category."
}
"""
            column_response = await self.enrich_with_rag(enrich_question)
            column_data = extract_json_from_response(column_response)
            if not isinstance(column_data, dict) or "description" not in column_data:
                print ("Invalid table overview response format")
                column_response = await self.enrich_with_rag(enrich_question)
                column_data = extract_json_from_response(column_response)
                if not isinstance(column_data, dict) or "description" not in column_data:
                    print("Invalid table overview response format")
                    continue

            catalog_entry = {
                "table_name": row["TABLE_NAME"],
                "column_name": row["COLUMN_NAME"],
                "data_type": row["DATA_TYPE"],
                "max_length": row["DATA_LENGTH"],
                "is_nullable": row["NULLABLE"] == "Y",
                "default_value": row["DATA_DEFAULT"],
                "is_primary_key": row["is_primary_key"],  # ✅ Now fetched from DB
                "foreign_key_reference": f"{row['REF_TABLE']}.{row['REF_COLUMN']}" if row["REF_TABLE"] else None,
                "description": column_data["description"],
                "relation_other_attributes": column_data["relation_other_attributes"],
                "sample_data": column_data["sample_data"],
                "validation_rules": column_data["validation_rules"],
                "usefulness": column_data["usefulness"],
                "category": column_data["category"],
                "source_type": "oracle",
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self.catalog.append(catalog_entry)

        connection.close()

    async def process_csv_catalog(self, csv_path):
        """Extract schema metadata from CSV files."""
        df = pd.read_csv(csv_path)
        for col in df.columns:
            catalog_entry = {
                "table_name": csv_path.split("/")[-1].replace(".csv", ""),
                "column_name": col,
                "data_type": "string",
                "max_length": None,
                "is_nullable": True,
                "default_value": None,
                "is_primary_key": False,
                "foreign_key_reference": None,
                "description": self.enrich_with_rag(col),
                "validation_rules": None,
                "category": self.categorize_column(col),
                "source_type": "csv",
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "mapped_to_seedd": None
            }
            self.catalog.append(catalog_entry)

    def categorize_column(self, column_name):
        """Categorize column based on naming patterns."""
        category_map = {
            "sample": "Sample Information",
            "test": "Test Information",
            "result": "Test Results",
            "lab": "Lab Metadata",
            "client": "Client Metadata",
            "date": "Timestamp"
        }
        for key, value in category_map.items():
            if key in column_name.lower():
                return value
        return "General"

    async def process_xml_catalog(self, xml_path):
        """Extract schema metadata from an XML file."""
        tree = ET.parse(xml_path)
        root = tree.getroot()

        async def traverse_element(element, parent_path="", level=0):
            """Recursive function to extract metadata from XML elements."""
            element_path = f"{parent_path}/{element.tag}" if parent_path else element.tag
            current_level = level
            print(f"Processing element: {element_path} (Level: {current_level})")  # Debugging

            # Process all attributes as a single list (if any)
            attr_list = []
            if element.attrib:
                attr_list = list(element.attrib.keys())
                # attr_response = await self.enrich_with_rag(
                #     f"Provide detailed information about the attribute columns {attr_list} in element '{element.tag}' with element path: {element_path}. Please return the response in json format:" \
                #     """
                #     {
                #         "description": "Provide a detailed description for the XML attributes. Explain their purpose, expected values, and how they are used within the system. If relevant, include examples of common values and their meanings.",
                #         "relation_other_attributes": "Provide relationships between these attributes and other attributes within the document hierarchy. List any known related attributes.",
                #         "sample_data": "Provide five representative sample values for these attributes. Include variations if applicable, and describe any formatting rules or constraints.",
                #         "validation_rules": "What are the validation rules for these attributes? Include constraints like data type, length restrictions, required fields, regex patterns, and business logic validations.",
                #         "usefulness": "Explain the significance of these attributes in reporting, decision-making, and operational processes.",
                #         "category": "One Word. Classify these attributes into one of the following categories: Identifier, Measurement, Date/Time, Categorical, Metadata, Reference."
                #     }
                #     """
                # )
                # catalog_entry = {
                #     "element_name": element.tag,
                #     "attribute_names": attr_list,
                #     "data_type": "string",  # XML attributes are typically strings
                #     "is_nullable": True,
                #     "default_value": element.attrib,  # include full dictionary of attributes
                #     "relation_other_attributes": attr_response["relation_other_attributes"],
                #     "description": attr_response["description"],
                #     "sample_data": attr_response["sample_data"],
                #     "validation_rules": attr_response["validation_rules"],
                #     "usefulness": attr_response["usefulness"],
                #     "category": attr_response["category"],
                #     "source_type": "xml",
                #     "hierarchy_path": element_path,
                #     "level": current_level,
                #     "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                # }
                # self.catalog.append(catalog_entry)
                # print(f"Added attribute list for element: {element.tag}")  # Debugging

            # Process element content (text)
            if element.tag and element.tag.strip():
                enrich_question = f"Provide detailed information about the element '{element.tag}' with element path: {element_path}. Please return the response in json format:" \
                  """
                  {
                      "description": "Provide a detailed description for the XML element. Explain its purpose, expected values, and how it is used within the system. Include examples of common values if applicable.",
                      "relation": "Provide relationships between this element and other elements within the document hierarchy. List any known related elements.",
                      "sample_data": "Provide upto five actual sample values for the element. Never include made up data. If no data, keep empty. Include variations if applicable, and describe any formatting rules or constraints.",
                      "validation_rules": "What are the validation rules for the element? Include constraints like data type, length restrictions, required fields, regex patterns, and business logic validations.",
                      "usefulness": "Explain how this element is useful in reporting, decision-making, and operational processes.",
                      "category": "One Word. Classify the element into one of the following categories: Identifier, Measurement, Date/Time, Categorical, Metadata, Reference."
                  }   
                  """
                elem_response = await self.enrich_with_rag(enrich_question)
                elem_data = extract_json_from_response(elem_response)
                if not isinstance(elem_data, dict) or "description" not in elem_data:
                    print("Invalid table overview response format")
                    elem_response = await self.enrich_with_rag(enrich_question)
                    elem_data = extract_json_from_response(elem_response)
                    if not isinstance(elem_data, dict) or "description" not in elem_data:
                        print("Invalid table overview response format")
                        return
                catalog_entry = {
                    "element_name": element.tag,
                    "attribute_names": attr_list,
                    "data_type": "string",
                    "is_nullable": True,
                    "default_value": element.text.strip() if element.text else "",
                    "is_primary_key": False,
                    "relation_other_attributes": elem_data["relation_other_attributes"],
                    "description": elem_data["description"],
                    "sample_data": elem_data["sample_data"],
                    "validation_rules": elem_data["validation_rules"],
                    "usefulness": elem_data["usefulness"],
                    "category": elem_data["category"],
                    "source_type": "xml",
                    "hierarchy_path": element_path,
                    "level": current_level,
                    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                self.catalog.append(catalog_entry)
                print(f"Added text content for element: {element.tag}")  # Debugging
                # await self.persist_catalog()

            # Recursively process child elements
            for child in element:
                await traverse_element(child, element_path, level=current_level + 1)

        # Start traversal from the root element.
        await traverse_element(root)


    async def persist_catalog(self, output_format="csv"):
        """Save the catalog as CSV or JSON."""
        df = pd.DataFrame(self.catalog)
        if output_format == "csv":
            df.to_csv(os.path.join(self.work_directory,f"{self.project}_data_catalog.csv"), index=False)
            return f"Catalog saved as {os.path.join(self.work_directory,f"{self.project}_data_catalog.csv")}"
        elif output_format == "json":
            with open(os.path.join(self.work_directory, f"{self.project}_data_catalog.json"), "w") as f:
                json.dump(self.catalog, f, indent=4)
            return f"Catalog saved as {os.path.join(self.work_directory, f"{self.project}_data_catalog.json")}"

    async def run(self, source_path=None):
        """Execute catalog extraction process."""
        if self.source_type == "oracle":
            await self.process_oracle_catalog()
        elif self.source_type == "csv" and source_path:
            await self.process_csv_catalog(source_path)
        elif self.source_type == "xml" and source_path:
            await self.process_xml_catalog(source_path)
        else:
            raise ValueError("Unsupported source type or missing source path.")

        return await self.persist_catalog()

# Example Usage
if __name__ == "__main__":
    from services.integration.phoenix import initialize_phoenix
    initialize_phoenix()
    project = os.getenv("PROJECT").lower()

    project_config = get_project_config(project)
    if not project_config:
        print ("Project NOT supported yet!")
        sys.exit(0)

    oracle_owner = os.getenv("ORACLE_OWNER")

    app = initialize_brewsearch_state_workflow("catalog_pipeline", project)
    # catalog_processor = CatalogProcessor(source_type="oracle", rag_service=app, project=project, database=oracle_owner, wd=project_config["work_directory"])
    # asyncio.run(catalog_processor.run())

    catalog_processor_xml = CatalogProcessor(source_type="xml", rag_service=app, project=project, database=oracle_owner, wd=project_config["work_directory"])
    asyncio.run(catalog_processor_xml.run("/Users/sarkarsaurabh.27/Documents/Projects/brewsearch/data/pace_labs_sedd/raw/data/dummy.xml"))
    print("DONE")
