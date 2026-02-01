import React from 'react';
import MCPGatewayIcon from "~/components/icons/MCPGatewayIcon";

interface ToolUseProps {
  name: string;
  input: Record<string, any>;
  id: string;
}

const ToolUse: React.FC<ToolUseProps> = ({ name, input, id }) => {
  // Extract key parameters to display
  const getDisplayParams = () => {
    switch (name) {
      case 'Read':
        return input.file_path ? `Reading: ${input.file_path}` : 'Reading file...';
      case 'Edit':
      case 'MultiEdit':
        return input.file_path ? `Editing: ${input.file_path}` : 'Editing file...';
      case 'Write':
        return input.file_path ? `Writing: ${input.file_path}` : 'Writing file...';
      case 'Bash':
        return input.command ? `Running: ${input.command.substring(0, 50)}${input.command.length > 50 ? '...' : ''}` : 'Running command...';
      case 'WebFetch':
        return input.url ? `Fetching: ${input.url}` : 'Fetching web content...';
      case 'WebSearch':
        return input.query ? `Searching: ${input.query}` : 'Searching web...';
      case 'Grep':
        return input.pattern ? `Searching for: ${input.pattern}` : 'Searching in files...';
      case 'Glob':
        return input.pattern ? `Finding files: ${input.pattern}` : 'Finding files...';
      case 'Task':
        return input.description || 'Running task...';
      default:
        return `Using ${name}...`;
    }
  };

  return (
    <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
      <MCPGatewayIcon size={24} alt={`${name} MCP tool`} className="flex-shrink-0" />
      <span className="font-medium">{name}</span>
      <span className="text-xs truncate flex-1">
        {getDisplayParams()}
      </span>
    </div>
  );
};

export default ToolUse;
