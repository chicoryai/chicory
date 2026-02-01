import { useState, useMemo } from 'react';
import { MagnifyingGlassIcon, FunnelIcon, ClipboardDocumentIcon, ChevronDownIcon, ChevronRightIcon } from '@heroicons/react/24/outline';
import MCPGatewayIcon from "~/components/icons/MCPGatewayIcon";
import type { ActivityPanelProps, ClaudeCodeMessage } from '~/types/panels';
import { 
  ClaudeCodeUtils,
  isAssistantMessage,
  isUserMessage,
  isSystemMessage,
  isResultMessage,
  type ContentBlock 
} from '~/types/claude-code';

export function ActivityPanel({ messages, agentId, className = "" }: ActivityPanelProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [filterType, setFilterType] = useState<string>("all");
  const [expandedMessages, setExpandedMessages] = useState<Record<string, boolean>>({});

  // Filter messages based on search and type
  const filteredMessages = useMemo(() => {
    let filtered = messages;
    
    // Filter by type
    if (filterType !== "all") {
      filtered = filtered.filter(msg => msg.message_type === filterType);
    }
    
    // Filter by search query
    if (searchQuery) {
      filtered = filtered.filter(msg => 
        msg.message.toLowerCase().includes(searchQuery.toLowerCase()) ||
        msg.message_type.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }
    
    // Sort by timestamp (newest first)
    return filtered.sort((a, b) => 
      new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );
  }, [messages, filterType, searchQuery]);

  // Parse message content for display
  const parseMessageContent = (msg: ClaudeCodeMessage): ContentBlock[] => {
    const blocks: ContentBlock[] = [];
    
    // First try to use structured_data if available and properly formatted
    if (msg.structured_data && typeof msg.structured_data === 'object') {
      // Check if it has a type field to identify the message type
      if ('type' in msg.structured_data && msg.structured_data.type === 'AssistantMessage') {
        if ('content' in msg.structured_data && Array.isArray(msg.structured_data.content)) {
          return msg.structured_data.content;
        }
      } else if (isAssistantMessage(msg.structured_data)) {
        return msg.structured_data.content;
      } else if (isUserMessage(msg.structured_data)) {
        // Handle UserMessage content
        if (typeof msg.structured_data.content === 'string') {
          blocks.push({ type: 'text', text: msg.structured_data.content });
        } else {
          return msg.structured_data.content;
        }
      } else if (isSystemMessage(msg.structured_data)) {
        // Create a text block for system messages
        blocks.push({ 
          type: 'text', 
          text: `${msg.structured_data.subtype}: ${JSON.stringify(msg.structured_data.data)}` 
        });
      } else if (isResultMessage(msg.structured_data)) {
        // Create a text block for result messages
        const parts = [];
        if (msg.structured_data.duration_ms) parts.push(`Duration: ${msg.structured_data.duration_ms}ms`);
        if (msg.structured_data.total_cost_usd) parts.push(`Cost: $${msg.structured_data.total_cost_usd}`);
        if (msg.structured_data.num_turns) parts.push(`Turns: ${msg.structured_data.num_turns}`);
        blocks.push({ type: 'text', text: parts.join(', ') });
      }
      
      if (blocks.length > 0) return blocks;
    }
    
    // Improved fallback parsing for the string message
    const message = msg.message || '';
    
    // Handle AssistantMessage with content array
    if (message.startsWith('AssistantMessage(content=[')) {
      // Extract the content array part
      const contentMatch = message.match(/content=\[(.*)\](?:,\s*model=|$)/s);
      if (contentMatch) {
        const contentStr = contentMatch[1];
        
        // Parse multiple TextBlocks - handle escaped quotes and multi-line
        const textBlockRegex = /TextBlock\(text=(?:'([^'\\]*(?:\\.[^'\\]*)*)'|"([^"\\]*(?:\\.[^"\\]*)*)")\)/g;
        let match;
        while ((match = textBlockRegex.exec(contentStr)) !== null) {
          const text = match[1] || match[2];
          if (text) {
            // Unescape the text
            const unescapedText = text
              .replace(/\\n/g, '\n')
              .replace(/\\t/g, '\t')
              .replace(/\\'/g, "'")
              .replace(/\\"/g, '"')
              .replace(/\\\\/g, '\\');
            blocks.push({ type: 'text', text: unescapedText });
          }
        }
      }
    }
    
    // Handle UserMessage with ToolResultBlock
    if (message.startsWith('UserMessage(content=[')) {
      const contentMatch = message.match(/content=\[(.*)\]/s);
      if (contentMatch) {
        const contentStr = contentMatch[1];
        
        // Parse ToolResultBlocks
        const toolResultRegex = /ToolResultBlock\(tool_use_id='([^']+)'(?:,\s*content=([^,)]+))?(?:,\s*is_error=(True|False))?\)/g;
        let match;
        while ((match = toolResultRegex.exec(contentStr)) !== null) {
          blocks.push({ 
            type: 'tool_result',
            tool_use_id: match[1],
            content: match[2] && match[2] !== 'None' ? match[2].replace(/^['"]|['"]$/g, '') : null,
            is_error: match[3] === 'True'
          });
        }
      }
    }
    
    // If still no blocks, try simpler parsing
    if (blocks.length === 0) {
      // Parse TextBlocks with simpler regex
      const simpleTextMatch = message.match(/TextBlock\(text=['"]([^'"]+)['"]\)/);
      if (simpleTextMatch) {
        blocks.push({ type: 'text', text: simpleTextMatch[1] });
      }
      
      // Parse ToolUseBlocks  
      const toolUseRegex = /ToolUseBlock\(id='([^']+)',\s*name='([^']+)',\s*input=(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})\)/g;
      let match;
      while ((match = toolUseRegex.exec(message)) !== null) {
        blocks.push({ 
          type: 'tool_use',
          id: match[1],
          name: match[2],
          input: parseToolInput(match[3])
        });
      }
      
      // Parse ToolResultBlocks if not already parsed
      if (!message.startsWith('UserMessage(')) {
        const toolResultRegex = /ToolResultBlock\(tool_use_id='([^']+)'(?:,\s*content=([^,)]+))?(?:,\s*is_error=(True|False))?\)/g;
        while ((match = toolResultRegex.exec(message)) !== null) {
          blocks.push({ 
            type: 'tool_result',
            tool_use_id: match[1],
            content: match[2] && match[2] !== 'None' ? match[2].replace(/^['"]|['"]$/g, '') : null,
            is_error: match[3] === 'True'
          });
        }
      }
      
      // Parse ThinkingBlocks
      const thinkingRegex = /ThinkingBlock\(thinking=(?:'([^'\\]*(?:\\.[^'\\]*)*)'|"([^"\\]*(?:\\.[^"\\]*)*)")(?:,\s*signature='([^']+)')?\)/g;
      while ((match = thinkingRegex.exec(message)) !== null) {
        const thinking = match[1] || match[2];
        if (thinking) {
          blocks.push({ 
            type: 'thinking',
            thinking: thinking.replace(/\\n/g, '\n').replace(/\\'/g, "'").replace(/\\"/g, '"'),
            signature: match[3] || ''
          });
        }
      }
    }
    
    // Special case: if message says "X blocks" this is likely a parsing issue
    if (blocks.length === 0 && message.match(/^\d+\s+blocks?$/)) {
      // This indicates we failed to parse the actual content
      blocks.push({ type: 'text', text: `[Unable to parse ${message}]` });
    }
    
    // If still no blocks were parsed, check for common patterns
    if (blocks.length === 0 && message) {
      // Check if it's just a number (like "196 blocks")
      if (!message.match(/^\d+\s+blocks?$/)) {
        blocks.push({ type: 'text', text: message });
      }
    }
    
    return blocks;
  };
  
  // Helper to parse tool input
  const parseToolInput = (inputStr: string): Record<string, any> => {
    try {
      // Convert Python dict format to JSON
      const jsonStr = inputStr
        .replace(/'/g, '"')
        .replace(/None/g, 'null')
        .replace(/True/g, 'true')
        .replace(/False/g, 'false');
      return JSON.parse(jsonStr);
    } catch {
      return { raw: inputStr };
    }
  };
  
  // Get a summary of the message for collapsed view
  const getMessageSummary = (msg: ClaudeCodeMessage): string => {
    // First check the message type for quick summary
    if (msg.message_type === 'UserMessage') {
      // Check if it's a tool result
      if (msg.message.includes('ToolResultBlock')) {
        const errorMatch = msg.message.match(/is_error=(True|False)/);
        return `📋 Tool Result${errorMatch && errorMatch[1] === 'True' ? ' (error)' : ''}`;
      }
      // Check if it's a tool use
      if (msg.message.includes('ToolUseBlock')) {
        const nameMatch = msg.message.match(/name='([^']+)'/);
        return nameMatch ? `Tool: ${nameMatch[1]}` : 'Tool Use';
      }
    } else if (msg.message_type === 'AssistantMessage') {
      // Try to extract text content
      if (msg.message.includes('TextBlock')) {
        const textMatch = msg.message.match(/TextBlock\(text=['"]([^'"]{1,100})[^'"]*['"]\)/);
        if (textMatch) {
          const preview = textMatch[1];
          return preview.length >= 100 ? preview + '...' : preview;
        }
      }
      // Check for tool use
      if (msg.message.includes('ToolUseBlock')) {
        const nameMatch = msg.message.match(/name='([^']+)'/);
        return nameMatch ? `Tool: ${nameMatch[1]}` : 'Tool Use';
      }
    } else if (msg.message_type === 'ResultMessage') {
      const durationMatch = msg.message.match(/duration_ms=(\d+)/);
      const costMatch = msg.message.match(/total_cost_usd=([\d.]+)/);
      if (durationMatch || costMatch) {
        const parts = [];
        if (durationMatch) parts.push(`${durationMatch[1]}ms`);
        if (costMatch) parts.push(`$${costMatch[1]}`);
        return `📊 Result: ${parts.join(', ')}`;
      }
      return '📊 Result';
    }
    
    // Fallback to parsed blocks
    const blocks = parseMessageContent(msg);
    
    if (blocks.length === 0) {
      // If we couldn't parse, show a snippet of the raw message
      const preview = msg.message.substring(0, 100);
      return preview + (msg.message.length > 100 ? '...' : '');
    }
    
    const firstBlock = blocks[0];
    
    if (ClaudeCodeUtils.guards.isTextBlock(firstBlock)) {
      const text = firstBlock.text;
      // Don't show "[Unable to parse...]" messages
      if (text.startsWith('[Unable to parse')) {
        return msg.message.substring(0, 100) + '...';
      }
      return text.length > 100 ? text.substring(0, 100) + '...' : text;
    } else if (ClaudeCodeUtils.guards.isToolUseBlock(firstBlock)) {
      return `Tool: ${firstBlock.name}`;
    } else if (ClaudeCodeUtils.guards.isToolResultBlock(firstBlock)) {
      return `📋 Tool Result${firstBlock.is_error ? ' (error)' : ''}`;
    } else if (ClaudeCodeUtils.guards.isThinkingBlock(firstBlock)) {
      return '💭 Thinking...';
    }
    
    return `${blocks.length} block${blocks.length > 1 ? 's' : ''}`;
  };

  // Copy message to clipboard
  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  // Toggle message expansion
  const toggleMessage = (messageId: string) => {
    setExpandedMessages(prev => ({
      ...prev,
      [messageId]: !prev[messageId]
    }));
  };

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Activity Log</h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Claude Code message history ({messages.length} messages)
        </p>
      </div>

      {/* Search and Filter */}
      <div className="px-4 py-3 space-y-3 border-b border-gray-200 dark:border-gray-700">
        {/* Search */}
        <div className="relative">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search messages..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500"
          />
        </div>

        {/* Filter */}
        <div className="flex items-center gap-2">
          <FunnelIcon className="h-4 w-4 text-gray-400" />
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="flex-1 px-3 py-1.5 text-sm border border-gray-200 dark:border-gray-700 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
          >
            <option value="all">All Messages</option>
            <option value="UserMessage">User Messages</option>
            <option value="AssistantMessage">Assistant Messages</option>
            <option value="SystemMessage">System Messages</option>
            <option value="ResultMessage">Result Messages</option>
          </select>
        </div>
      </div>

      {/* Messages List */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {filteredMessages.length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            {searchQuery || filterType !== "all" 
              ? "No messages match your filters" 
              : "No Claude Code messages yet"}
          </div>
        ) : (
          filteredMessages.map((msg) => {
            const isExpanded = expandedMessages[msg.id];
            const blocks = parseMessageContent(msg);
            const summary = getMessageSummary(msg);
            
            return (
              <div
                key={msg.id}
                className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden"
              >
                {/* Message Header */}
                <div 
                  className="px-3 py-2 bg-gray-50 dark:bg-gray-800 flex items-center justify-between cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700"
                  onClick={() => toggleMessage(msg.id)}
                >
                  <div className="flex items-center gap-2">
                    <button className="p-0.5">
                      {isExpanded ? 
                        <ChevronDownIcon className="h-4 w-4 text-gray-500" /> : 
                        <ChevronRightIcon className="h-4 w-4 text-gray-500" />
                      }
                    </button>
                    <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300">
                      {msg.message_type.replace('Message', '')}
                    </span>
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      {new Date(msg.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      copyToClipboard(JSON.stringify(msg, null, 2));
                    }}
                    className="p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded"
                    title="Copy message"
                  >
                    <ClipboardDocumentIcon className="h-4 w-4 text-gray-500 dark:text-gray-400" />
                  </button>
                </div>

                {/* Message Content (Collapsed View) */}
                {!isExpanded && (
                  <div className="px-3 py-2 text-sm text-gray-600 dark:text-gray-300">
                    <div className="truncate">
                      {summary}
                    </div>
                    {blocks.length > 1 && (
                      <span className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                        +{blocks.length - 1} more block{blocks.length > 2 ? 's' : ''}
                      </span>
                    )}
                  </div>
                )}

                {/* Message Content (Expanded View) */}
                {isExpanded && (
                  <div className="px-3 py-2 space-y-2">
                    {/* Parsed Blocks */}
                    <div className="space-y-2">
                      {blocks.map((block, idx) => (
                        <div key={idx} className="text-sm">
                          {ClaudeCodeUtils.guards.isTextBlock(block) && (
                            <div className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                              {block.text}
                            </div>
                          )}
                          {ClaudeCodeUtils.guards.isToolUseBlock(block) && (
                            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded p-2">
                              <div className="flex items-center gap-2 text-blue-700 dark:text-blue-300 font-medium mb-1">
                                <MCPGatewayIcon size={16} className="flex-shrink-0" />
                                <span>Tool: {block.name}</span>
                              </div>
                              {block.input && Object.keys(block.input).length > 0 && (
                                <details className="mt-1">
                                  <summary className="text-xs text-blue-600 dark:text-blue-400 cursor-pointer">
                                    Show inputs
                                  </summary>
                                  <pre className="mt-1 text-xs bg-white dark:bg-gray-900 rounded p-1 overflow-x-auto">
                                    {JSON.stringify(block.input, null, 2)}
                                  </pre>
                                </details>
                              )}
                            </div>
                          )}
                          {ClaudeCodeUtils.guards.isToolResultBlock(block) && (
                            <div className={`${block.is_error ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800' : 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'} border rounded p-2`}>
                              <div className={`flex items-center gap-2 ${block.is_error ? 'text-red-700 dark:text-red-300' : 'text-green-700 dark:text-green-300'} font-medium`}>
                                <span>📋</span>
                                <span>Tool Result{block.is_error ? ' (Error)' : ''}</span>
                              </div>
                              {block.content && (
                                <div className="mt-1 text-xs text-gray-700 dark:text-gray-300">
                                  <pre className="whitespace-pre-wrap">
                                    {typeof block.content === 'string' ? block.content : JSON.stringify(block.content, null, 2)}
                                  </pre>
                                </div>
                              )}
                            </div>
                          )}
                          {ClaudeCodeUtils.guards.isThinkingBlock(block) && (
                            <details className="bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded p-2">
                              <summary className="flex items-center gap-2 text-purple-700 dark:text-purple-300 font-medium cursor-pointer">
                                <span>💭</span>
                                <span>Thinking</span>
                              </summary>
                              <div className="mt-2 text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                                {block.thinking}
                              </div>
                            </details>
                          )}
                        </div>
                      ))}
                    </div>

                    {/* Debug Info */}
                    <details className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                      <summary className="text-xs text-gray-500 dark:text-gray-400 cursor-pointer hover:text-gray-700 dark:hover:text-gray-200">
                        Debug info
                      </summary>
                      <div className="mt-2 space-y-2">
                        {msg.structured_data && (
                          <div>
                            <div className="text-xs font-medium text-gray-500 dark:text-gray-400">
                              Structured Data:
                            </div>
                            <pre className="mt-1 text-xs bg-gray-100 dark:bg-gray-800 rounded p-2 overflow-x-auto">
                              {JSON.stringify(msg.structured_data, null, 2)}
                            </pre>
                          </div>
                        )}
                        <div>
                          <div className="text-xs font-medium text-gray-500 dark:text-gray-400">
                            Raw Message:
                          </div>
                          <pre className="mt-1 text-xs bg-gray-100 dark:bg-gray-800 rounded p-2 overflow-x-auto">
                            {msg.message}
                          </pre>
                        </div>
                      </div>
                    </details>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
