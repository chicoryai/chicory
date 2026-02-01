import React, { useEffect, useRef } from "react";
import { MarkdownRenderer } from "~/components/MarkdownRenderer";
import { ThinkingBlock } from "~/components/improved/ThinkingBlock";
import { ToolExecutionCard } from "~/components/improved/ToolExecutionCard";
import type { StreamingMessage } from "~/types/workzone";

interface StreamingMessageListProps {
  messages: StreamingMessage[];
  autoScroll?: boolean;
}

/**
 * Component for displaying streaming messages as they arrive
 * Shows ThinkingBlocks, TextBlocks, and ToolExecutionMessages
 */
export const StreamingMessageList: React.FC<StreamingMessageListProps> = ({
  messages,
  autoScroll = true
}) => {
  const listRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (autoScroll && listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages, autoScroll]);

  if (messages.length === 0) {
    return null;
  }

  return (
    <div
      ref={listRef}
      className="space-y-4 overflow-y-auto max-h-[calc(100vh-300px)]"
    >
      {messages.map((message, index) => {
        const key = `message-${message.timestamp}-${index}`;

        // Thinking block
        if (message.type === 'thinking') {
          return (
            <ThinkingBlock
              key={key}
              content={message.thinking}
              index={index}
            />
          );
        }

        // Text block
        if (message.type === 'text') {
          return (
            <div key={key} className="animate-slide-in opacity-0" style={{
              animationDelay: `${index * 50}ms`,
              animationFillMode: 'forwards'
            }}>
              <MarkdownRenderer
                content={message.text}
                variant="task"
                className="prose prose-sm max-w-none text-gray-900 dark:text-gray-100"
              />
            </div>
          );
        }

        // Tool execution (tool use + result)
        if (message.type === 'tool') {
          return (
            <ToolExecutionCard
              key={key}
              toolName={message.toolName}
              toolId={message.toolId}
              input={message.input}
              output={message.result}
              isError={message.isError}
              index={index}
            />
          );
        }

        return null;
      })}
    </div>
  );
};
