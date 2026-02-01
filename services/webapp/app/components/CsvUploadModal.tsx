import { Modal } from "~/components/ui/Modal";
import { Form, useActionData, useNavigation } from "@remix-run/react";
import { useState, useRef, ChangeEvent, useEffect } from "react";
import { CloudArrowUpIcon, CheckCircleIcon, XCircleIcon } from "@heroicons/react/24/outline";

interface CsvUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string;
}

interface FileUploadResult {
  filename: string; // Changed from 'name' to match backend response
  name?: string; // Keep for backward compatibility
  status: "success" | "error";
  dataSourceId?: string;
  error?: string;
}

interface ActionData {
  success: boolean;
  message: string;
  results?: FileUploadResult[];
  dataSource?: any;
  projectDataSources?: any[];
  _action?: string;
}

export default function CsvUploadModal({
  isOpen,
  onClose,
  projectId,
}: CsvUploadModalProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [dragActive, setDragActive] = useState<boolean>(false);
  const [uploadStatus, setUploadStatus] = useState<{[filename: string]: "pending" | "success" | "error"}>({});
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const dropAreaRef = useRef<HTMLDivElement>(null);

  const navigation = useNavigation();
  const actionData = useActionData<ActionData>();
  
  const isUploading = navigation.state === "submitting";
  
  // Reset form when modal is opened
  useEffect(() => {
    if (isOpen) {
      setFiles([]);
      setDragActive(false);
      setUploadStatus({});
      if (formRef.current) {
        formRef.current.reset();
      }
    }
  }, [isOpen]);
  
  // Update upload status when action data changes
  useEffect(() => {
    if (actionData && actionData._action === "uploadCsv") {
      if (actionData.results) {
        // Handle batch upload results
        const newStatus: {[filename: string]: "pending" | "success" | "error"} = {};
        
        actionData.results.forEach(result => {
          const fileName = result.filename || result.name || 'unknown';
          newStatus[fileName] = result.status === "success" ? "success" : "error";
        });
        
        setUploadStatus(prev => ({ ...prev, ...newStatus }));
        
        // If all files have been processed, close modal after showing status
        if (actionData.results.length === files.length) {
          setTimeout(() => onClose(), 2000); // Give users time to see status
        }
      } else if (actionData.success === false) {
        // Handle general error case - mark all files as error
        const errorStatus: {[filename: string]: "pending" | "success" | "error"} = {};
        files.forEach(file => {
          errorStatus[file.name] = "error";
        });
        setUploadStatus(errorStatus);
        
        // Don't auto-close on error, let user dismiss
      }
    }
  }, [actionData, files.length, onClose]);
  
  if (!isOpen) return null;
  
  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = e.target.files;
    if (!selectedFiles) return;
    
    // Convert FileList to Array and filter for CSV files
    const fileArray = Array.from(selectedFiles)
      .filter(file => file.type === "text/csv" || file.name.endsWith('.csv'));
    
    // Check if we're exceeding the 10 file limit
    if (fileArray.length > 10) {
      alert("You can only upload up to 10 files at once.");
      // Keep only the first 10 files
      setFiles(fileArray.slice(0, 10));
    } else {
      setFiles(fileArray);
    }
    
    // Initialize upload status for each file
    const initialStatus: {[filename: string]: "pending" | "success" | "error"} = {};
    fileArray.slice(0, 10).forEach(file => {
      initialStatus[file.name] = "pending";
    });
    setUploadStatus(initialStatus);
  };
  
  const handleBrowseClick = () => {
    fileInputRef.current?.click();
  };
  
  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(true);
  };
  
  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  };
  
  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      // Filter for CSV files
      const droppedFiles = Array.from(e.dataTransfer.files)
        .filter(file => file.type === "text/csv" || file.name.endsWith('.csv'));
      
      if (droppedFiles.length === 0) {
        alert("Please upload CSV files only");
        return;
      }
      
      // Check for the 10 file limit
      if (droppedFiles.length > 10) {
        alert("You can only upload up to 10 files at once.");
        // Keep only the first 10 files
        setFiles(droppedFiles.slice(0, 10));
      } else {
        setFiles(droppedFiles);
      }
      
      // Initialize upload status for each file
      const initialStatus: {[filename: string]: "pending" | "success" | "error"} = {};
      droppedFiles.slice(0, 10).forEach(file => {
        initialStatus[file.name] = "pending";
      });
      setUploadStatus(initialStatus);
      
      // Manually set the files to the file input
      const dataTransfer = new DataTransfer();
      droppedFiles.slice(0, 10).forEach(file => {
        dataTransfer.items.add(file);
      });
      
      if (fileInputRef.current) {
        fileInputRef.current.files = dataTransfer.files;
        // Trigger the onChange event manually
        const event = new Event('change', { bubbles: true });
        fileInputRef.current.dispatchEvent(event);
      }
    }
  };
  
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    if (files.length === 0) {
      e.preventDefault();
      alert("Please select at least one CSV file");
      return;
    }
    
    const nameInput = e.currentTarget.querySelector('input[name="name"]') as HTMLInputElement;
    if (!nameInput || !nameInput.value.trim()) {
      e.preventDefault();
      alert("Name is required");
      return;
    }
  };
  
  return (
    <Modal 
      isOpen={isOpen} 
      onClose={onClose}
      title="Upload CSV Data Source"
    >
      <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
        Upload a CSV file to use as a data source for this project.
      </p>
      
      <Form reloadDocument 
        ref={formRef}
        method="post" 
        encType="multipart/form-data" 
        action={`/projects/${projectId}/integrations`}
        className="space-y-4"
        onSubmit={handleSubmit}
      >
        <input type="hidden" name="_action" value="uploadCsv" />
        <input type="hidden" name="projectId" value={projectId} />
        
        <div className="mb-4">
          <label
            htmlFor="name"
            className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
          >
            Name <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            id="name"
            name="name"
            required
            className="w-full px-3 py-2 border border-gray-300 bg-white dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-lime-500 focus:border-lime-500 dark:bg-gray-700 dark:text-white"
            placeholder="Enter a name for this data source"
          />
        </div>
        
        <div className="mb-4">
          <label
            htmlFor="description"
            className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
          >
            Description
          </label>
          <textarea
            id="description"
            name="description"
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 bg-white dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-lime-500 focus:border-lime-500 dark:bg-gray-700 dark:text-white"
            placeholder="Optional description"
          />
        </div>
        
        <div className="mb-4">
          <label
            className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
          >
            CSV File <span className="text-red-500">*</span>
          </label>
          
          <input
            type="file"
            id="file"
            name="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".csv"
            className="hidden"
            multiple
            required
          />
          
          <div 
            ref={dropAreaRef}
            className={`mt-1 flex justify-center px-6 pt-5 pb-6 border-2 ${
              dragActive 
                ? 'border-lime-500 bg-lime-50 dark:bg-lime-900/20' 
                : 'border-gray-300 dark:border-gray-600 border-dashed'
            } rounded-md cursor-pointer transition-colors duration-200`}
            onClick={handleBrowseClick}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <div className="space-y-1 text-center">
              <CloudArrowUpIcon className={`mx-auto h-12 w-12 ${
                dragActive ? 'text-lime-500' : 'text-gray-400'
              }`} />
              <div className="flex flex-col sm:flex-row items-center justify-center text-sm text-gray-600 dark:text-gray-400">
                <span className="relative cursor-pointer rounded-md font-medium text-lime-600 hover:text-lime-500 focus-within:outline-none focus-within:ring-2 focus-within:ring-offset-2 focus-within:ring-lime-500">
                  Browse
                </span>
                <p className="pl-1">or drag and drop</p>
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                CSV files only (Max 10 files)
              </p>
              {files.length > 0 && (
                <div className="mt-2 text-sm text-gray-600 dark:text-gray-400 p-2 bg-gray-50 dark:bg-gray-700 rounded max-h-48 overflow-y-auto">
                  <p className="font-semibold mb-2">Selected {files.length} file(s):</p>
                  <ul className="space-y-2">
                    {files.map((file, index) => {
                      // Format file size
                      let fileSize = "";
                      if (file.size < 1024) {
                        fileSize = `${file.size} B`;
                      } else if (file.size < 1024 * 1024) {
                        fileSize = `${(file.size / 1024).toFixed(1)} KB`;
                      } else {
                        fileSize = `${(file.size / (1024 * 1024)).toFixed(1)} MB`;
                      }
                      
                      const status = uploadStatus[file.name];
                      
                      return (
                        <li key={index} className="flex items-center justify-between">
                          <div className="flex-1 truncate">
                            <div className="font-medium truncate">{file.name}</div>
                            <div className="text-xs">{fileSize}</div>
                          </div>
                          {status && (
                            <div className="ml-2">
                              {status === "pending" && (
                                <div className="h-5 w-5 rounded-full border-2 border-t-lime-500 border-r-lime-500 border-b-lime-500 border-l-transparent animate-spin"></div>
                              )}
                              {status === "success" && (
                                <CheckCircleIcon className="h-5 w-5 text-lime-500" />
                              )}
                              {status === "error" && (
                                <XCircleIcon className="h-5 w-5 text-red-500" />
                              )}
                            </div>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </div>
        
        {actionData?.success === false && actionData?._action === "uploadCsv" && (
          <div className="p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700">
            <div className="flex items-start">
              <XCircleIcon className="h-5 w-5 text-red-600 dark:text-red-400 mt-0.5 flex-shrink-0" />
              <div className="ml-3 flex-1">
                <h3 className="text-sm font-ui font-semibold text-red-900 dark:text-red-100">
                  Upload Failed
                </h3>
                <div className="mt-2 text-sm font-body text-red-700 dark:text-red-300">
                  {(() => {
                    // First check if we have detailed error in results array (from batch upload)
                    let message = actionData.message || "";

                    if (actionData.results && Array.isArray(actionData.results) && actionData.results.length > 0) {
                      const firstError = actionData.results.find(r => r.status === 'error' && r.error);
                      if (firstError && firstError.error) {
                        message = firstError.error;
                      }
                    }

                    // Check for encoding errors
                    if (message.includes("utf-8") || message.includes("codec") || message.includes("decode")) {
                      return (
                        <>
                          <p className="font-medium">File Encoding Error</p>
                          <p className="mt-1">
                            The CSV file contains characters that cannot be read. This usually happens when the file is saved in a non-UTF-8 encoding (e.g., Windows-1252 or ISO-8859-1).
                          </p>
                          <button
                            type="button"
                            onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
                            className="mt-2 text-xs font-ui font-medium text-red-900 dark:text-red-100 hover:text-red-700 dark:hover:text-red-300 flex items-center"
                          >
                            {showTechnicalDetails ? '▼' : '▶'} Technical details
                          </button>
                          {showTechnicalDetails && (
                            <div className="mt-2 p-2 bg-red-100 dark:bg-red-950/50 rounded border border-red-300 dark:border-red-800">
                              <p className="font-mono text-xs text-red-800 dark:text-red-200 break-words">
                                {message}
                              </p>
                            </div>
                          )}
                        </>
                      );
                    }

                    // Check for file size errors
                    if (message.includes("size") || message.includes("large") || message.includes("limit")) {
                      return (
                        <>
                          <p className="font-medium">File Too Large</p>
                          <p className="mt-1">Please try uploading a smaller file or split it into multiple files.</p>
                          <button
                            type="button"
                            onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
                            className="mt-2 text-xs font-ui font-medium text-red-900 dark:text-red-100 hover:text-red-700 dark:hover:text-red-300 flex items-center"
                          >
                            {showTechnicalDetails ? '▼' : '▶'} Technical details
                          </button>
                          {showTechnicalDetails && (
                            <div className="mt-2 p-2 bg-red-100 dark:bg-red-950/50 rounded border border-red-300 dark:border-red-800">
                              <p className="font-mono text-xs text-red-800 dark:text-red-200 break-words">
                                {message}
                              </p>
                            </div>
                          )}
                        </>
                      );
                    }

                    // Check for invalid CSV format
                    if (message.includes("Invalid CSV") || message.includes("parse") || message.includes("format")) {
                      return (
                        <>
                          <p className="font-medium">Invalid CSV Format</p>
                          <p className="mt-1">Please ensure your file is a valid CSV file with properly formatted data.</p>
                          <button
                            type="button"
                            onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
                            className="mt-2 text-xs font-ui font-medium text-red-900 dark:text-red-100 hover:text-red-700 dark:hover:text-red-300 flex items-center"
                          >
                            {showTechnicalDetails ? '▼' : '▶'} Technical details
                          </button>
                          {showTechnicalDetails && (
                            <div className="mt-2 p-2 bg-red-100 dark:bg-red-950/50 rounded border border-red-300 dark:border-red-800">
                              <p className="font-mono text-xs text-red-800 dark:text-red-200 break-words">
                                {message}
                              </p>
                            </div>
                          )}
                        </>
                      );
                    }

                    // Default error message
                    return <p>{message || "An error occurred during upload. Please try again."}</p>;
                  })()}
                </div>
                {actionData.results && actionData.results.some(r => r.status === "error") && (
                  <div className="mt-3 text-sm font-body text-red-700 dark:text-red-300">
                    <p className="font-medium">Failed files:</p>
                    <ul className="list-disc list-inside mt-1 space-y-1 ml-2">
                      {actionData.results.filter(r => r.status === "error").map((result, index) => {
                        const fileName = result.filename || result.name || 'unknown';
                        const error = result.error || "Unknown error";
                        return (
                          <li key={index} className="break-words">
                            <span className="font-medium">{fileName}</span>: {error}
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
        
        <div className="flex justify-end space-x-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium rounded-md bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lime-500"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={files.length === 0 || isUploading}
            className="px-4 py-2 text-sm font-medium rounded-md bg-lime-500 hover:bg-lime-600 text-white focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lime-500 disabled:opacity-50"
          >
            {isUploading ? "Uploading..." : `Upload ${files.length > 0 ? `(${files.length})` : ""}`}
          </button>
        </div>
      </Form>
    </Modal>
  );
}
