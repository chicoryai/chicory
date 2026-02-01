import type { DataSourceCredential, TrainingJob } from "~/services/chicory.server";

// ========================================
// BASE INTERFACES & TYPES
// ========================================

export interface ActionHandler {
  handle(request: Request, context: ActionContext): Promise<Response>;
}

export interface ActionContext {
  projectId: string;
  userId: string;
  orgId?: string;
  formData: FormData;
}

export class ValidationError extends Error {
  constructor(message: string, public code?: string) {
    super(message);
    this.name = 'ValidationError';
  }
}

export class AuthenticationError extends Error {
  constructor(message: string = 'Authentication required') {
    super(message);
    this.name = 'AuthenticationError';
  }
}

// ========================================
// FILE UPLOAD SPECIFIC TYPES
// ========================================

export interface FileUploadResult {
  filename: string;
  status: 'success' | 'error';
  dataSource?: DataSourceCredential;
  error?: string;
  size?: number;
  type?: string;
}

export interface BatchUploadResponse {
  success: boolean;
  results: FileUploadResult[];
  projectDataSources?: DataSourceCredential[];
  _action: string;
  message?: string;
}

export interface FileValidationConfig {
  maxFileSize: number;
  maxTotalSize: number;
  maxFiles: number;
  allowedTypes: string[];
  allowedExtensions: string[];
}

// ========================================
// ACTION RESPONSE TYPES
// ========================================

export interface BaseActionResponse {
  success: boolean;
  message?: string;
  error?: string;
  _action: string;
}

export interface DataSourceActionResponse extends BaseActionResponse {
  projectDataSources?: DataSourceCredential[];
  dataSource?: DataSourceCredential;
}

export interface TrainingActionResponse extends BaseActionResponse {
  trainingJob?: TrainingJob;
  trainingJobs?: TrainingJob[];
}

export interface ConnectionTestResponse extends BaseActionResponse {
  connectionValid?: boolean;
  details?: Record<string, any>;
  dataSourceId?: string;
}

// ========================================
// HANDLER CONFIGURATION
// ========================================

export interface HandlerConfig {
  fileValidation?: FileValidationConfig;
  concurrency?: {
    maxConcurrentUploads: number;
    batchDelayMs: number;
  };
  security?: {
    enableContentScanning: boolean;
    enableRateLimiting: boolean;
    rateLimitWindow: number;
    rateLimitMax: number;
  };
}

export const DEFAULT_HANDLER_CONFIG: HandlerConfig = {
  fileValidation: {
    maxFileSize: 100 * 1024 * 1024, // 100MB per file
    maxTotalSize: 500 * 1024 * 1024, // 500MB total
    maxFiles: 10,
    allowedTypes: [],
    allowedExtensions: []
  },
  concurrency: {
    maxConcurrentUploads: 3,
    batchDelayMs: 200
  },
  security: {
    enableContentScanning: false,
    enableRateLimiting: true,
    rateLimitWindow: 60000, // 1 minute
    rateLimitMax: 20 // 20 requests per minute
  }
};

// ========================================
// HANDLER REGISTRY TYPES
// ========================================

export type ActionType = 
  | 'uploadCsv'
  | 'uploadExcel' 
  | 'uploadGenericFile'
  | 'deleteDataSource'
  | 'createDataSource'
  | 'editDataSource'
  | 'startTraining'
  | 'testConnection'
  | 'validateCredentials'
  | 'create-project';

export interface HandlerRegistryEntry {
  handler: ActionHandler;
  config?: HandlerConfig;
  description?: string;
} 