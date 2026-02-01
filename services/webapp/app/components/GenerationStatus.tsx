import React from "react";
import PropTypes from "prop-types";

interface GenerationStatusProps {
  status: string;
  disabled?: boolean;
}

/**
 * GenerationStatus displays the current status of the response generation process with a simple spinner animation.
 */
export const GenerationStatus: React.FC<GenerationStatusProps> = ({ status, disabled }) => {
  // No need for state management with the simplified animation
  if (!status || disabled) return null;

  return (
    <div
      className="flex items-center text-left text-sm font-medium min-h-[1.5rem] transition-all duration-500"
      aria-live="polite"
      aria-atomic="true"
      data-testid="generation-status"
    >
      <div className="flex items-center space-x-2">
        <svg className="animate-spin h-4 w-4 text-purple-500 dark:text-lime-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <span className="text-purple-600 dark:text-lime-400">{status}</span>
      </div>
    </div>
  );
};

GenerationStatus.propTypes = {
  status: PropTypes.string.isRequired,
  disabled: PropTypes.bool,
};

export default GenerationStatus;
