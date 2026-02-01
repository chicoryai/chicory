import React, { useState } from "react";
import { ClipboardIcon, CheckIcon } from "@heroicons/react/24/outline";
import { twMerge } from "tailwind-merge";
import type { CopyButtonProps } from "~/types/markdown";

/**
 * Reusable copy button component with tooltip and feedback
 * Used across code blocks, tables, and other markdown elements
 * Memoized to prevent unnecessary re-renders
 */
export const CopyButton = React.memo(function CopyButton({ value, className, tooltip = "Copy" }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);
  
  const handleCopy = async (e: React.MouseEvent | React.KeyboardEvent) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    } catch (error) {
      console.error('Failed to copy to clipboard:', error);
      // Fallback for browsers that don't support clipboard API
      fallbackCopyToClipboard(value);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleCopy(e);
    }
    // Ctrl+C keyboard shortcut
    if (e.key === 'c' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      e.stopPropagation();
      handleCopy(e);
    }
  };

  return (
    <button
      type="button"
      className={twMerge(
        "ml-2 p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition relative group",
        "focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900",
        className
      )}
      aria-label={copied ? "Copied!" : tooltip}
      aria-describedby={copied ? undefined : "copy-instructions"}
      onClick={handleCopy}
      onKeyDown={handleKeyDown}
      tabIndex={0}
    >
      {/* Tooltip */}
      {copied ? (
        <span className="absolute -top-7 left-1/2 -translate-x-1/2 bg-green-600 text-white text-xs rounded px-2 py-1 z-10 whitespace-nowrap">
          Copied!
        </span>
      ) : (
        <span 
          id="copy-instructions"
          className="absolute -top-7 left-1/2 -translate-x-1/2 bg-gray-800 text-white text-xs rounded px-2 py-1 z-10 opacity-0 group-hover:opacity-100 group-focus:opacity-100 whitespace-nowrap transition-opacity"
        >
          {tooltip} (Enter or Ctrl+C)
        </span>
      )}
      
      {/* Icon */}
      {copied ? (
        <CheckIcon className="w-4 h-4 text-green-500" />
      ) : (
        <ClipboardIcon className="w-4 h-4 text-gray-600 dark:text-gray-400" />
      )}
    </button>
  );
});

/**
 * Fallback copy method for browsers without clipboard API
 */
function fallbackCopyToClipboard(text: string) {
  const textArea = document.createElement("textarea");
  textArea.value = text;
  textArea.style.position = "fixed";
  textArea.style.left = "-999999px";
  textArea.style.top = "-999999px";
  document.body.appendChild(textArea);
  textArea.focus();
  textArea.select();
  
  try {
    document.execCommand('copy');
  } catch (error) {
    console.error('Fallback copy failed:', error);
  }
  
  document.body.removeChild(textArea);
}

export default CopyButton;