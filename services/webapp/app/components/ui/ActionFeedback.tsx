import React from "react";
import { CheckCircleIcon, XCircleIcon } from "@heroicons/react/24/solid";

type FeedbackType = "success" | "error" | "info" | "warning";

interface ActionFeedbackProps {
  type: FeedbackType;
  message: string;
  onDismiss?: () => void;
}

/**
 * Displays feedback messages for user actions
 * Supports different types of messages: success, error, info, warning
 */
export function ActionFeedback({ type, message, onDismiss }: ActionFeedbackProps) {
  const getStyles = () => {
    switch (type) {
      case "success":
        return {
          bg: "bg-green-50 dark:bg-green-900",
          border: "border-green-200 dark:border-green-800",
          text: "text-green-800 dark:text-green-200",
          icon: <CheckCircleIcon className="h-5 w-5 text-green-500 dark:text-green-400" />
        };
      case "error":
        return {
          bg: "bg-red-50 dark:bg-red-900",
          border: "border-red-200 dark:border-red-800",
          text: "text-red-800 dark:text-red-200",
          icon: <XCircleIcon className="h-5 w-5 text-red-500 dark:text-red-400" />
        };
      case "warning":
        return {
          bg: "bg-yellow-50 dark:bg-yellow-900",
          border: "border-yellow-200 dark:border-yellow-800",
          text: "text-yellow-800 dark:text-yellow-200",
          icon: <XCircleIcon className="h-5 w-5 text-yellow-500 dark:text-yellow-400" />
        };
      case "info":
      default:
        return {
          bg: "bg-blue-50 dark:bg-blue-900",
          border: "border-blue-200 dark:border-blue-800",
          text: "text-blue-800 dark:text-blue-200",
          icon: <CheckCircleIcon className="h-5 w-5 text-blue-500 dark:text-blue-400" />
        };
    }
  };

  const styles = getStyles();

  return (
    <div className={`mb-6 p-4 ${styles.bg} border ${styles.border} rounded-md flex items-start`}>
      <div className="flex-shrink-0 mr-3">
        {styles.icon}
      </div>
      <div className="flex-1 min-w-0">
        <p className={`text-sm ${styles.text}`}>
          {message}
        </p>
      </div>
      {onDismiss && (
        <div className="ml-3 flex-shrink-0">
          <button
            type="button"
            className={`inline-flex rounded-md p-1.5 ${styles.text} hover:bg-opacity-20 hover:bg-gray-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500`}
            onClick={onDismiss}
          >
            <span className="sr-only">Dismiss</span>
            <XCircleIcon className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>
      )}
    </div>
  );
}
