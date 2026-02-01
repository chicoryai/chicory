import logging
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError

# Configure logging
logger = logging.getLogger(__name__)

def validate_credentials(role_arn: str, external_id: str,
                        region: Optional[str] = None) -> Dict[str, Any]:
    """
    Validate AWS Glue credentials using IAM role assumption with cross-account access

    Args:
        role_arn: IAM role ARN to assume for Glue access (e.g., arn:aws:iam::123456789012:role/RoleName)
        external_id: External ID for secure cross-account access
        region: AWS region (defaults to us-east-1 if not provided)

    Returns:
        Dict with status (success/error) and message
    """
    # Validate required fields
    if not role_arn:
        logger.error('IAM role ARN not provided')
        return {
            "status": "error",
            "message": "IAM role ARN is required",
            "details": None
        }

    if not external_id:
        logger.error('External ID not provided')
        return {
            "status": "error",
            "message": "External ID is required for secure cross-account access",
            "details": None
        }

    # Validate ARN format
    if not role_arn.startswith('arn:aws:iam::'):
        logger.error('Invalid ARN format')
        return {
            "status": "error",
            "message": "Invalid ARN format. Expected format: arn:aws:iam::ACCOUNT_ID:role/ROLE_NAME",
            "details": None
        }

    # Set default region if not provided
    if not region:
        region = 'us-east-1'
        logger.info(f'No region provided, using default: {region}')

    try:
        # Use the provided ARN directly
        logger.info(f'Attempting to assume role: {role_arn}')

        # Create STS client to assume role
        sts_client = boto3.client('sts', region_name=region)

        # Assume the role with external ID for security
        logger.info('Assuming IAM role with external ID...')
        assume_role_response = sts_client.assume_role(
            RoleArn=role_arn,
            RoleSessionName='GlueValidationSession',
            ExternalId=external_id,
            DurationSeconds=900  # 15 minutes session
        )

        # Extract temporary credentials
        credentials = assume_role_response['Credentials']
        logger.info('Successfully assumed IAM role')

        # Create Glue client with temporary credentials
        logger.info(f'Creating Glue client in region: {region}')
        glue_client = boto3.client(
            'glue',
            region_name=region,
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken']
        )

        # Test connection by listing databases
        logger.info('Testing Glue access by listing databases...')
        databases_response = glue_client.get_databases(MaxResults=10)

        databases = databases_response.get('DatabaseList', [])
        database_count = len(databases)
        database_names = [db['Name'] for db in databases[:10]]

        logger.info(f'Successfully listed {database_count} databases')

        # Get additional metadata if databases exist
        database_details = []
        if databases:
            # Get table count for first database as a sample
            sample_db = databases[0]['Name']
            try:
                tables_response = glue_client.get_tables(
                    DatabaseName=sample_db,
                    MaxResults=10
                )
                tables = tables_response.get('TableList', [])
                table_count = len(tables)
                table_names = [table['Name'] for table in tables]

                database_details.append({
                    "database_name": sample_db,
                    "table_count": table_count,
                    "sample_tables": table_names
                })
                logger.info(f'Successfully accessed database {sample_db} with {table_count} tables')
            except Exception as e:
                logger.warning(f'Could not retrieve tables from {sample_db}: {str(e)}')

        # Prepare success response with detailed info
        success_message = f"AWS Glue connection successful in region {region}"
        if database_count > 0:
            success_message += f" with access to {database_count} database(s)"

        return {
            "status": "success",
            "message": success_message,
            "details": {
                "region": region,
                "role_arn": role_arn,
                "database_count": database_count,
                "available_databases": database_names,
                "database_details": database_details if database_details else None
            }
        }

    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']

        logger.error(f'AWS Glue connection error [{error_code}]: {error_message}')

        # Provide specific error messages for common issues
        if error_code == 'AccessDenied':
            return {
                "status": "error",
                "message": f"Access denied: Unable to assume role or access Glue. Verify role permissions and external ID. Error: {error_message}",
                "details": {
                    "error_code": error_code,
                    "role_arn": role_arn
                }
            }
        elif error_code == 'InvalidClientTokenId':
            return {
                "status": "error",
                "message": "Invalid AWS credentials: The security token is invalid",
                "details": {"error_code": error_code}
            }
        elif error_code == 'EntityDoesNotExist':
            return {
                "status": "error",
                "message": f"IAM role not found: {role_arn}",
                "details": {
                    "error_code": error_code,
                    "role_arn": role_arn
                }
            }
        else:
            return {
                "status": "error",
                "message": f"AWS error [{error_code}]: {error_message}",
                "details": {"error_code": error_code}
            }

    except NoCredentialsError:
        logger.error('No AWS credentials found')
        return {
            "status": "error",
            "message": "No AWS credentials configured. Please configure AWS credentials for the application.",
            "details": None
        }

    except PartialCredentialsError as e:
        logger.error(f'Incomplete AWS credentials: {str(e)}')
        return {
            "status": "error",
            "message": f"Incomplete AWS credentials: {str(e)}",
            "details": None
        }

    except Exception as e:
        logger.error(f'Unexpected error during Glue validation: {str(e)}')
        return {
            "status": "error",
            "message": f"Connection error: {str(e)}",
            "details": None
        }
