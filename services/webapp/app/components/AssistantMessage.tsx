import React from 'react';
import MCPGatewayIcon from "~/components/icons/MCPGatewayIcon";

interface TextBlock {
  type: 'TextBlock';
  text: string;
}

interface ToolUseBlock {
  type: 'ToolUseBlock';
  id: string;
  name: string;
  input: Record<string, any>;
}

interface AssistantMessageProps {
  metadata: {
    textBlocks: TextBlock[];
    toolUseBlocks: ToolUseBlock[];
  } | null;
}

export function AssistantMessage({ metadata }: AssistantMessageProps) {
  if (!metadata) return null;

  const formatToolName = (name: string) => {
    // Remove mcp prefix and format the name
    return name
      .replace(/^mcp__/, '')
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (l) => l.toUpperCase());
  };

  const formatInputValue = (value: any): string => {
    if (typeof value === 'string') return value;
    if (typeof value === 'number') return value.toString();
    if (typeof value === 'boolean') return value ? 'Yes' : 'No';
    if (Array.isArray(value)) return value.join(', ');
    if (typeof value === 'object' && value !== null) {
      return JSON.stringify(value, null, 2);
    }
    return String(value);
  };

  return (
    <div className="assistant-message">
      {/* Render text blocks */}
      {metadata.textBlocks.map((block, index) => (
        <div key={`text-${index}`} className="mb-2 text-gray-800">
          {block.text}
        </div>
      ))}

      {/* Render tool use blocks as sub-items */}
      {metadata.toolUseBlocks.length > 0 && (
        <div className="ml-4 mt-2 space-y-2">
          {metadata.toolUseBlocks.map((block, index) => (
            <div
              key={`tool-${block.id || index}`}
              className="border-l-2 border-gray-300 pl-3 py-1"
            >
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <MCPGatewayIcon size={16} className="flex-shrink-0" />
                <span className="font-medium">
                  Using: {formatToolName(block.name)}
                </span>
              </div>
              {Object.keys(block.input).length > 0 && (
                <div className="ml-6 mt-1 text-xs text-gray-500 space-y-1">
                  {Object.entries(block.input).map(([key, value]) => (
                    <div key={key} className="flex gap-2">
                      <span className="font-medium">
                        {key.replace(/_/g, ' ')}:
                      </span>
                      <span className="font-mono">
                        {formatInputValue(value)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
