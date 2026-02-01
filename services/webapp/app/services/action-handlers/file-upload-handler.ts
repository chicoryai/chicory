import { json } from "@remix-run/node";
import { MultiFileUploadHandler } from "./base";
import type { 
  ActionContext, 
  FileUploadResult, 
  BatchUploadResponse,
  FileValidationConfig
} from "~/types/action-handlers";
import { 
  uploadCsvDataSource, 
  uploadExcelDataSource, 
  uploadGenericFileDataSource,
  getProjectDataSources
} from "~/services/chicory.server";
import { extractOptionalString, getFileValidationConfig } from "~/utils/action-utils";

// ========================================
// CSV UPLOAD HANDLER
// ========================================

export class CsvUploadHandler extends MultiFileUploadHandler {
  protected getActionType(): string {
    return 'csv_upload';
  }

  protected async processFile(
    file: File,
    fileName: string,
    description: string | undefined,
    context: ActionContext
  ) {
    const startTime = Date.now();
    const fileSizeKB = Math.round(file.size / 1024);

    this.log(`Starting CSV upload: ${fileName} (${fileSizeKB}KB)`);
    this.log(`Project ID: ${context.projectId}, Description: ${description || 'none'}`);

    try {
      const result = await uploadCsvDataSource(context.projectId, fileName, file, description);
      const duration = Date.now() - startTime;

      this.log(`CSV upload successful: ${fileName} in ${duration}ms`);
      this.log(`Created data source ID: ${result.id}`);

      return result;
    } catch (error) {
      const duration = Date.now() - startTime;
      this.logError(`CSV upload failed: ${fileName} after ${duration}ms`, error);
      throw error;
    }
  }

  protected async createBatchResponse(results: FileUploadResult[], actionType: string): Promise<Response> {
    // Get updated data sources after uploads
    const firstSuccessResult = results.find(r => r.status === 'success');
    let updatedDataSources;
    
    if (firstSuccessResult?.dataSource) {
      updatedDataSources = await getProjectDataSources(firstSuccessResult.dataSource.project_id);
    }

    const response: BatchUploadResponse = {
      success: results.every(r => r.status === 'success'),
      results,
      projectDataSources: updatedDataSources,
      _action: 'uploadCsv',
      message: this.generateBatchMessage(results)
    };

    return json(response);
  }

  private generateBatchMessage(results: FileUploadResult[]): string {
    const successCount = results.filter(r => r.status === 'success').length;
    const errorCount = results.filter(r => r.status === 'error').length;
    
    if (errorCount === 0) {
      return `Successfully uploaded ${successCount} CSV file${successCount !== 1 ? 's' : ''}`;
    } else if (successCount === 0) {
      return `Failed to upload ${errorCount} CSV file${errorCount !== 1 ? 's' : ''}`;
    } else {
      return `Uploaded ${successCount} CSV file${successCount !== 1 ? 's' : ''}, ${errorCount} failed`;
    }
  }
}

// ========================================
// EXCEL UPLOAD HANDLER
// ========================================

export class ExcelUploadHandler extends MultiFileUploadHandler {
  protected getActionType(): string {
    return 'xlsx_upload';
  }

  protected async processFile(
    file: File,
    fileName: string,
    description: string | undefined,
    context: ActionContext
  ) {
    const startTime = Date.now();
    const fileSizeKB = Math.round(file.size / 1024);

    this.log(`Starting Excel upload: ${fileName} (${fileSizeKB}KB)`);
    this.log(`Project ID: ${context.projectId}, Description: ${description || 'none'}`);

    try {
      const result = await uploadExcelDataSource(context.projectId, fileName, file, description);
      const duration = Date.now() - startTime;

      this.log(`Excel upload successful: ${fileName} in ${duration}ms`);
      this.log(`Created data source ID: ${result.id}`);

      return result;
    } catch (error) {
      const duration = Date.now() - startTime;
      this.logError(`Excel upload failed: ${fileName} after ${duration}ms`, error);
      throw error;
    }
  }

  protected async createBatchResponse(results: FileUploadResult[], actionType: string): Promise<Response> {
    // Get updated data sources after uploads
    const firstSuccessResult = results.find(r => r.status === 'success');
    let updatedDataSources;
    
    if (firstSuccessResult?.dataSource) {
      updatedDataSources = await getProjectDataSources(firstSuccessResult.dataSource.project_id);
    }

    const response: BatchUploadResponse = {
      success: results.every(r => r.status === 'success'),
      results,
      projectDataSources: updatedDataSources,
      _action: 'uploadExcel',
      message: this.generateBatchMessage(results)
    };

    return json(response);
  }

  private generateBatchMessage(results: FileUploadResult[]): string {
    const successCount = results.filter(r => r.status === 'success').length;
    const errorCount = results.filter(r => r.status === 'error').length;
    
    if (errorCount === 0) {
      return `Successfully uploaded ${successCount} Excel file${successCount !== 1 ? 's' : ''}`;
    } else if (successCount === 0) {
      return `Failed to upload ${errorCount} Excel file${errorCount !== 1 ? 's' : ''}`;
    } else {
      return `Uploaded ${successCount} Excel file${successCount !== 1 ? 's' : ''}, ${errorCount} failed`;
    }
  }
}

// ========================================
// GENERIC FILE UPLOAD HANDLER
// ========================================

export class GenericFileUploadHandler extends MultiFileUploadHandler {
  protected getActionType(): string {
    return 'generic_file_upload';
  }

  protected getValidationConfig(context: ActionContext): FileValidationConfig {
    // Get category from form data to determine file type restrictions
    const category = extractOptionalString(context.formData, 'category') || 'document';
    return getFileValidationConfig(this.getActionType(), category);
  }

  protected async processFile(
    file: File,
    fileName: string,
    description: string | undefined,
    context: ActionContext
  ) {
    const startTime = Date.now();
    const fileSizeKB = Math.round(file.size / 1024);

    // Get category from form data
    const category = extractOptionalString(context.formData, 'category') || 'document';

    this.log(`Starting generic file upload: ${fileName} (${fileSizeKB}KB)`);
    this.log(`Project ID: ${context.projectId}, Category: ${category}, Description: ${description || 'none'}`);

    if (!['document', 'code'].includes(category)) {
      this.logError(`Invalid category specified: ${category}`);
      throw new Error(`Invalid category: ${category}. Must be 'document' or 'code'.`);
    }

    try {
      const result = await uploadGenericFileDataSource(
        context.projectId,
        fileName,
        file,
        category as 'document' | 'code',
        description
      );
      const duration = Date.now() - startTime;

      this.log(`Generic file upload successful: ${fileName} in ${duration}ms`);
      this.log(`Created data source ID: ${result.id}`);

      return result;
    } catch (error) {
      const duration = Date.now() - startTime;
      this.logError(`Generic file upload failed: ${fileName} after ${duration}ms`, error);
      throw error;
    }
  }

  protected async createBatchResponse(results: FileUploadResult[], actionType: string): Promise<Response> {
    // Get updated data sources after uploads
    const firstSuccessResult = results.find(r => r.status === 'success');
    let updatedDataSources;
    
    if (firstSuccessResult?.dataSource) {
      updatedDataSources = await getProjectDataSources(firstSuccessResult.dataSource.project_id);
    }

    const response: BatchUploadResponse = {
      success: results.every(r => r.status === 'success'),
      results,
      projectDataSources: updatedDataSources,
      _action: 'uploadGenericFile',
      message: this.generateBatchMessage(results)
    };

    return json(response);
  }

  private generateBatchMessage(results: FileUploadResult[]): string {
    const successCount = results.filter(r => r.status === 'success').length;
    const errorCount = results.filter(r => r.status === 'error').length;
    
    if (errorCount === 0) {
      return `Successfully uploaded ${successCount} file${successCount !== 1 ? 's' : ''}`;
    } else if (successCount === 0) {
      return `Failed to upload ${errorCount} file${errorCount !== 1 ? 's' : ''}`;
    } else {
      return `Uploaded ${successCount} file${successCount !== 1 ? 's' : ''}, ${errorCount} failed`;
    }
  }
}

// ========================================
// HANDLER FACTORY
// ========================================

export function createFileUploadHandler(actionType: string): MultiFileUploadHandler {
  switch (actionType) {
    case 'uploadCsv':
      return new CsvUploadHandler();
    case 'uploadExcel':
      return new ExcelUploadHandler();
    case 'uploadGenericFile':
      return new GenericFileUploadHandler();
    default:
      throw new Error(`Unknown file upload action: ${actionType}`);
  }
} 