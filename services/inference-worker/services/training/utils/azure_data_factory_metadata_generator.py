"""
Azure Data Factory metadata generator for scanning and cataloging ADF resources.
Generates metadata for pipelines, datasets, triggers, linked services, data flows,
and integration runtimes using Azure AD Service Principal authentication.
"""

import json
import os
import datetime
from datetime import timedelta, timezone
from services.utils.logger import logger

# Try to import Azure libraries
try:
    from azure.identity import ClientSecretCredential
    from azure.mgmt.datafactory import DataFactoryManagementClient
    from azure.mgmt.datafactory.models import RunFilterParameters
    AZURE_ADF_AVAILABLE = True
except ImportError:
    logger.warning("Azure Data Factory libraries not available. Install with: pip install azure-identity azure-mgmt-datafactory")
    AZURE_ADF_AVAILABLE = False


def setup_azure_adf_client(config):
    """
    Set up Azure Data Factory client using Service Principal authentication

    Args:
        config: Dictionary containing Azure configuration
            - tenant_id: Azure AD tenant ID
            - client_id: Application (Client) ID
            - client_secret: Client secret
            - subscription_id: Azure subscription ID

    Returns:
        DataFactoryManagementClient instance
    """
    if not AZURE_ADF_AVAILABLE:
        raise ImportError("Azure Data Factory libraries not installed")

    if not config:
        return None

    try:
        # Extract configuration
        tenant_id = config.get("tenant_id")
        client_id = config.get("client_id")
        client_secret = config.get("client_secret")
        subscription_id = config.get("subscription_id")

        # Validate required fields
        required_fields = ['tenant_id', 'client_id', 'client_secret', 'subscription_id']
        missing_fields = [field for field in required_fields if not config.get(field)]

        if missing_fields:
            logger.error(f"Missing required Azure ADF fields: {missing_fields}")
            return None

        # Create credential using service principal
        credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret
        )

        # Create DataFactoryManagementClient
        adf_client = DataFactoryManagementClient(
            credential=credential,
            subscription_id=subscription_id
        )

        logger.info(f"Azure Data Factory client created for subscription: {subscription_id}")
        return adf_client

    except Exception as e:
        logger.error(f"Failed to create Azure Data Factory client: {e}")
        return None


def test_azure_adf_connection(client, resource_group, factory_name):
    """
    Test Azure Data Factory connection by getting factory info

    Args:
        client: DataFactoryManagementClient instance
        resource_group: Resource group name
        factory_name: Data factory name

    Returns:
        Factory info dict if successful, None otherwise
    """
    try:
        factory = client.factories.get(resource_group, factory_name)
        logger.info(f"Azure Data Factory connection test successful: {factory.name}")
        return {
            "name": factory.name,
            "location": factory.location,
            "provisioning_state": factory.provisioning_state,
            "create_time": str(factory.create_time) if factory.create_time else None,
            "version": factory.version
        }
    except Exception as e:
        logger.error(f"Azure Data Factory connection test failed: {e}")
        return None


def get_pipelines(client, resource_group, factory_name):
    """
    Get all pipelines from Azure Data Factory

    Args:
        client: DataFactoryManagementClient instance
        resource_group: Resource group name
        factory_name: Data factory name

    Returns:
        List of pipeline dictionaries
    """
    try:
        pipelines = []
        for pipeline in client.pipelines.list_by_factory(resource_group, factory_name):
            # Get full pipeline details
            pipeline_detail = client.pipelines.get(resource_group, factory_name, pipeline.name)

            activities = []
            if pipeline_detail.activities:
                for activity in pipeline_detail.activities:
                    activity_info = {
                        "name": activity.name,
                        "type": activity.type,
                        "description": getattr(activity, 'description', None),
                        "depends_on": [
                            {"activity": dep.activity, "dependency_conditions": dep.dependency_conditions}
                            for dep in (activity.depends_on or [])
                        ]
                    }
                    activities.append(activity_info)

            parameters = {}
            if pipeline_detail.parameters:
                for param_name, param_spec in pipeline_detail.parameters.items():
                    parameters[param_name] = {
                        "type": param_spec.type if hasattr(param_spec, 'type') else str(type(param_spec).__name__),
                        "default": str(param_spec.default_value) if hasattr(param_spec, 'default_value') and param_spec.default_value else None
                    }

            variables = {}
            if pipeline_detail.variables:
                for var_name, var_spec in pipeline_detail.variables.items():
                    variables[var_name] = {
                        "type": var_spec.type if hasattr(var_spec, 'type') else str(type(var_spec).__name__),
                        "default": str(var_spec.default_value) if hasattr(var_spec, 'default_value') and var_spec.default_value else None
                    }

            pipelines.append({
                "name": pipeline.name,
                "description": pipeline_detail.description,
                "folder": pipeline_detail.folder.name if pipeline_detail.folder else None,
                "activities": activities,
                "parameters": parameters,
                "variables": variables,
                "annotations": pipeline_detail.annotations or [],
                "concurrency": pipeline_detail.concurrency
            })

        logger.info(f"Retrieved {len(pipelines)} pipelines from Azure Data Factory")
        return pipelines

    except Exception as e:
        logger.error(f"Failed to get pipelines: {e}")
        return []


def get_datasets(client, resource_group, factory_name):
    """
    Get all datasets from Azure Data Factory

    Args:
        client: DataFactoryManagementClient instance
        resource_group: Resource group name
        factory_name: Data factory name

    Returns:
        List of dataset dictionaries
    """
    try:
        datasets = []
        for dataset in client.datasets.list_by_factory(resource_group, factory_name):
            # Get full dataset details
            dataset_detail = client.datasets.get(resource_group, factory_name, dataset.name)

            properties = dataset_detail.properties

            schema = []
            if hasattr(properties, 'schema') and properties.schema:
                for col in properties.schema:
                    if isinstance(col, dict):
                        schema.append(col)
                    else:
                        schema.append({
                            "name": getattr(col, 'name', str(col)),
                            "type": getattr(col, 'type', None)
                        })

            parameters = {}
            if hasattr(properties, 'parameters') and properties.parameters:
                for param_name, param_spec in properties.parameters.items():
                    parameters[param_name] = {
                        "type": param_spec.type if hasattr(param_spec, 'type') else str(type(param_spec).__name__),
                        "default": str(param_spec.default_value) if hasattr(param_spec, 'default_value') and param_spec.default_value else None
                    }

            datasets.append({
                "name": dataset.name,
                "type": properties.type,
                "description": getattr(properties, 'description', None),
                "linked_service": properties.linked_service_name.reference_name if hasattr(properties, 'linked_service_name') and properties.linked_service_name else None,
                "schema": schema,
                "folder": properties.folder.name if hasattr(properties, 'folder') and properties.folder else None,
                "parameters": parameters,
                "annotations": getattr(properties, 'annotations', []) or []
            })

        logger.info(f"Retrieved {len(datasets)} datasets from Azure Data Factory")
        return datasets

    except Exception as e:
        logger.error(f"Failed to get datasets: {e}")
        return []


def get_triggers(client, resource_group, factory_name):
    """
    Get all triggers from Azure Data Factory

    Args:
        client: DataFactoryManagementClient instance
        resource_group: Resource group name
        factory_name: Data factory name

    Returns:
        List of trigger dictionaries
    """
    try:
        triggers = []
        for trigger in client.triggers.list_by_factory(resource_group, factory_name):
            # Get full trigger details
            trigger_detail = client.triggers.get(resource_group, factory_name, trigger.name)

            properties = trigger_detail.properties

            # Extract trigger-specific info based on type
            trigger_info = {
                "name": trigger.name,
                "type": properties.type,
                "description": getattr(properties, 'description', None),
                "runtime_state": properties.runtime_state,
                "annotations": getattr(properties, 'annotations', []) or []
            }

            # Add schedule info for schedule triggers
            if hasattr(properties, 'recurrence'):
                recurrence = properties.recurrence
                trigger_info["schedule"] = {
                    "frequency": recurrence.frequency if recurrence else None,
                    "interval": recurrence.interval if recurrence else None,
                    "start_time": str(recurrence.start_time) if recurrence and recurrence.start_time else None,
                    "end_time": str(recurrence.end_time) if recurrence and recurrence.end_time else None,
                    "time_zone": recurrence.time_zone if recurrence else None
                }

            # Add pipeline associations
            if hasattr(properties, 'pipelines') and properties.pipelines:
                trigger_info["pipelines"] = [
                    {
                        "pipeline_name": p.pipeline_reference.reference_name if p.pipeline_reference else None,
                        "parameters": p.parameters or {}
                    }
                    for p in properties.pipelines
                ]

            triggers.append(trigger_info)

        logger.info(f"Retrieved {len(triggers)} triggers from Azure Data Factory")
        return triggers

    except Exception as e:
        logger.error(f"Failed to get triggers: {e}")
        return []


def get_linked_services(client, resource_group, factory_name):
    """
    Get all linked services from Azure Data Factory

    Args:
        client: DataFactoryManagementClient instance
        resource_group: Resource group name
        factory_name: Data factory name

    Returns:
        List of linked service dictionaries
    """
    try:
        linked_services = []
        for ls in client.linked_services.list_by_factory(resource_group, factory_name):
            # Get full linked service details
            ls_detail = client.linked_services.get(resource_group, factory_name, ls.name)

            properties = ls_detail.properties

            linked_services.append({
                "name": ls.name,
                "type": properties.type,
                "description": getattr(properties, 'description', None),
                "annotations": getattr(properties, 'annotations', []) or [],
                "connect_via": properties.connect_via.reference_name if hasattr(properties, 'connect_via') and properties.connect_via else None
            })

        logger.info(f"Retrieved {len(linked_services)} linked services from Azure Data Factory")
        return linked_services

    except Exception as e:
        logger.error(f"Failed to get linked services: {e}")
        return []


def get_data_flows(client, resource_group, factory_name):
    """
    Get all data flows from Azure Data Factory

    Args:
        client: DataFactoryManagementClient instance
        resource_group: Resource group name
        factory_name: Data factory name

    Returns:
        List of data flow dictionaries
    """
    try:
        data_flows = []
        for df in client.data_flows.list_by_factory(resource_group, factory_name):
            # Get full data flow details
            df_detail = client.data_flows.get(resource_group, factory_name, df.name)

            properties = df_detail.properties

            # Extract sources and sinks if available
            sources = []
            sinks = []

            if hasattr(properties, 'type_properties') and properties.type_properties:
                type_props = properties.type_properties
                if hasattr(type_props, 'sources'):
                    sources = [
                        {"name": s.name, "dataset": getattr(s.dataset, 'reference_name', None) if hasattr(s, 'dataset') and s.dataset else None}
                        for s in (type_props.sources or [])
                    ]
                if hasattr(type_props, 'sinks'):
                    sinks = [
                        {"name": s.name, "dataset": getattr(s.dataset, 'reference_name', None) if hasattr(s, 'dataset') and s.dataset else None}
                        for s in (type_props.sinks or [])
                    ]

            data_flows.append({
                "name": df.name,
                "type": properties.type,
                "description": getattr(properties, 'description', None),
                "folder": properties.folder.name if hasattr(properties, 'folder') and properties.folder else None,
                "annotations": getattr(properties, 'annotations', []) or [],
                "sources": sources,
                "sinks": sinks
            })

        logger.info(f"Retrieved {len(data_flows)} data flows from Azure Data Factory")
        return data_flows

    except Exception as e:
        logger.error(f"Failed to get data flows: {e}")
        return []


def get_integration_runtimes(client, resource_group, factory_name):
    """
    Get all integration runtimes from Azure Data Factory

    Args:
        client: DataFactoryManagementClient instance
        resource_group: Resource group name
        factory_name: Data factory name

    Returns:
        List of integration runtime dictionaries
    """
    try:
        integration_runtimes = []
        for ir in client.integration_runtimes.list_by_factory(resource_group, factory_name):
            # Get full IR details including status
            ir_detail = client.integration_runtimes.get(resource_group, factory_name, ir.name)

            properties = ir_detail.properties

            ir_info = {
                "name": ir.name,
                "type": properties.type,
                "description": getattr(properties, 'description', None)
            }

            # Try to get status
            try:
                status = client.integration_runtimes.get_status(resource_group, factory_name, ir.name)
                ir_info["state"] = status.properties.state if hasattr(status.properties, 'state') else None
            except Exception:
                ir_info["state"] = None

            integration_runtimes.append(ir_info)

        logger.info(f"Retrieved {len(integration_runtimes)} integration runtimes from Azure Data Factory")
        return integration_runtimes

    except Exception as e:
        logger.error(f"Failed to get integration runtimes: {e}")
        return []


def get_pipeline_runs(client, resource_group, factory_name, days_back=7):
    """
    Get recent pipeline runs from Azure Data Factory

    Args:
        client: DataFactoryManagementClient instance
        resource_group: Resource group name
        factory_name: Data factory name
        days_back: Number of days to look back for runs

    Returns:
        List of pipeline run dictionaries
    """
    try:
        # Calculate time range
        end_time = datetime.datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days_back)

        filter_params = RunFilterParameters(
            last_updated_after=start_time,
            last_updated_before=end_time
        )

        runs = []
        response = client.pipeline_runs.query_by_factory(
            resource_group,
            factory_name,
            filter_params
        )

        for run in response.value:
            duration_seconds = None
            if run.run_start and run.run_end:
                duration = run.run_end - run.run_start
                duration_seconds = duration.total_seconds()

            runs.append({
                "run_id": run.run_id,
                "pipeline_name": run.pipeline_name,
                "status": run.status,
                "start_time": str(run.run_start) if run.run_start else None,
                "end_time": str(run.run_end) if run.run_end else None,
                "duration_seconds": duration_seconds,
                "message": run.message,
                "invoked_by": {
                    "name": run.invoked_by.name if run.invoked_by else None,
                    "type": run.invoked_by.invoked_by_type if run.invoked_by else None
                } if run.invoked_by else None
            })

        logger.info(f"Retrieved {len(runs)} pipeline runs from last {days_back} days")
        return runs

    except Exception as e:
        logger.error(f"Failed to get pipeline runs: {e}")
        return []


def format_pipeline_card(pipeline_data, factory_info, config):
    """
    Generate schema card for a pipeline

    Args:
        pipeline_data: Dictionary containing pipeline metadata
        factory_info: Factory information dictionary
        config: Azure configuration

    Returns:
        Dictionary containing formatted pipeline card
    """
    subscription_id = config.get("subscription_id")
    resource_group = config.get("resource_group")
    factory_name = config.get("factory_name")
    pipeline_name = pipeline_data.get("name")

    fqtn = f"azure-adf://{subscription_id}/{resource_group}/{factory_name}/pipeline/{pipeline_name}"

    return {
        "version": "1.0",
        "provider": "azure_data_factory",
        "dialect": "azure_adf",
        "resource_type": "pipeline",
        "address": {
            "subscription_id": subscription_id,
            "resource_group": resource_group,
            "factory_name": factory_name,
            "name": pipeline_name
        },
        "fqtn": fqtn,
        "kind": "pipeline",
        "description": pipeline_data.get("description"),
        "folder": pipeline_data.get("folder"),
        "activities": pipeline_data.get("activities", []),
        "parameters": pipeline_data.get("parameters", {}),
        "variables": pipeline_data.get("variables", {}),
        "annotations": pipeline_data.get("annotations", []),
        "concurrency": pipeline_data.get("concurrency")
    }


def format_dataset_card(dataset_data, config):
    """
    Generate schema card for a dataset

    Args:
        dataset_data: Dictionary containing dataset metadata
        config: Azure configuration

    Returns:
        Dictionary containing formatted dataset card
    """
    subscription_id = config.get("subscription_id")
    resource_group = config.get("resource_group")
    factory_name = config.get("factory_name")
    dataset_name = dataset_data.get("name")

    fqtn = f"azure-adf://{subscription_id}/{resource_group}/{factory_name}/dataset/{dataset_name}"

    return {
        "version": "1.0",
        "provider": "azure_data_factory",
        "dialect": "azure_adf",
        "resource_type": "dataset",
        "address": {
            "subscription_id": subscription_id,
            "resource_group": resource_group,
            "factory_name": factory_name,
            "name": dataset_name
        },
        "fqtn": fqtn,
        "kind": "dataset",
        "type": dataset_data.get("type"),
        "description": dataset_data.get("description"),
        "linked_service": dataset_data.get("linked_service"),
        "schema": dataset_data.get("schema", []),
        "folder": dataset_data.get("folder"),
        "parameters": dataset_data.get("parameters", {}),
        "annotations": dataset_data.get("annotations", [])
    }


def generate_azure_data_factory_overview(
    base_dir,
    project,
    dest_folder,
    azure_adf_config,
    days_back=7,
    output_format="json"
):
    """
    Generate Azure Data Factory metadata overview

    Args:
        base_dir: Base directory for project data
        project: Project identifier
        dest_folder: Destination folder for metadata files
        azure_adf_config: Azure ADF configuration dictionary
        days_back: Number of days to look back for execution history
        output_format: Output format - "json", "text", or "both"
    """
    if not AZURE_ADF_AVAILABLE:
        logger.error("Azure Data Factory libraries not available. Cannot generate overview.")
        return

    try:
        # Setup client
        client = setup_azure_adf_client(azure_adf_config)
        if not client:
            logger.error("Failed to setup Azure Data Factory client")
            return

        resource_group = azure_adf_config.get("resource_group")
        factory_name = azure_adf_config.get("factory_name")

        # Test connection
        factory_info = test_azure_adf_connection(client, resource_group, factory_name)
        if not factory_info:
            logger.error("Azure Data Factory connection test failed")
            return

        # Create metadata directory structure
        metadata_base = os.path.join(dest_folder, "database_metadata")
        provider_dir = os.path.join(metadata_base, "providers", "azure_data_factory")

        # Create subdirectories for each resource type
        pipelines_dir = os.path.join(provider_dir, "pipelines")
        datasets_dir = os.path.join(provider_dir, "datasets")
        triggers_dir = os.path.join(provider_dir, "triggers")
        linked_services_dir = os.path.join(provider_dir, "linked_services")
        data_flows_dir = os.path.join(provider_dir, "data_flows")
        integration_runtimes_dir = os.path.join(provider_dir, "integration_runtimes")
        execution_history_dir = os.path.join(provider_dir, "execution_history")

        for dir_path in [pipelines_dir, datasets_dir, triggers_dir, linked_services_dir,
                         data_flows_dir, integration_runtimes_dir, execution_history_dir]:
            os.makedirs(dir_path, exist_ok=True)

        # Track statistics
        manifest_entries = []

        # Get and save pipelines
        logger.info("Fetching pipelines...")
        pipelines = get_pipelines(client, resource_group, factory_name)
        for pipeline in pipelines:
            pipeline_card = format_pipeline_card(pipeline, factory_info, azure_adf_config)
            file_path = os.path.join(pipelines_dir, f"{pipeline['name']}.json")
            with open(file_path, 'w') as f:
                json.dump(pipeline_card, f, indent=2, default=str)
            manifest_entries.append({
                "fqtn": pipeline_card["fqtn"],
                "provider": "azure_data_factory",
                "resource_type": "pipeline",
                "name": pipeline["name"],
                "file_path": f"providers/azure_data_factory/pipelines/{pipeline['name']}.json"
            })

        # Get and save datasets
        logger.info("Fetching datasets...")
        datasets = get_datasets(client, resource_group, factory_name)
        for dataset in datasets:
            dataset_card = format_dataset_card(dataset, azure_adf_config)
            file_path = os.path.join(datasets_dir, f"{dataset['name']}.json")
            with open(file_path, 'w') as f:
                json.dump(dataset_card, f, indent=2, default=str)
            manifest_entries.append({
                "fqtn": dataset_card["fqtn"],
                "provider": "azure_data_factory",
                "resource_type": "dataset",
                "name": dataset["name"],
                "file_path": f"providers/azure_data_factory/datasets/{dataset['name']}.json"
            })

        # Get and save triggers
        logger.info("Fetching triggers...")
        triggers = get_triggers(client, resource_group, factory_name)
        for trigger in triggers:
            fqtn = f"azure-adf://{azure_adf_config.get('subscription_id')}/{resource_group}/{factory_name}/trigger/{trigger['name']}"
            trigger_card = {
                "version": "1.0",
                "provider": "azure_data_factory",
                "dialect": "azure_adf",
                "resource_type": "trigger",
                "fqtn": fqtn,
                **trigger
            }
            file_path = os.path.join(triggers_dir, f"{trigger['name']}.json")
            with open(file_path, 'w') as f:
                json.dump(trigger_card, f, indent=2, default=str)
            manifest_entries.append({
                "fqtn": fqtn,
                "provider": "azure_data_factory",
                "resource_type": "trigger",
                "name": trigger["name"],
                "file_path": f"providers/azure_data_factory/triggers/{trigger['name']}.json"
            })

        # Get and save linked services
        logger.info("Fetching linked services...")
        linked_services = get_linked_services(client, resource_group, factory_name)
        for ls in linked_services:
            fqtn = f"azure-adf://{azure_adf_config.get('subscription_id')}/{resource_group}/{factory_name}/linked_service/{ls['name']}"
            ls_card = {
                "version": "1.0",
                "provider": "azure_data_factory",
                "dialect": "azure_adf",
                "resource_type": "linked_service",
                "fqtn": fqtn,
                **ls
            }
            file_path = os.path.join(linked_services_dir, f"{ls['name']}.json")
            with open(file_path, 'w') as f:
                json.dump(ls_card, f, indent=2, default=str)
            manifest_entries.append({
                "fqtn": fqtn,
                "provider": "azure_data_factory",
                "resource_type": "linked_service",
                "name": ls["name"],
                "file_path": f"providers/azure_data_factory/linked_services/{ls['name']}.json"
            })

        # Get and save data flows
        logger.info("Fetching data flows...")
        data_flows = get_data_flows(client, resource_group, factory_name)
        for df in data_flows:
            fqtn = f"azure-adf://{azure_adf_config.get('subscription_id')}/{resource_group}/{factory_name}/data_flow/{df['name']}"
            df_card = {
                "version": "1.0",
                "provider": "azure_data_factory",
                "dialect": "azure_adf",
                "resource_type": "data_flow",
                "fqtn": fqtn,
                **df
            }
            file_path = os.path.join(data_flows_dir, f"{df['name']}.json")
            with open(file_path, 'w') as f:
                json.dump(df_card, f, indent=2, default=str)
            manifest_entries.append({
                "fqtn": fqtn,
                "provider": "azure_data_factory",
                "resource_type": "data_flow",
                "name": df["name"],
                "file_path": f"providers/azure_data_factory/data_flows/{df['name']}.json"
            })

        # Get and save integration runtimes
        logger.info("Fetching integration runtimes...")
        integration_runtimes = get_integration_runtimes(client, resource_group, factory_name)
        for ir in integration_runtimes:
            fqtn = f"azure-adf://{azure_adf_config.get('subscription_id')}/{resource_group}/{factory_name}/integration_runtime/{ir['name']}"
            ir_card = {
                "version": "1.0",
                "provider": "azure_data_factory",
                "dialect": "azure_adf",
                "resource_type": "integration_runtime",
                "fqtn": fqtn,
                **ir
            }
            file_path = os.path.join(integration_runtimes_dir, f"{ir['name']}.json")
            with open(file_path, 'w') as f:
                json.dump(ir_card, f, indent=2, default=str)
            manifest_entries.append({
                "fqtn": fqtn,
                "provider": "azure_data_factory",
                "resource_type": "integration_runtime",
                "name": ir["name"],
                "file_path": f"providers/azure_data_factory/integration_runtimes/{ir['name']}.json"
            })

        # Get and save pipeline runs
        logger.info(f"Fetching pipeline runs from last {days_back} days...")
        pipeline_runs = get_pipeline_runs(client, resource_group, factory_name, days_back)

        # Calculate execution summary
        succeeded = len([r for r in pipeline_runs if r.get("status") == "Succeeded"])
        failed = len([r for r in pipeline_runs if r.get("status") == "Failed"])
        durations = [r.get("duration_seconds") for r in pipeline_runs if r.get("duration_seconds")]
        avg_duration = sum(durations) / len(durations) if durations else 0

        execution_history = {
            "version": "1.0",
            "provider": "azure_data_factory",
            "days_back": days_back,
            "total_runs": len(pipeline_runs),
            "succeeded": succeeded,
            "failed": failed,
            "avg_duration_seconds": avg_duration,
            "runs": pipeline_runs
        }

        with open(os.path.join(execution_history_dir, "recent_runs.json"), 'w') as f:
            json.dump(execution_history, f, indent=2, default=str)

        # Create provider overview
        provider_overview = {
            "version": "1.0",
            "provider": "azure_data_factory",
            "factory_name": factory_name,
            "resource_group": resource_group,
            "subscription_id": azure_adf_config.get("subscription_id"),
            "location": factory_info.get("location"),
            "provisioning_state": factory_info.get("provisioning_state"),
            "total_pipelines": len(pipelines),
            "total_datasets": len(datasets),
            "total_triggers": len(triggers),
            "total_linked_services": len(linked_services),
            "total_data_flows": len(data_flows),
            "total_integration_runtimes": len(integration_runtimes),
            "connection_info": {
                "authentication": "service_principal",
                "tenant_id": azure_adf_config.get("tenant_id"),
                "version": factory_info.get("version")
            },
            "execution_summary": {
                f"last_{days_back}_days": {
                    "total_runs": len(pipeline_runs),
                    "succeeded": succeeded,
                    "failed": failed,
                    "avg_duration_seconds": avg_duration
                }
            },
            "scanned_at": datetime.datetime.now().isoformat()
        }

        with open(os.path.join(provider_dir, "provider_overview.json"), 'w') as f:
            json.dump(provider_overview, f, indent=2, default=str)

        # Create manifest
        manifest = {
            "version": "1.0",
            "provider": "azure_data_factory",
            "resources": manifest_entries
        }

        with open(os.path.join(provider_dir, "manifest.json"), 'w') as f:
            json.dump(manifest, f, indent=2, default=str)

        logger.info(f"Azure Data Factory metadata generation completed: "
                    f"{len(pipelines)} pipelines, {len(datasets)} datasets, "
                    f"{len(triggers)} triggers, {len(linked_services)} linked services, "
                    f"{len(data_flows)} data flows, {len(integration_runtimes)} integration runtimes")

    except Exception as e:
        logger.error(f"Failed to generate Azure Data Factory overview: {e}", exc_info=True)
