import { Modal } from "~/components/ui/Modal";
import { Form, useActionData, useNavigation } from "@remix-run/react";
import { useState, useRef, ChangeEvent, useEffect } from "react";
import { CloudArrowUpIcon } from "@heroicons/react/24/outline";

interface ExcelUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string;
}

interface ActionData {
  success: boolean;
  message: string;
  dataSource?: any;
  projectDataSources?: any[];
  _action?: string;
}

export default function ExcelUploadModal({
  isOpen,
  onClose,
  projectId,
}: ExcelUploadModalProps) {
  const [fileName, setFileName] = useState<string>("");
  const [fileSize, setFileSize] = useState<string>("");
  const [dragActive, setDragActive] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const dropAreaRef = useRef<HTMLDivElement>(null);

  const navigation = useNavigation();
  const actionData = useActionData<ActionData>();
  
  const isUploading = navigation.state === "submitting";
  
  // Reset form when modal is opened
  useEffect(() => {
    if (isOpen) {
      setFileName("");
      setFileSize("");
      setDragActive(false);
      if (formRef.current) {
        formRef.current.reset();
      }
    }
  }, [isOpen]);
  
  // Close modal on successful upload
  useEffect(() => {
    if (actionData?.success && actionData?._action === "uploadExcel") {
      onClose();
    }
  }, [actionData, onClose]);
  
  if (!isOpen) return null;
  
  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFileName(selectedFile.name);
      
      // Format file size
      const size = selectedFile.size;
      if (size < 1024) {
        setFileSize(`${size} B`);
      } else if (size < 1024 * 1024) {
        setFileSize(`${(size / 1024).toFixed(1)} KB`);
      } else {
        setFileSize(`${(size / (1024 * 1024)).toFixed(1)} MB`);
      }
    } else {
      setFileName("");
      setFileSize("");
    }
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
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      
      // Check if file is an Excel file
      const isExcel = file.type === "application/vnd.ms-excel" || 
                     file.type === "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" ||
                     file.name.endsWith('.xls') || 
                     file.name.endsWith('.xlsx');
      
      if (isExcel) {
        // Manually set the file to the file input
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        
        if (fileInputRef.current) {
          fileInputRef.current.files = dataTransfer.files;
          // Trigger the onChange event manually
          const event = new Event('change', { bubbles: true });
          fileInputRef.current.dispatchEvent(event);
        }
      } else {
        alert("Please upload an Excel file (.xls or .xlsx)");
      }
    }
  };
  
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    // Validate before natural submission
    if (!fileInputRef.current?.files?.[0]) {
      // Stop submission if no file
      e.preventDefault();
      alert("Please select an Excel file");
      return;
    }

    const nameInput = e.currentTarget.querySelector('input[name="name"]') as HTMLInputElement;
    if (!nameInput || !nameInput.value.trim()) {
      e.preventDefault();
      alert("Name is required");
      return;
    }

    // Otherwise allow browser to submit normally (reloadDocument handles the rest)
  };
  
  return (
    <Modal 
      isOpen={isOpen} 
      onClose={onClose}
      title="Upload Excel Data Source"
    >
      <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
        Upload an Excel file to use as a data source for this project.
      </p>
      
      <Form
        reloadDocument
        ref={formRef}
        method="post" 
        encType="multipart/form-data" 
        action={`/projects/${projectId}/integrations`}
        className="space-y-4"
        onSubmit={handleSubmit}
      >
        <input type="hidden" name="_action" value="uploadExcel" />
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
            Excel File <span className="text-red-500">*</span>
          </label>
          
          <input
            type="file"
            id="file"
            name="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".xls,.xlsx,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            className="hidden"
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
                Excel files only (.xls, .xlsx)
              </p>
              {fileName && (
                <div className="mt-2 text-sm text-gray-600 dark:text-gray-400 p-2 bg-gray-50 dark:bg-gray-700 rounded">
                  <p>Selected: {fileName}</p>
                  <p>Size: {fileSize}</p>
                </div>
              )}
            </div>
          </div>
        </div>
        
        {actionData?.success === false && actionData?._action === "uploadExcel" && (
          <div className="p-3 rounded-md bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200">
            {actionData.message}
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
            disabled={!fileName || isUploading}
            className="px-4 py-2 text-sm font-medium rounded-md bg-lime-500 hover:bg-lime-600 text-white focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lime-500 disabled:opacity-50"
          >
            {isUploading ? "Uploading..." : "Upload"}
          </button>
        </div>
      </Form>
    </Modal>
  );
}
