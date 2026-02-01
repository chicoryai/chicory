import { json } from "@remix-run/node";
import { SimpleActionHandler } from "./base";
import type {
  ActionContext,
  DataSourceActionResponse
} from "~/types/action-handlers";
import { ValidationError } from "~/types/action-handlers";
import {
  createProjectDataSource,
  updateProjectDataSource,
  deleteProjectDataSource,
  getProjectDataSources,
  getDataSourceTypes
} from "~/services/chicory.server";
import {
  extractRequiredString,
  extractOptionalString,
  createSuccessResponse,
  createErrorResponse
} from "~/utils/action-utils";
import {
  MASKED_PASSWORD_PLACEHOLDER,
  isSensitiveField,
  isMaskedValue
} from "~/utils/dataSourceFieldUtils";

// ========================================
// DATA SOURCE CRUD HANDLER
// ========================================

export class DataSourceHandler extends SimpleActionHandler {
  protected async processAction(context: ActionContext): Promise<Response> {
    const actionType = extractRequiredString(context.formData, '_action');
    
    switch (actionType) {
      case 'createDataSource':
        return this.handleCreateDataSource(context);
      case 'editDataSource':
        return this.handleEditDataSource(context);
      case 'deleteDataSource':
        return this.handleDeleteDataSource(context);
      default:
        throw new ValidationError(`Unknown data source action: ${actionType}`);
    }
  }

  private async handleCreateDataSource(context: ActionContext): Promise<Response> {
    try {
      const dataSourceTypeId = extractRequiredString(context.formData, 'dataSourceTypeId');
      const name = extractRequiredString(context.formData, 'name');
      
      this.log(`Creating data source: ${name} (type: ${dataSourceTypeId})`);

      // Get data source type definition to build configuration
      const dataSourceTypes = await getDataSourceTypes();
      const dataSourceType = dataSourceTypes.find(ds => ds.id === dataSourceTypeId);
      
      if (!dataSourceType) {
        return createErrorResponse(`Invalid data source type: ${dataSourceTypeId}`, 'createDataSource');
      }

      // Build configuration from form data
      const configuration = this.buildConfigurationFromFormData(context.formData, dataSourceType.required_fields);

      this.log('Creating data source with configuration:', configuration);

      // Create the data source
      const dataSource = await createProjectDataSource(
        context.projectId,
        dataSourceTypeId,
        name,
        configuration
      );

      // Fetch updated data sources
      const updatedDataSources = await getProjectDataSources(context.projectId);

      const response: DataSourceActionResponse = {
        success: true,
        message: "Data source created successfully",
        dataSource,
        projectDataSources: updatedDataSources,
        _action: "createDataSource"
      };

      return json(response);

    } catch (error) {
      this.logError("Error creating data source:", error);
      return createErrorResponse(
        error instanceof Error ? error.message : "Failed to create data source",
        'createDataSource',
        500
      );
    }
  }

  private async handleEditDataSource(context: ActionContext): Promise<Response> {
    try {
      const dataSourceId = extractRequiredString(context.formData, 'dataSourceId');
      const dataSourceTypeId = extractRequiredString(context.formData, 'dataSourceTypeId');
      const name = extractRequiredString(context.formData, 'name');

      this.log(`Updating data source: ${dataSourceId}`);

      // Get data source type definition
      const dataSourceTypes = await getDataSourceTypes();
      const dataSourceType = dataSourceTypes.find(ds => ds.id === dataSourceTypeId);

      if (!dataSourceType) {
        return createErrorResponse(`Invalid data source type: ${dataSourceTypeId}`, 'updateDataSource');
      }

      // Get existing data source to preserve masked password fields
      const existingDataSources = await getProjectDataSources(context.projectId);
      const existingDataSource = existingDataSources.find(ds => ds.id === dataSourceId);

      if (!existingDataSource) {
        return createErrorResponse(`Data source not found: ${dataSourceId}`, 'updateDataSource');
      }

      // Build configuration from form data
      const configuration = this.buildConfigurationFromFormData(
        context.formData,
        dataSourceType.required_fields,
        existingDataSource.configuration
      );

      this.log('Updating data source with configuration:', configuration);

      // Update the data source
      await updateProjectDataSource(
        context.projectId,
        dataSourceId,
        name,
        configuration
      );

      // Fetch updated data sources
      const updatedDataSources = await getProjectDataSources(context.projectId);

      const response: DataSourceActionResponse = {
        success: true,
        message: "Data source updated successfully",
        projectDataSources: updatedDataSources,
        _action: "editDataSource"
      };

      return json(response);

    } catch (error) {
      this.logError("Error updating data source:", error);
              return createErrorResponse(
          error instanceof Error ? error.message : "Failed to update data source",
          'editDataSource',
          500
        );
    }
  }

  private async handleDeleteDataSource(context: ActionContext): Promise<Response> {
    try {
      const dataSourceId = extractRequiredString(context.formData, 'dataSourceId');
      const projectId = extractRequiredString(context.formData, 'projectId');
      const deleteS3Object = context.formData.get('deleteS3Object') === 'true';
      
      this.log(`Deleting data source: ${dataSourceId} (deleteS3Object: ${deleteS3Object})`);

      // Delete the data source
      await deleteProjectDataSource(projectId, dataSourceId, deleteS3Object);

      // Fetch updated data sources
      const updatedDataSources = await getProjectDataSources(projectId);

      const response: DataSourceActionResponse = {
        success: true,
        message: "Data source deleted successfully",
        projectDataSources: updatedDataSources,
        _action: 'deleteDataSource'
      };

      return json(response);

    } catch (error) {
      this.logError("Error deleting data source:", error);
      return createErrorResponse(
        error instanceof Error ? error.message : "Failed to delete data source",
        'deleteDataSource',
        500
      );
    }
  }

  private buildConfigurationFromFormData(
    formData: FormData,
    requiredFields: Array<{ name: string; optional?: boolean; type?: string }>,
    existingConfiguration?: Record<string, any>
  ): Record<string, any> {
    const configuration: Record<string, any> = {};

    for (const field of requiredFields) {
      const value = formData.get(field.name);
      const isOptional = field.optional ?? false;

      // Check if this is a sensitive field using shared utility
      const isFieldSensitive = isSensitiveField(field);

      // Check if the value is the masked placeholder using shared utility
      const isValueMasked = isMaskedValue(value);

      // If this is a masked sensitive field and we have an existing value, preserve it
      if (isFieldSensitive && isValueMasked && existingConfiguration && existingConfiguration[field.name]) {
        this.log(`Preserving existing value for masked field: ${field.name}`);
        configuration[field.name] = existingConfiguration[field.name];
        continue;
      }

      if (!isOptional && (!value || (typeof value === 'string' && value.trim() === ''))) {
        // If we're editing and have an existing value for this field, use it
        if (existingConfiguration && existingConfiguration[field.name]) {
          this.log(`Using existing value for required field with no new value: ${field.name}`);
          configuration[field.name] = existingConfiguration[field.name];
          continue;
        }
        throw new ValidationError(`Missing required field: ${field.name}`);
      }

      if (value) {
        configuration[field.name] = typeof value === 'string' ? value.trim() : value;
      }
    }

    return configuration;
  }
} 