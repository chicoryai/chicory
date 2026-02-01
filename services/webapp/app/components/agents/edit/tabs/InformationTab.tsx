import { useRef } from "react";
import { CheckIcon, XMarkIcon } from "@heroicons/react/24/outline";

interface InformationTabProps {
  description: string;
  isEditingDescription: boolean;
  descriptionInputRef: React.RefObject<HTMLTextAreaElement>;
  onDescriptionChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  onSaveDescription: () => void;
  onCancelEdit: () => void;
  onEditDescription: () => void;
}

export default function InformationTab({
  description,
  isEditingDescription,
  descriptionInputRef,
  onDescriptionChange,
  onSaveDescription,
  onCancelEdit,
  onEditDescription
}: InformationTabProps) {
  return (
    <div>
      <div className="mb-6">
        <div className="flex justify-between items-start mb-2">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">Description</h3>
          <button
            onClick={onEditDescription}
            className="p-1 text-gray-400 hover:text-gray-500 dark:hover:text-gray-300"
            aria-label="Edit description"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
            </svg>
          </button>
        </div>
        {isEditingDescription ? (
          <div>
            <textarea
              ref={descriptionInputRef}
              value={description}
              onChange={onDescriptionChange}
              rows={4}
              className="block w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500 dark:bg-gray-800 dark:text-white"
              placeholder="Describe what this agent does..."
            />
            <div className="mt-2 flex justify-end space-x-2">
              <button
                onClick={onSaveDescription}
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
          <p className="text-gray-600 dark:text-gray-400">
            {description || "No description provided."}
          </p>
        )}
      </div>
    </div>
  );
}
