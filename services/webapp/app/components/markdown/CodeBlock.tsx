import React, { useState, useCallback, useMemo } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { twMerge } from "tailwind-merge";
import { customSyntaxTheme } from "~/styles/syntax-theme";
import { CopyButton } from "./CopyButton";
import type { CodeBlockProps } from "~/types/markdown";

// Performance thresholds
const SYNTAX_HIGHLIGHT_THRESHOLD = 100; // lines
const VIRTUAL_SCROLL_THRESHOLD = 1000; // lines
const SHOW_LINE_NUMBERS_THRESHOLD = 10; // lines

/**
 * Code block component with syntax highlighting and copy functionality
 * Handles both inline and block code rendering
 * Memoized to prevent unnecessary re-renders
 */
export const CodeBlock = React.memo(function CodeBlock(props: CodeBlockProps) {
  const { className, children, inline } = props;
  const code = String(children).replace(/\n$/, ''); // Remove trailing newline
  
  // Heuristic: treat as block if className starts with 'language-' or code contains a newline
  const isBlock = !inline && ((className && className.startsWith('language-')) || code.includes('\n'));

  if (!isBlock) {
    // Inline code
    return <InlineCode>{code}</InlineCode>;
  }

  // Performance calculations
  const lines = useMemo(() => code.split('\n'), [code]);
  const lineCount = lines.length;
  const language = useMemo(() => {
    const match = /language-(\w+)/.exec(className || "");
    return match ? match[1] : undefined;
  }, [className]);

  // Performance optimizations based on content size
  const shouldHighlight = lineCount <= SYNTAX_HIGHLIGHT_THRESHOLD;
  const shouldShowLineNumbers = lineCount > SHOW_LINE_NUMBERS_THRESHOLD;
  const needsVirtualization = lineCount > VIRTUAL_SCROLL_THRESHOLD;

  // For very large code blocks, show a performance warning and option to enable highlighting
  if (needsVirtualization) {
    return <LargeCodeBlock code={code} language={language} />;
  }

  // For medium-large code blocks without syntax highlighting
  if (!shouldHighlight) {
    return <PlainCodeBlock code={code} language={language} shouldShowLineNumbers={shouldShowLineNumbers} />;
  }

  // Standard syntax-highlighted code block
  const codeBlockId = `code-block-${Math.random().toString(36).substr(2, 9)}`;
  
  return (
    <div className="relative group my-4" role="region" aria-labelledby={`${codeBlockId}-header`}>
      <div 
        id={`${codeBlockId}-header`}
        className="flex items-center justify-between bg-gray-800 dark:bg-gray-800 text-gray-300 px-3 py-1 text-xs rounded-t-lg"
      >
        <span aria-label={`Code language: ${language || 'plain text'}`}>
          {language || 'text'}
        </span>
        <div className="flex items-center space-x-2">
          <span className="text-gray-500" aria-label={`${lineCount} lines of code`}>
            {lineCount} lines
          </span>
          <CopyButton 
            value={code} 
            className="opacity-0 group-hover:opacity-100 transition-opacity" 
            tooltip="Copy code block" 
          />
        </div>
      </div>
      <div
        role="code"
        aria-label={`${language || 'Code'} snippet with ${lineCount} lines${shouldShowLineNumbers ? ', line numbers shown' : ''}`}
        tabIndex={0}
        className="focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900 rounded-b-lg"
      >
        <SyntaxHighlighter
          style={customSyntaxTheme}
          language={language}
          PreTag="div"
          className={twMerge(
            "rounded-t-none text-sm overflow-x-auto bg-gray-900 dark:bg-gray-900 text-gray-100 font-mono",
            "scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-800",
            className
          )}
          showLineNumbers={shouldShowLineNumbers}
          wrapLines={false}
          customStyle={{
            margin: 0,
            padding: '1rem',
            borderTopLeftRadius: 0,
            borderTopRightRadius: 0,
          }}
        >
          {code}
        </SyntaxHighlighter>
      </div>
    </div>
  );
});

/**
 * Inline code component (memoized)
 */
const InlineCode = React.memo(function InlineCode({ children, ...props }: React.HTMLAttributes<HTMLElement>) {
  return (
    <code
      className="inline-flex min-w-0 font-mono text-sm dark:bg-gray-800 bg-white text-gray-600 border border-gray-200 dark:border-gray-700 rounded-md px-2 py-0.5 my-1 dark:text-lime-400 font-semibold align-middle"
      {...props}
    >
      {children}
    </code>
  );
});

/**
 * Plain code block without syntax highlighting for medium-large code
 */
const PlainCodeBlock = React.memo(function PlainCodeBlock({ 
  code, 
  language, 
  shouldShowLineNumbers 
}: { 
  code: string; 
  language?: string; 
  shouldShowLineNumbers: boolean; 
}) {
  const [enableHighlighting, setEnableHighlighting] = useState(false);
  const lineCount = code.split('\n').length;

  if (enableHighlighting) {
    // User opted into syntax highlighting for large code
    return (
      <div className="relative group my-4">
        <div className="flex items-center justify-between bg-yellow-800 text-yellow-100 px-3 py-1 text-xs rounded-t-lg">
          <span>{language || 'text'} (Performance mode disabled)</span>
          <div className="flex items-center space-x-2">
            <span>{lineCount} lines</span>
            <button
              onClick={() => setEnableHighlighting(false)}
              className="text-yellow-200 hover:text-yellow-100 underline"
            >
              Disable highlighting
            </button>
            <CopyButton 
              value={code} 
              className="opacity-0 group-hover:opacity-100 transition-opacity" 
              tooltip="Copy code" 
            />
          </div>
        </div>
        <SyntaxHighlighter
          style={customSyntaxTheme}
          language={language}
          PreTag="div"
          className="rounded-t-none text-sm overflow-x-auto bg-gray-900 font-mono scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-800"
          showLineNumbers={shouldShowLineNumbers}
          wrapLines={false}
          customStyle={{
            margin: 0,
            padding: '1rem',
            borderTopLeftRadius: 0,
            borderTopRightRadius: 0,
          }}
        >
          {code}
        </SyntaxHighlighter>
      </div>
    );
  }

  return (
    <div className="relative group my-4">
      <div className="flex items-center justify-between bg-gray-700 text-gray-300 px-3 py-1 text-xs rounded-t-lg">
        <span>{language || 'text'} (Plain text mode for performance)</span>
        <div className="flex items-center space-x-2">
          <span>{lineCount} lines</span>
          <button
            onClick={() => setEnableHighlighting(true)}
            className="text-blue-400 hover:text-blue-300 underline"
            aria-label="Enable syntax highlighting"
          >
            Enable highlighting
          </button>
          <CopyButton 
            value={code} 
            className="opacity-0 group-hover:opacity-100 transition-opacity" 
            tooltip="Copy code" 
          />
        </div>
      </div>
      <pre className="rounded-t-none text-sm overflow-x-auto p-4 bg-gray-900 text-gray-100 font-mono border-gray-700 scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-800">
        <code>{code}</code>
      </pre>
    </div>
  );
});

/**
 * Large code block with virtualization for very large content
 */
const LargeCodeBlock = React.memo(function LargeCodeBlock({ 
  code, 
  language 
}: { 
  code: string; 
  language?: string; 
}) {
  const [showAll, setShowAll] = useState(false);
  const [enableHighlighting, setEnableHighlighting] = useState(false);
  const lines = useMemo(() => code.split('\n'), [code]);
  const lineCount = lines.length;
  
  // Show first 50 lines by default
  const PREVIEW_LINES = 50;
  const previewCode = useMemo(() => 
    lines.slice(0, PREVIEW_LINES).join('\n'), 
    [lines]
  );

  if (showAll && enableHighlighting) {
    // Full content with syntax highlighting (warning: may be slow)
    return (
      <div className="relative group my-4">
        <div className="flex items-center justify-between bg-red-800 text-red-100 px-3 py-1 text-xs rounded-t-lg">
          <span>⚠️ {language || 'text'} - Large file with highlighting (may be slow)</span>
          <div className="flex items-center space-x-2">
            <span>{lineCount} lines</span>
            <button
              onClick={() => setShowAll(false)}
              className="text-red-200 hover:text-red-100 underline"
            >
              Show preview
            </button>
            <CopyButton 
              value={code} 
              className="opacity-0 group-hover:opacity-100 transition-opacity" 
              tooltip="Copy all code" 
            />
          </div>
        </div>
        <div className="max-h-96 overflow-y-auto scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-800">
          <SyntaxHighlighter
            style={customSyntaxTheme}
            language={language}
            PreTag="div"
            className="rounded-t-none text-sm bg-gray-900 font-mono"
            showLineNumbers={true}
            wrapLines={false}
            customStyle={{
              margin: 0,
              padding: '1rem',
              borderTopLeftRadius: 0,
              borderTopRightRadius: 0,
            }}
          >
            {code}
          </SyntaxHighlighter>
        </div>
      </div>
    );
  }

  if (showAll) {
    // Full content without syntax highlighting
    return (
      <div className="relative group my-4">
        <div className="flex items-center justify-between bg-gray-700 text-gray-300 px-3 py-1 text-xs rounded-t-lg">
          <span>{language || 'text'} - Full content</span>
          <div className="flex items-center space-x-2">
            <span>{lineCount} lines</span>
            <button
              onClick={() => setEnableHighlighting(true)}
              className="text-blue-400 hover:text-blue-300 underline"
            >
              Enable highlighting
            </button>
            <button
              onClick={() => setShowAll(false)}
              className="text-gray-400 hover:text-gray-300 underline"
            >
              Show preview
            </button>
            <CopyButton 
              value={code} 
              className="opacity-0 group-hover:opacity-100 transition-opacity" 
              tooltip="Copy all code" 
            />
          </div>
        </div>
        <div className="max-h-96 overflow-y-auto scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-800">
          <pre className="rounded-t-none text-sm p-4 bg-gray-900 text-gray-100 font-mono">
            <code>{code}</code>
          </pre>
        </div>
      </div>
    );
  }

  // Preview mode (default for large files)
  return (
    <div className="relative group my-4">
      <div className="flex items-center justify-between bg-amber-800 text-amber-100 px-3 py-1 text-xs rounded-t-lg">
        <span>📄 {language || 'text'} - Large file preview</span>
        <div className="flex items-center space-x-2">
          <span>{lineCount} lines (showing {PREVIEW_LINES})</span>
          <button
            onClick={() => setShowAll(true)}
            className="text-amber-200 hover:text-amber-100 underline"
          >
            Show all
          </button>
          <CopyButton 
            value={code} 
            className="opacity-0 group-hover:opacity-100 transition-opacity" 
            tooltip="Copy all code" 
          />
        </div>
      </div>
      <SyntaxHighlighter
        style={customSyntaxTheme}
        language={language}
        PreTag="div"
        className="rounded-t-none text-sm overflow-x-auto bg-gray-900 font-mono scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-800"
        showLineNumbers={true}
        wrapLines={false}
        customStyle={{
          margin: 0,
          padding: '1rem',
          borderTopLeftRadius: 0,
          borderTopRightRadius: 0,
        }}
      >
        {previewCode}
      </SyntaxHighlighter>
      <div className="bg-gradient-to-t from-gray-900 to-transparent absolute bottom-0 left-0 right-0 h-12 flex items-end justify-center pb-2">
        <button
          onClick={() => setShowAll(true)}
          className="bg-gray-800 hover:bg-gray-700 text-gray-300 px-3 py-1 rounded text-xs transition-colors"
        >
          ... {lineCount - PREVIEW_LINES} more lines
        </button>
      </div>
    </div>
  );
});

export default CodeBlock;