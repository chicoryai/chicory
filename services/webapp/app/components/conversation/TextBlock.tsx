/**
 * TextBlock Component
 * Renders markdown text content for conversation messages
 * Animation is handled by parent wrapper component
 */

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface TextBlockProps {
  text: string;
  isStreaming?: boolean;
}

export function TextBlock({ text }: TextBlockProps) {
  return (
    <div className="prose prose-lg dark:prose-invert max-w-none break-words overflow-hidden prose-headings:font-semibold prose-headings:text-gray-900 dark:prose-headings:text-gray-100 prose-p:text-gray-700 dark:prose-p:text-gray-300 prose-strong:text-gray-900 dark:prose-strong:text-gray-100 prose-ul:list-disc prose-ol:list-decimal prose-li:text-gray-700 dark:prose-li:text-gray-300 prose-code:bg-gray-100 dark:prose-code:bg-gray-800 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-purple-600 dark:prose-code:text-purple-400 prose-pre:bg-gray-100 dark:prose-pre:bg-gray-800 prose-pre:rounded-lg">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
    </div>
  );
}
