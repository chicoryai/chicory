/**
 * NetworkError Component
 *
 * Displays a user-friendly error message when network failures occur.
 * Follows the application style guide for error presentation.
 */

interface NetworkErrorProps {
  /**
   * Error message to display
   */
  message?: string;

  /**
   * Callback function when user clicks retry button
   */
  onRetry?: () => void;

  /**
   * Optional title for the error message
   */
  title?: string;
}

export function NetworkError({
  message = "Unable to load data. Please check your connection and try again.",
  onRetry,
  title = "Connection Error"
}: NetworkErrorProps) {
  const handleRetry = () => {
    if (onRetry) {
      onRetry();
    } else {
      // Default behavior: reload the page
      window.location.reload();
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50 dark:bg-gray-900 p-4">
      <div className="relative overflow-hidden rounded-lg p-6 max-w-md w-full border border-red-200 dark:border-red-700 bg-red-50 dark:bg-red-900/20 shadow-md">
        <div className="relative z-10">
          {/* Icon */}
          <div className="flex justify-center mb-4">
            <div className="rounded-full bg-red-100 dark:bg-red-900/40 p-3">
              <svg
                className="w-8 h-8 text-red-600 dark:text-red-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M18.364 5.636a9 9 0 010 12.728m0 0l-2.829-2.829m2.829 2.829L21 21M15.536 8.464a5 5 0 010 7.072m0 0l-2.829-2.829m-4.243 2.829a4.978 4.978 0 01-1.414-2.83m-1.414 5.658a9 9 0 01-2.167-9.238m7.824 2.167a1 1 0 111.414 1.414m-1.414-1.414L3 3m8.293 8.293l1.414 1.414"
                />
              </svg>
            </div>
          </div>

          {/* Title */}
          <h3 className="text-lg font-ui font-semibold text-red-900 dark:text-red-100 text-center mb-2">
            {title}
          </h3>

          {/* Message */}
          <p className="text-sm font-body text-red-700 dark:text-red-300 text-center mb-6">
            {message}
          </p>

          {/* Retry Button */}
          <div className="flex justify-center">
            <button
              onClick={handleRetry}
              className="px-6 py-2 bg-purple-400 hover:bg-purple-500 text-white font-ui font-semibold rounded-lg transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-purple-400 focus:ring-offset-2"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Inline NetworkError Component
 *
 * A more compact version for inline error display within components
 */
interface InlineNetworkErrorProps extends NetworkErrorProps {
  /**
   * Whether to show as a banner instead of centered
   */
  inline?: boolean;
}

export function InlineNetworkError({
  message = "Failed to load data. Please try again.",
  onRetry,
  title = "Error",
  inline = true
}: InlineNetworkErrorProps) {
  const handleRetry = () => {
    if (onRetry) {
      onRetry();
    } else {
      window.location.reload();
    }
  };

  if (!inline) {
    return <NetworkError message={message} onRetry={onRetry} title={title} />;
  }

  return (
    <div className="rounded-lg p-4 border border-red-200 dark:border-red-700 bg-red-50 dark:bg-red-900/20 shadow-sm">
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-3 flex-1">
          {/* Icon */}
          <div className="flex-shrink-0">
            <svg
              className="w-5 h-5 text-red-600 dark:text-red-400 mt-0.5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
          </div>

          {/* Content */}
          <div className="flex-1">
            <h4 className="text-sm font-ui font-semibold text-red-900 dark:text-red-100">
              {title}
            </h4>
            <p className="text-sm font-body text-red-700 dark:text-red-300 mt-1">
              {message}
            </p>
          </div>
        </div>

        {/* Retry Button */}
        <button
          onClick={handleRetry}
          className="ml-4 flex-shrink-0 px-3 py-1.5 bg-purple-400 hover:bg-purple-500 text-white text-sm font-ui font-semibold rounded-lg transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-purple-400 focus:ring-offset-2"
        >
          Retry
        </button>
      </div>
    </div>
  );
}
