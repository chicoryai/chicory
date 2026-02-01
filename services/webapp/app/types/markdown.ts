/**
 * TypeScript type definitions for markdown components and processing
 * Replaces all 'any' types with proper interfaces
 */

import type { ReactNode, HTMLAttributes, AnchorHTMLAttributes, ImgHTMLAttributes } from 'react';
import type { Components } from 'react-markdown';

// ============================================================================
// Message Content Types
// ============================================================================

export interface MessageContent {
  content?: string;
  response?: string;
  [key: string]: unknown;
}

export type MessageRole = 'MessageRole.USER' | 'MessageRole.ASSISTANT' | 'TaskRole.USER' | 'TaskRole.ASSISTANT';

export interface BaseMessage {
  content: string;
  response?: string;
  role: MessageRole;
  createdAt?: string;
}

export interface ChatMessage extends BaseMessage {
  id?: string;
  userId?: string;
}

export interface TaskMessage extends BaseMessage {
  id?: string;
  status?: string;
}

// ============================================================================
// Markdown Component Props
// ============================================================================

export interface MarkdownComponentProps extends HTMLAttributes<HTMLElement> {
  children?: ReactNode;
}

export interface HeadingProps extends MarkdownComponentProps {
  level: 1 | 2 | 3 | 4 | 5 | 6;
}

export interface CodeBlockProps extends MarkdownComponentProps {
  className?: string;
  inline?: boolean;
}

export interface ListItemProps extends MarkdownComponentProps {
  checked?: boolean;
  ordered?: boolean;
}

export interface TableWrapperProps {
  children?: ReactNode;
}

export interface CopyButtonProps {
  value: string;
  className?: string;
  tooltip?: string;
}

export interface LinkProps extends AnchorHTMLAttributes<HTMLAnchorElement> {
  href?: string;
}

export interface ImageProps extends ImgHTMLAttributes<HTMLImageElement> {
  src?: string;
  alt?: string;
}

// ============================================================================
// Markdown Renderer Props
// ============================================================================

export type MarkdownVariant = 'chat' | 'task';

export interface MarkdownRendererProps {
  content: string;
  variant?: MarkdownVariant;
  isStreaming?: boolean;
  className?: string;
  /** Allow HTML in markdown (use with caution) */
  allowHtml?: boolean;
  /** Additional remark plugins */
  remarkPlugins?: Array<any>;
  /** Additional rehype plugins */
  rehypePlugins?: Array<any>;
}

// ============================================================================
// Processing Results
// ============================================================================

export type OriginalFormat = 'json' | 'plain' | 'empty';

export interface ProcessedMarkdown {
  content: string;
  isProcessed: boolean;
  originalFormat: OriginalFormat;
  /** Warnings or errors during processing */
  warnings?: string[];
  /** Whether content was truncated for safety */
  wasTruncated?: boolean;
}

// ============================================================================
// Error Boundary Props
// ============================================================================

export interface MarkdownErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: any) => void;
}

export interface MarkdownErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

// ============================================================================
// Plugin System Types (for future extensibility)
// ============================================================================

export interface MarkdownPlugin {
  name: string;
  version: string;
  remark?: any;
  rehype?: any;
  components?: Partial<Components>;
}

export interface MarkdownConfig {
  plugins: MarkdownPlugin[];
  security: {
    allowHtml: boolean;
    maxContentLength: number;
    sanitizeLinks: boolean;
  };
  performance: {
    enableCodeHighlighting: boolean;
    codeHighlightThreshold: number;
    enableVirtualization: boolean;
  };
}

// ============================================================================
// Re-export for backward compatibility
// ============================================================================

export type MarkdownComponents = Components;

// ============================================================================
// Utility Types
// ============================================================================

export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

export type RequiredProps<T, K extends keyof T> = T & Required<Pick<T, K>>;

export type OptionalProps<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;