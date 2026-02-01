import { redirect, unstable_parseMultipartFormData } from "@remix-run/node";
import type { UploadHandler } from "@remix-run/node";
import type { 
  ActionHandler, 
  ActionContext,
  ActionType,
  HandlerRegistryEntry
} from "~/types/action-handlers";
import { ValidationError, AuthenticationError } from "~/types/action-handlers";
import { 
  extractActionType, 
  createActionContext,
  handleActionError
} from "~/utils/action-utils";

// ========================================
// ACTION ROUTER CLASS
// ========================================

export class ActionRouter {
  private handlers = new Map<ActionType, HandlerRegistryEntry>();
  private middlewares: ActionMiddleware[] = [];

  constructor() {
    this.log("ActionRouter initialized");
  }

  /**
   * Register a handler for a specific action type
   */
  register(actionType: ActionType, handler: ActionHandler, config?: Partial<HandlerRegistryEntry>): ActionRouter {
    this.handlers.set(actionType, {
      handler,
      config: config?.config,
      description: config?.description || `Handler for ${actionType} action`
    });
    
    this.log(`Registered handler for action: ${actionType}`);
    return this;
  }

  /**
   * Add middleware to the router
   */
  use(middleware: ActionMiddleware): ActionRouter {
    this.middlewares.push(middleware);
    this.log(`Added middleware: ${middleware.name || 'anonymous'}`);
    return this;
  }

  /**
   * Route incoming request to appropriate handler
   */
  async route(request: Request): Promise<Response> {
    const requestId = this.generateRequestId();
    const startTime = Date.now();

    try {
      // Log incoming request with metadata
      const contentType = request.headers.get("Content-Type") || "unknown";
      const contentLength = request.headers.get("Content-Length");
      const userAgent = request.headers.get("User-Agent") || "unknown";

      this.log(`[${requestId}] Processing incoming request`);
      this.log(`[${requestId}] Content-Type: ${contentType}`);
      this.log(`[${requestId}] Content-Length: ${contentLength ? `${contentLength} bytes` : "unknown"}`);
      this.log(`[${requestId}] User-Agent: ${userAgent}`);

      // Determine content type and parse form data accordingly
      this.log(`[${requestId}] Parsing request data...`);
      const { formData, isMultipart } = await this.parseRequestData(request);
      this.log(`[${requestId}] Request data parsed successfully (multipart: ${isMultipart})`);

      // Extract action type
      const actionType = extractActionType(formData);
      if (!actionType) {
        this.logError(`[${requestId}] Missing _action parameter in form data`);
        throw new ValidationError("Missing _action parameter");
      }

      this.log(`[${requestId}] Action type: ${actionType}`);

      // Validate action type
      if (!this.handlers.has(actionType as ActionType)) {
        this.logError(`[${requestId}] Unknown action type: ${actionType}`);
        throw new ValidationError(`Unknown action type: ${actionType}`);
      }

      // Create action context
      const context = await createActionContext(request, formData);

      // Apply middlewares
      await this.applyMiddlewares(request, context);

      // Get handler
      const handlerEntry = this.handlers.get(actionType as ActionType)!;

      // Execute handler - pass pre-parsed data for multipart requests
      this.log(`[${requestId}] Dispatching to handler: ${handlerEntry.handler.constructor.name}`);
      let response;
      if (isMultipart && 'handleWithParsedData' in handlerEntry.handler) {
        // For multipart handlers, pass the already-parsed data to avoid stream re-read
        response = await (handlerEntry.handler as any).handleWithParsedData(formData, context);
      } else {
        response = await handlerEntry.handler.handle(request, context);
      }

      const duration = Date.now() - startTime;
      this.log(`[${requestId}] Handler completed successfully in ${duration}ms`);
      return response;

    } catch (error) {
      const duration = Date.now() - startTime;
      this.logError(`[${requestId}] Router error after ${duration}ms:`, error);

      // Handle authentication errors specially
      if (error instanceof AuthenticationError) {
        return redirect("/api/auth/login");
      }

      return handleActionError(error);
    }
  }

  /**
   * Generate unique request ID for tracking
   */
  private generateRequestId(): string {
    return `req-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
  }

  /**
   * Parse request data based on content type
   */
  private async parseRequestData(request: Request): Promise<{ formData: FormData; isMultipart: boolean }> {
    const contentType = request.headers.get("Content-Type") || "";
    
    if (contentType.includes("multipart/form-data")) {
      // For multipart data, do full parsing since we need the data anyway
      const formData = await this.parseMultipartDataFully(request);
      return { formData, isMultipart: true };
    } else {
      // Regular form data
      const formData = await request.formData();
      return { formData, isMultipart: false };
    }
  }

  /**
   * Full multipart parsing for file upload handlers
   */
  private async parseMultipartDataFully(request: Request): Promise<FormData> {
    this.log("Starting multipart form data parsing");

    // Check content length to prevent huge uploads
    const contentLength = request.headers.get('content-length');
    const maxTotalSize = 500 * 1024 * 1024; // 500MB default

    if (contentLength) {
      const sizeInMB = Math.round(parseInt(contentLength) / 1024 / 1024);
      this.log(`Total request size: ${sizeInMB}MB`);

      if (parseInt(contentLength) > maxTotalSize) {
        this.logError(`Request size exceeds maximum: ${sizeInMB}MB > ${Math.round(maxTotalSize / 1024 / 1024)}MB`);
        throw new ValidationError(`Request too large: ${sizeInMB}MB`);
      }
    } else {
      this.log("Content-Length header not present");
    }

    let fileCount = 0;
    const uploadHandler: UploadHandler = async ({ name, filename, data, contentType }) => {
      // Handle non-file fields
      if (!filename) {
        const chunks: Uint8Array[] = [];
        let totalSize = 0;
        const maxFieldSize = 10000; // 10KB max for form fields

        for await (const chunk of data) {
          totalSize += chunk.length;
          if (totalSize > maxFieldSize) {
            this.logError(`Form field '${name}' exceeds size limit: ${totalSize} bytes > ${maxFieldSize} bytes`);
            throw new ValidationError(`Form field '${name}' too large`);
          }
          chunks.push(chunk);
        }

        const value = Buffer.concat(chunks).toString();
        this.log(`Parsed form field '${name}': ${value.length} characters`);
        return value;
      }

      // Handle file fields - process 'file' field for uploads
      if (name !== "file") {
        this.log(`Skipping non-file field: ${name} (filename: ${filename})`);
        return undefined;
      }

      fileCount++;
      this.log(`Processing file upload #${fileCount}: ${filename} (${contentType})`);

      // Collect file chunks with size limits
      const chunks: Uint8Array[] = [];
      let totalSize = 0;
      const maxFileSize = 100 * 1024 * 1024; // 100MB per file

      for await (const chunk of data) {
        totalSize += chunk.length;
        if (totalSize > maxFileSize) {
          const sizeInMB = Math.round(totalSize / 1024 / 1024);
          this.logError(`File '${filename}' exceeds size limit: ${sizeInMB}MB > ${Math.round(maxFileSize / 1024 / 1024)}MB`);
          throw new ValidationError(`File '${filename}' too large: ${sizeInMB}MB`);
        }
        chunks.push(chunk);
      }

      const fileSizeInKB = Math.round(totalSize / 1024);
      this.log(`File '${filename}' upload complete: ${fileSizeInKB}KB`);

      // Create File object
      return new File(chunks, filename, { type: contentType });
    };

    try {
      const formData = await unstable_parseMultipartFormData(request, uploadHandler);
      this.log(`Multipart parsing complete. Total files processed: ${fileCount}`);
      return formData;
    } catch (error) {
      this.logError("Error parsing multipart data:", error);
      throw error;
    }
  }

  /**
   * Apply all registered middlewares
   */
  private async applyMiddlewares(request: Request, context: ActionContext): Promise<void> {
    for (const middleware of this.middlewares) {
      await middleware.execute(request, context);
    }
  }

  /**
   * Get information about registered handlers
   */
  getHandlerInfo(): Record<ActionType, HandlerRegistryEntry> {
    const info: Record<string, HandlerRegistryEntry> = {};
    
    for (const [actionType, entry] of this.handlers.entries()) {
      info[actionType] = {
        ...entry,
        handler: {
          name: entry.handler.constructor.name
        } as any // Hide implementation details
      };
    }
    
    return info as Record<ActionType, HandlerRegistryEntry>;
  }

  /**
   * Check if an action type is registered
   */
  hasHandler(actionType: ActionType): boolean {
    return this.handlers.has(actionType);
  }

  /**
   * Remove a handler (useful for testing or dynamic reconfiguration)
   */
  unregister(actionType: ActionType): boolean {
    const removed = this.handlers.delete(actionType);
    if (removed) {
      this.log(`Unregistered handler for action: ${actionType}`);
    }
    return removed;
  }

  private log(message: string, data?: any): void {
    console.log(`[ActionRouter] ${message}`, data || '');
  }

  private logError(message: string, error?: any): void {
    console.error(`[ActionRouter] ${message}`, error || '');
  }
}

// ========================================
// MIDDLEWARE INTERFACE
// ========================================

export interface ActionMiddleware {
  name?: string;
  execute(request: Request, context: ActionContext): Promise<void>;
}

// ========================================
// BUILT-IN MIDDLEWARES
// ========================================

/**
 * Rate limiting middleware
 */
export class RateLimitMiddleware implements ActionMiddleware {
  name = "RateLimit";
  private requests = new Map<string, number[]>();

  constructor(
    private windowMs: number = 60000, // 1 minute
    private maxRequests: number = 20
  ) {}

  async execute(request: Request, context: ActionContext): Promise<void> {
    const key = `${context.userId}:${context.projectId}`;
    const now = Date.now();
    
    // Get or create request history for this key
    const requests = this.requests.get(key) || [];
    
    // Remove old requests outside the window
    const validRequests = requests.filter(timestamp => now - timestamp < this.windowMs);
    
    // Check if limit exceeded
    if (validRequests.length >= this.maxRequests) {
      throw new ValidationError(`Rate limit exceeded. Maximum ${this.maxRequests} requests per ${this.windowMs/1000} seconds.`);
    }
    
    // Add current request
    validRequests.push(now);
    this.requests.set(key, validRequests);
  }
}

/**
 * Logging middleware
 */
export class LoggingMiddleware implements ActionMiddleware {
  name = "Logging";

  async execute(request: Request, context: ActionContext): Promise<void> {
    const userAgent = request.headers.get("User-Agent") || "unknown";
    const ip = request.headers.get("X-Forwarded-For") || 
               request.headers.get("X-Real-IP") || 
               "unknown";
    
    console.log(`[ActionRequest] ${context.userId} from ${ip} (${userAgent}) - Project: ${context.projectId}`);
  }
}

/**
 * Security headers middleware
 */
export class SecurityMiddleware implements ActionMiddleware {
  name = "Security";

  async execute(request: Request, context: ActionContext): Promise<void> {
    // Check for suspicious patterns in form data
    for (const [key, value] of context.formData.entries()) {
      if (typeof value === 'string') {
        // Check for script injection attempts
        if (this.containsSuspiciousContent(value)) {
          throw new ValidationError(`Suspicious content detected in field: ${key}`);
        }
      }
    }
  }

  private containsSuspiciousContent(content: string): boolean {
    const suspiciousPatterns = [
      /<script[^>]*>/i,
      /javascript:/i,
      /vbscript:/i,
      /on\w+\s*=/i,
      /data:text\/html/i
    ];
    
    return suspiciousPatterns.some(pattern => pattern.test(content));
  }
}

// ========================================
// SINGLETON ROUTER INSTANCE
// ========================================

export const actionRouter = new ActionRouter();

// Add default middlewares
actionRouter
  .use(new LoggingMiddleware())
  .use(new RateLimitMiddleware())
  .use(new SecurityMiddleware()); 