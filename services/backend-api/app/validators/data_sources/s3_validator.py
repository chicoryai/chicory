import logging
import os
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError

# Configure logging
logger = logging.getLogger(__name__)

def validate_credentials(role_arn: str, external_id: str,
                        region: Optional[str] = None) -> Dict[str, Any]:
    """
    Validate AWS S3 credentials using IAM role assumption with cross-account access

    Args:
        role_arn: IAM role ARN to assume for S3 access (e.g., arn:aws:iam::123456789012:role/RoleName)
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
        # Create STS client (uses default credential chain)
        sts_client = boto3.client('sts')

        logger.info(f'Attempting intermediary role pattern for: {role_arn}')

        # Get current account ID to construct intermediary role ARN
        caller_identity = sts_client.get_caller_identity()
        account_id = caller_identity['Account']
        intermediary_role_name = os.environ.get('CHICORY_CUSTOMER_ROLE', 'ChicoryCustomerRole')
        intermediary_role_arn = f"arn:aws:iam::{account_id}:role/{intermediary_role_name}"

        # Hop 1: Assume intermediary role in Chicory account
        intermediary_assumed = sts_client.assume_role(
            RoleArn=intermediary_role_arn,
            RoleSessionName='chicory-intermediary-session'
        )

        intermediary_creds = intermediary_assumed['Credentials']

        # Hop 2: Use intermediary role to assume customer role
        intermediary_sts = boto3.client(
            'sts',
            aws_access_key_id=intermediary_creds['AccessKeyId'],
            aws_secret_access_key=intermediary_creds['SecretAccessKey'],
            aws_session_token=intermediary_creds['SessionToken']
        )

        final_assumed = intermediary_sts.assume_role(
            RoleArn=role_arn,
            RoleSessionName='chicory-mcp-session',
            ExternalId=external_id
        )

        credentials = final_assumed['Credentials']
        logger.info(f'Intermediary role assumption succeeded for: {role_arn}')

        # Role assumption succeeded - validation passes
        return {
            "status": "success",
            "message": f"Successfully assumed role {role_arn}",
            "details": {
                "region": region,
                "role_arn": role_arn,
                "session_expiration": credentials['Expiration'].isoformat()
            }
        }

    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']

        logger.error(f'AWS S3 connection error [{error_code}]: {error_message}')

        # Provide specific error messages for common issues
        if error_code == 'AccessDenied':
            return {
                "status": "error",
                "message": f"Access denied: Unable to assume role or access S3. Verify role permissions and external ID. Error: {error_message}",
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
        elif error_code == 'NoSuchBucket':
            return {
                "status": "error",
                "message": "The specified bucket does not exist",
                "details": {"error_code": error_code}
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
        logger.error(f'Unexpected error during S3 validation: {str(e)}')
        return {
            "status": "error",
            "message": f"Connection error: {str(e)}",
            "details": None
        }
