import React, { Component, ReactNode } from 'react';
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';
import type { MarkdownErrorBoundaryProps, MarkdownErrorBoundaryState } from '~/types/markdown';

/**
 * Error boundary component for markdown rendering
 * Provides graceful fallback when markdown processing fails
 */
export class MarkdownErrorBoundary extends Component<MarkdownErrorBoundaryProps, MarkdownErrorBoundaryState> {
  constructor(props: MarkdownErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): MarkdownErrorBoundaryState {
    return {
      hasError: true,
      error
    };
  }

  componentDidCatch(error: Error, errorInfo: any) {
    console.error('Markdown rendering error:', error, errorInfo);
    
    // Call optional error handler
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
  }

  private handleRetry = () => {
    this.setState({ hasError: false, error: undefined });
  };

  render() {
    if (this.state.hasError) {
      // Custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default fallback UI
      return (
        <div className="border border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-700 rounded-lg p-4 my-2">
          <div className="flex items-start">
            <ExclamationTriangleIcon className="h-5 w-5 text-red-500 dark:text-red-400 mt-0.5 mr-3 flex-shrink-0" />
            <div className="flex-1">
              <h3 className="text-sm font-medium text-red-800 dark:text-red-200">
                Content Rendering Error
              </h3>
              <p className="text-sm text-red-700 dark:text-red-300 mt-1">
                There was an error rendering this content. The content may contain invalid formatting.
              </p>
              {process.env.NODE_ENV === 'development' && this.state.error && (
                <details className="mt-2">
                  <summary className="text-xs text-red-600 dark:text-red-400 cursor-pointer">
                    Technical Details
                  </summary>
                  <pre className="text-xs text-red-600 dark:text-red-400 mt-1 whitespace-pre-wrap">
                    {this.state.error.message}
                  </pre>
                </details>
              )}
              <button
                onClick={this.handleRetry}
                className="mt-2 text-sm text-red-800 dark:text-red-200 underline hover:no-underline focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900 rounded"
              >
                Try again
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * Hook for functional component error handling
 * Use with React.Suspense for better UX
 */
export function useMarkdownErrorHandler() {
  const [error, setError] = React.useState<Error | null>(null);

  const resetError = React.useCallback(() => {
    setError(null);
  }, []);

  const handleError = React.useCallback((error: Error) => {
    setError(error);
  }, []);

  if (error) {
    throw error; // Will be caught by nearest error boundary
  }

  return { handleError, resetError };
}

export default MarkdownErrorBoundary;