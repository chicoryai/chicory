import logging
from typing import Any, Dict, Optional

# Configure logging
logger = logging.getLogger(__name__)


def validate_credentials(
    tenant_id: str,
    client_id: str,
    client_secret: str,
    storage_account_name: str,
    subscription_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Validate Azure Blob Storage credentials using Azure AD Service Principal authentication.

    Args:
        tenant_id: Azure AD Tenant ID
        client_id: Application (Client) ID
        client_secret: Client Secret
        storage_account_name: Storage Account Name
        subscription_id: Azure Subscription ID (optional, not used for blob operations)

    Returns:
        Dict with status (success/error) and message
    """
    # Validate required fields
    if not tenant_id:
        logger.error('Azure AD Tenant ID not provided')
        return {
            "status": "error",
            "message": "Azure AD Tenant ID is required",
            "details": None
        }

    if not client_id:
        logger.error('Application (Client) ID not provided')
        return {
            "status": "error",
            "message": "Application (Client) ID is required",
            "details": None
        }

    if not client_secret:
        logger.error('Client Secret not provided')
        return {
            "status": "error",
            "message": "Client Secret is required",
            "details": None
        }

    # Note: subscription_id is accepted for consistency with other Azure integrations
    # but is not required for Blob Storage data plane operations

    if not storage_account_name:
        logger.error('Storage Account Name not provided')
        return {
            "status": "error",
            "message": "Storage Account Name is required",
            "details": None
        }

    try:
        from azure.identity import ClientSecretCredential
        from azure.storage.blob import BlobServiceClient

        logger.info(f'Attempting to authenticate with Azure AD for storage account: {storage_account_name}')

        # Create credential using service principal
        credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret
        )

        # Create BlobServiceClient
        account_url = f"https://{storage_account_name}.blob.core.windows.net"
        blob_service_client = BlobServiceClient(
            account_url=account_url,
            credential=credential
        )

        # Test connection by listing containers
        logger.info('Testing Blob Storage access by listing containers...')
        # Use results_per_page for pagination and take first 10
        container_list = []
        for container in blob_service_client.list_containers(results_per_page=10):
            container_list.append(container)
            if len(container_list) >= 10:
                break
        container_count = len(container_list)
        container_names = [container['name'] for container in container_list]

        logger.info(f'Successfully listed {container_count} containers')

        # Get storage account properties if accessible
        account_info = None
        try:
            account_info = blob_service_client.get_account_information()
            logger.info('Successfully retrieved account information')
        except Exception as e:
            logger.warning(f'Could not retrieve account information: {str(e)}')

        success_message = f"Azure Blob Storage connection successful for account {storage_account_name}"
        if container_count > 0:
            success_message += f" with access to {container_count} container(s)"

        return {
            "status": "success",
            "message": success_message,
            "details": {
                "storage_account_name": storage_account_name,
                "container_count": container_count,
                "available_containers": container_names,
                "account_info": {
                    "sku_name": account_info.get('sku_name') if account_info else None,
                    "account_kind": account_info.get('account_kind') if account_info else None
                } if account_info else None
            }
        }

    except ImportError as e:
        logger.error(f'Azure SDK not installed: {str(e)}')
        return {
            "status": "error",
            "message": "Azure SDK not installed. Please install azure-identity and azure-storage-blob packages.",
            "details": None
        }

    except Exception as e:
        error_message = str(e)
        logger.error(f'Azure Blob Storage connection error: {error_message}')

        # Provide specific error messages for common issues
        if 'InvalidAuthenticationInfo' in error_message or 'AuthenticationFailed' in error_message:
            return {
                "status": "error",
                "message": f"Authentication failed: Invalid credentials. Verify tenant_id, client_id, and client_secret. Error: {error_message}",
                "details": {
                    "error_type": "authentication_failed",
                    "storage_account_name": storage_account_name
                }
            }
        elif 'AuthorizationFailure' in error_message or 'AuthorizationPermissionMismatch' in error_message:
            return {
                "status": "error",
                "message": f"Authorization failed: The service principal does not have access to the storage account. Ensure the service principal has 'Storage Blob Data Reader' or 'Storage Blob Data Contributor' role. Error: {error_message}",
                "details": {
                    "error_type": "authorization_failed",
                    "storage_account_name": storage_account_name
                }
            }
        elif 'ResourceNotFound' in error_message or 'AccountNotFound' in error_message:
            return {
                "status": "error",
                "message": f"Storage account not found: {storage_account_name}",
                "details": {
                    "error_type": "account_not_found",
                    "storage_account_name": storage_account_name
                }
            }
        elif 'InvalidResourceName' in error_message:
            return {
                "status": "error",
                "message": f"Invalid storage account name: {storage_account_name}",
                "details": {
                    "error_type": "invalid_account_name",
                    "storage_account_name": storage_account_name
                }
            }
        else:
            return {
                "status": "error",
                "message": f"Connection error: {error_message}",
                "details": {
                    "error_type": "unknown",
                    "storage_account_name": storage_account_name
                }
            }
