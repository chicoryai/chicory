import { useFetcher, useRevalidator } from "@remix-run/react";
import { useState, useEffect } from "react";
import type { DataSourceFieldDefinition } from "~/services/chicory.server";
import { MASKED_PASSWORD_PLACEHOLDER, isSensitiveField as checkIsSensitiveField } from "~/utils/dataSourceFieldUtils";

interface ActionData {
  success: boolean;
  message: string;
  _action?: string;
  [key: string]: any;
}

interface DataSourceFormProps {
  /**
   * Data source type definition
   */
  dataSource: {
    id: string;
    name: string;
    requiredFields: DataSourceFieldDefinition[];
  };
  /**
   * Project ID to associate the data source with
   */
  projectId: string;
  /**
   * Optional callback when form submission is successful
   */
  onSuccess?: () => void;
  /**
   * Optional initial form values
   */
  initialValues?: Record<string, string>;
  /**
   * Whether this form is for editing an existing data source
   */
  isEditing?: boolean;
  /**
   * ID of the data source being edited (required when isEditing is true)
   */
  dataSourceId?: string;
}

/**
 * A reusable form component for data source connections.
 * Handles testing and saving connections using Remix's fetcher.
 */
export function DataSourceForm({ 
  dataSource, 
  projectId, 
  onSuccess,
  initialValues = {},
  isEditing = false,
  dataSourceId = ""
}: DataSourceFormProps) {
  const fetcher = useFetcher<ActionData>();
  const revalidator = useRevalidator();
  const [testResult, setTestResult] = useState<{
    status: "success" | "error" | null;
    message: string;
  }>({ status: null, message: "" });
  
  // Reset test result when data source changes
  useEffect(() => {
    setTestResult({ status: null, message: "" });
  }, [dataSource.id]);
  
  // State to track which fields should show their values (for password/API key fields)
  const [visibleFields, setVisibleFields] = useState<Record<string, boolean>>({});

  // State to track which password fields user wants to update (for edit mode)
  const [fieldsToUpdate, setFieldsToUpdate] = useState<Record<string, boolean>>({});

  // Toggle visibility for a specific field
  const toggleFieldVisibility = (fieldName: string) => {
    setVisibleFields(prev => ({
      ...prev,
      [fieldName]: !prev[fieldName]
    }));
  };

  // Enable a password field for editing
  const enableFieldForUpdate = (fieldName: string) => {
    setFieldsToUpdate(prev => ({
      ...prev,
      [fieldName]: true
    }));
  };
  
  // Handle fetcher response
  useEffect(() => {
    if (fetcher.data && fetcher.state === "idle") {
      console.log(`[DataSourceForm] Received fetcher data:`, fetcher.data);
      console.log(`[DataSourceForm] Fetcher state:`, fetcher.state);
      
      if (fetcher.data._action === "validateCredentials") {
        console.log(`[DataSourceForm] Processing validateCredentials response`);
        console.log(`[DataSourceForm] Success:`, fetcher.data.success);
        console.log(`[DataSourceForm] Message:`, fetcher.data.message);
        
        setTestResult({
          status: fetcher.data.success ? "success" : "error",
          message: fetcher.data.message
        });
      } else if ((fetcher.data._action === "createDataSource" || fetcher.data._action === "updateDataSource" || fetcher.data._action === "editDataSource") && fetcher.data.success) {
        // Show success message
        setTestResult({
          status: "success",
          message: fetcher.data.message || (isEditing ? "Data source updated successfully!" : "Data source created successfully!")
        });
        
        // Close the modal after a short delay to show the success message
        setTimeout(() => {
          setTestResult({ status: null, message: "" });
          
          // Skip revalidation to avoid turbo-stream parsing issues
          // The main page will refresh data through other mechanisms
          
          onSuccess?.();
        }, 1500);
      } else if ((fetcher.data._action === "createDataSource" || fetcher.data._action === "updateDataSource" || fetcher.data._action === "editDataSource") && !fetcher.data.success) {
        // Show error message
        setTestResult({
          status: "error",
          message: fetcher.data.message || "An error occurred. Please try again."
        });
      }
    }
  }, [fetcher.data, fetcher.state, onSuccess, isEditing]);
  
  const handleTest = () => {
    const form = document.getElementById("data-source-form") as HTMLFormElement;
    if (!form) return;
    
    const formData = new FormData(form);
    
    // Check if this is a file-based data source that doesn't need validation
    const fileDataSources = ['csv_upload', 'xlsx_upload', 'generic_file_upload'];
    const isFileDataSource = fileDataSources.includes(dataSource.id);
    
    if (isFileDataSource) {
      // For file data sources, skip validation
      setTestResult({
        status: "success",
        message: "File data sources don't require connection testing."
      });
      return;
    }
    
    // Always use validateCredentials for all data sources
    formData.set("_action", "validateCredentials");
    formData.set("dataSourceTypeId", dataSource.id);
    
    fetcher.submit(formData, { method: "post" });
  };
  
  return (
    <div>
      <fetcher.Form 
        id="data-source-form" 
        method="post" 
        action={`/projects/${projectId}/integrations`}
        className="space-y-4"
      >
        <input type="hidden" name="projectId" value={projectId} />
        <input type="hidden" name="dataSourceTypeId" value={dataSource.id} />
        <input type="hidden" name="_action" value={isEditing ? "editDataSource" : "createDataSource"} />
        {isEditing && <input type="hidden" name="dataSourceId" value={dataSourceId} />}
        
        {/* Hidden name field automatically set based on data source type */}
        <input 
          type="hidden" 
          name="name" 
          value={initialValues.name || `${dataSource.name} Connection`} 
        />
        
        {dataSource.requiredFields.map((field) => {
          // Check if this is a sensitive field (password or API key)
          const isSensitive = checkIsSensitiveField(field);

          // Check if this field has an existing value (when editing)
          const hasExistingValue = isEditing && initialValues[field.name];

          // Check if field is protected (has existing value and user hasn't chosen to update it)
          const isProtected = isSensitive && hasExistingValue && !fieldsToUpdate[field.name];

          return (
            <div key={field.name} className="mb-4">
              <label
                htmlFor={field.name}
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >
                {field.name.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase())}
                {!field.optional && (
                  <span className="text-red-500 ml-1">*</span>
                )}
              </label>
              <div className="relative">
                <input
                  type={isSensitive && !visibleFields[field.name] ? "password" : "text"}
                  id={field.name}
                  name={field.name}
                  defaultValue={isProtected ? MASKED_PASSWORD_PLACEHOLDER : initialValues[field.name] || ""}
                  readOnly={!!isProtected}
                  className={`w-full px-3 py-2 border border-gray-300 bg-white dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-lime-500 focus:border-lime-500 dark:bg-gray-700 dark:text-white ${
                    isProtected ? 'opacity-60 cursor-not-allowed' : ''
                  }`}
                  placeholder={isProtected ? "Existing value (hidden for security)" : field.description}
                  required={!field.optional && !hasExistingValue}
                />
                {isSensitive && initialValues[field.name] && !isProtected && (
                  <button
                    type="button"
                    onClick={() => toggleFieldVisibility(field.name)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                  >
                    {visibleFields[field.name] ? (
                      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88" />
                      </svg>
                    ) : (
                      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                        <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      </svg>
                    )}
                  </button>
                )}
              </div>
              {isProtected && (
                <div className="mt-2 flex items-start justify-between">
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    This field is protected for security. The existing value will be preserved.
                  </p>
                  <button
                    type="button"
                    onClick={() => enableFieldForUpdate(field.name)}
                    className="ml-2 text-xs font-medium text-lime-600 hover:text-lime-700 dark:text-lime-400 dark:hover:text-lime-300 whitespace-nowrap"
                  >
                    Change Value
                  </button>
                </div>
              )}
              {field.description && !isProtected && (
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  {field.description}
                </p>
              )}
            </div>
          );
        })}
        
        {testResult.status && (
          <div
            className={`mb-4 p-3 rounded-md ${
              testResult.status === "success"
                ? "bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200"
                : "bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200"
            }`}
          >
            {testResult.message}
          </div>
        )}
        
        <div className="flex justify-end space-x-3">
          <button
            type="button"
            onClick={handleTest}
            disabled={fetcher.state !== "idle"}
            className="px-4 py-2 text-sm font-medium rounded-md bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lime-500 disabled:opacity-50"
          >
            {fetcher.state !== "idle" && fetcher.formData?.get("_action") === "validateCredentials" 
              ? "Testing..." 
              : "Test Connection"}
          </button>
          <button
            type="submit"
            disabled={fetcher.state !== "idle"}
            className="px-4 py-2 text-sm font-medium rounded-md bg-lime-500 hover:bg-lime-600 text-white focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lime-500 disabled:opacity-50"
          >
            {fetcher.state !== "idle" && (fetcher.formData?.get("_action") === "saveConnection" || fetcher.formData?.get("_action") === "updateConnection")
              ? isEditing ? "Updating..." : "Saving..." 
              : isEditing ? "Update" : "Save"}
          </button>
        </div>
      </fetcher.Form>
    </div>
  );
}
