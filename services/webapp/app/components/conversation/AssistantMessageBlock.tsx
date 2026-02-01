/**
 * AssistantMessageBlock Component
 * Renders assistant message content blocks (text, thinking, tool_use)
 * Left-justified, no bubble styling
 */

import { motion } from "framer-motion";
import type { Message, ContentBlock } from "~/services/chicory-conversation.server";
import type { StreamingContentBlock } from "~/hooks/useConversationStream";
import { TextBlock } from "./TextBlock";
import { ThinkingDropdown } from "./ThinkingDropdown";
import { ToolUseDropdown } from "./ToolUseDropdown";
import {
  textRevealVariants,
  textRevealBlurVariants,
  easeInVariants,
  ANIMATION_DURATION,
} from "~/components/animations/transitions";

interface AssistantMessageBlockProps {
  message?: Message;
  streamingContentBlocks?: StreamingContentBlock[];
  isStreaming?: boolean;
}

/**
 * Generate a stable React key for a content block.
 * - Streaming blocks have IDs on all types
 * - Persisted blocks only have IDs on tool_use, so we use type+index for others
 */
function getBlockKey(block: ContentBlock | StreamingContentBlock, index: number): string {
  // Check if block has an id property (streaming blocks always do, persisted tool_use does)
  if ('id' in block && block.id) {
    return `${block.type}-${block.id}`;
  }
  // Fallback for persisted text/thinking blocks that don't have IDs
  return `${block.type}-${index}`;
}

function ContentBlockRenderer({
  block,
  isStreamingBlock = false,
}: {
  block: ContentBlock | StreamingContentBlock;
  isStreamingBlock?: boolean;
}) {
  if (block.type === "text") {
    return <TextBlock text={block.text} isStreaming={isStreamingBlock} />;
  }

  if (block.type === "thinking") {
    return <ThinkingDropdown thinking={block.thinking} signature={block.signature} isStreaming={isStreamingBlock} />;
  }

  if (block.type === "tool_use") {
    // For streaming blocks, tool is executing if output is null
    // For persisted blocks, tool is always complete (not executing)
    const isExecuting = isStreamingBlock && block.output === null;
    // active_description is available on both streaming and persisted blocks
    const activeDescription = 'active_description' in block ? block.active_description : block.name;
    return (
      <ToolUseDropdown
        id={block.id}
        name={block.name}
        input={block.input}
        output={block.output}
        isError={block.is_error}
        isExecuting={isExecuting}
        isStreaming={isStreamingBlock}
        activeDescription={activeDescription}
      />
    );
  }

  return null;
}

export function AssistantMessageBlock({
  message,
  streamingContentBlocks = [],
  isStreaming = false,
}: AssistantMessageBlockProps) {
  // Determine which content blocks to render
  // If we're streaming and have streaming blocks, prefer those over empty persisted message content
  // This handles the case where message exists with status="processing" but no content yet
  const messageHasContent = message?.content_blocks && message.content_blocks.length > 0;
  const useStreamingBlocks = isStreaming && streamingContentBlocks.length > 0 && !messageHasContent;
  const blocks = useStreamingBlocks ? streamingContentBlocks : (message?.content_blocks ?? streamingContentBlocks);
  const hasContent = blocks.length > 0;

  return (
    <div className="mb-3">
      <motion.div
        variants={isStreaming ? textRevealVariants : easeInVariants}
        initial="hidden"
        animate="visible"
        className="relative text-gray-900 dark:text-gray-100"
      >
        {hasContent ? (
          <div className="space-y-4">
            {blocks.map((block, idx) => (
              <ContentBlockRenderer
                key={getBlockKey(block, idx)}
                block={block}
                isStreamingBlock={useStreamingBlocks}
              />
            ))}
          </div>
        ) : isStreaming ? (
          // Typing indicator when streaming but no content yet
          <div className="flex items-center gap-1 py-2">
            <div
              className="w-2 h-2 rounded-full bg-gray-400 animate-bounce"
              style={{ animationDelay: "0ms" }}
            />
            <div
              className="w-2 h-2 rounded-full bg-gray-400 animate-bounce"
              style={{ animationDelay: "150ms" }}
            />
            <div
              className="w-2 h-2 rounded-full bg-gray-400 animate-bounce"
              style={{ animationDelay: "300ms" }}
            />
          </div>
        ) : null}

        {/* Status indicators - only show when not actively streaming content */}
        {message?.status === "processing" && !isStreaming && (
          <div className="mt-2 flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
            <div className="animate-pulse">Processing...</div>
          </div>
        )}
        {message?.status === "failed" && (
          <div className="mt-2 text-xs text-red-500">Failed to process</div>
        )}

        {/* Bottom blur overlay that fades out during streaming reveal */}
        {isStreaming && hasContent && (
          <motion.div
            variants={textRevealBlurVariants}
            initial="visible"
            animate="hidden"
            className="absolute bottom-0 left-0 right-0 h-16 pointer-events-none"
            style={{
              background: "linear-gradient(to top, rgb(255 255 255) 0%, rgb(255 255 255 / 0.8) 50%, transparent 100%)",
              backdropFilter: "blur(8px)",
              WebkitBackdropFilter: "blur(8px)",
            }}
          />
        )}
        {/* Dark mode blur overlay */}
        {isStreaming && hasContent && (
          <motion.div
            variants={textRevealBlurVariants}
            initial="visible"
            animate="hidden"
            className="absolute bottom-0 left-0 right-0 h-16 pointer-events-none dark:block hidden"
            style={{
              background: "linear-gradient(to top, rgb(17 24 39) 0%, rgb(17 24 39 / 0.8) 50%, transparent 100%)",
              backdropFilter: "blur(8px)",
              WebkitBackdropFilter: "blur(8px)",
            }}
          />
        )}
      </motion.div>
    </div>
  );
}
