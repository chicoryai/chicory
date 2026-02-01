import { forwardRef } from "react";
/**
 * TurnBlock Component
 * Container for a user message + assistant response pair
 */

import { motion } from "framer-motion";
import type { Message } from "~/services/chicory-conversation.server";
import type { StreamingContentBlock } from "~/hooks/useConversationStream";
import { UserMessageBlock } from "./UserMessageBlock";
import { AssistantMessageBlock } from "./AssistantMessageBlock";

export interface Turn {
  id: string;
  userMessage: Message;
  assistantMessage: Message | null;
}

interface TurnBlockProps {
  turn: Turn;
  streamingContentBlocks?: StreamingContentBlock[];
  isStreaming?: boolean;
  isLatest?: boolean;
}

export const TurnBlock = forwardRef<HTMLDivElement, TurnBlockProps>(function TurnBlock({
  turn,
  streamingContentBlocks = [],
  isStreaming = false,
  isLatest = false,
}, ref) {
  // Only pass streaming blocks to the assistant message if this is the latest turn
  const showStreaming = isLatest && isStreaming;

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
      className={`py-6 first:pt-0 last:pb-0 ${isLatest ? 'min-h-[80vh] flex flex-col justify-start' : ''}`}
    >
      {/* User Message */}
      <UserMessageBlock message={turn.userMessage} />

      {/* Assistant Response */}
      {(turn.assistantMessage || showStreaming) && (
        <AssistantMessageBlock
          message={turn.assistantMessage ?? undefined}
          streamingContentBlocks={showStreaming ? streamingContentBlocks : undefined}
          isStreaming={showStreaming}
        />
      )}
    </motion.div>
  );
});

/**
 * Helper function to group messages into turns
 */
export function groupMessagesIntoTurns(messages: Message[]): Turn[] {
  const turns: Turn[] = [];

  for (let i = 0; i < messages.length; i++) {
    const msg = messages[i];
    if (msg.role === "user") {
      // Find the next assistant message (if any)
      const assistantMsg =
        messages[i + 1]?.role === "assistant" ? messages[i + 1] : null;
      turns.push({
        id: msg.id,
        userMessage: msg,
        assistantMessage: assistantMsg,
      });
      if (assistantMsg) i++; // Skip the assistant message
    }
  }

  return turns;
}
