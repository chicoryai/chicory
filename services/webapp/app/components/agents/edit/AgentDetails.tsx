import { useRef, useState } from "react";
import { CheckIcon, XMarkIcon, PowerIcon } from "@heroicons/react/24/outline";
import { Form, useSubmit } from "@remix-run/react";

interface AgentDetailsProps {
  name: string;
  description?: string;
  taskCount: number;
  status: string;
  createdAt: string;
  id: string;
  projectId: string;
  capabilities?: string[];
  isEditingName: boolean;
  isEditingDescription: boolean;
  nameInputRef: React.RefObject<HTMLInputElement>;
  descriptionInputRef: React.RefObject<HTMLTextAreaElement>;
  onNameChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onDescriptionChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  onSaveName: () => void;
  onSaveDescription: () => void;
  onCancelEdit: () => void;
  onEditName: () => void;
  onEditDescription: () => void;
  onStatusChange?: (newStatus: string) => void;
  isUpdatingStatus?: boolean;
}

export default function AgentDetails({
  name,
  description,
  taskCount,
  status,
  createdAt,
  id,
  projectId,
  capabilities = [],
  isEditingName,
  isEditingDescription,
  nameInputRef,
  descriptionInputRef,
  onNameChange,
  onDescriptionChange,
  onSaveName,
  onSaveDescription,
  onCancelEdit,
  onEditName,
  onEditDescription,
  onStatusChange,
  isUpdatingStatus = false
}: AgentDetailsProps) {
  const submit = useSubmit();
  
  const handleToggleStatus = () => {
    const newState = status === 'enabled' ? 'disabled' : 'enabled';
    
    const formData = new FormData();
    formData.append('intent', 'updateStatus');
    formData.append('state', newState);
    
    submit(formData, { method: 'post' });
    
    if (onStatusChange) {
      onStatusChange(newState);
    }
  };
  
  return (
    <div className="dark:bg-gray-900 rounded-lg border border-gray-300 dark:border-gray-700 p-6 md:col-span-1 h-fit self-start relative">
      {/* Power toggle button */}
      <button
        onClick={handleToggleStatus}
        disabled={isUpdatingStatus}
        className={`absolute top-4 right-4 p-2 rounded-full transition-colors ${isUpdatingStatus
          ? 'bg-gray-100 text-gray-400 dark:bg-gray-800 dark:text-gray-500'
          : status === 'enabled'
            ? 'bg-green-200 text-green-600 hover:bg-green-200 dark:bg-green-900 dark:text-green-400 dark:hover:bg-green-800'
            : 'bg-red-100 text-red-600 hover:bg-red-200 dark:bg-red-900 dark:text-red-400 dark:hover:bg-red-800'
        }`}
        aria-label={status === 'enabled' ? 'Disable agent' : 'Enable agent'}
      >
        {isUpdatingStatus ? (
          <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        ) : (
          <PowerIcon className="h-5 w-5" />
        )}
      </button>
      <div className="space-y-6">
        <div>
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Name</h3>
          {isEditingName ? (
            <div className="mt-1">
              <input
                ref={nameInputRef}
                type="text"
                value={name}
                onChange={onNameChange}
                className="block w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500 dark:bg-gray-800 dark:text-white"
                placeholder="Agent name"
              />
              <div className="mt-2 flex space-x-2">
                <button
                  onClick={onSaveName}
                  className="inline-flex items-center px-2 py-1 border border-transparent text-xs font-medium rounded shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                  disabled={!name.trim()}
                >
                  <CheckIcon className="h-3 w-3 mr-1" />
                  Save
                </button>
                <button
                  onClick={onCancelEdit}
                  className="inline-flex items-center px-2 py-1 border border-gray-300 dark:border-gray-700 text-xs font-medium rounded text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
                >
                  <XMarkIcon className="h-3 w-3 mr-1" />
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="mt-1 flex items-center">
              <p className="text-lg font-medium text-gray-900 dark:text-white">{name}</p>
              <button
                onClick={onEditName}
                className="p-1 text-gray-400 hover:text-gray-500 dark:hover:text-gray-300"
                aria-label="Edit agent name"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                </svg>
              </button>
            </div>
          )}
        </div>
        
        <div>
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Tasks</h3>
          <p className="mt-1 text-lg font-medium text-gray-900 dark:text-white">{taskCount}</p>
        </div>
        
        <div>
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Status</h3>
          <div className="mt-1 flex items-center">
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
              status === 'enabled' 
                ? 'bg-green-200 text-green-800 dark:bg-green-900 dark:text-green-200' 
                : 'bg-gray-200 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
            }`}>
              {status === 'enabled' ? 'Enabled' : 'Disabled'}
            </span>
          </div>
        </div>
        
        <div>
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Created</h3>
          <p className="mt-1 text-sm text-gray-900 dark:text-gray-200">
            {new Date(createdAt).toLocaleDateString()}
          </p>
        </div>
        
        {capabilities && capabilities.length > 0 && (
          <div>
            <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Capabilities</h3>
            <div className="mt-2 flex flex-wrap gap-2">
              {capabilities.map((capability, index) => (
                <span 
                  key={index}
                  className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200"
                >
                  {capability}
                </span>
              ))}
            </div>
          </div>
        )}
        
        <div>
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Description</h3>
          {isEditingDescription ? (
            <div className="mt-1">
              <textarea
                ref={descriptionInputRef}
                value={description}
                onChange={onDescriptionChange}
                className="block w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500 dark:bg-gray-800 dark:text-white"
                placeholder="Agent description"
                rows={3}
              />
              <div className="mt-2 flex space-x-2">
                <button
                  onClick={onSaveDescription}
                  className="inline-flex items-center px-2 py-1 border border-transparent text-xs font-medium rounded shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                >
                  <CheckIcon className="h-3 w-3 mr-1" />
                  Save
                </button>
                <button
                  onClick={onCancelEdit}
                  className="inline-flex items-center px-2 py-1 border border-gray-300 dark:border-gray-700 text-xs font-medium rounded text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
                >
                  <XMarkIcon className="h-3 w-3 mr-1" />
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="mt-1 flex items-center">
              <p className="text-sm text-gray-900 dark:text-gray-200 flex-grow">{description || "No description provided"}</p>
              <button
                onClick={onEditDescription}
                className="p-1 text-gray-400 hover:text-gray-500 dark:hover:text-gray-300"
                aria-label="Edit agent description"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                </svg>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
