"""
Azure Data Factory provider for ADF operations.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from providers.base import ToolsProvider

logger = logging.getLogger(__name__)


class AzureDataFactoryProvider(ToolsProvider):
    """
    Azure Data Factory provider for data integration operations.
    Uses Azure AD Service Principal authentication.
    """

    def __init__(self):
        super().__init__()
        self.tenant_id: Optional[str] = None
        self.client_id: Optional[str] = None
        self.client_secret: Optional[str] = None
        self.subscription_id: Optional[str] = None
        self.resource_group: Optional[str] = None
        self.factory_name: Optional[str] = None
        self.adf_client: Optional[Any] = None

    async def _initialize_client(self) -> None:
        """Initialize Azure Data Factory client with credentials."""
        if not self.credentials:
            raise ValueError("No credentials provided")

        # Extract Azure connection parameters
        self.tenant_id = self.credentials.get("tenant_id")
        self.client_id = self.credentials.get("client_id")
        self.client_secret = self.credentials.get("client_secret")
        self.subscription_id = self.credentials.get("subscription_id")
        self.resource_group = self.credentials.get("resource_group")
        self.factory_name = self.credentials.get("factory_name")

        # Validate required parameters
        if not all([self.tenant_id, self.client_id, self.client_secret,
                    self.subscription_id, self.resource_group, self.factory_name]):
            raise ValueError("Missing required Azure Data Factory credentials: tenant_id, client_id, client_secret, subscription_id, resource_group, factory_name")

        try:
            from azure.identity import ClientSecretCredential
            from azure.mgmt.datafactory import DataFactoryManagementClient

            logger.info(f"Initializing Azure Data Factory client for factory: {self.factory_name}")

            # Create credential using service principal
            credential = ClientSecretCredential(
                tenant_id=self.tenant_id,
                client_id=self.client_id,
                client_secret=self.client_secret
            )

            # Create Data Factory Management Client
            self.adf_client = DataFactoryManagementClient(
                credential=credential,
                subscription_id=self.subscription_id
            )

            logger.info(f"Azure Data Factory provider initialized successfully for factory: {self.factory_name}")

        except Exception as e:
            logger.error(f"Failed to initialize Azure Data Factory client: {e}")
            raise

    def _handle_error(self, operation: str, error: Exception) -> Dict[str, Any]:
        """Handle Azure errors and return standardized error response."""
        error_msg = str(error)
        logger.error(f"Azure Data Factory {operation} failed: {error_msg}")
        return {"error": error_msg}

    # ==================== Pipeline Operations ====================

    async def list_pipelines(self) -> Dict[str, Any]:
        """
        List all pipelines in the Data Factory.

        Returns:
            Dictionary containing list of pipelines and metadata
        """
        self._log_operation("list_pipelines")
        self._ensure_initialized()

        try:
            pipelines = list(self.adf_client.pipelines.list_by_factory(
                resource_group_name=self.resource_group,
                factory_name=self.factory_name
            ))

            pipeline_list = []
            for pipeline in pipelines:
                pipeline_list.append({
                    "name": pipeline.name,
                    "description": pipeline.description,
                    "activity_count": len(pipeline.activities) if pipeline.activities else 0,
                    "parameters": list(pipeline.parameters.keys()) if pipeline.parameters else [],
                    "variables": list(pipeline.variables.keys()) if pipeline.variables else [],
                    "folder": pipeline.folder.name if pipeline.folder else None
                })

            return {
                "pipelines": pipeline_list,
                "count": len(pipeline_list),
                "factory_name": self.factory_name
            }

        except Exception as e:
            return self._handle_error("list_pipelines", e)

    async def get_pipeline(self, pipeline_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific pipeline.

        Args:
            pipeline_name: Name of the pipeline

        Returns:
            Dictionary containing pipeline details
        """
        self._log_operation("get_pipeline", pipeline_name=pipeline_name)
        self._ensure_initialized()

        try:
            pipeline = self.adf_client.pipelines.get(
                resource_group_name=self.resource_group,
                factory_name=self.factory_name,
                pipeline_name=pipeline_name
            )

            activities = []
            if pipeline.activities:
                for activity in pipeline.activities:
                    activities.append({
                        "name": activity.name,
                        "type": activity.type,
                        "description": activity.description,
                        "depends_on": [dep.activity for dep in activity.depends_on] if activity.depends_on else []
                    })

            return {
                "name": pipeline.name,
                "description": pipeline.description,
                "activities": activities,
                "activity_count": len(activities),
                "parameters": {k: {"type": v.type, "default_value": v.default_value}
                              for k, v in pipeline.parameters.items()} if pipeline.parameters else {},
                "variables": {k: {"type": v.type, "default_value": v.default_value}
                             for k, v in pipeline.variables.items()} if pipeline.variables else {},
                "folder": pipeline.folder.name if pipeline.folder else None,
                "annotations": pipeline.annotations
            }

        except Exception as e:
            return self._handle_error("get_pipeline", e)

    async def run_pipeline(self, pipeline_name: str,
                           parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Trigger a pipeline run.

        Args:
            pipeline_name: Name of the pipeline to run
            parameters: Optional parameters to pass to the pipeline

        Returns:
            Dictionary containing the run ID and status
        """
        self._log_operation("run_pipeline", pipeline_name=pipeline_name)
        self._ensure_initialized()

        try:
            run_response = self.adf_client.pipelines.create_run(
                resource_group_name=self.resource_group,
                factory_name=self.factory_name,
                pipeline_name=pipeline_name,
                parameters=parameters
            )

            return {
                "success": True,
                "run_id": run_response.run_id,
                "pipeline_name": pipeline_name,
                "message": f"Pipeline run started with run_id: {run_response.run_id}"
            }

        except Exception as e:
            return self._handle_error("run_pipeline", e)

    async def get_pipeline_run(self, run_id: str) -> Dict[str, Any]:
        """
        Get the status of a pipeline run.

        Args:
            run_id: The run ID to check

        Returns:
            Dictionary containing run status and details
        """
        self._log_operation("get_pipeline_run", run_id=run_id)
        self._ensure_initialized()

        try:
            run = self.adf_client.pipeline_runs.get(
                resource_group_name=self.resource_group,
                factory_name=self.factory_name,
                run_id=run_id
            )

            return {
                "run_id": run.run_id,
                "pipeline_name": run.pipeline_name,
                "status": run.status,
                "run_start": str(run.run_start) if run.run_start else None,
                "run_end": str(run.run_end) if run.run_end else None,
                "duration_in_ms": run.duration_in_ms,
                "message": run.message,
                "parameters": run.parameters,
                "invoked_by": {
                    "name": run.invoked_by.name if run.invoked_by else None,
                    "id": run.invoked_by.id if run.invoked_by else None
                } if run.invoked_by else None
            }

        except Exception as e:
            return self._handle_error("get_pipeline_run", e)

    async def list_pipeline_runs(self, pipeline_name: Optional[str] = None,
                                  days_back: int = 7,
                                  max_results: int = 100) -> Dict[str, Any]:
        """
        List recent pipeline runs.

        Args:
            pipeline_name: Optional filter by pipeline name
            days_back: Number of days to look back (default: 7)
            max_results: Maximum number of runs to return

        Returns:
            Dictionary containing list of pipeline runs
        """
        self._log_operation("list_pipeline_runs", pipeline_name=pipeline_name, days_back=days_back)
        self._ensure_initialized()

        try:
            from azure.mgmt.datafactory.models import RunFilterParameters, RunQueryFilter, RunQueryFilterOperand, RunQueryFilterOperator

            # Set up date filter
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=days_back)

            filter_params = RunFilterParameters(
                last_updated_after=start_time,
                last_updated_before=end_time
            )

            # Add pipeline name filter if specified
            if pipeline_name:
                filter_params.filters = [
                    RunQueryFilter(
                        operand=RunQueryFilterOperand.PIPELINE_NAME,
                        operator=RunQueryFilterOperator.EQUALS,
                        values=[pipeline_name]
                    )
                ]

            runs_response = self.adf_client.pipeline_runs.query_by_factory(
                resource_group_name=self.resource_group,
                factory_name=self.factory_name,
                filter_parameters=filter_params
            )

            runs = []
            for run in runs_response.value[:max_results]:
                runs.append({
                    "run_id": run.run_id,
                    "pipeline_name": run.pipeline_name,
                    "status": run.status,
                    "run_start": str(run.run_start) if run.run_start else None,
                    "run_end": str(run.run_end) if run.run_end else None,
                    "duration_in_ms": run.duration_in_ms,
                    "message": run.message
                })

            return {
                "runs": runs,
                "count": len(runs),
                "days_back": days_back,
                "factory_name": self.factory_name
            }

        except Exception as e:
            return self._handle_error("list_pipeline_runs", e)

    # ==================== Dataset Operations ====================

    async def list_datasets(self) -> Dict[str, Any]:
        """
        List all datasets in the Data Factory.

        Returns:
            Dictionary containing list of datasets
        """
        self._log_operation("list_datasets")
        self._ensure_initialized()

        try:
            datasets = list(self.adf_client.datasets.list_by_factory(
                resource_group_name=self.resource_group,
                factory_name=self.factory_name
            ))

            dataset_list = []
            for dataset in datasets:
                dataset_list.append({
                    "name": dataset.name,
                    "type": dataset.properties.type if dataset.properties else None,
                    "description": dataset.properties.description if dataset.properties else None,
                    "linked_service_name": dataset.properties.linked_service_name.reference_name if dataset.properties and dataset.properties.linked_service_name else None,
                    "folder": dataset.properties.folder.name if dataset.properties and dataset.properties.folder else None
                })

            return {
                "datasets": dataset_list,
                "count": len(dataset_list),
                "factory_name": self.factory_name
            }

        except Exception as e:
            return self._handle_error("list_datasets", e)

    async def get_dataset(self, dataset_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific dataset.

        Args:
            dataset_name: Name of the dataset

        Returns:
            Dictionary containing dataset details
        """
        self._log_operation("get_dataset", dataset_name=dataset_name)
        self._ensure_initialized()

        try:
            dataset = self.adf_client.datasets.get(
                resource_group_name=self.resource_group,
                factory_name=self.factory_name,
                dataset_name=dataset_name
            )

            props = dataset.properties

            return {
                "name": dataset.name,
                "type": props.type if props else None,
                "description": props.description if props else None,
                "linked_service_name": props.linked_service_name.reference_name if props and props.linked_service_name else None,
                "parameters": {k: {"type": v.type, "default_value": v.default_value}
                              for k, v in props.parameters.items()} if props and props.parameters else {},
                "schema": props.schema if props else None,
                "folder": props.folder.name if props and props.folder else None,
                "annotations": props.annotations if props else None
            }

        except Exception as e:
            return self._handle_error("get_dataset", e)

    # ==================== Trigger Operations ====================

    async def list_triggers(self) -> Dict[str, Any]:
        """
        List all triggers in the Data Factory.

        Returns:
            Dictionary containing list of triggers
        """
        self._log_operation("list_triggers")
        self._ensure_initialized()

        try:
            triggers = list(self.adf_client.triggers.list_by_factory(
                resource_group_name=self.resource_group,
                factory_name=self.factory_name
            ))

            trigger_list = []
            for trigger in triggers:
                trigger_list.append({
                    "name": trigger.name,
                    "type": trigger.properties.type if trigger.properties else None,
                    "description": trigger.properties.description if trigger.properties else None,
                    "runtime_state": trigger.properties.runtime_state if trigger.properties else None
                })

            return {
                "triggers": trigger_list,
                "count": len(trigger_list),
                "factory_name": self.factory_name
            }

        except Exception as e:
            return self._handle_error("list_triggers", e)

    async def get_trigger(self, trigger_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific trigger.

        Args:
            trigger_name: Name of the trigger

        Returns:
            Dictionary containing trigger details
        """
        self._log_operation("get_trigger", trigger_name=trigger_name)
        self._ensure_initialized()

        try:
            trigger = self.adf_client.triggers.get(
                resource_group_name=self.resource_group,
                factory_name=self.factory_name,
                trigger_name=trigger_name
            )

            props = trigger.properties

            result = {
                "name": trigger.name,
                "type": props.type if props else None,
                "description": props.description if props else None,
                "runtime_state": props.runtime_state if props else None,
                "annotations": props.annotations if props else None
            }

            # Add schedule info for schedule triggers
            if hasattr(props, 'recurrence') and props.recurrence:
                result["recurrence"] = {
                    "frequency": props.recurrence.frequency,
                    "interval": props.recurrence.interval,
                    "start_time": str(props.recurrence.start_time) if props.recurrence.start_time else None,
                    "end_time": str(props.recurrence.end_time) if props.recurrence.end_time else None,
                    "time_zone": props.recurrence.time_zone
                }

            # Add pipelines for multi-pipeline triggers
            if hasattr(props, 'pipelines') and props.pipelines:
                result["pipelines"] = [
                    {
                        "pipeline_name": p.pipeline_reference.reference_name if p.pipeline_reference else None,
                        "parameters": p.parameters
                    }
                    for p in props.pipelines
                ]

            return result

        except Exception as e:
            return self._handle_error("get_trigger", e)

    # ==================== Linked Service Operations ====================

    async def list_linked_services(self) -> Dict[str, Any]:
        """
        List all linked services in the Data Factory.

        Returns:
            Dictionary containing list of linked services
        """
        self._log_operation("list_linked_services")
        self._ensure_initialized()

        try:
            linked_services = list(self.adf_client.linked_services.list_by_factory(
                resource_group_name=self.resource_group,
                factory_name=self.factory_name
            ))

            ls_list = []
            for ls in linked_services:
                ls_list.append({
                    "name": ls.name,
                    "type": ls.properties.type if ls.properties else None,
                    "description": ls.properties.description if ls.properties else None,
                    "connect_via": ls.properties.connect_via.reference_name if ls.properties and ls.properties.connect_via else None
                })

            return {
                "linked_services": ls_list,
                "count": len(ls_list),
                "factory_name": self.factory_name
            }

        except Exception as e:
            return self._handle_error("list_linked_services", e)

    async def get_linked_service(self, service_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific linked service.

        Args:
            service_name: Name of the linked service

        Returns:
            Dictionary containing linked service details
        """
        self._log_operation("get_linked_service", service_name=service_name)
        self._ensure_initialized()

        try:
            linked_service = self.adf_client.linked_services.get(
                resource_group_name=self.resource_group,
                factory_name=self.factory_name,
                linked_service_name=service_name
            )

            props = linked_service.properties

            return {
                "name": linked_service.name,
                "type": props.type if props else None,
                "description": props.description if props else None,
                "connect_via": props.connect_via.reference_name if props and props.connect_via else None,
                "annotations": props.annotations if props else None,
                "parameters": {k: {"type": v.type, "default_value": v.default_value}
                              for k, v in props.parameters.items()} if props and props.parameters else {}
            }

        except Exception as e:
            return self._handle_error("get_linked_service", e)

    # ==================== Data Flow Operations ====================

    async def list_data_flows(self) -> Dict[str, Any]:
        """
        List all data flows in the Data Factory.

        Returns:
            Dictionary containing list of data flows
        """
        self._log_operation("list_data_flows")
        self._ensure_initialized()

        try:
            data_flows = list(self.adf_client.data_flows.list_by_factory(
                resource_group_name=self.resource_group,
                factory_name=self.factory_name
            ))

            df_list = []
            for df in data_flows:
                df_list.append({
                    "name": df.name,
                    "type": df.properties.type if df.properties else None,
                    "description": df.properties.description if df.properties else None,
                    "folder": df.properties.folder.name if df.properties and df.properties.folder else None
                })

            return {
                "data_flows": df_list,
                "count": len(df_list),
                "factory_name": self.factory_name
            }

        except Exception as e:
            return self._handle_error("list_data_flows", e)

    async def get_data_flow(self, data_flow_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific data flow.

        Args:
            data_flow_name: Name of the data flow

        Returns:
            Dictionary containing data flow details
        """
        self._log_operation("get_data_flow", data_flow_name=data_flow_name)
        self._ensure_initialized()

        try:
            data_flow = self.adf_client.data_flows.get(
                resource_group_name=self.resource_group,
                factory_name=self.factory_name,
                data_flow_name=data_flow_name
            )

            props = data_flow.properties

            result = {
                "name": data_flow.name,
                "type": props.type if props else None,
                "description": props.description if props else None,
                "folder": props.folder.name if props and props.folder else None,
                "annotations": props.annotations if props else None
            }

            # Add sources and sinks if available (for MappingDataFlow)
            if hasattr(props, 'type_properties') and props.type_properties:
                if hasattr(props.type_properties, 'sources'):
                    result["sources"] = [
                        {"name": s.name, "dataset": s.dataset.reference_name if s.dataset else None}
                        for s in props.type_properties.sources
                    ] if props.type_properties.sources else []

                if hasattr(props.type_properties, 'sinks'):
                    result["sinks"] = [
                        {"name": s.name, "dataset": s.dataset.reference_name if s.dataset else None}
                        for s in props.type_properties.sinks
                    ] if props.type_properties.sinks else []

                if hasattr(props.type_properties, 'transformations'):
                    result["transformations"] = [
                        {"name": t.name, "description": t.description}
                        for t in props.type_properties.transformations
                    ] if props.type_properties.transformations else []

            return result

        except Exception as e:
            return self._handle_error("get_data_flow", e)

    # ==================== Integration Runtime Operations ====================

    async def list_integration_runtimes(self) -> Dict[str, Any]:
        """
        List all integration runtimes in the Data Factory.

        Returns:
            Dictionary containing list of integration runtimes
        """
        self._log_operation("list_integration_runtimes")
        self._ensure_initialized()

        try:
            runtimes = list(self.adf_client.integration_runtimes.list_by_factory(
                resource_group_name=self.resource_group,
                factory_name=self.factory_name
            ))

            ir_list = []
            for ir in runtimes:
                ir_list.append({
                    "name": ir.name,
                    "type": ir.properties.type if ir.properties else None,
                    "description": ir.properties.description if ir.properties else None
                })

            return {
                "integration_runtimes": ir_list,
                "count": len(ir_list),
                "factory_name": self.factory_name
            }

        except Exception as e:
            return self._handle_error("list_integration_runtimes", e)

    async def get_integration_runtime(self, runtime_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific integration runtime.

        Args:
            runtime_name: Name of the integration runtime

        Returns:
            Dictionary containing integration runtime details
        """
        self._log_operation("get_integration_runtime", runtime_name=runtime_name)
        self._ensure_initialized()

        try:
            runtime = self.adf_client.integration_runtimes.get(
                resource_group_name=self.resource_group,
                factory_name=self.factory_name,
                integration_runtime_name=runtime_name
            )

            # Get status as well
            status = self.adf_client.integration_runtimes.get_status(
                resource_group_name=self.resource_group,
                factory_name=self.factory_name,
                integration_runtime_name=runtime_name
            )

            props = runtime.properties

            result = {
                "name": runtime.name,
                "type": props.type if props else None,
                "description": props.description if props else None,
                "state": status.properties.state if status.properties else None
            }

            # Add type-specific properties
            if hasattr(status.properties, 'nodes') and status.properties.nodes:
                result["nodes"] = [
                    {
                        "node_name": node.node_name,
                        "status": node.status,
                        "version": node.version
                    }
                    for node in status.properties.nodes
                ]

            return result

        except Exception as e:
            return self._handle_error("get_integration_runtime", e)

    # ==================== Factory Operations ====================

    async def get_factory_info(self) -> Dict[str, Any]:
        """
        Get information about the Data Factory itself.

        Returns:
            Dictionary containing factory details
        """
        self._log_operation("get_factory_info")
        self._ensure_initialized()

        try:
            factory = self.adf_client.factories.get(
                resource_group_name=self.resource_group,
                factory_name=self.factory_name
            )

            return {
                "name": factory.name,
                "location": factory.location,
                "provisioning_state": factory.provisioning_state,
                "create_time": str(factory.create_time) if factory.create_time else None,
                "version": factory.version,
                "repo_configuration": {
                    "type": factory.repo_configuration.type if factory.repo_configuration else None
                } if factory.repo_configuration else None,
                "global_parameters": list(factory.global_parameters.keys()) if factory.global_parameters else [],
                "tags": factory.tags
            }

        except Exception as e:
            return self._handle_error("get_factory_info", e)

    async def cleanup(self) -> None:
        """Clean up Azure Data Factory provider resources."""
        if self.adf_client:
            self.adf_client = None

        await super().cleanup()
