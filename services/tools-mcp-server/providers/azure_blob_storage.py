"""
Azure Blob Storage provider for blob storage operations.
"""

import logging
import base64
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from providers.base import ToolsProvider

logger = logging.getLogger(__name__)


class AzureBlobStorageProvider(ToolsProvider):
    """
    Azure Blob Storage provider for object storage operations.
    Uses Azure AD Service Principal authentication.
    """

    def __init__(self):
        super().__init__()
        self.tenant_id: Optional[str] = None
        self.client_id: Optional[str] = None
        self.client_secret: Optional[str] = None
        self.subscription_id: Optional[str] = None
        self.storage_account_name: Optional[str] = None
        self.blob_service_client: Optional[Any] = None

    async def _initialize_client(self) -> None:
        """Initialize Azure Blob Storage client with credentials."""
        if not self.credentials:
            raise ValueError("No credentials provided")

        # Extract Azure connection parameters
        self.tenant_id = self.credentials.get("tenant_id")
        self.client_id = self.credentials.get("client_id")
        self.client_secret = self.credentials.get("client_secret")
        self.subscription_id = self.credentials.get("subscription_id")
        self.storage_account_name = self.credentials.get("storage_account_name")

        # Validate required parameters
        if not all([self.tenant_id, self.client_id, self.client_secret, self.storage_account_name]):
            raise ValueError("Missing required Azure Blob Storage credentials: tenant_id, client_id, client_secret, storage_account_name")

        try:
            from azure.identity import ClientSecretCredential
            from azure.storage.blob import BlobServiceClient

            logger.info(f"Initializing Azure Blob Storage client for account: {self.storage_account_name}")

            # Create credential using service principal
            credential = ClientSecretCredential(
                tenant_id=self.tenant_id,
                client_id=self.client_id,
                client_secret=self.client_secret
            )

            # Create BlobServiceClient
            account_url = f"https://{self.storage_account_name}.blob.core.windows.net"
            self.blob_service_client = BlobServiceClient(
                account_url=account_url,
                credential=credential
            )

            # Store credential for SAS generation
            self._credential = credential

            logger.info(f"Azure Blob Storage provider initialized successfully for account: {self.storage_account_name}")

        except Exception as e:
            logger.error(f"Failed to initialize Azure Blob Storage client: {e}")
            raise

    def _handle_error(self, operation: str, error: Exception) -> Dict[str, Any]:
        """Handle Azure errors and return standardized error response."""
        error_msg = str(error)
        logger.error(f"Azure Blob Storage {operation} failed: {error_msg}")
        return {"error": error_msg}

    async def list_containers(self, max_results: int = 100) -> Dict[str, Any]:
        """
        List all containers in the storage account.

        Args:
            max_results: Maximum number of containers to return

        Returns:
            Dictionary containing list of containers and metadata
        """
        self._log_operation("list_containers", max_results=max_results)
        self._ensure_initialized()

        try:
            container_list = []
            for container in self.blob_service_client.list_containers():
                container_list.append({
                    "name": container['name'],
                    "last_modified": str(container.get('last_modified', '')),
                    "metadata": container.get('metadata', {}),
                    "public_access": container.get('public_access'),
                    "has_immutability_policy": container.get('has_immutability_policy', False),
                    "has_legal_hold": container.get('has_legal_hold', False)
                })
                if len(container_list) >= max_results:
                    break

            return {
                "containers": container_list,
                "count": len(container_list),
                "storage_account": self.storage_account_name
            }

        except Exception as e:
            return self._handle_error("list_containers", e)

    async def list_blobs(self, container_name: str, prefix: str = "",
                         max_results: int = 1000, delimiter: str = "") -> Dict[str, Any]:
        """
        List blobs in a container.

        Args:
            container_name: Name of the container
            prefix: Prefix to filter blobs
            max_results: Maximum number of blobs to return
            delimiter: Delimiter for virtual directory structure (e.g., '/')

        Returns:
            Dictionary containing list of blobs and metadata
        """
        self._log_operation("list_blobs", container_name=container_name, prefix=prefix)
        self._ensure_initialized()

        try:
            container_client = self.blob_service_client.get_container_client(container_name)

            if delimiter:
                # Use walk_blobs for hierarchical listing
                blobs = []
                prefixes = []
                for item in container_client.walk_blobs(name_starts_with=prefix, delimiter=delimiter):
                    if hasattr(item, 'prefix'):
                        prefixes.append({"prefix": item.prefix})
                    else:
                        blobs.append({
                            "name": item.name,
                            "size": item.size,
                            "content_type": item.content_settings.content_type if item.content_settings else None,
                            "last_modified": str(item.last_modified) if item.last_modified else None,
                            "etag": item.etag,
                            "blob_type": item.blob_type
                        })
                    if len(blobs) + len(prefixes) >= max_results:
                        break
            else:
                blobs = []
                for blob in container_client.list_blobs(name_starts_with=prefix):
                    blobs.append({
                        "name": blob.name,
                        "size": blob.size,
                        "content_type": blob.content_settings.content_type if blob.content_settings else None,
                        "last_modified": str(blob.last_modified) if blob.last_modified else None,
                        "etag": blob.etag,
                        "blob_type": blob.blob_type
                    })
                    if len(blobs) >= max_results:
                        break
                prefixes = []

            return {
                "blobs": blobs,
                "count": len(blobs),
                "common_prefixes": prefixes,
                "container_name": container_name,
                "prefix": prefix
            }

        except Exception as e:
            return self._handle_error("list_blobs", e)

    async def get_blob(self, container_name: str, blob_name: str) -> Dict[str, Any]:
        """
        Get a blob from a container.

        Args:
            container_name: Name of the container
            blob_name: Name of the blob to retrieve

        Returns:
            Dictionary containing blob data and metadata
        """
        self._log_operation("get_blob", container_name=container_name, blob_name=blob_name)
        self._ensure_initialized()

        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_name
            )

            # Download the blob content
            download_stream = blob_client.download_blob()
            blob_data = download_stream.readall()

            # Try to decode as UTF-8 text, otherwise return base64
            try:
                content = blob_data.decode('utf-8')
                content_type = 'text'
            except UnicodeDecodeError:
                content = base64.b64encode(blob_data).decode('utf-8')
                content_type = 'base64'

            # Get blob properties
            properties = blob_client.get_blob_properties()

            return {
                "content": content,
                "content_type": content_type,
                "metadata": {
                    "blob_type": properties.blob_type,
                    "content_type": properties.content_settings.content_type if properties.content_settings else None,
                    "content_length": properties.size,
                    "last_modified": str(properties.last_modified) if properties.last_modified else None,
                    "etag": properties.etag,
                    "creation_time": str(properties.creation_time) if properties.creation_time else None,
                    "user_metadata": properties.metadata
                }
            }

        except Exception as e:
            return self._handle_error("get_blob", e)

    async def get_blob_metadata(self, container_name: str, blob_name: str) -> Dict[str, Any]:
        """
        Get metadata for a blob without downloading the content.

        Args:
            container_name: Name of the container
            blob_name: Name of the blob

        Returns:
            Dictionary containing blob metadata
        """
        self._log_operation("get_blob_metadata", container_name=container_name, blob_name=blob_name)
        self._ensure_initialized()

        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_name
            )

            properties = blob_client.get_blob_properties()

            return {
                "metadata": {
                    "name": properties.name,
                    "blob_type": properties.blob_type,
                    "content_type": properties.content_settings.content_type if properties.content_settings else None,
                    "content_length": properties.size,
                    "last_modified": str(properties.last_modified) if properties.last_modified else None,
                    "etag": properties.etag,
                    "creation_time": str(properties.creation_time) if properties.creation_time else None,
                    "content_encoding": properties.content_settings.content_encoding if properties.content_settings else None,
                    "content_language": properties.content_settings.content_language if properties.content_settings else None,
                    "content_md5": properties.content_settings.content_md5 if properties.content_settings else None,
                    "cache_control": properties.content_settings.cache_control if properties.content_settings else None,
                    "lease_status": properties.lease.status if properties.lease else None,
                    "lease_state": properties.lease.state if properties.lease else None,
                    "copy_status": properties.copy.status if properties.copy else None,
                    "user_metadata": properties.metadata,
                    "access_tier": properties.blob_tier,
                    "archive_status": properties.archive_status
                }
            }

        except Exception as e:
            return self._handle_error("get_blob_metadata", e)

    async def upload_blob(self, container_name: str, blob_name: str, content: str,
                          content_type: Optional[str] = None,
                          metadata: Optional[Dict[str, str]] = None,
                          overwrite: bool = True) -> Dict[str, Any]:
        """
        Upload a blob to a container.

        Args:
            container_name: Name of the container
            blob_name: Name for the blob
            content: Content to upload (string or base64 encoded)
            content_type: MIME type of the content (optional)
            metadata: User-defined metadata (optional)
            overwrite: Whether to overwrite if blob exists (default: True)

        Returns:
            Dictionary containing upload result
        """
        self._log_operation("upload_blob", container_name=container_name, blob_name=blob_name)
        self._ensure_initialized()

        try:
            from azure.storage.blob import ContentSettings

            blob_client = self.blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_name
            )

            # Try to detect if content is base64 encoded
            try:
                # If content looks like base64, decode it
                if len(content) % 4 == 0 and all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=' for c in content[:100]):
                    data = base64.b64decode(content)
                else:
                    data = content.encode('utf-8')
            except Exception:
                # If decoding fails, treat as regular text
                data = content.encode('utf-8')

            # Prepare content settings
            content_settings = None
            if content_type:
                content_settings = ContentSettings(content_type=content_type)

            # Upload the blob
            result = blob_client.upload_blob(
                data=data,
                overwrite=overwrite,
                content_settings=content_settings,
                metadata=metadata
            )

            return {
                "success": True,
                "container_name": container_name,
                "blob_name": blob_name,
                "etag": result.get('etag'),
                "last_modified": str(result.get('last_modified', ''))
            }

        except Exception as e:
            return self._handle_error("upload_blob", e)

    async def delete_blob(self, container_name: str, blob_name: str) -> Dict[str, Any]:
        """
        Delete a blob from a container.

        Args:
            container_name: Name of the container
            blob_name: Name of the blob to delete

        Returns:
            Dictionary containing deletion result
        """
        self._log_operation("delete_blob", container_name=container_name, blob_name=blob_name)
        self._ensure_initialized()

        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_name
            )

            blob_client.delete_blob()

            return {
                "success": True,
                "container_name": container_name,
                "blob_name": blob_name,
                "message": f"Blob '{blob_name}' deleted successfully"
            }

        except Exception as e:
            return self._handle_error("delete_blob", e)

    async def generate_sas_url(self, container_name: str, blob_name: str,
                               expiry_hours: int = 1,
                               permission: str = "r") -> Dict[str, Any]:
        """
        Generate a SAS (Shared Access Signature) URL for a blob.

        Args:
            container_name: Name of the container
            blob_name: Name of the blob
            expiry_hours: URL expiration time in hours (default: 1)
            permission: Permission string (r=read, w=write, d=delete, default: r)

        Returns:
            Dictionary containing the SAS URL and metadata

        Note:
            This operation requires the service principal to have the
            'Storage Blob Delegator' role on the storage account to generate
            user delegation SAS tokens.
        """
        self._log_operation("generate_sas_url", container_name=container_name,
                            blob_name=blob_name, expiry_hours=expiry_hours)
        self._ensure_initialized()

        try:
            from azure.storage.blob import generate_blob_sas, BlobSasPermissions

            # Map permission string to BlobSasPermissions
            permissions = BlobSasPermissions(
                read='r' in permission,
                write='w' in permission,
                delete='d' in permission
            )

            # Calculate expiry time
            expiry = datetime.now(timezone.utc) + timedelta(hours=expiry_hours)

            # Get user delegation key (requires Storage Blob Delegator role)
            try:
                user_delegation_key = self.blob_service_client.get_user_delegation_key(
                    key_start_time=datetime.now(timezone.utc),
                    key_expiry_time=expiry
                )
            except Exception as delegation_error:
                error_msg = str(delegation_error)
                if 'AuthorizationPermissionMismatch' in error_msg or 'AuthorizationFailure' in error_msg:
                    return {
                        "error": "Permission denied: The service principal requires the 'Storage Blob Delegator' role "
                                 "to generate SAS URLs. Please assign this role to the service principal on the storage account.",
                        "error_type": "authorization_failed",
                        "container_name": container_name,
                        "blob_name": blob_name
                    }
                raise

            sas_token = generate_blob_sas(
                account_name=self.storage_account_name,
                container_name=container_name,
                blob_name=blob_name,
                user_delegation_key=user_delegation_key,
                permission=permissions,
                expiry=expiry
            )

            blob_url = f"https://{self.storage_account_name}.blob.core.windows.net/{container_name}/{blob_name}"
            sas_url = f"{blob_url}?{sas_token}"

            return {
                "success": True,
                "url": sas_url,
                "container_name": container_name,
                "blob_name": blob_name,
                "expiry": expiry.isoformat(),
                "expiry_hours": expiry_hours,
                "permission": permission
            }

        except Exception as e:
            return self._handle_error("generate_sas_url", e)

    async def get_container_properties(self, container_name: str) -> Dict[str, Any]:
        """
        Get properties for a container.

        Args:
            container_name: Name of the container

        Returns:
            Dictionary containing container properties
        """
        self._log_operation("get_container_properties", container_name=container_name)
        self._ensure_initialized()

        try:
            container_client = self.blob_service_client.get_container_client(container_name)
            properties = container_client.get_container_properties()

            return {
                "name": properties.name,
                "last_modified": str(properties.last_modified) if properties.last_modified else None,
                "etag": properties.etag,
                "lease_status": properties.lease.status if properties.lease else None,
                "lease_state": properties.lease.state if properties.lease else None,
                "public_access": properties.public_access,
                "has_immutability_policy": properties.has_immutability_policy,
                "has_legal_hold": properties.has_legal_hold,
                "metadata": properties.metadata
            }

        except Exception as e:
            return self._handle_error("get_container_properties", e)

    async def cleanup(self) -> None:
        """Clean up Azure Blob Storage provider resources."""
        if self.blob_service_client:
            self.blob_service_client = None

        await super().cleanup()
