import { isRouteErrorResponse } from "@remix-run/react";

interface ErrorDisplayProps {
  /**
   * The error to display
   */
  error: unknown;
  /**
   * Optional function to reset the error boundary
   */
  resetErrorBoundary?: () => void;
  /**
   * Optional title to display
   */
  title?: string;
}

/**
 * A reusable component for displaying errors.
 * Can be used in error boundaries or for inline errors.
 */
export function ErrorDisplay({ 
  error, 
  resetErrorBoundary,
  title = "Something went wrong"
}: ErrorDisplayProps) {
  // Extract error message based on error type
  let errorMessage = "An unexpected error occurred";
  
  if (isRouteErrorResponse(error)) {
    errorMessage = `${error.status} ${error.statusText}`;
    if (error.data?.message) {
      errorMessage = error.data.message;
    }
  } else if (error instanceof Error) {
    errorMessage = error.message;
  } else if (typeof error === "string") {
    errorMessage = error;
  }
  
  return (
    <div className="p-6 bg-red-50 dark:bg-red-900/30 rounded-lg border border-red-200 dark:border-red-800">
      <h2 className="text-xl font-semibold text-red-800 dark:text-red-200 mb-2">
        {title}
      </h2>
      <p className="text-red-700 dark:text-red-300 mb-4">
        {errorMessage}
      </p>
      {resetErrorBoundary && (
        <button
          onClick={resetErrorBoundary}
          className="px-4 py-2 bg-red-100 dark:bg-red-800 text-red-800 dark:text-red-200 rounded-md hover:bg-red-200 dark:hover:bg-red-700 transition-colors"
        >
          Try again
        </button>
      )}
    </div>
  );
}
