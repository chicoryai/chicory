import { json } from "@remix-run/node";
import type { 
  FileValidationConfig,
  BaseActionResponse,
  ActionContext 
} from "~/types/action-handlers";
import { ValidationError, AuthenticationError } from "~/types/action-handlers";
import { getUserOrgDetails } from "~/auth/auth.server";

// ========================================
// FILE VALIDATION UTILITIES
// ========================================

export function validateFileType(file: File, allowedTypes: string[], allowedExtensions: string[]): boolean {
  // Check MIME type
  if (allowedTypes.length > 0) {
    const isValidMimeType = allowedTypes.some(type => {
      if (type.includes('*')) {
        // Handle wildcard types like 'image/*'
        const [category] = type.split('/');
        return file.type.startsWith(`${category}/`);
      }
      return file.type === type;
    });
    
    if (isValidMimeType) return true;
  }
  
  // Check file extension
  if (allowedExtensions.length > 0) {
    const fileName = file.name.toLowerCase();
    return allowedExtensions.some(ext => fileName.endsWith(ext.toLowerCase()));
  }
  
  // If no restrictions specified, allow all
  return allowedTypes.length === 0 && allowedExtensions.length === 0;
}

export function validateFileSize(file: File, maxSize: number): boolean {
  return file.size <= maxSize;
}

export function validateBatchConstraints(
  files: File[], 
  config: FileValidationConfig
): { valid: boolean; error?: string } {
  if (files.length === 0) {
    return { valid: false, error: "No files provided" };
  }
  
  if (files.length > config.maxFiles) {
    return { 
      valid: false, 
      error: `Too many files. Maximum ${config.maxFiles} allowed, got ${files.length}` 
    };
  }
  
  const totalSize = files.reduce((sum, file) => sum + file.size, 0);
  if (totalSize > config.maxTotalSize) {
    return { 
      valid: false, 
      error: `Total file size too large: ${formatBytes(totalSize)}. Maximum ${formatBytes(config.maxTotalSize)} allowed` 
    };
  }
  
  // Validate individual files
  for (const file of files) {
    if (!validateFileSize(file, config.maxFileSize)) {
      return { 
        valid: false, 
        error: `File '${file.name}' is too large: ${formatBytes(file.size)}. Maximum ${formatBytes(config.maxFileSize)} allowed` 
      };
    }
    
    if (!validateFileType(file, config.allowedTypes, config.allowedExtensions)) {
      return { 
        valid: false, 
        error: `File '${file.name}' has invalid type: ${file.type}` 
      };
    }
  }
  
  return { valid: true };
}

// ========================================
// FORM DATA PARSING UTILITIES
// ========================================

export function extractFilesFromFormData(formData: FormData): File[] {
  const files: File[] = [];
  
  // Try multiple field name patterns commonly used
  const fieldNames = ['file', 'files', 'files[]', 'upload', 'uploads[]'];
  
  for (const fieldName of fieldNames) {
    const entries = formData.getAll(fieldName);
    for (const entry of entries) {
      if (entry instanceof File && entry.size > 0) {
        files.push(entry);
      }
    }
  }
  
  // Fallback: check all form entries for File objects
  if (files.length === 0) {
    for (const [key, value] of formData.entries()) {
      if (value instanceof File && value.size > 0) {
        files.push(value);
      }
    }
  }
  
  return files;
}

export function extractActionType(formData: FormData): string | null {
  return formData.get("_action") as string | null;
}

export function sanitizeString(input: string | null, maxLength: number = 255): string {
  if (!input) return '';
  return input.trim().slice(0, maxLength);
}

export function extractRequiredString(formData: FormData, key: string): string {
  const value = formData.get(key);
  if (!value || typeof value !== 'string' || value.trim() === '') {
    throw new ValidationError(`Missing required field: ${key}`);
  }
  return value.trim();
}

export function extractOptionalString(formData: FormData, key: string): string | undefined {
  const value = formData.get(key);
  if (!value || typeof value !== 'string') return undefined;
  const trimmed = value.trim();
  return trimmed === '' ? undefined : trimmed;
}

// ========================================
// CONTEXT CREATION UTILITIES
// ========================================

export async function createActionContext(request: Request, formData: FormData): Promise<ActionContext> {
  const userDetails = await getUserOrgDetails(request);

  if (userDetails instanceof Response || !userDetails) {
    throw new AuthenticationError();
  }

  // Prefer explicit projectId provided with the action
  let projectId = formData.get('projectId');
  if (typeof projectId === 'string') {
    projectId = projectId.trim();
  } else {
    projectId = null;
  }

  // Fall back to the project encoded in the current URL
  if (!projectId) {
    const url = new URL(request.url);
    const match = url.pathname.match(/\/projects\/([^/]+)/);
    if (match) {
      projectId = decodeURIComponent(match[1]);
    }
  }

  // Fallback to the user's default project only if still missing
  if (!projectId && 'project' in userDetails && userDetails.project) {
    projectId = userDetails.project.id;
  }

  if (!projectId) {
    throw new ValidationError('Project ID is required');
  }
  
  return {
    projectId,
    userId: userDetails.userId,
    orgId: 'orgId' in userDetails ? userDetails.orgId : undefined,
    formData
  };
}

// ========================================
// ERROR HANDLING UTILITIES
// ========================================

export function handleActionError(error: unknown): Response {
  console.error("Action error:", error);
  
  if (error instanceof ValidationError) {
    return json<BaseActionResponse>(
      { 
        success: false, 
        error: error.message,
        _action: "error"
      }, 
      { status: 400 }
    );
  }
  
  if (error instanceof AuthenticationError) {
    return json<BaseActionResponse>(
      { 
        success: false, 
        error: "Authentication required",
        _action: "error"
      }, 
      { status: 401 }
    );
  }
  
  // Generic error
  return json<BaseActionResponse>(
    { 
      success: false, 
      error: "An unexpected error occurred",
      _action: "error"
    }, 
    { status: 500 }
  );
}

export function createSuccessResponse<T extends BaseActionResponse>(
  data: Omit<T, 'success'> & { success?: boolean }
): Response {
  return json<T>({
    ...data,
    success: true
  } as T);
}

export function createErrorResponse(
  message: string, 
  action: string = "error", 
  status: number = 400
): Response {
  return json<BaseActionResponse>(
    {
      success: false,
      error: message,
      _action: action
    },
    { status }
  );
}

// ========================================
// UTILITY FUNCTIONS
// ========================================

export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

export function createBatches<T>(items: T[], batchSize: number): T[][] {
  const batches: T[][] = [];
  for (let i = 0; i < items.length; i += batchSize) {
    batches.push(items.slice(i, i + batchSize));
  }
  return batches;
}

export function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

export function generateUniqueFileName(baseName: string, fileName: string, index: number, totalFiles: number): string {
  if (totalFiles === 1) {
    return baseName;
  }
  
  // Remove file extension for cleaner names
  const cleanFileName = fileName.replace(/\.[^/.]+$/, "");
  return `${baseName} - ${cleanFileName}`;
}

// ========================================
// CONTENT TYPE DETECTION
// ========================================

export function getDataSourceTypeFromAction(action: string): string {
  switch (action) {
    case 'uploadCsv':
      return 'csv_upload';
    case 'uploadExcel':
      return 'xlsx_upload';
    case 'uploadGenericFile':
      return 'generic_file_upload';
    default:
      throw new ValidationError(`Unknown upload action: ${action}`);
  }
}

export function getFileValidationConfig(dataSourceType: string, category?: string): FileValidationConfig {
  const baseConfig = {
    maxFileSize: 100 * 1024 * 1024, // 100MB
    maxTotalSize: 500 * 1024 * 1024, // 500MB
    maxFiles: 10
  };
  
  switch (dataSourceType) {
    case 'csv_upload':
      return {
        ...baseConfig,
        allowedTypes: ['text/csv'],
        allowedExtensions: ['.csv']
      };
    case 'xlsx_upload':
      return {
        ...baseConfig,
        allowedTypes: [
          'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
          'application/vnd.ms-excel'
        ],
        allowedExtensions: ['.xlsx', '.xls']
      };
    case 'generic_file_upload':
      if (category === 'code') {
        return {
          ...baseConfig,
          allowedTypes: [
            'text/javascript',
            'text/typescript',
            'text/x-python',
            'text/x-python-script',
            'text/python',
            'text/x-java-source',
            'text/x-c',
            'text/x-c++src',
            'text/x-csharp',
            'text/x-php',
            'text/x-ruby',
            'text/x-go',
            'text/x-rust',
            'text/x-swift',
            'text/x-kotlin',
            'text/x-scala',
            'text/html',
            'text/css',
            'text/xml',
            'application/json',
            'application/javascript',
            'application/typescript',
            'application/x-yaml',
            'text/yaml',
            'text/plain',
            'text/markdown'
          ],
          allowedExtensions: ['.js', '.jsx', '.ts', '.tsx', '.py', '.java', '.cpp', '.c', '.h', '.cs', '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.scala', '.clj', '.hs', '.ml', '.fs', '.vb', '.pl', '.sh', '.sql', '.html', '.css', '.scss', '.sass', '.less', '.xml', '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf', '.md', '.txt']
        };
      } else {
        return {
          ...baseConfig,
          allowedTypes: [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain',
            'text/markdown'
          ],
          allowedExtensions: ['.pdf', '.doc', '.docx', '.txt', '.md']
        };
      }
    default:
      return {
        ...baseConfig,
        allowedTypes: [],
        allowedExtensions: []
      };
  }
} 
