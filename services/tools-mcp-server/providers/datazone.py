"""
Datazone provider for AWS DataZone operations.
"""

import logging
import boto3
from typing import Any, Dict, List, Optional
from botocore.exceptions import ClientError, BotoCoreError

from providers.base import ToolsProvider

logger = logging.getLogger(__name__)


class DatazoneProvider(ToolsProvider):
    """
    AWS DataZone provider for data governance and catalog operations.
    """

    def __init__(self):
        super().__init__()
        self.region: Optional[str] = None
        self.role_arn: Optional[str] = None
        self.external_id: Optional[str] = None
        self.client: Optional[Any] = None

    async def _initialize_client(self) -> None:
        """Initialize AWS DataZone client with credentials."""
        if not self.credentials:
            raise ValueError("No credentials provided")

        # Extract DataZone connection parameters
        self.region = self.credentials.get("region")
        self.role_arn = self.credentials.get("role_arn")
        self.external_id = self.credentials.get("external_id")

        # Validate required parameters
        if not all([self.region, self.role_arn, self.external_id]):
            raise ValueError("Missing required DataZone credentials: region, role_arn, external_id")

        # Assume role with external ID
        try:
            sts_client = boto3.client('sts')

            assumed_role = sts_client.assume_role(
                RoleArn=self.role_arn,
                RoleSessionName='chicory-mcp-session',
                ExternalId=self.external_id
            )

            credentials = assumed_role['Credentials']

            # Create DataZone client with assumed role credentials
            self.client = boto3.client(
                'datazone',
                region_name=self.region,
                aws_access_key_id=credentials['AccessKeyId'],
                aws_secret_access_key=credentials['SecretAccessKey'],
                aws_session_token=credentials['SessionToken']
            )

            logger.info(f"DataZone provider initialized successfully for region: {self.region}")

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to initialize DataZone client: {e}")
            raise

    def _handle_error(self, operation: str, error: Exception) -> Dict[str, Any]:
        """Handle AWS errors and return standardized error response."""
        error_msg = str(error)
        logger.error(f"DataZone {operation} failed: {error_msg}")
        return {"error": error_msg}

    async def list_domains(self, max_results: int = 25) -> Dict[str, Any]:
        """List all DataZone domains."""
        self._log_operation("list_domains", max_results=max_results)
        self._ensure_initialized()

        try:
            response = self.client.list_domains(maxResults=max_results)

            domains = response.get('items', [])
            return {
                "domains": domains,
                "count": len(domains),
                "next_token": response.get('nextToken')
            }

        except (ClientError, BotoCoreError) as e:
            return self._handle_error("list_domains", e)

    async def get_domain(self, domain_id: str) -> Dict[str, Any]:
        """Get details of a specific DataZone domain."""
        self._log_operation("get_domain", domain_id=domain_id)
        self._ensure_initialized()

        try:
            response = self.client.get_domain(identifier=domain_id)
            return {"domain": response}

        except (ClientError, BotoCoreError) as e:
            return self._handle_error("get_domain", e)

    async def list_projects(self, domain_id: str, max_results: int = 25) -> Dict[str, Any]:
        """List all projects in a DataZone domain."""
        self._log_operation("list_projects", domain_id=domain_id, max_results=max_results)
        self._ensure_initialized()

        try:
            response = self.client.list_projects(
                domainIdentifier=domain_id,
                maxResults=max_results
            )

            projects = response.get('items', [])
            return {
                "projects": projects,
                "count": len(projects),
                "next_token": response.get('nextToken')
            }

        except (ClientError, BotoCoreError) as e:
            return self._handle_error("list_projects", e)

    async def get_project(self, domain_id: str, project_id: str) -> Dict[str, Any]:
        """Get details of a specific DataZone project."""
        self._log_operation("get_project", domain_id=domain_id, project_id=project_id)
        self._ensure_initialized()

        try:
            response = self.client.get_project(
                domainIdentifier=domain_id,
                identifier=project_id
            )
            return {"project": response}

        except (ClientError, BotoCoreError) as e:
            return self._handle_error("get_project", e)

    async def search_listings(self, domain_id: str, search_text: str = "",
                            filters: Optional[Dict[str, Any]] = None,
                            max_results: int = 25) -> Dict[str, Any]:
        """Search for data assets in DataZone catalog."""
        self._log_operation("search_listings", domain_id=domain_id, search_text=search_text)
        self._ensure_initialized()

        try:
            params = {
                'domainIdentifier': domain_id,
                'maxResults': max_results
            }

            if search_text:
                params['searchText'] = search_text

            if filters:
                params['filters'] = filters

            response = self.client.search_listings(**params)

            items = response.get('items', [])
            return {
                "listings": items,
                "count": len(items),
                "next_token": response.get('nextToken')
            }

        except (ClientError, BotoCoreError) as e:
            return self._handle_error("search_listings", e)

    async def get_listing(self, domain_id: str, listing_id: str) -> Dict[str, Any]:
        """Get details of a specific data listing."""
        self._log_operation("get_listing", domain_id=domain_id, listing_id=listing_id)
        self._ensure_initialized()

        try:
            response = self.client.get_listing(
                domainIdentifier=domain_id,
                identifier=listing_id
            )
            return {"listing": response}

        except (ClientError, BotoCoreError) as e:
            return self._handle_error("get_listing", e)

    async def list_environments(self, domain_id: str, project_id: str,
                               max_results: int = 25) -> Dict[str, Any]:
        """List environments in a DataZone project."""
        self._log_operation("list_environments", domain_id=domain_id, project_id=project_id)
        self._ensure_initialized()

        try:
            response = self.client.list_environments(
                domainIdentifier=domain_id,
                projectIdentifier=project_id,
                maxResults=max_results
            )

            environments = response.get('items', [])
            return {
                "environments": environments,
                "count": len(environments),
                "next_token": response.get('nextToken')
            }

        except (ClientError, BotoCoreError) as e:
            return self._handle_error("list_environments", e)

    async def get_environment(self, domain_id: str, environment_id: str) -> Dict[str, Any]:
        """Get details of a specific environment."""
        self._log_operation("get_environment", domain_id=domain_id, environment_id=environment_id)
        self._ensure_initialized()

        try:
            response = self.client.get_environment(
                domainIdentifier=domain_id,
                identifier=environment_id
            )
            return {"environment": response}

        except (ClientError, BotoCoreError) as e:
            return self._handle_error("get_environment", e)

    async def get_asset(self, domain_id: str, asset_id: str) -> Dict[str, Any]:
        """Get details of a specific data asset."""
        self._log_operation("get_asset", domain_id=domain_id, asset_id=asset_id)
        self._ensure_initialized()

        try:
            response = self.client.get_asset(
                domainIdentifier=domain_id,
                identifier=asset_id
            )
            return {"asset": response}

        except (ClientError, BotoCoreError) as e:
            return self._handle_error("get_asset", e)

    async def list_asset_revisions(self, domain_id: str, asset_id: str,
                                   max_results: int = 25) -> Dict[str, Any]:
        """List revisions of a data asset."""
        self._log_operation("list_asset_revisions", domain_id=domain_id, asset_id=asset_id)
        self._ensure_initialized()

        try:
            response = self.client.list_asset_revisions(
                domainIdentifier=domain_id,
                identifier=asset_id,
                maxResults=max_results
            )

            revisions = response.get('items', [])
            return {
                "revisions": revisions,
                "count": len(revisions),
                "next_token": response.get('nextToken')
            }

        except (ClientError, BotoCoreError) as e:
            return self._handle_error("list_asset_revisions", e)

    async def get_glossary(self, domain_id: str, glossary_id: str) -> Dict[str, Any]:
        """Get details of a business glossary."""
        self._log_operation("get_glossary", domain_id=domain_id, glossary_id=glossary_id)
        self._ensure_initialized()

        try:
            response = self.client.get_glossary(
                domainIdentifier=domain_id,
                identifier=glossary_id
            )
            return {"glossary": response}

        except (ClientError, BotoCoreError) as e:
            return self._handle_error("get_glossary", e)

    async def get_glossary_term(self, domain_id: str, term_id: str) -> Dict[str, Any]:
        """Get details of a glossary term."""
        self._log_operation("get_glossary_term", domain_id=domain_id, term_id=term_id)
        self._ensure_initialized()

        try:
            response = self.client.get_glossary_term(
                domainIdentifier=domain_id,
                identifier=term_id
            )
            return {"term": response}

        except (ClientError, BotoCoreError) as e:
            return self._handle_error("get_glossary_term", e)

    async def create_form_type(self, domain_id: str, name: str, model: Dict[str, Any],
                              owning_project_id: str, description: Optional[str] = None,
                              status: str = "ENABLED") -> Dict[str, Any]:
        """Create a new form type in DataZone."""
        self._log_operation("create_form_type", domain_id=domain_id, name=name)
        self._ensure_initialized()

        try:
            params = {
                'domainIdentifier': domain_id,
                'name': name,
                'model': model,
                'owningProjectIdentifier': owning_project_id,
                'status': status
            }

            if description:
                params['description'] = description

            response = self.client.create_form_type(**params)
            return {"form_type": response}

        except (ClientError, BotoCoreError) as e:
            return self._handle_error("create_form_type", e)

    async def get_form_type(self, domain_id: str, form_type_id: str,
                           revision: Optional[str] = None) -> Dict[str, Any]:
        """Get details of a specific form type."""
        self._log_operation("get_form_type", domain_id=domain_id, form_type_id=form_type_id)
        self._ensure_initialized()

        try:
            params = {
                'domainIdentifier': domain_id,
                'formTypeIdentifier': form_type_id
            }

            if revision:
                params['revision'] = revision

            response = self.client.get_form_type(**params)
            return {"form_type": response}

        except (ClientError, BotoCoreError) as e:
            return self._handle_error("get_form_type", e)

    async def create_asset_type(self, domain_id: str, name: str,
                               owning_project_id: str, description: Optional[str] = None,
                               forms_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a new asset type in DataZone."""
        self._log_operation("create_asset_type", domain_id=domain_id, name=name)
        self._ensure_initialized()

        try:
            params = {
                'domainIdentifier': domain_id,
                'name': name,
                'owningProjectIdentifier': owning_project_id
            }

            if description:
                params['description'] = description

            if forms_input:
                params['formsInput'] = forms_input

            response = self.client.create_asset_type(**params)
            return {"asset_type": response}

        except (ClientError, BotoCoreError) as e:
            return self._handle_error("create_asset_type", e)

    async def get_asset_type(self, domain_id: str, asset_type_id: str,
                            revision: Optional[str] = None) -> Dict[str, Any]:
        """Get details of a specific asset type."""
        self._log_operation("get_asset_type", domain_id=domain_id, asset_type_id=asset_type_id)
        self._ensure_initialized()

        try:
            params = {
                'domainIdentifier': domain_id,
                'identifier': asset_type_id
            }

            if revision:
                params['revision'] = revision

            response = self.client.get_asset_type(**params)
            return {"asset_type": response}

        except (ClientError, BotoCoreError) as e:
            return self._handle_error("get_asset_type", e)

    async def list_asset_types(self, domain_id: str, owning_project_id: Optional[str] = None,
                              max_results: int = 25) -> Dict[str, Any]:
        """List asset types in a DataZone domain."""
        self._log_operation("list_asset_types", domain_id=domain_id)
        self._ensure_initialized()

        try:
            params = {
                'domainIdentifier': domain_id,
                'maxResults': max_results
            }

            if owning_project_id:
                params['projectIdentifier'] = owning_project_id

            response = self.client.list_asset_types(**params)

            asset_types = response.get('items', [])
            return {
                "asset_types": asset_types,
                "count": len(asset_types),
                "next_token": response.get('nextToken')
            }

        except (ClientError, BotoCoreError) as e:
            return self._handle_error("list_asset_types", e)

    async def cleanup(self) -> None:
        """Clean up DataZone provider resources."""
        if self.client:
            self.client = None

        await super().cleanup()
