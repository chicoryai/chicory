"""
Azure Blob Storage metadata generator for scanning and cataloging blob storage.
Generates metadata for containers and blobs using Azure AD Service Principal authentication.
"""

import json
import os
import datetime
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from services.utils.logger import logger

# Try to import Azure libraries
try:
    from azure.identity import ClientSecretCredential
    from azure.storage.blob import BlobServiceClient
    AZURE_BLOB_AVAILABLE = True
except ImportError:
    logger.warning("Azure Blob Storage libraries not available. Install with: pip install azure-identity azure-storage-blob")
    AZURE_BLOB_AVAILABLE = False


def setup_azure_blob_client(config):
    """
    Set up Azure Blob Storage client using Service Principal authentication

    Args:
        config: Dictionary containing Azure configuration
            - tenant_id: Azure AD tenant ID
            - client_id: Application (Client) ID
            - client_secret: Client secret
            - storage_account_name: Name of the storage account

    Returns:
        BlobServiceClient instance
    """
    if not AZURE_BLOB_AVAILABLE:
        raise ImportError("Azure Blob Storage libraries not installed")

    if not config:
        return None

    try:
        # Extract configuration
        tenant_id = config.get("tenant_id")
        client_id = config.get("client_id")
        client_secret = config.get("client_secret")
        storage_account_name = config.get("storage_account_name")

        # Validate required fields
        required_fields = ['tenant_id', 'client_id', 'client_secret', 'storage_account_name']
        missing_fields = [field for field in required_fields if not config.get(field)]

        if missing_fields:
            logger.error(f"Missing required Azure Blob Storage fields: {missing_fields}")
            return None

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

        logger.info(f"Azure Blob Storage client created for account: {storage_account_name}")
        return blob_service_client

    except Exception as e:
        logger.error(f"Failed to create Azure Blob Storage client: {e}")
        return None


def test_azure_blob_connection(client):
    """
    Test Azure Blob Storage connection by listing containers

    Args:
        client: BlobServiceClient instance

    Returns:
        True if connection successful, False otherwise
    """
    try:
        # Simple test - list containers (limit to 1)
        for container in client.list_containers():
            break  # Just need to verify we can list, no need to fetch all
        logger.info("Azure Blob Storage connection test successful")
        return True

    except Exception as e:
        logger.error(f"Azure Blob Storage connection test failed: {e}")
        return False


def get_containers(client, target_containers=None):
    """
    Get list of containers from Azure Blob Storage

    Args:
        client: BlobServiceClient instance
        target_containers: Optional list of specific container names to fetch

    Returns:
        List of container objects with metadata
    """
    try:
        containers = []

        if target_containers:
            # Fetch specific containers
            for container_name in target_containers:
                try:
                    container_client = client.get_container_client(container_name)
                    properties = container_client.get_container_properties()
                    containers.append({
                        "name": properties.name,
                        "last_modified": str(properties.last_modified) if properties.last_modified else None,
                        "etag": properties.etag,
                        "public_access": properties.public_access,
                        "has_immutability_policy": properties.has_immutability_policy,
                        "has_legal_hold": properties.has_legal_hold,
                        "metadata": properties.metadata or {}
                    })
                except Exception as e:
                    logger.warning(f"Failed to get container {container_name}: {e}")
        else:
            # Fetch all containers
            for container in client.list_containers():
                containers.append({
                    "name": container['name'],
                    "last_modified": str(container.get('last_modified', '')),
                    "metadata": container.get('metadata', {}),
                    "public_access": container.get('public_access'),
                    "has_immutability_policy": container.get('has_immutability_policy', False),
                    "has_legal_hold": container.get('has_legal_hold', False)
                })

        logger.info(f"Retrieved {len(containers)} containers from Azure Blob Storage")
        return containers

    except Exception as e:
        logger.error(f"Failed to get container list: {e}")
        return []


def get_blobs_in_container(client, container_name, max_blobs=1000):
    """
    Get list of blobs in a container

    Args:
        client: BlobServiceClient instance
        container_name: Name of the container
        max_blobs: Maximum number of blobs to retrieve

    Returns:
        List of blob metadata dictionaries
    """
    try:
        container_client = client.get_container_client(container_name)
        blobs = []

        for blob in container_client.list_blobs():
            blobs.append({
                "name": blob.name,
                "size": blob.size,
                "content_type": blob.content_settings.content_type if blob.content_settings else None,
                "last_modified": str(blob.last_modified) if blob.last_modified else None,
                "created_on": str(blob.creation_time) if blob.creation_time else None,
                "etag": blob.etag,
                "blob_type": blob.blob_type,
                "access_tier": blob.blob_tier,
                "metadata": blob.metadata or {}
            })

            if len(blobs) >= max_blobs:
                logger.info(f"Reached max_blobs limit ({max_blobs}) for container {container_name}")
                break

        logger.info(f"Retrieved {len(blobs)} blobs from container {container_name}")
        return blobs

    except Exception as e:
        logger.error(f"Failed to get blobs from container {container_name}: {e}")
        return []


def infer_file_format(blob_name, content_type):
    """
    Infer file format from blob name and content type

    Args:
        blob_name: Name of the blob
        content_type: MIME content type

    Returns:
        Inferred format string
    """
    # Extension-based inference
    ext_map = {
        '.parquet': 'parquet',
        '.csv': 'csv',
        '.json': 'json',
        '.jsonl': 'jsonl',
        '.avro': 'avro',
        '.orc': 'orc',
        '.txt': 'text',
        '.xml': 'xml',
        '.tsv': 'tsv',
        '.gz': 'gzip',
        '.zip': 'zip',
        '.pdf': 'pdf',
        '.xlsx': 'excel',
        '.xls': 'excel',
    }

    blob_lower = blob_name.lower()
    for ext, fmt in ext_map.items():
        if blob_lower.endswith(ext):
            return fmt

    # Content-type based inference
    if content_type:
        ct_lower = content_type.lower()
        if 'parquet' in ct_lower:
            return 'parquet'
        elif 'csv' in ct_lower:
            return 'csv'
        elif 'json' in ct_lower:
            return 'json'
        elif 'xml' in ct_lower:
            return 'xml'
        elif 'text' in ct_lower:
            return 'text'

    return 'binary'


def format_blob_card(blob_data, storage_account, container_name):
    """
    Generate schema card for a blob

    Args:
        blob_data: Dictionary containing blob metadata
        storage_account: Name of the storage account
        container_name: Name of the container

    Returns:
        Dictionary containing formatted blob card
    """
    blob_path = blob_data.get("name", "")
    fqtn = f"azure-blob://{storage_account}/{container_name}/{blob_path}"

    inferred_format = infer_file_format(
        blob_path,
        blob_data.get("content_type")
    )

    return {
        "version": "1.0",
        "provider": "azure_blob_storage",
        "dialect": "azure_blob",
        "address": {
            "storage_account": storage_account,
            "container": container_name,
            "blob_path": blob_path
        },
        "fqtn": fqtn,
        "kind": "blob",
        "content_type": blob_data.get("content_type"),
        "size_bytes": blob_data.get("size"),
        "last_modified": blob_data.get("last_modified"),
        "created_on": blob_data.get("created_on"),
        "etag": blob_data.get("etag"),
        "blob_type": blob_data.get("blob_type"),
        "access_tier": blob_data.get("access_tier"),
        "metadata": blob_data.get("metadata", {}),
        "inferred_schema": {
            "format": inferred_format,
            "columns": []
        }
    }


def safe_filename(name):
    """
    Convert a blob path to a safe filename

    Args:
        name: Blob path

    Returns:
        Safe filename string
    """
    # Replace path separators and invalid characters
    safe = name.replace("/", "_").replace("\\", "_")
    # If too long, hash it
    if len(safe) > 200:
        hash_suffix = hashlib.md5(name.encode()).hexdigest()[:8]
        safe = safe[:190] + "_" + hash_suffix
    return safe


def generate_azure_blob_storage_overview(
    base_dir,
    project,
    dest_folder,
    azure_config,
    target_containers=None,
    max_blobs_per_container=1000,
    output_format="json"
):
    """
    Generate Azure Blob Storage metadata overview

    Args:
        base_dir: Base directory for project data
        project: Project identifier
        dest_folder: Destination folder for metadata files
        azure_config: Azure configuration dictionary
        target_containers: Optional list of specific containers to scan
        max_blobs_per_container: Maximum blobs to scan per container
        output_format: Output format - "json", "text", or "both"
    """
    if not AZURE_BLOB_AVAILABLE:
        logger.error("Azure Blob Storage libraries not available. Cannot generate overview.")
        return

    try:
        # Setup client
        client = setup_azure_blob_client(azure_config)
        if not client:
            logger.error("Failed to setup Azure Blob Storage client")
            return

        # Test connection
        if not test_azure_blob_connection(client):
            logger.error("Azure Blob Storage connection test failed")
            return

        storage_account = azure_config.get("storage_account_name")

        # Create metadata directory structure
        metadata_base = os.path.join(dest_folder, "database_metadata")
        provider_dir = os.path.join(metadata_base, "providers", "azure_blob_storage")
        containers_dir = os.path.join(provider_dir, "containers")
        os.makedirs(containers_dir, exist_ok=True)

        # Get containers
        containers = get_containers(client, target_containers)

        if not containers:
            logger.warning("No containers found in Azure Blob Storage")
            return

        logger.info(f"Processing {len(containers)} containers...")

        # Track overall statistics
        total_blobs = 0
        total_size_bytes = 0
        manifest_entries = []

        # Process each container
        for container in containers:
            container_name = container.get('name')
            logger.info(f"Processing container: {container_name}")

            # Create container directory
            container_dir = os.path.join(containers_dir, container_name)
            blobs_dir = os.path.join(container_dir, "blobs")
            os.makedirs(blobs_dir, exist_ok=True)

            # Save container metadata
            container_metadata = {
                "version": "1.0",
                "provider": "azure_blob_storage",
                "resource_type": "container",
                "address": {
                    "storage_account": storage_account,
                    "container": container_name
                },
                "fqtn": f"azure-blob://{storage_account}/{container_name}",
                "name": container_name,
                "last_modified": container.get("last_modified"),
                "public_access": container.get("public_access"),
                "has_immutability_policy": container.get("has_immutability_policy"),
                "has_legal_hold": container.get("has_legal_hold"),
                "metadata": container.get("metadata", {})
            }

            with open(os.path.join(container_dir, "container_metadata.json"), 'w') as f:
                json.dump(container_metadata, f, indent=2, default=str)

            try:
                # Get blobs in container
                blobs = get_blobs_in_container(client, container_name, max_blobs_per_container)

                # Process each blob
                for blob in blobs:
                    blob_name = blob.get("name")

                    try:
                        # Create blob card
                        blob_card = format_blob_card(blob, storage_account, container_name)

                        # Save blob metadata
                        safe_name = safe_filename(blob_name)
                        blob_file_path = os.path.join(blobs_dir, f"{safe_name}.json")

                        with open(blob_file_path, 'w') as f:
                            json.dump(blob_card, f, indent=2, default=str)

                        # Add to manifest
                        manifest_entries.append({
                            "fqtn": blob_card["fqtn"],
                            "provider": "azure_blob_storage",
                            "container": container_name,
                            "blob_path": blob_name,
                            "content_type": blob.get("content_type"),
                            "size_bytes": blob.get("size"),
                            "file_path": f"providers/azure_blob_storage/containers/{container_name}/blobs/{safe_name}.json"
                        })

                        total_blobs += 1
                        total_size_bytes += blob.get("size", 0) or 0

                    except Exception as e:
                        logger.warning(f"Could not process blob {container_name}/{blob_name}: {e}")
                        continue

            except Exception as e:
                logger.error(f"Failed to process container {container_name}: {e}")

        # Create provider overview
        provider_overview = {
            "version": "1.0",
            "provider": "azure_blob_storage",
            "storage_account_name": storage_account,
            "total_containers": len(containers),
            "total_blobs": total_blobs,
            "total_size_bytes": total_size_bytes,
            "connection_info": {
                "authentication": "service_principal",
                "tenant_id": azure_config.get("tenant_id")
            },
            "scanned_at": datetime.datetime.now().isoformat()
        }

        with open(os.path.join(provider_dir, "provider_overview.json"), 'w') as f:
            json.dump(provider_overview, f, indent=2, default=str)

        # Create manifest
        manifest = {
            "version": "1.0",
            "provider": "azure_blob_storage",
            "blobs": manifest_entries
        }

        with open(os.path.join(provider_dir, "manifest.json"), 'w') as f:
            json.dump(manifest, f, indent=2, default=str)

        logger.info(f"Azure Blob Storage metadata generation completed: {total_blobs} blobs from {len(containers)} containers")

    except Exception as e:
        logger.error(f"Failed to generate Azure Blob Storage overview: {e}", exc_info=True)
