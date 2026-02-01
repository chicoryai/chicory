import { unstable_parseMultipartFormData } from "@remix-run/node";
import type { UploadHandler } from "@remix-run/node";
import type { 
  ActionHandler, 
  ActionContext,
  HandlerConfig,
  FileUploadResult,
  FileValidationConfig
} from "~/types/action-handlers";
import { ValidationError, DEFAULT_HANDLER_CONFIG } from "~/types/action-handlers";
import { 
  extractFilesFromFormData, 
  validateBatchConstraints,
  createBatches,
  delay,
  generateUniqueFileName,
  getFileValidationConfig,
  formatBytes
} from "~/utils/action-utils";

// ========================================
// BASE ACTION HANDLER
// ========================================

export abstract class BaseActionHandler implements ActionHandler {
  protected config: HandlerConfig;

  constructor(config: Partial<HandlerConfig> = {}) {
    this.config = this.mergeConfig(DEFAULT_HANDLER_CONFIG, config);
  }

  abstract handle(request: Request, context: ActionContext): Promise<Response>;

  protected mergeConfig(defaultConfig: HandlerConfig, customConfig: Partial<HandlerConfig>): HandlerConfig {
    return {
      fileValidation: { 
        ...defaultConfig.fileValidation!, 
        ...(customConfig.fileValidation || {}) 
      },
      concurrency: { 
        ...defaultConfig.concurrency!, 
        ...(customConfig.concurrency || {}) 
      },
      security: { 
        ...defaultConfig.security!, 
        ...(customConfig.security || {}) 
      }
    };
  }

  protected log(message: string, data?: any): void {
    console.log(`[${this.constructor.name}] ${message}`, data || '');
  }

  protected logError(message: string, error?: any): void {
    console.error(`[${this.constructor.name}] ${message}`, error || '');
  }
}

// ========================================
// MULTI-FILE UPLOAD HANDLER BASE
// ========================================

export abstract class MultiFileUploadHandler extends BaseActionHandler {
  protected abstract processFile(
    file: File, 
    fileName: string, 
    description: string | undefined,
    context: ActionContext
  ): Promise<any>;

  protected abstract getActionType(): string;

  // Override this method to provide custom validation config
  protected getValidationConfig(context: ActionContext): FileValidationConfig {
    return getFileValidationConfig(this.getActionType());
  }

  async handle(request: Request, context: ActionContext): Promise<Response> {
    try {
      // Parse multipart form data
      const formData = await this.parseMultipartFormData(request);
      
      return await this.handleWithFormData(formData, context);
    } catch (error) {
      this.logError("Handler error:", error);
      throw error;
    }
  }

  async handleWithParsedData(formData: FormData, context: ActionContext): Promise<Response> {
    try {
      return await this.handleWithFormData(formData, context);
    } catch (error) {
      this.logError("Handler error:", error);
      throw error;
    }
  }

  private async handleWithFormData(formData: FormData, context: ActionContext): Promise<Response> {
    const startTime = Date.now();

    // Extract files from form data
    const files = extractFilesFromFormData(formData);

    this.log(`Processing ${files.length} files for action: ${this.getActionType()}`);

    // Log file metadata
    files.forEach((file, index) => {
      const fileSizeKB = Math.round(file.size / 1024);
      this.log(`File ${index + 1}/${files.length}: ${file.name} (${fileSizeKB}KB, ${file.type || 'unknown type'})`);
    });

    // Get validation config for this action type
    const validationConfig = this.getValidationConfig(context);
    this.log(`Validation config: maxFiles=${validationConfig.maxFiles}, maxFileSize=${Math.round(validationConfig.maxFileSize / 1024 / 1024)}MB, maxTotalSize=${Math.round(validationConfig.maxTotalSize / 1024 / 1024)}MB`);

    // Validate batch constraints
    const validation = validateBatchConstraints(files, validationConfig);
    if (!validation.valid) {
      this.logError(`Batch validation failed: ${validation.error}`);
      throw new ValidationError(validation.error!);
    }

    this.log("Batch validation passed");

    // Process files
    const results = await this.processFilesIteratively(files, formData, context);

    const duration = Date.now() - startTime;
    const successCount = results.filter(r => r.status === 'success').length;
    const errorCount = results.filter(r => r.status === 'error').length;
    this.log(`Batch processing complete in ${duration}ms. Success: ${successCount}, Errors: ${errorCount}`);

    return this.createBatchResponse(results, this.getActionType());
  }

  protected async parseMultipartFormData(request: Request): Promise<FormData> {
    // Check content length to prevent huge uploads
    const contentLength = request.headers.get('content-length');
    if (contentLength && parseInt(contentLength) > this.config.fileValidation!.maxTotalSize) {
      throw new ValidationError(`Request too large: ${formatBytes(parseInt(contentLength))}`);
    }

    const uploadHandler: UploadHandler = async ({ name, filename, data, contentType }) => {
      // Handle non-file fields
      if (!filename) {
        const chunks = [];
        let totalSize = 0;
        const maxFieldSize = 10000; // 10KB max for form fields
        
        for await (const chunk of data) {
          totalSize += chunk.length;
          if (totalSize > maxFieldSize) {
            throw new ValidationError(`Form field '${name}' too large`);
          }
          chunks.push(chunk);
        }
        
        return Buffer.concat(chunks).toString();
      }

      // Handle file fields - only process 'file' field
      if (name !== "file") {
        return undefined;
      }

      this.log(`Processing file upload: ${filename} (${contentType})`);

      // Collect file chunks
      const chunks = [];
      let totalSize = 0;
      const maxFileSize = this.config.fileValidation!.maxFileSize;

      for await (const chunk of data) {
        totalSize += chunk.length;
        if (totalSize > maxFileSize) {
          throw new ValidationError(`File '${filename}' too large: ${formatBytes(totalSize)}`);
        }
        chunks.push(chunk);
      }

      // Create File object
      return new File(chunks, filename, { type: contentType });
    };

    return await unstable_parseMultipartFormData(request, uploadHandler);
  }

  protected async processFilesIteratively(
    files: File[],
    formData: FormData,
    context: ActionContext
  ): Promise<FileUploadResult[]> {
    const results: FileUploadResult[] = [];
    const baseName = formData.get("name") as string || "Upload";
    const description = formData.get("description") as string | undefined;

    // Process files in batches with concurrency control
    const concurrentUploads = this.config.concurrency?.maxConcurrentUploads || 3;
    const batches = createBatches(files, concurrentUploads);

    this.log(`Processing ${files.length} files in ${batches.length} batches (concurrency: ${concurrentUploads})`);

    for (const [batchIndex, batch] of batches.entries()) {
      const batchStartTime = Date.now();
      this.log(`Processing batch ${batchIndex + 1}/${batches.length} with ${batch.length} files`);

      const batchPromises = batch.map((file, index) =>
        this.processSingleFileWithErrorHandling(
          file,
          baseName,
          description,
          context,
          results.length + index,
          files.length
        )
      );

      const batchResults = await Promise.allSettled(batchPromises);

      // Process results
      let batchSuccessCount = 0;
      let batchErrorCount = 0;

      batchResults.forEach((result, index) => {
        const file = batch[index];
        if (result.status === 'fulfilled') {
          results.push(result.value);
          if (result.value.status === 'success') {
            batchSuccessCount++;
          } else {
            batchErrorCount++;
          }
        } else {
          batchErrorCount++;
          this.logError(`File ${file.name} failed:`, result.reason);
          results.push({
            filename: file.name,
            status: 'error',
            error: result.reason?.message || 'Upload failed',
            size: file.size,
            type: file.type
          });
        }
      });

      const batchDuration = Date.now() - batchStartTime;
      this.log(`Batch ${batchIndex + 1}/${batches.length} complete in ${batchDuration}ms. Success: ${batchSuccessCount}, Errors: ${batchErrorCount}`);

      // Add delay between batches to prevent API overload
      if (batchIndex < batches.length - 1) {
        const delayMs = this.config.concurrency?.batchDelayMs || 200;
        this.log(`Waiting ${delayMs}ms before next batch...`);
        await delay(delayMs);
      }
    }

    const totalSuccess = results.filter(r => r.status === 'success').length;
    const totalErrors = results.filter(r => r.status === 'error').length;
    this.log(`Completed processing all batches. Total Success: ${totalSuccess}, Total Errors: ${totalErrors}`);

    return results;
  }

  protected async processSingleFileWithErrorHandling(
    file: File,
    baseName: string,
    description: string | undefined,
    context: ActionContext,
    fileIndex: number,
    totalFiles: number
  ): Promise<FileUploadResult> {
    try {
      // Generate unique name for this file
      const uniqueName = generateUniqueFileName(baseName, file.name, fileIndex, totalFiles);
      
      this.log(`Processing file ${fileIndex + 1}/${totalFiles}: ${file.name} -> ${uniqueName}`);
      
      // Process the file using the abstract method
      const result = await this.processFile(file, uniqueName, description, context);
      
      return {
        filename: file.name,
        status: 'success',
        dataSource: result,
        size: file.size,
        type: file.type
      };
    } catch (error) {
      this.logError(`Error processing ${file.name}:`, error);
      return {
        filename: file.name,
        status: 'error',
        error: error instanceof Error ? error.message : 'Processing failed',
        size: file.size,
        type: file.type
      };
    }
  }

  protected abstract createBatchResponse(results: FileUploadResult[], actionType: string): Promise<Response>;
}

// ========================================
// SIMPLE ACTION HANDLER BASE
// ========================================

export abstract class SimpleActionHandler extends BaseActionHandler {
  async handle(request: Request, context: ActionContext): Promise<Response> {
    try {
      return await this.processAction(context);
    } catch (error) {
      this.logError("Handler error:", error);
      throw error;
    }
  }

  protected abstract processAction(context: ActionContext): Promise<Response>;
} 