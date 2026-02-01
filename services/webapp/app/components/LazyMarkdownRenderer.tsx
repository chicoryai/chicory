import React, { useState, useRef, useEffect, useCallback } from 'react';
import { twMerge } from 'tailwind-merge';
import MarkdownRenderer from './MarkdownRenderer';
import type { MarkdownRendererProps } from '~/types/markdown';

interface LazyMarkdownRendererProps extends MarkdownRendererProps {
  /** Threshold for when to start lazy loading (characters) */
  lazyThreshold?: number;
  /** Whether to use intersection observer for viewport-based loading */
  useIntersectionObserver?: boolean;
  /** Custom loading component */
  loadingComponent?: React.ReactNode;
}

/**
 * Lazy loading wrapper for MarkdownRenderer
 * Optimizes performance for long conversations and large content
 */
export function LazyMarkdownRenderer({
  content,
  lazyThreshold = 5000, // 5KB threshold
  useIntersectionObserver = true,
  loadingComponent,
  className,
  ...props
}: LazyMarkdownRendererProps) {
  const [isLoaded, setIsLoaded] = useState(false);
  const [isInView, setIsInView] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Check if content should be lazy loaded
  const shouldLazyLoad = content.length > lazyThreshold;

  // Intersection Observer for viewport-based loading
  useEffect(() => {
    if (!shouldLazyLoad || !useIntersectionObserver || !containerRef.current) {
      setIsInView(true);
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        if (entry.isIntersecting) {
          setIsInView(true);
          observer.disconnect();
        }
      },
      {
        root: null,
        rootMargin: '100px', // Start loading 100px before entering viewport
        threshold: 0,
      }
    );

    observer.observe(containerRef.current);

    return () => observer.disconnect();
  }, [shouldLazyLoad, useIntersectionObserver]);

  // Load content when in view or on user interaction
  const loadContent = useCallback(() => {
    setIsLoaded(true);
  }, []);

  // Auto-load if in view and should lazy load
  useEffect(() => {
    if (isInView && shouldLazyLoad && !isLoaded) {
      // Small delay to prevent loading during fast scrolling
      const timer = setTimeout(loadContent, 100);
      return () => clearTimeout(timer);
    }
  }, [isInView, shouldLazyLoad, isLoaded, loadContent]);

  // If content is small, render immediately
  if (!shouldLazyLoad) {
    return <MarkdownRenderer content={content} className={className} {...props} />;
  }

  // If loaded, render the full markdown
  if (isLoaded) {
    return <MarkdownRenderer content={content} className={className} {...props} />;
  }

  // Show loading/preview state
  return (
    <div 
      ref={containerRef}
      className={twMerge("relative", className)}
    >
      {loadingComponent || <DefaultLoadingComponent content={content} onLoad={loadContent} />}
    </div>
  );
}

/**
 * Default loading component with content preview
 */
function DefaultLoadingComponent({ 
  content, 
  onLoad 
}: { 
  content: string; 
  onLoad: () => void; 
}) {
  // Show a preview of the content (first 200 characters)
  const preview = content.slice(0, 200);
  const totalSize = new Blob([content]).size;
  const formattedSize = formatBytes(totalSize);
  
  return (
    <div className="border border-gray-300 dark:border-gray-600 rounded-lg p-4 bg-gray-50 dark:bg-gray-800">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <div className="w-4 h-4 bg-gray-400 dark:bg-gray-500 rounded animate-pulse"></div>
          <span className="text-sm text-gray-600 dark:text-gray-400">
            Large content ({formattedSize})
          </span>
        </div>
        <button
          onClick={onLoad}
          className="px-3 py-1 bg-purple-600 hover:bg-purple-700 text-white text-sm rounded transition-colors focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800"
          aria-label="Load full content"
        >
          Load content
        </button>
      </div>
      
      <div className="text-sm text-gray-700 dark:text-gray-300 font-mono bg-white dark:bg-gray-900 p-3 rounded border">
        <div className="whitespace-pre-wrap line-clamp-3">
          {preview}
          {content.length > 200 && (
            <span className="text-gray-500 dark:text-gray-400">...</span>
          )}
        </div>
      </div>
      
      <div className="mt-3 text-xs text-gray-500 dark:text-gray-400 text-center">
        Click "Load content" or scroll to view full markdown
      </div>
    </div>
  );
}

/**
 * Format bytes to human readable string
 */
function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  
  const k = 1024;
  const sizes = ['B', 'KB', 'MB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

export default LazyMarkdownRenderer;