import React from 'react';
import ReactMarkdown from 'react-markdown';
import { twMerge } from 'tailwind-merge';
import { MarkdownProcessor } from '~/utils/markdown-processor';
import { getPluginConfig } from '~/utils/markdown-plugins';
import { markdownComponents } from './MarkdownComponents';
import MarkdownErrorBoundary from './MarkdownErrorBoundary';
import type { MarkdownRendererProps } from '~/types/markdown';

/**
 * Unified markdown renderer component
 * Single source of truth for all markdown rendering across the webapp
 * Replaces duplicate logic in ChatMessageItem and TaskMessageItem
 */
export function MarkdownRenderer({ 
  content, 
  variant = 'chat', 
  isStreaming = false,
  className,
  allowHtml = false,
  remarkPlugins = [],
  rehypePlugins = []
}: MarkdownRendererProps) {
  // Process the content based on whether it's assistant or user content
  // For now, we assume all content going through MarkdownRenderer is assistant content
  // User content should be handled separately with whitespace-pre-wrap
  const processedContent = React.useMemo(() => {
    return MarkdownProcessor.processContent(content, undefined, true);
  }, [content, variant]);

  // Handle empty content
  if (!processedContent.content.trim()) {
    return (
      <div className={twMerge("text-gray-500 dark:text-gray-400 italic", className)}>
      </div>
    );
  }

  // Get standardized plugin configuration
  const pluginConfig = getPluginConfig('standard');
  
  // Combine default plugins with any additional ones passed in
  const allRemarkPlugins = [...pluginConfig.remark, ...remarkPlugins];
  const allRehypePlugins = [...pluginConfig.rehype, ...rehypePlugins];

  return (
    <MarkdownErrorBoundary>
      <div className={twMerge(
        "markdown-content",
        // Base styles for markdown content
        "text-gray-800 dark:text-white",
        // Variant-specific styles
        variant === 'task' && "task-markdown",
        className
      )}>
        <ReactMarkdown
          skipHtml={!allowHtml}
          remarkPlugins={allRemarkPlugins}
          rehypePlugins={allRehypePlugins}
          components={markdownComponents}
        >
          {processedContent.content}
        </ReactMarkdown>
        
        {/* Development warnings */}
        {process.env.NODE_ENV === 'development' && processedContent.warnings && processedContent.warnings.length > 0 && (
          <div className="mt-2 p-2 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded text-xs">
            <strong>Dev Warnings:</strong>
            <ul className="mt-1 ml-4 list-disc">
              {processedContent.warnings.map((warning: string, index: number) => (
                <li key={index} className="text-yellow-700 dark:text-yellow-300">
                  {warning}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </MarkdownErrorBoundary>
  );
}

/**
 * Legacy wrapper for backwards compatibility during migration
 * @deprecated Use MarkdownRenderer instead
 */
export function LegacyMarkdownRenderer({ 
  content, 
  isAssistant = true, 
  className 
}: { 
  content: string; 
  isAssistant?: boolean; 
  className?: string; 
}) {
  if (!isAssistant) {
    // For user content, preserve whitespace
    return (
      <div className={twMerge("whitespace-pre-wrap", className)}>
        {content}
      </div>
    );
  }

  return (
    <MarkdownRenderer 
      content={content} 
      className={className}
    />
  );
}

export default MarkdownRenderer;
