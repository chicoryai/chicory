import logging
from typing import Dict, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)


def validate_credentials(
    tenant_id: str,
    client_id: str,
    client_secret: str,
    subscription_id: str,
    resource_group: str,
    factory_name: str
) -> Dict[str, Any]:
    """
    Validate Azure Data Factory credentials using Azure AD Service Principal authentication.

    Args:
        tenant_id: Azure AD Tenant ID
        client_id: Application (Client) ID
        client_secret: Client Secret
        subscription_id: Azure Subscription ID
        resource_group: Resource Group Name
        factory_name: Data Factory Name

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

    if not subscription_id:
        logger.error('Azure Subscription ID not provided')
        return {
            "status": "error",
            "message": "Azure Subscription ID is required",
            "details": None
        }

    if not resource_group:
        logger.error('Resource Group Name not provided')
        return {
            "status": "error",
            "message": "Resource Group Name is required",
            "details": None
        }

    if not factory_name:
        logger.error('Data Factory Name not provided')
        return {
            "status": "error",
            "message": "Data Factory Name is required",
            "details": None
        }

    try:
        from azure.identity import ClientSecretCredential
        from azure.mgmt.datafactory import DataFactoryManagementClient

        logger.info(f'Attempting to authenticate with Azure AD for Data Factory: {factory_name}')

        # Create credential using service principal
        credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret
        )

        # Create Data Factory Management Client
        adf_client = DataFactoryManagementClient(
            credential=credential,
            subscription_id=subscription_id
        )

        # Test connection by getting factory details
        logger.info(f'Testing Data Factory access by getting factory details...')
        factory = adf_client.factories.get(
            resource_group_name=resource_group,
            factory_name=factory_name
        )

        logger.info(f'Successfully retrieved factory: {factory.name}')

        # List pipelines
        logger.info('Listing pipelines...')
        pipelines = list(adf_client.pipelines.list_by_factory(
            resource_group_name=resource_group,
            factory_name=factory_name
        ))
        pipeline_count = len(pipelines)
        pipeline_names = [p.name for p in pipelines[:10]]

        logger.info(f'Found {pipeline_count} pipelines')

        # List datasets
        logger.info('Listing datasets...')
        datasets = list(adf_client.datasets.list_by_factory(
            resource_group_name=resource_group,
            factory_name=factory_name
        ))
        dataset_count = len(datasets)
        dataset_names = [d.name for d in datasets[:10]]

        logger.info(f'Found {dataset_count} datasets')

        # List triggers
        logger.info('Listing triggers...')
        triggers = list(adf_client.triggers.list_by_factory(
            resource_group_name=resource_group,
            factory_name=factory_name
        ))
        trigger_count = len(triggers)
        trigger_names = [t.name for t in triggers[:10]]

        logger.info(f'Found {trigger_count} triggers')

        # List linked services
        logger.info('Listing linked services...')
        linked_services = list(adf_client.linked_services.list_by_factory(
            resource_group_name=resource_group,
            factory_name=factory_name
        ))
        linked_service_count = len(linked_services)
        linked_service_names = [ls.name for ls in linked_services[:10]]

        logger.info(f'Found {linked_service_count} linked services')

        # List data flows
        logger.info('Listing data flows...')
        data_flows = list(adf_client.data_flows.list_by_factory(
            resource_group_name=resource_group,
            factory_name=factory_name
        ))
        data_flow_count = len(data_flows)
        data_flow_names = [df.name for df in data_flows[:10]]

        logger.info(f'Found {data_flow_count} data flows')

        # List integration runtimes
        logger.info('Listing integration runtimes...')
        integration_runtimes = list(adf_client.integration_runtimes.list_by_factory(
            resource_group_name=resource_group,
            factory_name=factory_name
        ))
        ir_count = len(integration_runtimes)
        ir_names = [ir.name for ir in integration_runtimes[:10]]

        logger.info(f'Found {ir_count} integration runtimes')

        success_message = f"Azure Data Factory connection successful for factory {factory_name}"

        return {
            "status": "success",
            "message": success_message,
            "details": {
                "factory_name": factory_name,
                "resource_group": resource_group,
                "subscription_id": subscription_id,
                "factory_location": factory.location,
                "factory_provisioning_state": factory.provisioning_state,
                "pipeline_count": pipeline_count,
                "available_pipelines": pipeline_names,
                "dataset_count": dataset_count,
                "available_datasets": dataset_names,
                "trigger_count": trigger_count,
                "available_triggers": trigger_names,
                "linked_service_count": linked_service_count,
                "available_linked_services": linked_service_names,
                "data_flow_count": data_flow_count,
                "available_data_flows": data_flow_names,
                "integration_runtime_count": ir_count,
                "available_integration_runtimes": ir_names
            }
        }

    except ImportError as e:
        logger.error(f'Azure SDK not installed: {str(e)}')
        return {
            "status": "error",
            "message": "Azure SDK not installed. Please install azure-identity and azure-mgmt-datafactory packages.",
            "details": None
        }

    except Exception as e:
        error_message = str(e)
        logger.error(f'Azure Data Factory connection error: {error_message}')

        # Provide specific error messages for common issues
        if 'InvalidAuthenticationToken' in error_message or 'AuthenticationFailed' in error_message:
            return {
                "status": "error",
                "message": f"Authentication failed: Invalid credentials. Verify tenant_id, client_id, and client_secret. Error: {error_message}",
                "details": {
                    "error_type": "authentication_failed",
                    "factory_name": factory_name
                }
            }
        elif 'AuthorizationFailed' in error_message:
            return {
                "status": "error",
                "message": f"Authorization failed: The service principal does not have access to the Data Factory. Ensure the service principal has 'Data Factory Contributor' role. Error: {error_message}",
                "details": {
                    "error_type": "authorization_failed",
                    "factory_name": factory_name
                }
            }
        elif 'ResourceNotFound' in error_message or 'FactoryNotFound' in error_message:
            return {
                "status": "error",
                "message": f"Data Factory not found: {factory_name} in resource group {resource_group}",
                "details": {
                    "error_type": "factory_not_found",
                    "factory_name": factory_name,
                    "resource_group": resource_group
                }
            }
        elif 'ResourceGroupNotFound' in error_message:
            return {
                "status": "error",
                "message": f"Resource group not found: {resource_group}",
                "details": {
                    "error_type": "resource_group_not_found",
                    "resource_group": resource_group
                }
            }
        elif 'SubscriptionNotFound' in error_message or 'InvalidSubscriptionId' in error_message:
            return {
                "status": "error",
                "message": f"Invalid or inaccessible subscription: {subscription_id}",
                "details": {
                    "error_type": "subscription_not_found",
                    "subscription_id": subscription_id
                }
            }
        else:
            return {
                "status": "error",
                "message": f"Connection error: {error_message}",
                "details": {
                    "error_type": "unknown",
                    "factory_name": factory_name,
                    "resource_group": resource_group
                }
            }
