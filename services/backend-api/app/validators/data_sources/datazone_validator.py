import logging
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError

# Configure logging
logger = logging.getLogger(__name__)

def validate_credentials(role_arn: str, external_id: str,
                        region: Optional[str] = None) -> Dict[str, Any]:
    """
    Validate AWS DataZone credentials using IAM role assumption with cross-account access

    Args:
        role_arn: IAM role ARN to assume for DataZone access (e.g., arn:aws:iam::123456789012:role/RoleName)
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
            RoleSessionName='DataZoneValidationSession',
            ExternalId=external_id,
            DurationSeconds=900  # 15 minutes session
        )

        # Extract temporary credentials
        credentials = assume_role_response['Credentials']
        logger.info('Successfully assumed IAM role')

        # Create DataZone client with temporary credentials
        logger.info(f'Creating DataZone client in region: {region}')
        datazone_client = boto3.client(
            'datazone',
            region_name=region,
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken']
        )

        # Test connection by listing domains
        logger.info('Testing DataZone access by listing domains...')
        domains_response = datazone_client.list_domains(maxResults=10)

        domains = domains_response.get('items', [])
        domain_count = len(domains)
        domain_names = [domain['name'] for domain in domains[:10]]

        logger.info(f'Successfully listed {domain_count} domain(s)')

        # Get additional metadata if domains exist
        domain_details = []
        if domains:
            # Get project count for first domain as a sample
            sample_domain_id = domains[0]['id']
            sample_domain_name = domains[0]['name']
            try:
                projects_response = datazone_client.list_projects(
                    domainIdentifier=sample_domain_id,
                    maxResults=10
                )
                projects = projects_response.get('items', [])
                project_count = len(projects)
                project_names = [project['name'] for project in projects]

                domain_details.append({
                    "domain_id": sample_domain_id,
                    "domain_name": sample_domain_name,
                    "project_count": project_count,
                    "sample_projects": project_names
                })
                logger.info(f'Successfully accessed domain {sample_domain_name} with {project_count} project(s)')
            except Exception as e:
                logger.warning(f'Could not retrieve projects from {sample_domain_name}: {str(e)}')

        # Prepare success response with detailed info
        success_message = f"AWS DataZone connection successful in region {region}"
        if domain_count > 0:
            success_message += f" with access to {domain_count} domain(s)"

        return {
            "status": "success",
            "message": success_message,
            "details": {
                "region": region,
                "role_arn": role_arn,
                "domain_count": domain_count,
                "available_domains": domain_names,
                "domain_details": domain_details if domain_details else None
            }
        }

    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']

        logger.error(f'AWS DataZone connection error [{error_code}]: {error_message}')

        # Provide specific error messages for common issues
        if error_code == 'AccessDenied' or error_code == 'AccessDeniedException':
            return {
                "status": "error",
                "message": f"Access denied: Unable to assume role or access DataZone. Verify role permissions and external ID. Error: {error_message}",
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
        elif error_code == 'EntityDoesNotExist' or error_code == 'NoSuchEntity':
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
        logger.error(f'Unexpected error during DataZone validation: {str(e)}')
        return {
            "status": "error",
            "message": f"Connection error: {str(e)}",
            "details": None
        }
