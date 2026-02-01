/**
 * Shared utility for processing markdown content across chat and task messages
 * Consolidates duplicate logic and provides consistent preprocessing
 */

import type { ProcessedMarkdown, OriginalFormat } from '~/types/markdown';

export interface MessageContent {
  content?: string;
  response?: string;
}

/**
 * Sanitizes and validates markdown content to prevent XSS and ensure safe rendering
 */
export function sanitizeMarkdownContent(content: string): string {
  // Basic sanitization - remove potentially dangerous patterns
  // Note: More comprehensive sanitization should be added with DOMPurify in Phase 1.1.3
  
  // Remove script tags and javascript: URLs
  let sanitized = content
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
    .replace(/javascript:/gi, '')
    .replace(/on\w+\s*=/gi, ''); // Remove event handlers
  
  // Limit content length to prevent DoS
  const MAX_CONTENT_LENGTH = 100000; // 100KB limit
  if (sanitized.length > MAX_CONTENT_LENGTH) {
    sanitized = sanitized.substring(0, MAX_CONTENT_LENGTH) + '\n\n*[Content truncated for performance]*';
  }
  
  return sanitized;
}

/**
 * Standardizes list spacing by removing double newlines before list items
 */
export function normalizeListSpacing(content: string): string {
  return content.replace(/\n\n([*+-] )/g, '\n$1');
}

/**
 * Removes markdown code fences that wrap the entire content
 */
export function stripMarkdownFences(content: string): string {
  return content.replace(/^```markdown\n|```$/g, '');
}

/**
 * Unescapes JSON-encoded markdown content with Unicode sequences
 * Handles double-encoded content from API responses
 */
export function unescapeMarkdownContent(content: string): string {
  let unescaped = content
    // Replace escaped newlines with actual newlines
    .replace(/\\n/g, '\n')
    // Replace escaped tabs with actual tabs  
    .replace(/\\t/g, '\t')
    // Replace escaped quotes
    .replace(/\\"/g, '"')
    .replace(/\\'/g, "'")
    // Replace common Unicode sequences
    .replace(/\\u2022/g, '•')  // Bullet point
    .replace(/\\u2013/g, '–')  // En dash
    .replace(/\\u2014/g, '—')  // Em dash
    .replace(/\\u2003/g, ' ')  // Em space
    .replace(/\\u2002/g, ' ')  // En space
    .replace(/\\u2009/g, ' ')  // Thin space
    .replace(/\\u00A0/g, ' ')  // Non-breaking space
    .replace(/\\u201c/g, '"')  // Left double quote
    .replace(/\\u201d/g, '"')  // Right double quote
    .replace(/\\u2018/g, "'")  // Left single quote
    .replace(/\\u2019/g, "'")  // Right single quote
    // Replace any remaining Unicode escapes
    .replace(/\\u([0-9a-fA-F]{4})/g, (match, code) => {
      return String.fromCharCode(parseInt(code, 16));
    });
  
  // Transform plain text structure to markdown format
  return transformPlainTextToMarkdown(unescaped);
}

// Cache for transformation results to ensure stability
const transformationCache = new Map<string, string>();

/**
 * Transforms plain text with structured content to proper markdown
 * Handles common patterns from API responses that need markdown formatting
 */
export function transformPlainTextToMarkdown(content: string): string {
  // Return cached result if available to ensure stability
  if (transformationCache.has(content)) {
    return transformationCache.get(content)!;
  }
  
  const transformed = content
    // FIRST: Fix Unicode escape sequences that come from backend
    .replace(/\\\\u2013/g, '–')               // Fix escaped en dash
    .replace(/\\\\u201c/g, '"')               // Fix escaped left quote
    .replace(/\\\\u201d/g, '"')               // Fix escaped right quote
    .replace(/\\\\u2026/g, '…')               // Fix escaped ellipsis
    .replace(/\\\\u2011/g, '-')               // Fix escaped non-breaking hyphen
    .replace(/\\\\u2022/g, '•')               // Fix escaped bullet
    .replace(/\\\\u25[0-9a-fA-F]{2}/g, '')    // Remove box drawing characters
    
    // Convert standalone section titles to headers
    .replace(/^(Key points|Next steps you might take|Typical use cases|Summary|Overview|Analysis|Recommendations?|Purpose & Grain|Physical schema|Row volumes & cardinality|Relationship map|Key distributions|Data quality notes|Operational considerations)$/gm, '## $1')
    .replace(/^(Key points|Next steps you might take|Typical use cases|Summary|Overview|Analysis|Recommendations?|Purpose & Grain|Physical schema|Row volumes & cardinality|Relationship map|Key distributions|Data quality notes|Operational considerations)\s*$/gm, '## $1')
    
    // Convert bullet points to markdown lists
    .replace(/^•\s+(.+)$/gm, '- $1')          // • to -
    .replace(/^\u2022\s+(.+)$/gm, '- $1')     // Unicode bullet to -
    .replace(/^–\s+(.+)$/gm, '  - $1')        // En dash to nested list
    .replace(/^\u2013\s+(.+)$/gm, '  - $1')   // Unicode en dash to nested list
    
    // Handle lettered lists (a), b), etc.)
    .replace(/^\s*([a-z])\)\s+(.+)$/gm, '   $1) **$2**')  // Make lettered items bold and indent
    
    // Convert numbered lists that aren't already markdown
    .replace(/^(\d+)\.\s+(.+)$/gm, '$1. $2')
    
    // Convert dotted data lines to structured format (basic attempt)
    .replace(/^(\s+)([A-Za-z\s]+)\s*[.…]{3,}\s*([0-9,\s&]+)\s*(\([^)]*\))?$/gm, '$1- **$2**: $3 $4')
    
    // Convert code-like patterns to inline code
    .replace(/\b([A-Z_]{2,}[A-Z0-9_]*)\b/g, '`$1`')  // ALL_CAPS variables like SYSTEM_ID
    .replace(/\b([a-z_]+\.[a-z_]+)\b/g, '`$1`')       // dotted names like file.ext
    .replace(/\b([a-z_]+_[a-z_]+)\b/g, '`$1`')        // snake_case identifiers
    
    // Convert table references to code
    .replace(/\{workspace\}\.\{[^}]+\}\.[a-z_]+/g, (match) => `\`${match}\``)
    
    // Improve spacing around headers
    .replace(/\n(##\s+[^\n]+)\n/g, '\n\n$1\n\n')
    
    // Clean up excessive whitespace but preserve intentional formatting
    .replace(/\n{3,}/g, '\n\n')               // Max 2 consecutive newlines
    .replace(/^\s+$/gm, '')                   // Remove whitespace-only lines
    .trim();
  
  // Cache the result (limit cache size to prevent memory leaks)
  if (transformationCache.size > 100) {
    transformationCache.clear();
  }
  transformationCache.set(content, transformed);
  
  return transformed;
}

/**
 * Attempts to parse JSON content and extract markdown from standard fields
 */
export function parseMessageContent(rawContent: string | undefined): ProcessedMarkdown {
  if (!rawContent || rawContent.trim() === '') {
    return {
      content: '',
      isProcessed: false,
      originalFormat: 'empty' as OriginalFormat
    };
  }

  // Try to parse as JSON first
  try {
    const parsed = JSON.parse(rawContent);
    
    // Look for standard content fields
    if (typeof parsed.content === 'string' || typeof parsed.response === 'string') {
      let extractedContent = parsed.content || parsed.response;
      
      // Handle double-encoded JSON strings with Unicode escapes
      extractedContent = unescapeMarkdownContent(extractedContent);
      
      return {
        content: extractedContent,
        isProcessed: true,
        originalFormat: 'json' as OriginalFormat
      };
    } else {
      // JSON doesn't have expected fields, use original content
      return {
        content: rawContent,
        isProcessed: false,
        originalFormat: 'json' as OriginalFormat
      };
    }
  } catch {
    // Not JSON, use content directly
    return {
      content: rawContent,
      isProcessed: false,
      originalFormat: 'plain' as OriginalFormat
    };
  }
}

/**
 * Processes message content for assistant messages with consistent preprocessing
 */
export function processAssistantMarkdown(
  messageContent: string | undefined,
  fallbackContent?: string
): ProcessedMarkdown {
  const parsed = parseMessageContent(messageContent);
  
  if (parsed.content === '' && fallbackContent) {
    const fallbackParsed = parseMessageContent(fallbackContent);
    parsed.content = fallbackParsed.content;
    parsed.isProcessed = fallbackParsed.isProcessed;
  }
  
  if (parsed.content) {
    // Apply consistent preprocessing
    let processedContent = parsed.content;
    processedContent = sanitizeMarkdownContent(processedContent);
    processedContent = normalizeListSpacing(processedContent);
    processedContent = stripMarkdownFences(processedContent);
    
    return {
      content: processedContent,
      isProcessed: true,
      originalFormat: parsed.originalFormat
    };
  }
  
  return parsed;
}

/**
 * Processes user message content (typically plain text, preserve whitespace)
 */
export function processUserContent(
  messageContent: string | undefined,
  fallbackContent?: string
): ProcessedMarkdown {
  const content = messageContent || fallbackContent || '';
  
  return {
    content: sanitizeMarkdownContent(content),
    isProcessed: false, // User content is treated as plain text
    originalFormat: 'plain' as OriginalFormat
  };
}

/**
 * Main processor function that handles both assistant and user messages
 */
export class MarkdownProcessor {
  static processContent(
    content: string | undefined,
    fallbackContent: string | undefined,
    isAssistantMessage: boolean
  ): ProcessedMarkdown {
    if (isAssistantMessage) {
      return processAssistantMarkdown(content, fallbackContent);
    } else {
      return processUserContent(content, fallbackContent);
    }
  }
  
  /**
   * Legacy method for backwards compatibility during migration
   * @deprecated Use processContent instead
   */
  static processAssistantMessage(
    content: string | undefined,
    fallbackContent?: string
  ): string {
    const result = processAssistantMarkdown(content, fallbackContent);
    return result.content;
  }
  
  /**
   * Legacy method for backwards compatibility during migration  
   * @deprecated Use processContent instead
   */
  static processUserMessage(
    content: string | undefined,
    fallbackContent?: string
  ): string {
    const result = processUserContent(content, fallbackContent);
    return result.content;
  }
}