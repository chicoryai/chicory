import { Modal } from "~/components/ui/Modal";
import { useFetcher } from "@remix-run/react";
import { useState, useEffect, useCallback, useRef } from "react";
import { 
  CloudArrowUpIcon,
  DocumentIcon,
  ExclamationCircleIcon,
  CheckCircleIcon,
  XMarkIcon
} from "@heroicons/react/24/outline";
import type { DataSourceTypeDefinition } from "~/services/chicory.server";
import { GitHubConnectButton } from "~/components/GitHubConnectButton";
import { JiraConnectButton } from "~/components/JiraConnectButton";

interface ActionData {
  success?: boolean;
  message?: string;
  error?: string;
  _action?: string;
}

interface DataSourceCreateModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
  dataSourceType: DataSourceTypeDefinition;
  projectId: string;
}

export default function DataSourceCreateModal({
  isOpen,
  onClose,
  onSuccess,
  dataSourceType,
  projectId,
}: DataSourceCreateModalProps) {
  const fetcher = useFetcher<ActionData>();
  const [dragActive, setDragActive] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [validationResult, setValidationResult] = useState<{
    status: 'success' | 'error' | 'loading' | null;
    message: string;
  }>({ status: null, message: '' });
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [jsonFile, setJsonFile] = useState<File | null>(null);
  const [jsonFileError, setJsonFileError] = useState<string>('');
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);

  const [githubAuthMethod, setGithubAuthMethod] = useState<'oauth' | 'pat'>('oauth');
  const [webfetchMode, setWebfetchMode] = useState<'scrape' | 'crawl'>('scrape');

  // Handle webfetch mode change - clear mode-specific fields
  const handleWebfetchModeChange = (newMode: 'scrape' | 'crawl') => {
    setWebfetchMode(newMode);
    // Clear mode-specific fields when switching modes
    setFormData(prev => {
      const { url, start_url, max_pages, ...rest } = prev;
      return rest;
    });
  };

  // Create a ref for the hidden file input
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Pre-populate external_id for S3, DataZone and Glue
  useEffect(() => {
    if ((dataSourceType.id === 'datazone' || dataSourceType.id === 'glue' || dataSourceType.id === 's3') && !formData.external_id) {
      setFormData(prev => ({
        ...prev,
        external_id: `chicory-${projectId}`
      }));
    }
  }, [dataSourceType.id, projectId, formData.external_id]);

  // Check if this is a file-based data source
  const fileDataSources = ['csv_upload', 'xlsx_upload', 'generic_file_upload'];
  const isFileDataSource = fileDataSources.includes(dataSourceType.id);
  
  // Check if this data source supports JSON credential file upload
  const jsonCredentialDataSources = ['bigquery', 'google_drive'];
  const supportsJsonCredentials = jsonCredentialDataSources.includes(dataSourceType.id);

  // Check if this is GitHub or Jira (use OAuth instead of form)
  const isGitHubDataSource = dataSourceType.id === 'github';
  const isJiraDataSource = dataSourceType.id === 'jira';
  const isWebfetchDataSource = dataSourceType.id === 'webfetch';

  // Get accepted file types based on data source type and category
  const getAcceptedFileTypes = () => {
    switch (dataSourceType.id) {
      case 'csv_upload':
        return '.csv,text/csv';
      case 'xlsx_upload':
        return '.xlsx,.xls,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel';
      case 'generic_file_upload':
        if (dataSourceType.category === 'code') {
          return '.js,.jsx,.ts,.tsx,.py,.java,.cpp,.c,.h,.cs,.php,.rb,.go,.rs,.swift,.kt,.scala,.clj,.hs,.ml,.fs,.vb,.pl,.sh,.sql,.html,.css,.scss,.sass,.less,.xml,.json,.yaml,.yml,.toml,.ini,.cfg,.conf,.md,.txt,text/javascript,text/typescript,text/python,text/java,text/cpp,text/csharp,text/php,text/ruby,text/go,text/rust,text/swift,text/kotlin,text/scala,text/clojure,text/haskell,text/ocaml,text/fsharp,text/vbnet,text/perl,text/shell,text/sql,text/html,text/css,text/xml,application/json,application/yaml,text/plain,text/markdown';
        } else {
          return '.pdf,.doc,.docx,.txt,.md,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown';
        }
      default:
        return '*/*';
    }
  };

  // Get file type description based on data source type and category
  const getFileTypeDescription = () => {
    switch (dataSourceType.id) {
      case 'csv_upload':
        return 'CSV files (.csv)';
      case 'xlsx_upload':
        return 'Excel files (.xlsx, .xls)';
      case 'generic_file_upload':
        if (dataSourceType.category === 'code') {
          return 'Code files (.js, .py, .java, .cpp, .ts, .html, .css, etc.)';
        } else {
          return 'Documents (.pdf, .doc, .docx, .txt, .md)';
        }
      default:
        return 'All files';
    }
  };

  // Handle form input changes
  const handleInputChange = (fieldName: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      [fieldName]: value
    }));
  };

  // Handle JSON credential file upload
  const handleJsonFileUpload = async (file: File) => {
    setJsonFileError('');
    
    // Validate file type
    if (!file.name.endsWith('.json')) {
      setJsonFileError('Please upload a valid JSON file');
      return;
    }
    
    try {
      const text = await file.text();
      const jsonData = JSON.parse(text);
      
      // Validate required fields based on data source type
      const requiredFields = ['project_id', 'private_key_id', 'private_key', 'client_email', 'client_id'];
      const missingFields = requiredFields.filter(field => !jsonData[field]);
      
      if (missingFields.length > 0) {
        setJsonFileError(`Missing required fields: ${missingFields.join(', ')}`);
        return;
      }
      
      // Extract and populate form data from service account JSON
      // Note: dataset_id and folder_id are NOT part of the service account JSON
      // and must be entered manually by the user
      const newFormData: Record<string, string> = {
        project_id: jsonData.project_id || '',
        private_key_id: jsonData.private_key_id || '',
        private_key: jsonData.private_key || '',
        client_email: jsonData.client_email || '',
        client_id: jsonData.client_id || '',
        client_cert_url: jsonData.client_x509_cert_url || '',
      };
      
      setFormData(newFormData);
      setJsonFile(file);
      setValidationResult({
        status: 'success',
        message: `Successfully loaded credentials from ${file.name}`
      });
    } catch (error) {
      setJsonFileError('Invalid JSON file format');
      console.error('Error parsing JSON file:', error);
    }
  };
  
  // Handle JSON file input change
  const handleJsonFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleJsonFileUpload(e.target.files[0]);
    }
  };

  // Handle file selection
  const handleFileSelect = (files: File[]) => {
    // Maximum of 10 files
    if (files.length > 10) {
      setValidationResult({
        status: 'error',
        message: 'You can upload a maximum of 10 files at once.'
      });
      return;
    }

    // Validate all files
    const acceptedTypes = getAcceptedFileTypes().split(',');
    const maxSize = 100 * 1024 * 1024; // 100MB
    
    const invalidTypeFiles: string[] = [];
    const oversizedFiles: string[] = [];
    
    files.forEach(file => {
      // Check file type
      const isValidType = acceptedTypes.some(type => {
        if (type.startsWith('.')) {
          return file.name.toLowerCase().endsWith(type.toLowerCase());
        } else {
          return file.type === type;
        }
      });
      
      if (!isValidType && getAcceptedFileTypes() !== '*/*') {
        invalidTypeFiles.push(file.name);
      }
      
      // Check file size
      if (file.size > maxSize) {
        oversizedFiles.push(file.name);
      }
    });
    
    // Handle validation errors
    if (invalidTypeFiles.length > 0) {
      setValidationResult({
        status: 'error',
        message: `Invalid file type${invalidTypeFiles.length > 1 ? 's' : ''}: ${invalidTypeFiles.join(', ')}. Please select ${getFileTypeDescription()}.`
      });
      return;
    }
    
    if (oversizedFiles.length > 0) {
      setValidationResult({
        status: 'error',
        message: `File${oversizedFiles.length > 1 ? 's' : ''} too large: ${oversizedFiles.join(', ')}. Files must be less than 100MB.`
      });
      return;
    }
    
    // Clear any previous validation errors
    setValidationResult({ status: null, message: '' });
    
    setUploadedFiles(files);
    
    // Update form data with the first file's info for backward compatibility
    if (files.length > 0) {
      setFormData(prev => ({
        ...prev,
        filename: files[0].name,
        file_size: files[0].size.toString(),
        mime_type: files[0].type
      }));
    }
  };

  // Handle drag and drop
  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const filesArray = Array.from(e.dataTransfer.files);
      handleFileSelect(filesArray);
    }
  }, []);

  // Handle file input change
  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const filesArray = Array.from(e.target.files);
      handleFileSelect(filesArray);
    }
  };

  // Handle additional form fields change
  const handleFieldChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // For file-based data sources, validate files are present
    if (isFileDataSource && uploadedFiles.length === 0) {
      setValidationResult({
        status: 'error',
        message: 'Please select at least one file to upload'
      });
      return;
    }

    // For BigQuery and Google Drive, validate JSON file is uploaded
    if (supportsJsonCredentials && !jsonFile) {
      setValidationResult({
        status: 'error',
        message: 'Please upload a service account JSON file'
      });
      return;
    }

    // For Google Drive, validate folder_id is provided
    if (dataSourceType.id === 'google_drive' && !formData.folder_id) {
      setValidationResult({
        status: 'error',
        message: 'Please enter a Google Drive folder ID'
      });
      return;
    }

    // Set loading state
    setValidationResult({
      status: 'loading',
      message: 'Uploading, please wait...'
    });

    // Create standard FormData object for submission
    const submitFormData = new FormData();
    
    // Determine the action type based on data source type and file handling
    let actionType = "createDataSource";
    
    if (isFileDataSource) {
      // For file-based data sources, use specific upload actions
      if (dataSourceType.id === "csv_upload") {
        actionType = "uploadCsv";
      } else if (dataSourceType.id === "xlsx_upload") {
        actionType = "uploadExcel";
      } else if (dataSourceType.id === "generic_file_upload") {
        actionType = "uploadGenericFile";
      }
    }
    submitFormData.append("_action", actionType);
    submitFormData.append("dataSourceTypeId", dataSourceType.id);
    submitFormData.append("projectId", projectId);
    
    // Add category for generic file uploads to distinguish between code and document uploads
    if (dataSourceType.id === "generic_file_upload" && dataSourceType.category) {
      submitFormData.append("category", dataSourceType.category);
    }
    
    // Auto-generate appropriate name based on data source type
    if (isFileDataSource) {
      // Handle file-based data sources
      let fileName = 'Upload'; // Default name if no valid file
      
      // Add all files to form data with 'file' field name
      uploadedFiles.forEach((file, index) => {
        if (file instanceof File) {
          // If this is the first file, use its name (without extension) for the data source
          if (index === 0) {
            // Get filename without extension for the first file
            fileName = file.name.replace(/\.[^/.]+$/, "");
          }
          
          // Add the file with field name 'file'
          submitFormData.append("file", file);
        }
      });
      
      // Set the name using the first file's name (without extension)
      submitFormData.append("name", fileName);
      
      // Add other form data
      Object.entries(formData).forEach(([key, value]) => {
        if (value && key !== 'filename' && key !== 'file_size' && key !== 'mime_type') {
          submitFormData.append(key, value);
        }
      });
    } else {
      // For connection-based data sources
      // Generate a clean, descriptive name with data source prefix
      let autoName = '';

      // Use appropriate field based on data source type with proper prefix
      if (dataSourceType.id === 'databricks') {
        autoName = `Databricks - ${formData.host || 'Connection'}`;
      } else if (dataSourceType.id === 'snowflake') {
        autoName = `Snowflake - ${formData.username || 'Connection'}`;
      } else if (dataSourceType.id === 'github') {
        autoName = `GitHub - ${formData.username || 'Connection'}`;
      } else if (dataSourceType.id === 'google_drive') {
        autoName = `Google Drive - ${formData.folder_id || formData.project_id || 'Connection'}`;
      } else if (dataSourceType.id === 'bigquery') {
        autoName = `BigQuery - ${formData.project_id || 'Connection'}`;
      } else if (dataSourceType.id === 'glue') {
        autoName = `AWS Glue - ${formData.customer_account_id || 'Connection'}`;
      } else if (dataSourceType.id === 'datazone') {
        autoName = `AWS DataZone - ${formData.customer_account_id || 'Connection'}`;
      } else if (dataSourceType.id === 's3') {
        autoName = `AWS S3 - ${formData.customer_account_id || 'Connection'}`;
      } else if (dataSourceType.id === 'redash') {
        autoName = `Redash - ${formData.base_url || 'Connection'}`;
      } else if (dataSourceType.id === 'redshift') {
        autoName = `Redshift - ${formData.host || 'Connection'}`;
      } else if (dataSourceType.id === 'looker') {
        autoName = `Looker - ${formData.client_id || 'Connection'}`;
      } else if (dataSourceType.id === 'dbt') {
        autoName = `dbt - ${formData.account_id || 'Connection'}`;
      } else if (dataSourceType.id === 'datahub') {
        autoName = `DataHub - ${formData.base_url || 'Connection'}`;
      } else if (dataSourceType.id === 'airflow') {
        autoName = `Airflow - ${formData.base_url || 'Connection'}`;
      } else if (dataSourceType.id === 'anthropic') {
        autoName = 'Anthropic - API Connection';
      } else if (dataSourceType.id === 'webfetch') {
        const targetUrl = webfetchMode === 'scrape' ? formData.url : formData.start_url;
        autoName = `Web Fetch - ${targetUrl || 'Connection'}`;
      } else {
        // Fallback: use data source name with first non-empty field value
        const firstValue = Object.values(formData).find(value => value && value.trim());
        autoName = `${dataSourceType.name} - ${firstValue || 'Connection'}`;
      }

      submitFormData.append("name", autoName);

      // Add form data
      Object.entries(formData).forEach(([key, value]) => {
        if (value) {
          submitFormData.append(key, value);
        }
      });

      // Add webfetch mode if applicable
      if (isWebfetchDataSource) {
        submitFormData.append("mode", webfetchMode);
      }
    }

    // Submit the form data with useFetcher
    // Ensure we specify the right encoding type for file uploads
    fetcher.submit(submitFormData, { 
      method: "post",
      action: `/projects/${projectId}/integrations`,
      encType: "multipart/form-data"
    });
  };

  // Handle fetcher response
  useEffect(() => {
    if (fetcher.data && fetcher.state === "idle") {
      if (fetcher.data.success) {
        // On success, call callback and close modal immediately
        onSuccess?.();
        onClose();
      } else if (fetcher.data.error || fetcher.data.message) {
        // On error, show the error message to the user
        // First check if we have detailed error in results array (from batch upload)
        let errorMessage = fetcher.data.error || fetcher.data.message || "An error occurred";

        if (fetcher.data.results && Array.isArray(fetcher.data.results) && fetcher.data.results.length > 0) {
          const firstError = fetcher.data.results.find((r: any) => r.status === 'error' && r.error);
          if (firstError && firstError.error) {
            errorMessage = firstError.error;
          }
        }

        // Clear the loading state and show the error
        setValidationResult({
          status: 'error',
          message: errorMessage
        });

        // Don't close the modal - let the user read the error and try again
      }
    }
  }, [fetcher.data, fetcher.state, onSuccess, onClose]);

  // Reset form when modal closes
  useEffect(() => {
    // Reset all form state when modal is opened/closed
    // Only reset on mount and when onClose is called (will be handled in onClose)
    return () => {
      setFormData({});
      setUploadedFiles([]);
      setValidationResult({ status: null, message: '' });
      setJsonFile(null);
      setJsonFileError('');
    };
  }, []);

  // Helper function to capitalize first letter of every word
  const capitalizeWords = (str: string) => {
    return str
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(' ');
  };

  // Component will be conditionally rendered by the parent

  const getIntegrationIcon = (integrationId: string) => {
    // Handle generic_file_upload with different icons based on category
    if (integrationId === 'generic_file_upload') {
      return dataSourceType.category === 'code' ? '/icons/code_file_upload.svg' : '/icons/generic_file_upload.svg';
    }
    
    const iconMap: Record<string, string> = {
      'csv_upload': '/icons/csv_upload.svg',
      'xlsx_upload': '/icons/xlsx_upload.svg',
      'google_drive': '/icons/google_drive.svg',
      'github': '/icons/github.svg',
      'jira': '/icons/jira.svg',
      'databricks': '/icons/databricks.svg',
      'snowflake': '/icons/snowflake.svg',
      'direct_upload': '/icons/direct_upload.svg',
      'bigquery': '/icons/bigquery.svg',
      'glue': '/icons/glue.svg',
      'datazone': '/icons/datazone.svg',
      's3': '/icons/s3.png',
      'redash': '/icons/redash.svg',
      'redshift': '/icons/redshift.svg',
      'looker': '/icons/looker.svg',
      'dbt': '/icons/dbt.svg',
      'datahub': '/icons/datahub.svg',
      'airflow': '/icons/airflow.svg',
      'anthropic': '/icons/anthropic.png',
      'webfetch': '/icons/webfetch.svg'
    };
    return iconMap[integrationId] || '/icons/generic-integration.svg';
  };

  return (
    <Modal 
      isOpen={true} 
      onClose={onClose}
      title={`Connect ${dataSourceType.name}`}
    >
      <div className="space-y-6">
        {/* Header with Icon */}
        <div className="flex items-start space-x-4">
          <div className="flex-shrink-0">
            <div className="w-12 h-12 bg-whiteLime-100 dark:bg-lime-900 rounded-lg flex items-center justify-center overflow-hidden">
              <img 
                src={getIntegrationIcon(dataSourceType.id)} 
                alt={`${dataSourceType.name} icon`}
                className="w-8 h-8 object-contain"
                onError={(e) => {
                  const target = e.target as HTMLImageElement;
                  target.style.display = 'none';
                  target.nextElementSibling?.classList.remove('hidden');
                }}
              />
              <DocumentIcon className="w-6 h-6 text-lime-600 dark:text-lime-400 hidden" />
            </div>
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">
              {dataSourceType.name}
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {dataSourceType.description || `Connect your ${dataSourceType.name} data source`}
            </p>
          </div>
        </div>

        {/* CloudFormation Links for AWS Glue */}
        {dataSourceType.id === 'glue' && (
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <div className="flex items-start space-x-2">
              <svg className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div className="flex-1">
                <h4 className="text-sm font-medium text-blue-900 dark:text-blue-100 mb-2">
                  Setup CloudFormation Stack
                </h4>
                <p className="text-xs text-blue-800 dark:text-blue-200 mb-2">
                  Click one of the links below to create the required IAM role in your AWS account:
                </p>
                <div className="space-y-1 mb-2">
                  <a
                    href={`https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/create/review?templateURL=https://chicory-public-templates.s3.us-west-2.amazonaws.com/chicory-glue-athena-crossaccount.yaml&stackName=ChicoryGlueAccess&param_ChicoryAccountId=070567846440&param_ExternalId=${encodeURIComponent(formData.external_id || `chicory-${projectId}`)}&param_RoleName=GlueAccessRoleForChicory&param_AccessLevel=ReadOnly`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block text-sm text-blue-700 dark:text-blue-300 hover:text-blue-800 dark:hover:text-blue-200 hover:underline"
                  >
                    Create Stack with ReadOnly Access →
                  </a>
                </div>
                <p className="text-xs text-blue-700 dark:text-blue-200">
                  For manual setup steps, follow{' '}
                  <a
                    href="https://docs.chicory.ai/reference-guides/how-to-guides/integrations/aws"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-medium underline hover:text-blue-800 dark:hover:text-blue-100"
                  >
                    our documentation
                  </a>
                </p>
              </div>
            </div>
          </div>
        )}

        {/* CloudFormation Links for AWS DataZone */}
        {dataSourceType.id === 'datazone' && (
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <div className="flex items-start space-x-2">
              <svg className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div className="flex-1">
                <h4 className="text-sm font-medium text-blue-900 dark:text-blue-100 mb-2">
                  Setup CloudFormation Stack
                </h4>
                <p className="text-xs text-blue-800 dark:text-blue-200 mb-2">
                  Click one of the links below to create the required IAM role in your AWS account:
                </p>
                <div className="space-y-1 mb-2">
                  <a
                    href={`https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/create/review?templateURL=https://chicory-public-templates.s3.us-west-2.amazonaws.com/chicory-datazone-crossaccount.yaml&stackName=ChicoryDatazoneAccess&param_ChicoryAccountId=070567846440&param_ExternalId=${encodeURIComponent(formData.external_id || `chicory-${projectId}`)}&param_RoleName=DatazoneAccessRoleForChicory&param_AccessLevel=ReadOnly`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block text-sm text-blue-700 dark:text-blue-300 hover:text-blue-800 dark:hover:text-blue-200 hover:underline"
                  >
                    Create Stack with ReadOnly Access →
                  </a>
                </div>
                <p className="text-xs text-blue-700 dark:text-blue-200">
                  For manual setup steps, follow{' '}
                  <a
                    href="https://docs.chicory.ai/reference-guides/how-to-guides/integrations/aws"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-medium underline hover:text-blue-800 dark:hover:text-blue-100"
                  >
                    our documentation
                  </a>
                </p>
              </div>
            </div>
          </div>
        )}

        {/* CloudFormation Links for AWS S3 */}
        {dataSourceType.id === 's3' && (
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <div className="flex items-start space-x-2">
              <svg className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div className="flex-1">
                <h4 className="text-sm font-medium text-blue-900 dark:text-blue-100 mb-2">
                  Setup CloudFormation Stack
                </h4>
                <p className="text-xs text-blue-800 dark:text-blue-200 mb-2">
                  Click one of the links below to create the required IAM role in your AWS account:
                </p>
                <div className="space-y-1 mb-2">
                  <a
                    href={`https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/create/review?templateURL=https://chicory-public-templates.s3.us-west-2.amazonaws.com/chicory-s3-crossaccount.yaml&stackName=ChicoryS3Access&param_ChicoryAccountId=070567846440&param_ExternalId=${encodeURIComponent(formData.external_id || `chicory-${projectId}`)}&param_RoleName=S3AccessRoleForChicory&param_AccessLevel=ReadOnly`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block text-sm text-blue-700 dark:text-blue-300 hover:text-blue-800 dark:hover:text-blue-200 hover:underline"
                  >
                    Create Stack with ReadOnly Access →
                  </a>
                </div>
                <p className="text-xs text-blue-700 dark:text-blue-200">
                  For manual setup steps, follow{' '}
                  <a
                    href="https://docs.chicory.ai/reference-guides/how-to-guides/integrations/aws"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-medium underline hover:text-blue-800 dark:hover:text-blue-100"
                  >
                    our documentation
                  </a>
                </p>
              </div>
            </div>
          </div>
        )}

        {/* GitHub OAuth Flow */}
        {isGitHubDataSource ? (
          <div className="space-y-6">
            {/* Authentication Method Selector */}
            <div className="flex space-x-2 p-1 bg-gray-100 dark:bg-gray-800 rounded-lg">
              <button
                type="button"
                onClick={() => setGithubAuthMethod('oauth')}
                className={`flex-1 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                  githubAuthMethod === 'oauth'
                    ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                GitHub App (OAuth)
              </button>
              <button
                type="button"
                onClick={() => setGithubAuthMethod('pat')}
                className={`flex-1 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                  githubAuthMethod === 'pat'
                    ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                Personal Access Token
              </button>
            </div>

            {/* OAuth Method */}
            {githubAuthMethod === 'oauth' ? (
              <>
                <div className="text-center py-8">
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                    Connect Your GitHub Account
                  </h3>
                  <p className="text-gray-600 dark:text-gray-400 mb-6">
                    Authorize ChicoryAI to access your GitHub repositories securely via OAuth
                  </p>
                  <GitHubConnectButton 
                    projectId={projectId}
                    onError={(error) => {
                      setValidationResult({
                        status: 'error',
                        message: error
                      });
                    }}
                  />
                </div>
                
                {/* Show any errors from OAuth flow */}
                {validationResult.status === 'error' && (
                  <div className="rounded-lg p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
                    <div className="flex">
                      <ExclamationCircleIcon className="w-5 h-5 text-red-400 flex-shrink-0" />
                      <div className="ml-3">
                        <p className="text-sm font-medium text-red-800 dark:text-red-200">
                          {validationResult.message}
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                <div className="flex justify-end">
                  <button
                    type="button"
                    onClick={onClose}
                    className="px-4 py-2 text-sm font-medium rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </>
            ) : (
              /* PAT Method */
              <>
                {/* Notification */}
                {validationResult.status && (
                  <div className={`rounded-lg p-4 ${
                    validationResult.status === 'success' 
                      ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800' 
                      : validationResult.status === 'loading'
                      ? 'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800'
                      : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800'
                  }`}>
                    <div className="flex">
                      {validationResult.status === 'success' ? (
                        <CheckCircleIcon className="w-5 h-5 text-green-400 flex-shrink-0" />
                      ) : (
                        <ExclamationCircleIcon className="w-5 h-5 text-red-400 flex-shrink-0" />
                      )}
                      <div className="ml-3">
                        <p className={`text-sm font-medium ${
                          validationResult.status === 'success' 
                            ? 'text-green-800 dark:text-green-200' 
                            : validationResult.status === 'loading'
                            ? 'text-blue-800 dark:text-blue-200'
                            : 'text-red-800 dark:text-red-200'
                        }`}>
                          {validationResult.message}
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-6">
                  <div className="space-y-4">
                    <h4 className="text-sm font-medium text-gray-900 dark:text-white">
                      GitHub Configuration
                    </h4>
                    
                    <div>
                      <label htmlFor="username" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        GitHub Username
                        <span className="text-red-500 ml-1">*</span>
                      </label>
                      <input
                        type="text"
                        id="username"
                        name="username"
                        required
                        value={formData.username || ''}
                        onChange={(e) => handleInputChange('username', e.target.value)}
                        placeholder="Enter your GitHub username"
                        className="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-lime-500 focus:border-lime-500 bg-transparent dark:bg-gray-700 dark:text-white text-sm"
                      />
                    </div>

                    <div>
                      <label htmlFor="access_token" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Personal Access Token
                        <span className="text-red-500 ml-1">*</span>
                      </label>
                      <input
                        type="password"
                        id="access_token"
                        name="access_token"
                        required
                        value={formData.access_token || ''}
                        onChange={(e) => handleInputChange('access_token', e.target.value)}
                        placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                        className="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-lime-500 focus:border-lime-500 bg-transparent dark:bg-gray-700 dark:text-white text-sm font-mono"
                      />
                      <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                        Create a token at{' '}
                        <a 
                          href="https://github.com/settings/tokens" 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="text-lime-600 dark:text-lime-400 hover:underline"
                        >
                          github.com/settings/tokens
                        </a>
                        {' '}with 'repo' scope
                      </p>
                    </div>
                  </div>

                  <div className="flex justify-end space-x-3 pt-4">
                    <button
                      type="button"
                      onClick={onClose}
                      className="px-4 py-2 text-sm font-medium rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={fetcher.state === 'submitting'}
                      className="px-4 py-2 text-sm font-medium rounded-lg bg-lime-600 text-white hover:bg-lime-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lime-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      {fetcher.state === 'submitting' ? 'Connecting...' : 'Connect GitHub'}
                    </button>
                  </div>
                </form>
              </>
            )}
          </div>
        ) : isJiraDataSource ? (
          /* Jira OAuth Flow */
          <div className="space-y-6">
            <div className="text-center py-8">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                Connect Your Jira Account
              </h3>
              <p className="text-gray-600 dark:text-gray-400 mb-6">
                Authorize ChicoryAI to access your Jira projects securely via OAuth
              </p>
              <JiraConnectButton
                projectId={projectId}
                onError={(error) => {
                  setValidationResult({
                    status: 'error',
                    message: error
                  });
                }}
              />
            </div>

            {/* Show any errors from OAuth flow */}
            {validationResult.status === 'error' && (
              <div className="rounded-lg p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
                <div className="flex">
                  <ExclamationCircleIcon className="w-5 h-5 text-red-400 flex-shrink-0" />
                  <div className="ml-3">
                    <p className="text-sm font-medium text-red-800 dark:text-red-200">
                      {validationResult.message}
                    </p>
                  </div>
                </div>
              </div>
            )}

            <div className="flex justify-end">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : isWebfetchDataSource ? (
          /* Webfetch (Firecrawl) Form */
          <div className="space-y-6">
            {/* Mode Selector */}
            <div className="flex space-x-2 p-1 bg-gray-100 dark:bg-gray-800 rounded-lg">
              <button
                type="button"
                onClick={() => handleWebfetchModeChange('scrape')}
                className={`flex-1 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                  webfetchMode === 'scrape'
                    ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                Scrape (Single Page)
              </button>
              <button
                type="button"
                onClick={() => handleWebfetchModeChange('crawl')}
                className={`flex-1 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                  webfetchMode === 'crawl'
                    ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                Crawl (Multiple Pages)
              </button>
            </div>

            {/* Notification */}
            {validationResult.status && (
              <div className={`rounded-lg p-4 ${
                validationResult.status === 'success'
                  ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800'
                  : validationResult.status === 'loading'
                  ? 'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800'
                  : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800'
              }`}>
                <div className="flex">
                  {validationResult.status === 'success' ? (
                    <CheckCircleIcon className="w-5 h-5 text-green-400 flex-shrink-0" />
                  ) : validationResult.status === 'loading' ? (
                    <div className="h-5 w-5 rounded-full border-2 border-t-blue-500 border-r-blue-500 border-b-blue-500 border-l-transparent animate-spin flex-shrink-0"></div>
                  ) : (
                    <ExclamationCircleIcon className="w-5 h-5 text-red-400 flex-shrink-0" />
                  )}
                  <div className="ml-3">
                    <p className={`text-sm font-medium ${
                      validationResult.status === 'success'
                        ? 'text-green-800 dark:text-green-200'
                        : validationResult.status === 'loading'
                        ? 'text-blue-800 dark:text-blue-200'
                        : 'text-red-800 dark:text-red-200'
                    }`}>
                      {validationResult.message}
                    </p>
                  </div>
                </div>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-4">
                <h4 className="text-sm font-medium text-gray-900 dark:text-white">
                  Firecrawl Configuration
                </h4>

                {/* API Key (always required) */}
                <div>
                  <label htmlFor="api_key" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Firecrawl API Key
                    <span className="text-red-500 ml-1">*</span>
                  </label>
                  <input
                    type="password"
                    id="api_key"
                    name="api_key"
                    required
                    value={formData.api_key || ''}
                    onChange={(e) => handleInputChange('api_key', e.target.value)}
                    placeholder="fc-xxxxxxxxxxxxxxxxxxxx"
                    className="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-lime-500 focus:border-lime-500 bg-transparent dark:bg-gray-700 dark:text-white text-sm font-mono"
                  />
                  <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                    Get your API key at{' '}
                    <a
                      href="https://firecrawl.dev"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-lime-600 dark:text-lime-400 hover:underline"
                    >
                      firecrawl.dev
                    </a>
                  </p>
                </div>

                {/* Mode-specific fields */}
                {webfetchMode === 'scrape' ? (
                  <div>
                    <label htmlFor="url" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      URL to Scrape
                      <span className="text-red-500 ml-1">*</span>
                    </label>
                    <input
                      type="url"
                      id="url"
                      name="url"
                      required
                      value={formData.url || ''}
                      onChange={(e) => handleInputChange('url', e.target.value)}
                      placeholder="https://example.com/page"
                      className="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-lime-500 focus:border-lime-500 bg-transparent dark:bg-gray-700 dark:text-white text-sm"
                    />
                    <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                      Enter the full URL of the page you want to scrape
                    </p>
                  </div>
                ) : (
                  <>
                    <div>
                      <label htmlFor="start_url" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Starting URL
                        <span className="text-red-500 ml-1">*</span>
                      </label>
                      <input
                        type="url"
                        id="start_url"
                        name="start_url"
                        required
                        value={formData.start_url || ''}
                        onChange={(e) => handleInputChange('start_url', e.target.value)}
                        placeholder="https://example.com"
                        className="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-lime-500 focus:border-lime-500 bg-transparent dark:bg-gray-700 dark:text-white text-sm"
                      />
                      <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                        The starting URL for the crawl
                      </p>
                    </div>

                    <div>
                      <label htmlFor="max_pages" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Max Pages
                      </label>
                      <input
                        type="number"
                        id="max_pages"
                        name="max_pages"
                        min="1"
                        max="1000"
                        value={formData.max_pages || '100'}
                        onChange={(e) => {
                          const value = e.target.value;
                          // Validate the value is within range
                          const numValue = parseInt(value, 10);
                          if (value === '' || (numValue >= 1 && numValue <= 1000)) {
                            handleInputChange('max_pages', value);
                          }
                        }}
                        placeholder="100"
                        className="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-lime-500 focus:border-lime-500 bg-transparent dark:bg-gray-700 dark:text-white text-sm"
                      />
                      <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                        Maximum number of pages to crawl (1-1000, default: 100)
                      </p>
                    </div>
                  </>
                )}

                {/* Info note */}
                <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
                  <div className="flex items-start space-x-2">
                    <svg className="w-4 h-4 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <p className="text-xs text-blue-800 dark:text-blue-200">
                      {webfetchMode === 'scrape'
                        ? 'The page will be scraped when you start scanning.'
                        : 'The site will be crawled when you start scanning. Large crawls may take several minutes.'
                      }
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex justify-end space-x-3 pt-4">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-sm font-medium rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={fetcher.state === 'submitting'}
                  className="px-4 py-2 text-sm font-medium rounded-lg bg-lime-600 text-white hover:bg-lime-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lime-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {fetcher.state === 'submitting' ? 'Connecting...' : 'Add Web Fetch'}
                </button>
              </div>
            </form>
          </div>
        ) : (
          <>
            {/* Notification */}
            {validationResult.status && validationResult.status !== 'loading' && (
          <div className={`rounded-lg p-4 ${
            validationResult.status === 'success'
              ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800'
              : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800'
          }`}>
            <div className="flex items-start">
              {validationResult.status === 'success' ? (
                <CheckCircleIcon className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" />
              ) : (
                <ExclamationCircleIcon className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              )}
              <div className="ml-3 flex-1">
                {validationResult.status === 'error' ? (
                  <div className="text-sm">
                    {(() => {
                      const message = validationResult.message || "";

                      // Check for encoding errors
                      if (message.includes("utf-8") || message.includes("codec") || message.includes("decode")) {
                        return (
                          <>
                            <p className="font-ui font-semibold text-red-900 dark:text-red-100 mb-1">
                              File Encoding Error
                            </p>
                            <p className="font-body text-red-700 dark:text-red-300">
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
                            <p className="font-ui font-semibold text-red-900 dark:text-red-100 mb-1">
                              File Too Large
                            </p>
                            <p className="font-body text-red-700 dark:text-red-300">
                              Please try uploading a smaller file or split it into multiple files.
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

                      // Check for invalid CSV format
                      if (message.includes("Invalid CSV") || message.includes("parse") || message.includes("format")) {
                        return (
                          <>
                            <p className="font-ui font-semibold text-red-900 dark:text-red-100 mb-1">
                              Invalid CSV Format
                            </p>
                            <p className="font-body text-red-700 dark:text-red-300">
                              Please ensure your file is a valid CSV file with properly formatted data.
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

                      // Default error message
                      return (
                        <p className="font-body text-red-800 dark:text-red-200">
                          {message}
                        </p>
                      );
                    })()}
                  </div>
                ) : (
                  <p className="text-sm font-body text-green-800 dark:text-green-200">
                    {validationResult.message}
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Loading State */}
        {validationResult.status === 'loading' && (
          <div className="rounded-lg p-4 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-700">
            <div className="flex items-center">
              <div className="h-5 w-5 rounded-full border-2 border-t-purple-500 border-r-purple-500 border-b-purple-500 border-l-transparent animate-spin flex-shrink-0"></div>
              <p className="ml-3 text-sm font-body text-purple-800 dark:text-purple-200">
                {validationResult.message}
              </p>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* File Upload Area for File-based Data Sources */}
          {isFileDataSource && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Upload File
              </label>
              <div
                className={`relative border-2 border-dashed rounded-lg p-6 transition-colors ${
                  dragActive
                    ? 'border-lime-400 bg-lime-50 dark:bg-lime-900/20'
                    : uploadedFiles.length > 0
                    ? 'border-green-300 bg-green-50 dark:bg-green-900/20'
                    : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
                }`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
              >
                {/* Only show the invisible file input when there are no files */}
                {uploadedFiles.length === 0 && (
                  <input
                    type="file"
                    multiple
                    accept={getAcceptedFileTypes()}
                    onChange={handleFileInputChange}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  />
                )}
                
                {uploadedFiles.length > 0 ? (
                  <div className="text-center">
                    <DocumentIcon className="mx-auto h-12 w-12 text-green-400" />
                    <div className="mt-4 max-h-40 overflow-y-auto">
                      {uploadedFiles.map((file, index) => (
                        <div key={`${file.name}-${index}`} className="flex items-center justify-between py-1 border-b border-gray-100 dark:border-gray-700 last:border-0">
                          <div className="text-left">
                            <p className="text-sm font-medium text-gray-900 dark:text-white truncate max-w-xs">
                              {file.name}
                            </p>
                            <p className="text-xs text-gray-500 dark:text-gray-400">
                              {(file.size / 1024 / 1024).toFixed(2)} MB
                            </p>
                          </div>
                          <button
                            type="button"
                            onClick={() => {
                              const newFiles = [...uploadedFiles];
                              newFiles.splice(index, 1);
                              setUploadedFiles(newFiles);
                              
                              // Update form data if there are still files, or clear if empty
                              if (newFiles.length > 0) {
                                setFormData(prev => ({
                                  ...prev,
                                  filename: newFiles[0].name,
                                  file_size: newFiles[0].size.toString(),
                                  mime_type: newFiles[0].type
                                }));
                              } else {
                                setFormData(prev => {
                                  const { filename, file_size, mime_type, ...rest } = prev;
                                  return rest;
                                });
                              }
                            }}
                            className="text-sm text-red-600 hover:text-red-500"
                          >
                            <XMarkIcon className="h-4 w-4" />
                          </button>
                        </div>
                      ))}
                    </div>
                    <div className="mt-2 flex space-x-4 justify-center">
                      <button
                        type="button"
                        onClick={() => {
                          setUploadedFiles([]);
                          setFormData(prev => {
                            const { filename, file_size, mime_type, ...rest } = prev;
                            return rest;
                          });
                        }}
                        className="text-sm text-red-600 hover:text-red-500"
                      >
                        Remove all files
                      </button>
                      
                      <label className="text-sm text-chicoryGreen-900 hover:text-chicoryGreen-400 cursor-pointer">
                        Add more files
                        <input
                          type="file"
                          multiple
                          accept={getAcceptedFileTypes()}
                          onChange={handleFileInputChange}
                          className="hidden"
                        />
                      </label>
                    </div>
                  </div>
                ) : (
                  <div className="text-center">
                    <CloudArrowUpIcon className="mx-auto h-12 w-12 text-gray-400" />
                    <div className="mt-4">
                      <p className="text-sm font-medium text-gray-900 dark:text-white">
                        Drop your files here, or click to browse
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        Supports {getFileTypeDescription()} (up to 10 files)
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Configuration Fields for Connection-based Data Sources */}
          {!isFileDataSource && dataSourceType.required_fields && (
            <div className="space-y-4">
              <h4 className="text-sm font-medium text-gray-900 dark:text-white">
                Connection Configuration
              </h4>

              {/* Instructional note for S3, Glue and DataZone */}
              {(dataSourceType.id === 'glue' || dataSourceType.id === 'datazone' || dataSourceType.id === 's3') && (
                <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-3">
                  <div className="flex items-start space-x-2">
                    <svg className="w-4 h-4 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <p className="text-xs text-yellow-800 dark:text-yellow-200">
                      After creating the CloudFormation stack using the links above, fill in the required information below to complete the integration.
                    </p>
                  </div>
                </div>
              )}

              {/* Simplified JSON File Upload for BigQuery and Google Drive */}
              {supportsJsonCredentials ? (
                <>
                  {/* JSON File Upload */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Service Account JSON File
                      <span className="text-red-500 ml-1">*</span>
                    </label>
                    <div className="flex items-center space-x-3">
                      <label className="flex-1 cursor-pointer">
                        <div className={`border-2 border-dashed rounded-lg p-4 text-center transition-colors ${
                          jsonFile 
                            ? 'border-green-300 bg-green-50 dark:bg-green-900/20'
                            : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
                        }`}>
                          {jsonFile ? (
                            <div className="flex items-center justify-center space-x-2">
                              <CheckCircleIcon className="w-5 h-5 text-green-500" />
                              <span className="text-sm text-gray-700 dark:text-gray-300">
                                {jsonFile.name}
                              </span>
                            </div>
                          ) : (
                            <div>
                              <CloudArrowUpIcon className="mx-auto h-8 w-8 text-gray-400" />
                              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                                Click to upload your service account JSON file
                              </p>
                            </div>
                          )}
                        </div>
                        <input
                          type="file"
                          accept=".json,application/json"
                          onChange={handleJsonFileInputChange}
                          className="hidden"
                        />
                      </label>
                      {jsonFile && (
                        <button
                          type="button"
                          onClick={() => {
                            setJsonFile(null);
                            setFormData({});
                            setValidationResult({ status: null, message: '' });
                          }}
                          className="text-sm text-red-600 hover:text-red-500"
                        >
                          <XMarkIcon className="h-5 w-5" />
                        </button>
                      )}
                    </div>
                    {jsonFileError && (
                      <p className="mt-2 text-sm text-red-600 dark:text-red-400">
                        {jsonFileError}
                      </p>
                    )}
                    <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                      Upload your Google Cloud service account JSON file
                    </p>
                  </div>

                  {/* Dataset ID for BigQuery or Folder ID for Google Drive */}
                  {dataSourceType.id === 'bigquery' && (
                    <div>
                      <label htmlFor="dataset_id" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Dataset ID
                      </label>
                      <input
                        type="text"
                        id="dataset_id"
                        name="dataset_id"
                        value={formData.dataset_id || ''}
                        onChange={(e) => handleInputChange('dataset_id', e.target.value)}
                        placeholder="Enter BigQuery dataset ID"
                        className="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-lime-500 focus:border-lime-500 bg-transparent dark:bg-gray-700 dark:text-white text-sm"
                      />
                      <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                        Optional: Specify a default dataset ID to access
                      </p>
                    </div>
                  )}

                  {dataSourceType.id === 'google_drive' && (
                    <div>
                      <label htmlFor="folder_id" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Folder ID
                        <span className="text-red-500 ml-1">*</span>
                      </label>
                      <input
                        type="text"
                        id="folder_id"
                        name="folder_id"
                        required
                        value={formData.folder_id || ''}
                        onChange={(e) => handleInputChange('folder_id', e.target.value)}
                        placeholder="Enter Google Drive folder ID"
                        className="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-lime-500 focus:border-lime-500 bg-transparent dark:bg-gray-700 dark:text-white text-sm"
                      />
                      <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                        Google Drive folder ID to access
                      </p>
                    </div>
                  )}
                </>
              ) : (
                // For other data sources, show all required fields
                dataSourceType.required_fields.map((field) => {
                  const isSensitiveField = field.type === "password" || 
                                          field.name.toLowerCase().includes("key") || 
                                          field.name.toLowerCase().includes("token") ||
                                          field.name.toLowerCase().includes("secret");

                  return (
                    <div key={field.name}>
                      <label htmlFor={field.name} className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        {capitalizeWords(field.name)}
                        {!field.optional && <span className="text-red-500 ml-1">*</span>}
                      </label>
                      <input
                        type={isSensitiveField ? "password" : "text"}
                        id={field.name}
                        name={field.name}
                        required={!field.optional}
                        value={formData[field.name] || ''}
                        onChange={(e) => handleInputChange(field.name, e.target.value)}
                        placeholder={`Enter ${capitalizeWords(field.name)}`}
                        className="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-lime-500 focus:border-lime-500 bg-transparent dark:bg-gray-700 dark:text-white text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                      />
                      {field.description && (
                        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                          {field.description}
                        </p>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex justify-end space-x-3">
            <button
              type="button"
              onClick={onClose}
              disabled={fetcher.state !== "idle"}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 disabled:opacity-50 transition-colors"
            >
              Cancel
            </button>
            
            <button
              type="submit"
              disabled={fetcher.state !== "idle" || (isFileDataSource && uploadedFiles.length === 0)}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-lime-600 hover:bg-lime-700 text-white focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lime-500 disabled:opacity-50 transition-colors"
            >
              {fetcher.state !== "idle" ? "Processing..." :
               isFileDataSource ? "Upload & Create" : "Create"}
            </button>
          </div>
        </form>
          </>
        )}
      </div>
    </Modal>
  );
} 
