import React from 'react';
import { twMerge } from 'tailwind-merge';

interface SkipLinkProps {
  targetId: string;
  children: React.ReactNode;
  className?: string;
}

/**
 * Skip link component for accessibility
 * Allows keyboard users to skip over large content blocks
 */
export function SkipLink({ targetId, children, className }: SkipLinkProps) {
  const handleSkip = (e: React.MouseEvent | React.KeyboardEvent) => {
    e.preventDefault();
    const target = document.getElementById(targetId);
    if (target) {
      target.focus();
      target.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      handleSkip(e);
    }
  };

  return (
    <button
      onClick={handleSkip}
      onKeyDown={handleKeyDown}
      className={twMerge(
        "sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 z-50",
        "bg-purple-600 text-white px-3 py-2 rounded-md text-sm font-medium",
        "focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2",
        "hover:bg-purple-700 transition-colors",
        className
      )}
      aria-label={`Skip ${typeof children === 'string' ? children.toLowerCase() : 'content'}`}
    >
      {children}
    </button>
  );
}

export default SkipLink;