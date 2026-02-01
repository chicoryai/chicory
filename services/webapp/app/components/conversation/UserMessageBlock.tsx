/**
 * UserMessageBlock Component
 * Renders user message with bubble styling, left-justified
 */

import ReactMarkdown from "react-markdown";
import type { Message, TextBlock } from "~/services/chicory-conversation.server";

interface UserMessageBlockProps {
  message: Message;
}

function getTextContent(message: Message): string {
  return message.content_blocks
    .filter((block): block is TextBlock => block.type === "text")
    .map((block) => block.text)
    .join("");
}

export function UserMessageBlock({ message }: UserMessageBlockProps) {
  const textContent = getTextContent(message);

  return (
    <div className="flex justify-end mb-6 mt-4">
      <div className="max-w-[85%] rounded-2xl px-5 py-2 bg-whitePurple-100 text-gray-900 dark:bg-purple-900 dark:text-gray-100">
        <div className="prose prose-lg max-w-none dark:prose-invert">
          <ReactMarkdown>{textContent}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
