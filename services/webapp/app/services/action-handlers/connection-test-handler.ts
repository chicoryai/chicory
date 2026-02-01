import { json } from "@remix-run/node";
import { SimpleActionHandler } from "./base";
import type { 
  ActionContext, 
  ConnectionTestResponse 
} from "~/types/action-handlers";
import { ValidationError } from "~/types/action-handlers";
import { 
  testNewDataSourceConnection,
  getDataSourceTypes,
  validateDataSourceCredentials
} from "~/services/chicory.server";
import { 
  extractRequiredString,
  extractOptionalString,
  createErrorResponse
} from "~/utils/action-utils";

// ========================================
// CONNECTION TEST HANDLER
// ========================================

export class ConnectionTestHandler extends SimpleActionHandler {
  protected async processAction(context: ActionContext): Promise<Response> {
    const actionType = extractRequiredString(context.formData, '_action');
    
    switch (actionType) {
      case 'testConnection':
        return this.handleTestConnection(context);
      case 'validateCredentials':
        return this.handleValidateCredentials(context);
      default:
        throw new ValidationError(`Unknown connection test action: ${actionType}`);
    }
  }

  private async handleTestConnection(context: ActionContext): Promise<Response> {
    try {
      // Debug: Log all form data entries
      console.log("[ConnectionTestHandler] All form data entries:");
      for (const [key, value] of context.formData.entries()) {
        console.log(`  ${key}: ${value}`);
      }
      
      // Check if this is testing an existing data source or a new connection
      const dataSourceId = extractOptionalString(context.formData, 'dataSourceId');
      const dataSourceTypeId = extractOptionalString(context.formData, 'dataSourceTypeId');
      
      if (dataSourceId) {
        // Test existing data source
        this.log(`Testing existing data source: ${dataSourceId}`);
        return this.handleTestExistingDataSource(context, dataSourceId);
      } else if (dataSourceTypeId) {
        // Test new connection with configuration
        this.log(`Testing new connection for data source type: ${dataSourceTypeId}`);
        return this.handleTestNewConnection(context, dataSourceTypeId);
      } else {
        throw new ValidationError("Either dataSourceId or dataSourceTypeId is required");
      }

    } catch (error) {
      this.logError("Error testing connection:", error);
      return createErrorResponse(
        error instanceof Error ? error.message : "Connection test failed",
        'testConnection',
        500
      );
    }
  }

  private async handleTestExistingDataSource(context: ActionContext, dataSourceId: string): Promise<Response> {
    try {
      // Import the existing data source test function
      const { testDataSourceConnection } = await import("~/services/chicory.server");
      
      // Test the existing data source
      const result = await testDataSourceConnection(context.projectId, dataSourceId);

      const response: ConnectionTestResponse = {
        success: result.success,
        message: result.message,
        connectionValid: result.success,
        dataSourceId: dataSourceId, // Include dataSourceId for component-level handling
        _action: 'testConnection'
      };
      
      return json(response);

    } catch (error) {
      this.logError("Error testing existing data source:", error);
      return createErrorResponse(
        error instanceof Error ? error.message : "Connection test failed",
        'testConnection',
        500
      );
    }
  }

  private async handleTestNewConnection(context: ActionContext, dataSourceTypeId: string): Promise<Response> {
    try {
      // Get data source type definition
      const dataSourceTypes = await getDataSourceTypes();
      const dataSourceType = dataSourceTypes.find(ds => ds.id === dataSourceTypeId);
      
      if (!dataSourceType) {
        return createErrorResponse(`Invalid data source type: ${dataSourceTypeId}`, 'testConnection');
      }

      // Build configuration from form data
      const configuration = this.buildConfigurationFromFormData(context.formData, dataSourceType.required_fields);

      // Test the new connection
      const result = await testNewDataSourceConnection(
        context.projectId,
        dataSourceTypeId,
        configuration
      );

      const response: ConnectionTestResponse = {
        success: result.success,
        message: result.message,
        connectionValid: result.success,
        _action: 'testConnection'
      };

      return json(response);

    } catch (error) {
      this.logError("Error testing new connection:", error);
      return createErrorResponse(
        error instanceof Error ? error.message : "Connection test failed",
        'testConnection',
        500
      );
    }
  }

  private async handleValidateCredentials(context: ActionContext): Promise<Response> {
    try {
      const dataSourceTypeId = extractRequiredString(context.formData, 'dataSourceTypeId');
      
      this.log(`Validating credentials for data source type: ${dataSourceTypeId}`);

      // Get data source type definition
      const dataSourceTypes = await getDataSourceTypes();
      const dataSourceType = dataSourceTypes.find(ds => ds.id === dataSourceTypeId);
      
      if (!dataSourceType) {
        return createErrorResponse(`Invalid data source type: ${dataSourceTypeId}`, 'validateCredentials');
      }

      // Build configuration from form data
      const configuration = this.buildConfigurationFromFormData(context.formData, dataSourceType.required_fields);

      // Validate credentials
      const result = await validateDataSourceCredentials(dataSourceTypeId, configuration);
      
      console.log(`[ConnectionTestHandler] validateDataSourceCredentials result:`, result);

      const response: ConnectionTestResponse = {
        success: result.success,
        message: result.message,
        connectionValid: result.success,
        _action: 'validateCredentials'
      };
      
      console.log(`[ConnectionTestHandler] Returning response to UI:`, response);

      return json(response);

    } catch (error) {
      this.logError("Error validating credentials:", error);
      return createErrorResponse(
        error instanceof Error ? error.message : "Credential validation failed",
        'validateCredentials',
        500
      );
    }
  }

  private buildConfigurationFromFormData(
    formData: FormData, 
    requiredFields: Array<{ name: string; optional?: boolean }>
  ): Record<string, any> {
    const configuration: Record<string, any> = {};
    
    for (const field of requiredFields) {
      const value = formData.get(field.name);
      const isOptional = field.optional ?? false;
      
      if (!isOptional && (!value || (typeof value === 'string' && value.trim() === ''))) {
        throw new ValidationError(`Missing required field: ${field.name}`);
      }
      
      if (value) {
        configuration[field.name] = typeof value === 'string' ? value.trim() : value;
      }
    }
    
    return configuration;
  }
} 