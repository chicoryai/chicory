from typing import Dict, Any
import logging
from app.models.data_source import DataSourceType

# Import validators
from app.validators.data_sources import github_validator, databricks_validator, google_docs_validator, snowflake_validator, bigquery_validator, glue_validator, datazone_validator, redash_validator, dbt_validator, looker_validator, datahub_validator, airflow_validator, anthropic_validator, s3_validator, jira_validator, azure_blob_storage_validator, azure_data_factory_validator, webfetch_validator, atlan_validator

# Configure logging
logger = logging.getLogger(__name__)

def get_validator(data_source_type: DataSourceType):
    """
    Factory function to get the appropriate validator for a data source type
    
    Args:
        data_source_type: The type of data source to validate
        
    Returns:
        The appropriate validator function or None if not supported
    """
    validators = {
        DataSourceType.GITHUB: github_validator.validate_credentials,
        DataSourceType.JIRA: jira_validator.validate_credentials,
        DataSourceType.DATABRICKS: databricks_validator.validate_credentials,
        DataSourceType.GOOGLE_DRIVE: google_docs_validator.validate_credentials,
        DataSourceType.SNOWFLAKE: snowflake_validator.validate_credentials,
        DataSourceType.BIGQUERY: bigquery_validator.validate_credentials,
        DataSourceType.GLUE: glue_validator.validate_credentials,
        DataSourceType.DATAZONE: datazone_validator.validate_credentials,
        DataSourceType.REDASH: redash_validator.validate_credentials,
        DataSourceType.DBT: dbt_validator.validate_credentials,
        DataSourceType.LOOKER: looker_validator.validate_credentials,
        DataSourceType.DATAHUB: datahub_validator.validate_credentials,
        DataSourceType.AIRFLOW: airflow_validator.validate_credentials,
        DataSourceType.ANTHROPIC: anthropic_validator.validate_credentials,
        DataSourceType.S3: s3_validator.validate_credentials,
        DataSourceType.AZURE_BLOB_STORAGE: azure_blob_storage_validator.validate_credentials,
        DataSourceType.AZURE_DATA_FACTORY: azure_data_factory_validator.validate_credentials,
        DataSourceType.WEBFETCH: webfetch_validator.validate_credentials,
        DataSourceType.ATLAN: atlan_validator.validate_credentials,
        # Add more validators as they are implemented
    }
    
    validator = validators.get(data_source_type)
    if not validator:
        logger.warning(f"No validator available for data source type: {data_source_type}")
    
    return validator


def validate(data_source_type: DataSourceType, credentials: Dict[str, Any], project_id: str = None) -> Dict[str, Any]:
    """
    Validate credentials for a specific data source type

    Args:
        data_source_type: The type of data source to validate
        credentials: Dictionary containing the credentials to validate
        project_id: Optional project ID for auto-generating external_id for AWS services

    Returns:
        Dict with validation status and message
    """
    validator = get_validator(data_source_type)

    if not validator:
        return {
            "status": "error",
            "message": f"Validation not supported for data source type: {data_source_type}",
            "details": None
        }

    # Auto-generate external_id for AWS services if not provided
    if data_source_type in [DataSourceType.GLUE, DataSourceType.DATAZONE, DataSourceType.S3]:
        if not credentials.get("external_id") and project_id:
            credentials["external_id"] = f"chicory-{project_id}"
            logger.info(f"Auto-generated external_id for {data_source_type}: chicory-{project_id}")
    
    # Handle specific types of validations
    if data_source_type == DataSourceType.GITHUB:
        return validator(
            access_token=credentials.get("access_token")
        )
    elif data_source_type == DataSourceType.JIRA:
        return validator(
            access_token=credentials.get("access_token"),
            cloud_id=credentials.get("cloud_id")
        )
    elif data_source_type == DataSourceType.DATABRICKS:
        return validator(
            access_token=credentials.get("access_token"),
            host=credentials.get("host"),
            catalog=credentials.get("catalog"),
            schema=credentials.get("schema"),
            http_path=credentials.get("http_path"),
            workspace_url=credentials.get("workspace_url"),
            database=credentials.get("database")
        )
    elif data_source_type == DataSourceType.GOOGLE_DRIVE:
        return validator(
            project_id=credentials.get("project_id"),
            private_key_id=credentials.get("private_key_id"),
            private_key=credentials.get("private_key"),
            client_email=credentials.get("client_email"),
            client_id=credentials.get("client_id"),
            client_cert_url=credentials.get("client_cert_url"),
            folder_id=credentials.get("folder_id")
        )
    elif data_source_type == DataSourceType.SNOWFLAKE:
        return validator(
            account=credentials.get("account"),
            username=credentials.get("username"),
            password=credentials.get("password"),
            private_key=credentials.get("private_key"),
            private_key_passphrase=credentials.get("private_key_passphrase"),
            role=credentials.get("role"),
            warehouse=credentials.get("warehouse"),
            database=credentials.get("database"),
            schema=credentials.get("schema")
        )
    elif data_source_type == DataSourceType.BIGQUERY:
        return validator(
            project_id=credentials.get("project_id"),
            private_key_id=credentials.get("private_key_id"),
            private_key=credentials.get("private_key"),
            client_email=credentials.get("client_email"),
            client_id=credentials.get("client_id"),
            client_cert_url=credentials.get("client_cert_url"),
            dataset_id=credentials.get("dataset_id")
        )
    elif data_source_type == DataSourceType.GLUE:
        return validator(
            role_arn=credentials.get("role_arn"),
            external_id=credentials.get("external_id"),
            region=credentials.get("region")
        )
    elif data_source_type == DataSourceType.DATAZONE:
        return validator(
            role_arn=credentials.get("role_arn"),
            external_id=credentials.get("external_id"),
            region=credentials.get("region")
        )
    elif data_source_type == DataSourceType.REDASH:
        return validator(
            base_url=credentials.get("base_url"),
            api_key=credentials.get("api_key")
        )
    elif data_source_type == DataSourceType.DBT:
        return validator(
            api_token=credentials.get("api_token"),
            account_id=credentials.get("account_id"),
            base_url=credentials.get("base_url"),
            project_id=credentials.get("project_id"),
            environment_id=credentials.get("environment_id")
        )
    elif data_source_type == DataSourceType.LOOKER:
        return validator(
            base_url=credentials.get("base_url"),
            client_id=credentials.get("client_id"),
            client_secret=credentials.get("client_secret")
        )
    elif data_source_type == DataSourceType.DATAHUB:
        return validator(
            base_url=credentials.get("base_url"),
            api_key=credentials.get("api_key")
        )
    elif data_source_type == DataSourceType.AIRFLOW:
        return validator(
            base_url=credentials.get("base_url"),
            username=credentials.get("username"),
            password=credentials.get("password")
        )
    elif data_source_type == DataSourceType.ANTHROPIC:
        return validator(
            api_key=credentials.get("api_key")
        )
    elif data_source_type == DataSourceType.S3:
        return validator(
            role_arn=credentials.get("role_arn"),
            external_id=credentials.get("external_id"),
            region=credentials.get("region")
        )
    elif data_source_type == DataSourceType.AZURE_BLOB_STORAGE:
        return validator(
            tenant_id=credentials.get("tenant_id"),
            client_id=credentials.get("client_id"),
            client_secret=credentials.get("client_secret"),
            subscription_id=credentials.get("subscription_id"),
            storage_account_name=credentials.get("storage_account_name")
        )
    elif data_source_type == DataSourceType.AZURE_DATA_FACTORY:
        return validator(
            tenant_id=credentials.get("tenant_id"),
            client_id=credentials.get("client_id"),
            client_secret=credentials.get("client_secret"),
            subscription_id=credentials.get("subscription_id"),
            resource_group=credentials.get("resource_group"),
            factory_name=credentials.get("factory_name")
        )
    elif data_source_type == DataSourceType.WEBFETCH:
        return validator(
            api_key=credentials.get("api_key"),
            mode=credentials.get("mode", "scrape"),
            url=credentials.get("url"),
            start_url=credentials.get("start_url"),
            max_pages=credentials.get("max_pages")
        )
    elif data_source_type == DataSourceType.ATLAN:
        return validator(
            tenant_url=credentials.get("tenant_url"),
            api_token=credentials.get("api_token")
        )

    # Default fallback if no specific handling is defined
    # but validator exists
    return validator(**credentials)
