import { CheckIcon, XMarkIcon } from "@heroicons/react/24/outline";

interface OutputFormatTabProps {
  outputFormat: string;
  isEditingOutputFormat: boolean;
  onOutputFormatChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  onSaveOutputFormat: () => void;
  onCancelEdit: () => void;
  onEditOutputFormat: () => void;
}

export default function OutputFormatTab({
  outputFormat,
  isEditingOutputFormat,
  onOutputFormatChange,
  onSaveOutputFormat,
  onCancelEdit,
  onEditOutputFormat
}: OutputFormatTabProps) {
  return (
    <div>
      <div className="flex justify-between items-start mb-2">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white">Output Format</h3>
        <button
          onClick={onEditOutputFormat}
          className="p-1 text-gray-400 hover:text-gray-500 dark:hover:text-gray-300"
          aria-label="Edit output format"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
          </svg>
        </button>
      </div>
      {isEditingOutputFormat ? (
        <div>
          <textarea
            value={outputFormat}
            onChange={onOutputFormatChange}
            rows={3}
            className="block w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500 bg-whiteLime-50 dark:bg-gray-800 dark:text-white"
            placeholder="Specify the format for agent responses. Examples:
- 'text' for plain text responses
- 'json' for structured data
- 'markdown' for formatted text
- Custom JSON schema for specific data structures"
          />
          <div className="mt-2 flex justify-end space-x-2">
            <button
              onClick={onSaveOutputFormat}
              className="inline-flex items-center px-3 py-1.5 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
            >
              <CheckIcon className="h-4 w-4 mr-1" />
              Save
            </button>
            <button
              onClick={onCancelEdit}
              className="inline-flex items-center px-3 py-1.5 border border-gray-300 dark:border-gray-700 text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500"
            >
              <XMarkIcon className="h-4 w-4 mr-1" />
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div className="bg-whiteLime-50 dark:bg-gray-800 rounded-md border border-gray-200 dark:border-gray-700 p-4 my-2">
          <p className="text-gray-600 dark:text-gray-400">
            {outputFormat || ""}
          </p>
        </div>
      )}
      <div className="mt-4">
        <h4 className="text-md font-medium text-gray-900 dark:text-white mb-2">About Output Formats</h4>
        <div className="bg-whiteLime-50 dark:bg-gray-800 rounded-md border border-gray-200 dark:border-gray-700 p-4 my-2">
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
            The output format determines how the agent's responses are structured. Common formats include:
          </p>
          <ul className="list-disc list-inside text-sm text-gray-600 dark:text-gray-400 space-y-1">
            <li><strong>text</strong>: Plain text responses</li>
            <li><strong>json</strong>: Structured JSON data</li>
            <li><strong>markdown</strong>: Formatted text with Markdown syntax</li>
            <li><strong>html</strong>: HTML-formatted content</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
