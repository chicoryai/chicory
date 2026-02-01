"""
S3 provider for AWS S3 operations.
"""

import logging
import os
import boto3
from typing import Any, Dict, List, Optional
from botocore.exceptions import ClientError, BotoCoreError

from providers.base import ToolsProvider

logger = logging.getLogger(__name__)


class S3Provider(ToolsProvider):
    """
    AWS S3 provider for object storage operations.
    """

    def __init__(self):
        super().__init__()
        self.region: Optional[str] = None
        self.role_arn: Optional[str] = None
        self.external_id: Optional[str] = None
        self.client: Optional[Any] = None

    async def _initialize_client(self) -> None:
        """Initialize AWS S3 client with credentials."""
        if not self.credentials:
            raise ValueError("No credentials provided")

        # Extract S3 connection parameters
        self.region = self.credentials.get("region", "us-east-1")
        self.role_arn = self.credentials.get("role_arn")
        self.external_id = self.credentials.get("external_id")

        # Validate required parameters
        if not all([self.role_arn, self.external_id]):
            raise ValueError("Missing required S3 credentials: role_arn, external_id")

        # Assume role with external ID
        try:
            sts_client = boto3.client('sts')

            logger.info(f"Attempting intermediary role pattern for: {self.role_arn}")

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
                RoleArn=self.role_arn,
                RoleSessionName='chicory-mcp-session',
                ExternalId=self.external_id
            )

            credentials = final_assumed['Credentials']
            logger.info(f"Intermediary role assumption succeeded for: {self.role_arn}")

            # Create S3 client with assumed role credentials
            self.client = boto3.client(
                's3',
                region_name=self.region,
                aws_access_key_id=credentials['AccessKeyId'],
                aws_secret_access_key=credentials['SecretAccessKey'],
                aws_session_token=credentials['SessionToken']
            )

            logger.info(f"S3 provider initialized successfully for region: {self.region}")

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            raise

    def _handle_error(self, operation: str, error: Exception) -> Dict[str, Any]:
        """Handle AWS errors and return standardized error response."""
        error_msg = str(error)
        logger.error(f"S3 {operation} failed: {error_msg}")
        return {"error": error_msg}

    async def list_buckets(self) -> Dict[str, Any]:
        """List all S3 buckets."""
        self._log_operation("list_buckets")
        self._ensure_initialized()

        try:
            response = self.client.list_buckets()

            buckets = response.get('Buckets', [])
            return {
                "buckets": buckets,
                "count": len(buckets),
                "owner": response.get('Owner')
            }

        except (ClientError, BotoCoreError) as e:
            return self._handle_error("list_buckets", e)

    async def list_objects(self, bucket_name: str, prefix: str = "",
                          max_keys: int = 1000, delimiter: str = "") -> Dict[str, Any]:
        """
        List objects in an S3 bucket.

        Args:
            bucket_name: Name of the S3 bucket
            prefix: Prefix to filter objects
            max_keys: Maximum number of objects to return
            delimiter: Delimiter for grouping keys (e.g., '/' for folder structure)

        Returns:
            Dictionary containing list of objects and metadata
        """
        self._log_operation("list_objects", bucket_name=bucket_name, prefix=prefix)
        self._ensure_initialized()

        try:
            params = {
                'Bucket': bucket_name,
                'MaxKeys': max_keys
            }

            if prefix:
                params['Prefix'] = prefix

            if delimiter:
                params['Delimiter'] = delimiter

            response = self.client.list_objects_v2(**params)

            contents = response.get('Contents', [])
            common_prefixes = response.get('CommonPrefixes', [])

            return {
                "objects": contents,
                "count": len(contents),
                "common_prefixes": common_prefixes,
                "is_truncated": response.get('IsTruncated', False),
                "next_continuation_token": response.get('NextContinuationToken'),
                "prefix": response.get('Prefix', ''),
                "delimiter": response.get('Delimiter', '')
            }

        except (ClientError, BotoCoreError) as e:
            return self._handle_error("list_objects", e)

    async def get_object(self, bucket_name: str, object_key: str) -> Dict[str, Any]:
        """
        Get an object from S3.

        Args:
            bucket_name: Name of the S3 bucket
            object_key: Key of the object to retrieve

        Returns:
            Dictionary containing object data and metadata
        """
        self._log_operation("get_object", bucket_name=bucket_name, object_key=object_key)
        self._ensure_initialized()

        try:
            response = self.client.get_object(Bucket=bucket_name, Key=object_key)

            # Read the body content
            body = response['Body'].read()

            # Try to decode as UTF-8 text, otherwise return base64
            try:
                content = body.decode('utf-8')
                content_type = 'text'
            except UnicodeDecodeError:
                import base64
                content = base64.b64encode(body).decode('utf-8')
                content_type = 'base64'

            return {
                "content": content,
                "content_type": content_type,
                "metadata": {
                    "content_type": response.get('ContentType'),
                    "content_length": response.get('ContentLength'),
                    "last_modified": str(response.get('LastModified')),
                    "etag": response.get('ETag'),
                    "version_id": response.get('VersionId'),
                    "user_metadata": response.get('Metadata', {})
                }
            }

        except (ClientError, BotoCoreError) as e:
            return self._handle_error("get_object", e)

    async def get_object_metadata(self, bucket_name: str, object_key: str) -> Dict[str, Any]:
        """
        Get metadata for an S3 object without downloading the content.

        Args:
            bucket_name: Name of the S3 bucket
            object_key: Key of the object

        Returns:
            Dictionary containing object metadata
        """
        self._log_operation("get_object_metadata", bucket_name=bucket_name, object_key=object_key)
        self._ensure_initialized()

        try:
            response = self.client.head_object(Bucket=bucket_name, Key=object_key)

            return {
                "metadata": {
                    "content_type": response.get('ContentType'),
                    "content_length": response.get('ContentLength'),
                    "last_modified": str(response.get('LastModified')),
                    "etag": response.get('ETag'),
                    "version_id": response.get('VersionId'),
                    "storage_class": response.get('StorageClass'),
                    "user_metadata": response.get('Metadata', {}),
                    "server_side_encryption": response.get('ServerSideEncryption')
                }
            }

        except (ClientError, BotoCoreError) as e:
            return self._handle_error("get_object_metadata", e)

    async def create_bucket(self, bucket_name: str, region: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new S3 bucket.

        Args:
            bucket_name: Name of the bucket to create
            region: AWS region for the bucket (defaults to provider region)

        Returns:
            Dictionary containing creation result
        """
        self._log_operation("create_bucket", bucket_name=bucket_name, region=region)
        self._ensure_initialized()

        try:
            # Use provider region if not specified
            target_region = region or self.region

            params = {'Bucket': bucket_name}

            # Only add LocationConstraint if not us-east-1 (default region)
            if target_region and target_region != 'us-east-1':
                params['CreateBucketConfiguration'] = {
                    'LocationConstraint': target_region
                }

            response = self.client.create_bucket(**params)

            return {
                "success": True,
                "bucket_name": bucket_name,
                "location": response.get('Location'),
                "region": target_region
            }

        except (ClientError, BotoCoreError) as e:
            return self._handle_error("create_bucket", e)

    async def put_object(self, bucket_name: str, object_key: str, content: str,
                        content_type: Optional[str] = None,
                        metadata: Optional[Dict[str, str]] = None,
                        storage_class: str = "STANDARD") -> Dict[str, Any]:
        """
        Upload an object to S3.

        Args:
            bucket_name: Name of the S3 bucket
            object_key: Key for the object
            content: Content to upload (string or base64 encoded)
            content_type: MIME type of the content (optional)
            metadata: User-defined metadata (optional)
            storage_class: Storage class (default: STANDARD)

        Returns:
            Dictionary containing upload result
        """
        self._log_operation("put_object", bucket_name=bucket_name, object_key=object_key)
        self._ensure_initialized()

        try:
            # Try to detect if content is base64 encoded
            import base64
            try:
                # If content looks like base64, decode it
                if len(content) % 4 == 0 and all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=' for c in content[:100]):
                    body = base64.b64decode(content)
                else:
                    body = content.encode('utf-8')
            except Exception:
                # If decoding fails, treat as regular text
                body = content.encode('utf-8')

            params = {
                'Bucket': bucket_name,
                'Key': object_key,
                'Body': body,
                'StorageClass': storage_class
            }

            if content_type:
                params['ContentType'] = content_type

            if metadata:
                params['Metadata'] = metadata

            response = self.client.put_object(**params)

            return {
                "success": True,
                "bucket_name": bucket_name,
                "object_key": object_key,
                "etag": response.get('ETag'),
                "version_id": response.get('VersionId'),
                "server_side_encryption": response.get('ServerSideEncryption')
            }

        except (ClientError, BotoCoreError) as e:
            return self._handle_error("put_object", e)

    async def generate_presigned_url(self, bucket_name: str, object_key: str,
                                     operation: str = "get_object",
                                     expiration: int = 3600,
                                     http_method: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a presigned URL for S3 object operations.

        Args:
            bucket_name: Name of the S3 bucket
            object_key: Key of the object
            operation: S3 operation (e.g., 'get_object', 'put_object', 'delete_object')
            expiration: URL expiration time in seconds (default: 3600 = 1 hour)
            http_method: HTTP method override (e.g., 'GET', 'PUT', 'DELETE')

        Returns:
            Dictionary containing the presigned URL and metadata
        """
        self._log_operation("generate_presigned_url", bucket_name=bucket_name,
                          object_key=object_key, s3_operation=operation)
        self._ensure_initialized()

        try:
            params = {
                'Bucket': bucket_name,
                'Key': object_key
            }

            # Add HTTP method if specified
            if http_method:
                params['HttpMethod'] = http_method

            url = self.client.generate_presigned_url(
                ClientMethod=operation,
                Params=params,
                ExpiresIn=expiration
            )

            return {
                "success": True,
                "url": url,
                "bucket_name": bucket_name,
                "object_key": object_key,
                "operation": operation,
                "expiration_seconds": expiration
            }

        except (ClientError, BotoCoreError) as e:
            return self._handle_error("generate_presigned_url", e)

    async def generate_presigned_post(self, bucket_name: str, object_key: str,
                                      expiration: int = 3600,
                                      conditions: Optional[List[Any]] = None,
                                      fields: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Generate presigned POST data for direct browser uploads to S3.

        Args:
            bucket_name: Name of the S3 bucket
            object_key: Key for the object to be uploaded
            expiration: POST policy expiration time in seconds (default: 3600 = 1 hour)
            conditions: List of conditions for the policy (optional)
            fields: Dictionary of form fields to include (optional)

        Returns:
            Dictionary containing the presigned POST URL, fields, and metadata
        """
        self._log_operation("generate_presigned_post", bucket_name=bucket_name,
                          object_key=object_key)
        self._ensure_initialized()

        try:
            params = {
                'Bucket': bucket_name,
                'Key': object_key
            }

            kwargs = {
                'ExpiresIn': expiration
            }

            if conditions:
                kwargs['Conditions'] = conditions

            if fields:
                kwargs['Fields'] = fields

            response = self.client.generate_presigned_post(
                **params,
                **kwargs
            )

            return {
                "success": True,
                "url": response.get('url'),
                "fields": response.get('fields'),
                "bucket_name": bucket_name,
                "object_key": object_key,
                "expiration_seconds": expiration
            }

        except (ClientError, BotoCoreError) as e:
            return self._handle_error("generate_presigned_post", e)

    async def cleanup(self) -> None:
        """Clean up S3 provider resources."""
        if self.client:
            self.client = None

        await super().cleanup()
