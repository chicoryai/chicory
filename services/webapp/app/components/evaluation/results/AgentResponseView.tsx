import React, { useState } from 'react';
import { MarkdownRenderer } from '~/components/MarkdownRenderer';
import { DocumentDuplicateIcon, ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/24/outline';

interface AgentResponseViewProps {
  response: string;
}

export function AgentResponseView({ response }: AgentResponseViewProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [copied, setCopied] = useState(false);

  // Extract response content if it's JSON format
  const displayContent = React.useMemo(() => {
    if (!response) return '';
    
    try {
      const parsed = JSON.parse(response);
      // Check if it has a "response" field (agent response format)
      if (parsed.response !== undefined) {
        return parsed.response;
      }
    } catch {
      // Not JSON or parsing failed, use as-is
    }
    return response;
  }, [response]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(displayContent);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <div className="bg-white dark:bg-whitePurple-50/5 backdrop-blur-sm rounded-lg border border-gray-200 dark:border-purple-900/20 overflow-hidden h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-gray-50 dark:bg-purple-900/10 border-b border-gray-200 dark:border-purple-900/20">
        <h5 className="text-sm font-medium text-gray-700 dark:text-gray-300">
          Agent Response
        </h5>
        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-purple-800/30 transition-colors"
            title="Copy response"
          >
            <DocumentDuplicateIcon className="w-4 h-4 text-gray-500 dark:text-gray-400" />
          </button>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-purple-800/30 transition-colors"
            title={isExpanded ? "Collapse" : "Expand"}
          >
            {isExpanded ? (
              <ChevronUpIcon className="w-4 h-4 text-gray-500 dark:text-gray-400" />
            ) : (
              <ChevronDownIcon className="w-4 h-4 text-gray-500 dark:text-gray-400" />
            )}
          </button>
        </div>
      </div>

      {/* Content */}
      {isExpanded && (
        <div className="p-4 max-h-96 overflow-y-auto">
          {displayContent ? (
            <MarkdownRenderer 
              content={displayContent} 
              variant="chat"
              className="text-sm"
            />
          ) : (
            <p className="text-sm text-gray-500 dark:text-gray-400 italic">
              No response available
            </p>
          )}
        </div>
      )}

      {/* Copied notification */}
      {copied && (
        <div className="absolute top-12 right-4 bg-green-500 text-white px-2 py-1 rounded text-xs">
          Copied!
        </div>
      )}
    </div>
  );
}