import type { ChatMessage } from '~/services/chicory.server';
import { twMerge } from 'tailwind-merge';
import type { User } from '@supabase/supabase-js';
import MarkdownRenderer from './MarkdownRenderer';

export interface ChatMessageItemProps {
  message: ChatMessage;
  user: string | null;
  isStreaming?: boolean;
}

/**
 * Component for displaying a single chat message with formatted timestamp
 */
export function ChatMessageItem({ message, user, isStreaming }: ChatMessageItemProps) {
  // Format the date in a more readable format
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      month: 'numeric',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    });
  };

  // Check if the message is from the user
  const isUserMessage = message.role === 'MessageRole.USER';
  const isAssistantMessage = message.role === 'MessageRole.ASSISTANT';

  // Get the first initial for user avatar (default to 'U' if no name is available)
  const getInitial = () => {
    // Try to get name from message or use "User" as default
    const name = user || "User";
    return name.charAt(0).toUpperCase();
  };

  // Get the content to display (let MarkdownRenderer handle processing for assistant messages)
  const contentToDisplay = message.content || message.response || '';

  return (
    <div className={twMerge(
      // Ensure max width matches input area (max-w-3xl + center + min-w-0)
      "mb-4 p-3 rounded-lg w-full flex justify-center",
      isUserMessage ? "dark:bg-gray-800 bg-gray-200" : ""
    )}>
      {isUserMessage && (
        <div className="flex-shrink-0 mr-3">
          <div className="w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center text-white font-medium">
            {getInitial()}
          </div>
        </div>
      )}
      <div className="flex-1 w-full max-w-3xl min-w-0">
        <div className="dark:text-white text-gray-800">
          {isAssistantMessage ? (
            <MarkdownRenderer 
              content={contentToDisplay}
              variant="chat"
              isStreaming={isStreaming}
            />
          ) : (
            <div className="whitespace-pre-wrap">{contentToDisplay}</div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ChatMessageItem;
