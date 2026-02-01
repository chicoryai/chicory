import os
from pathlib import Path
from services.training.tasks import databricks_scanning_task, oracle_scanning_task, snowflake_scanning_task, \
    bigquery_scanning_task, redshift_scanning_task, glue_scanning_task, \
    azure_blob_storage_scanning_task, azure_data_factory_scanning_task, atlan_scanning_task
from services.utils.logger import logger
import json
import datetime


def check_file_types(folder_path):
    """Check if folder contains valid data files"""
    valid_extensions = {".csv", ".xls", ".xlsx", ".parquet", ".dtd", ".sqlite", ".db", ".sqlite3"}
    folder = Path(folder_path)
    for file_path in folder.rglob('*'):
        if file_path.suffix.lower() in valid_extensions:
            return True
    return False


def generate_unified_metadata_files(base_dir, project):
    """
    Generate unified metadata files that consolidate information from all providers
    """
    try:
        metadata_dir = os.path.join(base_dir, project, "raw", "data", "database_metadata")
        providers_dir = os.path.join(metadata_dir, "providers")

        if not os.path.exists(providers_dir):
            logger.info("No provider metadata found, skipping unified file generation")
            return

        # Initialize unified structures
        all_manifest_entries = []
        provider_summaries = {}

        # Process each provider's metadata
        for provider in ["snowflake", "databricks", "bigquery", "oracle", "glue",
                         "azure_blob_storage", "azure_data_factory", "atlan"]:
            provider_path = os.path.join(providers_dir, provider)
            if not os.path.exists(provider_path):
                continue

            logger.info(f"Processing {provider} metadata for unified files...")

            # Read provider's manifest if it exists
            provider_manifest_path = os.path.join(provider_path, "manifest.json")
            if os.path.exists(provider_manifest_path):
                with open(provider_manifest_path, 'r') as f:
                    provider_manifest = json.load(f)
                    # Handle different manifest key names across providers
                    provider_entries = (
                        provider_manifest.get("tables", []) or
                        provider_manifest.get("blobs", []) or
                        provider_manifest.get("resources", [])
                    )
                    all_manifest_entries.extend(provider_entries)

            # Read provider overview
            provider_overview_path = os.path.join(provider_path, "provider_overview.json")
            if os.path.exists(provider_overview_path):
                with open(provider_overview_path, 'r') as f:
                    provider_overview = json.load(f)

                    # Extract summary information based on provider type
                    if provider == "snowflake":
                        provider_summaries[provider] = {
                            "account_count": 1,
                            "database_count": provider_overview.get("total_databases", 0),
                            "table_count": len([e for e in all_manifest_entries if e.get("provider") == provider]),
                            "regions": [provider_overview.get("region", "unknown")]
                        }
                    elif provider == "databricks":
                        provider_summaries[provider] = {
                            "workspace_count": 1,
                            "catalog_count": provider_overview.get("total_catalogs", 0),
                            "table_count": len([e for e in all_manifest_entries if e.get("provider") == provider]),
                            "regions": [provider_overview.get("region", "unknown")]
                        }
                    elif provider == "bigquery":
                        provider_summaries[provider] = {
                            "project_count": 1,
                            "dataset_count": provider_overview.get("total_datasets", 0),
                            "table_count": len([e for e in all_manifest_entries if e.get("provider") == provider]),
                            "regions": [provider_overview.get("location", "unknown")]
                        }
                    elif provider == "oracle":
                        provider_summaries[provider] = {
                            "instance_count": 1,
                            "schema_count": provider_overview.get("total_schemas", 0),
                            "table_count": len([e for e in all_manifest_entries if e.get("provider") == provider]),
                            "regions": [provider_overview.get("region", "unknown")]
                        }
                    elif provider == "glue":
                        provider_summaries[provider] = {
                            "account_count": 1,
                            "database_count": provider_overview.get("total_databases", 0),
                            "table_count": len([e for e in all_manifest_entries if e.get("provider") == provider]),
                            "regions": [provider_overview.get("region", "unknown")]
                        }
                    elif provider == "azure_blob_storage":
                        provider_summaries[provider] = {
                            "storage_account_count": 1,
                            "container_count": provider_overview.get("total_containers", 0),
                            "blob_count": provider_overview.get("total_blobs", 0),
                            "total_size_bytes": provider_overview.get("total_size_bytes", 0)
                        }
                    elif provider == "azure_data_factory":
                        provider_summaries[provider] = {
                            "factory_count": 1,
                            "pipeline_count": provider_overview.get("total_pipelines", 0),
                            "dataset_count": provider_overview.get("total_datasets", 0),
                            "trigger_count": provider_overview.get("total_triggers", 0),
                            "linked_service_count": provider_overview.get("total_linked_services", 0),
                            "data_flow_count": provider_overview.get("total_data_flows", 0),
                            "integration_runtime_count": provider_overview.get("total_integration_runtimes", 0)
                        }
                    elif provider == "atlan":
                        provider_summaries[provider] = {
                            "tenant_url": provider_overview.get("tenant_url", ""),
                            "total_assets": provider_overview.get("total_assets", 0),
                            "assets_by_type": provider_overview.get("assets_by_type", {}),
                            "tables_with_lineage": provider_overview.get("tables_with_lineage", 0),
                            "glossary_terms": provider_overview.get("glossary_terms", 0),
                            "failed_assets": provider_overview.get("failed_assets", 0)
                        }

        # Calculate total tables across all providers
        total_tables = len(all_manifest_entries)

        # Write unified manifest.json
        unified_manifest = {
            "version": "1.0",
            "tables": all_manifest_entries
        }

        with open(os.path.join(metadata_dir, "manifest.json"), 'w') as f:
            json.dump(unified_manifest, f, indent=2, default=str)

        # Write database_overview.json
        database_overview = {
            "version": "1.0",
            "providers": provider_summaries,
            "total_tables": total_tables,
            "generated_at": datetime.datetime.now().isoformat()
        }

        with open(os.path.join(metadata_dir, "database_overview.json"), 'w') as f:
            json.dump(database_overview, f, indent=2, default=str)

        # Create placeholder files for advanced features
        # TODO: enable for customers as needed
        # glossary.json - Business glossary and data dictionary
        # glossary = {
        #     "version": "1.0",
        #     "terms": [],
        #     "generated_at": datetime.datetime.now().isoformat(),
        #     "note": "Placeholder for business glossary - populate with domain-specific terms"
        # }

        # with open(os.path.join(metadata_dir, "glossary.json"), 'w') as f:
        #     json.dump(glossary, f, indent=2, default=str)

        # policies.json - Data governance policies
        # policies = {
        #     "version": "1.0",
        #     "policies": [],
        #     "generated_at": datetime.datetime.now().isoformat(),
        #     "note": "Placeholder for data governance policies - populate with access controls, retention policies, etc."
        # }

        # with open(os.path.join(metadata_dir, "policies.json"), 'w') as f:
        #     json.dump(policies, f, indent=2, default=str)

        # metrics.json - Data quality and usage metrics
        # metrics = {
        #     "version": "1.0",
        #     "metrics": [],
        #     "generated_at": datetime.datetime.now().isoformat(),
        #     "note": "Placeholder for data quality metrics - populate with freshness, completeness, accuracy metrics"
        # }

        # with open(os.path.join(metadata_dir, "metrics.json"), 'w') as f:
        #     json.dump(metrics, f, indent=2, default=str)

        # Generate README.md for Claude
        readme_content = f"""# Database Metadata Documentation

**Version:** 1.0  
**Description:** Database metadata generated by unified dwh scanning system

## Structure

- **`database_overview.json`** - Summary of all providers and tables
- **`manifest.json`** - Index of all table cards with quick access info  
- **`providers/`** - Provider-specific metadata organized by provider type

## Supported Providers

{chr(10).join(f'- {provider}' for provider in provider_summaries.keys())}

## Scan Summary

**Total tables scanned:** {total_tables}

## Navigation Tips

1. **Start with `manifest.json`** to find specific tables
2. **Check `provider_overview.json`** for connection details
3. **Table files are organized as:** `providers/bigquery/tables/<project>/<dataset>/<table>.json`

## FQTN Format

```
bigquery://<project>/<dataset>/<table>
```

---
*Generated by unified scanning system*
        """

        with open(os.path.join(metadata_dir, "README.md"), 'w') as f:
            f.write(readme_content)

        # Update generatedat timestamp
        with open(os.path.join(metadata_dir, "generatedat"), 'w') as f:
            f.write(datetime.datetime.now().isoformat())

        logger.info(
            f"Generated unified metadata files with {total_tables} tables from {len(provider_summaries)} providers")

    except Exception as e:
        logger.error(f"Error generating unified metadata files: {e}", exc_info=True)


def run(config):
    """Main entry point for data scanning task"""
    logger.info("Analysing...")
    project = config["PROJECT"].lower()
    base_dir = config["BASE_DIR"]

    # Always run cloud provider scans (they can coexist with local files)
    providers_run = []

    # Databricks scanning
    if config.get("DISABLE_DATABRICKS_SCANNING", "false").lower() == "false":
        logger.info("Running Databricks scanning task...")
        try:
            databricks_scanning_task.run(config)
            providers_run.append("databricks")
        except Exception as e:
            logger.error(f"Databricks scanning failed: {e}")
    else:
        logger.info("Databricks scanning skipped...")

    # Oracle scanning
    if config.get("DISABLE_ORACLE_SCANNING", "false").lower() == "false":
        logger.info("Running Oracle scanning task...")
        try:
            oracle_scanning_task.run(config)
            providers_run.append("oracle")
        except Exception as e:
            logger.error(f"Oracle scanning failed: {e}")
    else:
        logger.info("Oracle scanning skipped...")

    # Snowflake scanning
    if config.get("DISABLE_SNOWFLAKE_SCANNING", "false").lower() == "false":
        logger.info("Running Snowflake scanning task...")
        try:
            snowflake_scanning_task.run(config)
            providers_run.append("snowflake")
        except Exception as e:
            logger.error(f"Snowflake scanning failed: {e}")
    else:
        logger.info("Snowflake scanning skipped...")

    # BigQuery scanning
    if config.get("DISABLE_BIGQUERY_SCANNING", "false").lower() == "false":
        logger.info("Running BigQuery scanning task...")
        try:
            bigquery_scanning_task.run(config)
            providers_run.append("bigquery")
        except Exception as e:
            logger.error(f"BigQuery scanning failed: {e}")
    else:
        logger.info("BigQuery scanning skipped...")

    if config.get("DISABLE_REDSHIFT_SCANNING", "false").lower() == "false":
        logger.info("Running Redshift scanning task...")
        try:
            redshift_scanning_task.run(config)
            providers_run.append("redshift")
        except Exception as e:
            logger.error(f"Redshift scanning failed: {e}")
    else:
        logger.info("Redshift scanning skipped...")

    # AWS Glue scanning
    if config.get("DISABLE_GLUE_SCANNING", "false").lower() == "false":
        logger.info("Running AWS Glue scanning task...")
        try:
            glue_scanning_task.run(config)
            providers_run.append("glue")
        except Exception as e:
            logger.error(f"AWS Glue scanning failed: {e}")
    else:
        logger.info("AWS Glue scanning skipped...")

    # Azure Blob Storage scanning
    if config.get("DISABLE_AZURE_BLOB_STORAGE_SCANNING", "false").lower() == "false":
        logger.info("Running Azure Blob Storage scanning task...")
        try:
            azure_blob_storage_scanning_task.run(config)
            providers_run.append("azure_blob_storage")
        except Exception as e:
            logger.error(f"Azure Blob Storage scanning failed: {e}")
    else:
        logger.info("Azure Blob Storage scanning skipped...")

    # Azure Data Factory scanning
    if config.get("DISABLE_AZURE_DATA_FACTORY_SCANNING", "false").lower() == "false":
        logger.info("Running Azure Data Factory scanning task...")
        try:
            azure_data_factory_scanning_task.run(config)
            providers_run.append("azure_data_factory")
        except Exception as e:
            logger.error(f"Azure Data Factory scanning failed: {e}")
    else:
        logger.info("Azure Data Factory scanning skipped...")

    # Atlan data catalog scanning
    if config.get("DISABLE_ATLAN_SCANNING", "false").lower() == "false":
        logger.info("Running Atlan data catalog scanning task...")
        try:
            atlan_scanning_task.run(config)
            providers_run.append("atlan")
        except Exception as e:
            logger.error(f"Atlan scanning failed: {e}")
    else:
        logger.info("Atlan scanning skipped...")

    # Generate unified metadata files if any providers were run
    if providers_run:
        logger.info(f"Generating unified metadata files for providers: {', '.join(providers_run)}")
        generate_unified_metadata_files(base_dir, project)
