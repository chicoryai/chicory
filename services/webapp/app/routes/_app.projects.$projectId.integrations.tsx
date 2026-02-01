import type { LoaderFunctionArgs, ActionFunctionArgs, UploadHandler } from "@remix-run/node";
import { json, redirect, unstable_parseMultipartFormData } from "@remix-run/node";
import { useLoaderData, useActionData, useFetcher } from "@remix-run/react";
import { useState, useEffect } from "react";

// Heroicons
import { CheckCircleIcon, ExclamationCircleIcon } from "@heroicons/react/24/solid";

// Layout Components
import IntegrationsLayout from "~/components/integrations/layout/IntegrationsLayout";
import ContentSection from "~/components/integrations/layout/ContentSection";

// Data Source Components
import {
  ConnectedDataSourcesTable,
  AddDataSourceButton,
  AvailableIntegrationsList,
  DataBrowserPanel,
  DataPreviewDrawer
} from "~/components/integrations/data-sources";
import type { PreviewRequest } from "~/components/integrations/data-sources/DataBrowserPanel";

// Training Components
import {
  TrainingJobsList,
  StartTrainingButton,
  TrainingProgress
} from "~/components/integrations/training";

// UI Components
import { EmptyState, LoadingSpinner } from "~/components/integrations/layout";
import DataSourceEditModal from "~/components/DataSourceEditModal";
import DataSourceDeleteModal from "~/components/DataSourceDeleteModal";
import FolderFilesModal from "~/components/FolderFilesModal";

// Icons
import { 
  CircleStackIcon, 
  CpuChipIcon, 
  ExclamationTriangleIcon 
} from "@heroicons/react/24/outline";
import { getUserOrgDetails } from "~/auth/auth.server";
import { verifyProjectAccess } from "~/utils/rbac.server";

// Services and Types
import {
  getProjectDataSources,
  getDataSourceTypes,
  getProjectTrainingJobs,
  createProjectTrainingJob,
  type DataSourceCredential,
  type DataSourceTypeDefinition,
  type TrainingJob,
  testDataSourceConnection,
  validateDataSourceCredentials,
  updateProjectDataSource,
  deleteProjectDataSource,
  createProjectDataSource,
  uploadCsvDataSource,
  uploadExcelDataSource,
  uploadGenericFileDataSource,
  getDataSourceMetadata,
  type DataSourceMetadata
} from "~/services/chicory.server";

// Removed formatDate function - components now handle their own date formatting

interface LoaderData {
  projectId: string;
  dataSources: DataSourceCredential[];
  dataSourceTypes: DataSourceTypeDefinition[];
  trainingJobs: TrainingJob[];
  metadata: DataSourceMetadata;
}

interface FileUploadResult {
  name: string;
  status: "success" | "error";
  dataSourceId?: string;
  error?: string;
}

interface ActionData {
  success?: boolean;
  error?: string;
  trainingJob?: TrainingJob;
  message?: string;
  dataSourceId?: string;
  results?: FileUploadResult[];
  _action?: string;
}

interface IntegrationType extends DataSourceTypeDefinition {
  connected: boolean;
}

export async function loader({ request, params }: LoaderFunctionArgs) {
  const { projectId } = params;

  if (!projectId) {
    throw new Response("Project ID is required", { status: 400 });
  }

  // Verify user has access to this project
  await verifyProjectAccess(request, projectId);

  try {
    const [dataSources, dataSourceTypes, trainingJobs, metadata] = await Promise.all([
      getProjectDataSources(projectId),
      getDataSourceTypes(),
      getProjectTrainingJobs(projectId),
      getDataSourceMetadata(projectId)
    ]);

    const finalDataSourceTypes = getUnifiedDataSourceTypes(dataSourceTypes);

    return json<LoaderData>({
      projectId,
      dataSources,
      dataSourceTypes: finalDataSourceTypes,
      trainingJobs: trainingJobs,
      metadata
    });
  } catch (error) {
    console.error("Error loading integrations data:", error);
    throw new Response("Failed to load integrations data", { status: 500 });
  }
}

// Helper function to get unified data source types
function getUnifiedDataSourceTypes(apiDataSourceTypes: DataSourceTypeDefinition[]): DataSourceTypeDefinition[] {

  // Remove duplicates based on both id and category to preserve entries like generic_file_upload
  // that need to exist for multiple categories
  const seenCombinations = new Set<string>();
  const filteredTypes = apiDataSourceTypes.filter(type => {
    // Create a unique key combining id and category
    const key = `${type.id}-${type.category}`;
    
    // Skip duplicates based on id+category combination
    if (seenCombinations.has(key)) {
      return false;
    }
    
    seenCombinations.add(key);
    return true;
  });
  return filteredTypes;
}

// Import the new action router
import { configuredActionRouter } from "~/services/action-handlers";

export async function action({ request, params }: ActionFunctionArgs) {
  const { projectId } = params;
  const startTime = Date.now();
  const requestId = `action-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;

  try {
    console.log(`[Integration Route] [${requestId}] === NEW ACTION ROUTER ===`);
    console.log(`[Integration Route] [${requestId}] Project ID: ${projectId}`);
    console.log(`[Integration Route] [${requestId}] Request method: ${request.method}`);
    console.log(`[Integration Route] [${requestId}] Routing to new action handler architecture`);

    // Use the new action router
    const response = await configuredActionRouter.route(request);

    const duration = Date.now() - startTime;
    console.log(`[Integration Route] [${requestId}] Action router completed successfully in ${duration}ms`);
    return response;

  } catch (error) {
    const duration = Date.now() - startTime;
    console.error(`[Integration Route] [${requestId}] Action router error after ${duration}ms:`, error);

    // Fallback to legacy handler for unsupported actions (temporary)
    console.log(`[Integration Route] [${requestId}] === FALLBACK TO LEGACY HANDLER ===`);
    return handleLegacyAction(request, projectId);
  }
}

// Legacy action handler for backward compatibility during transition
async function handleLegacyAction(request: Request, projectIdFromParams?: string) {
  const legacyStartTime = Date.now();
  const legacyId = `legacy-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;

  console.log(`[Legacy Handler] [${legacyId}] Starting legacy action handler`);

  // Check content type to determine how to handle the request
  const contentType = request.headers.get("Content-Type") || "";
  console.log(`[Legacy Handler] [${legacyId}] Content-Type: ${contentType}`);

  let formData: FormData;

  // Handle file uploads (multipart/form-data)
  if (contentType.includes("multipart/form-data")) {
    console.log(`[Legacy Handler] [${legacyId}] Handling multipart/form-data request`);

    // Create a custom upload handler for files
    const uploadHandler: UploadHandler = async ({ name, filename, data, contentType }) => {
      // For non-file fields, return the text value
      if (!filename) {
        const chunks = [];
        for await (const chunk of data) {
          chunks.push(chunk);
        }
        return Buffer.concat(chunks).toString();
      }

      // Only process the file field with a filename
      if (name !== "file") {
        return undefined;
      }

      console.log(`[Legacy Handler] [${legacyId}] Processing file upload: ${filename} (${contentType})`);

      // Collect file chunks
      const chunks = [];
      for await (const chunk of data) {
        chunks.push(chunk);
      }

      // Create a File object from the chunks
      return new File(chunks, filename, { type: contentType });
    };

    // Parse the multipart form data
    formData = await unstable_parseMultipartFormData(request, uploadHandler);
  } else {
    // Handle regular form data
    formData = await request.formData();
  }

  const actionType = formData.get("_action");
  let projectId = projectIdFromParams || (formData.get("projectId") as string);

  console.log(`[Legacy Handler] [${legacyId}] Action type: ${actionType}`);
  console.log(`[Legacy Handler] [${legacyId}] Project ID: ${projectId}`);

  if (!projectId) {
    const userDetails = await getUserOrgDetails(request);
    if (userDetails instanceof Response) {
      return userDetails;
    }
    return json<ActionData>({ error: "Project ID is required" }, { status: 400 });
  }
  
  console.log("Form data entries (legacy):");
  for (const [key, value] of formData.entries()) {
    if (value instanceof File) {
      console.log(`  ${key}: File(${value.name}, ${value.size} bytes, ${value.type})`);
    } else {
      console.log(`  ${key}: ${value}`);
    }
  }
  console.log("Action type:", actionType);
  console.log("Project ID:", projectId);
  
  if (!projectId) {
    console.log("ERROR: Project ID is required");
    return json<ActionData>({ error: "Project ID is required" }, { status: 400 });
  }

  try {
    switch (actionType) {
      case "testConnection": {
        console.log("--- TEST CONNECTION ACTION ---");
        const dataSourceId = formData.get("dataSourceId") as string;
        console.log("Data source ID:", dataSourceId);
        
        if (!dataSourceId) {
          console.log("ERROR: Data source ID is required");
          return json<ActionData>({ 
            error: "Data source ID is required" 
          }, { status: 400 });
        }

        console.log(`Calling testDataSourceConnection with projectId: ${projectId}, dataSourceId: ${dataSourceId}`);
        
        try {
          const result = await testDataSourceConnection(projectId, dataSourceId);
          console.log("Test connection result:", result);

          const response = { 
            success: result.success,
            message: result.message,
            dataSourceId,
            _action: "testConnection"
          };
          console.log("Returning response:", response);

          return json<ActionData>(response);
        } catch (testError) {
          console.error("Error during testDataSourceConnection:", testError);
          return json<ActionData>({ 
            success: false,
            error: testError instanceof Error ? testError.message : "Test connection failed",
            message: testError instanceof Error ? testError.message : "Test connection failed",
            dataSourceId,
            _action: "testConnection"
          }, { status: 500 });
        }
      }

      case "startTraining": {
        console.log("--- START TRAINING ACTION ---");
        const modelName = formData.get("modelName") as string;
        const dataSourceIds = formData.getAll("dataSourceIds") as string[];
        
        console.log("Model name:", modelName);
        console.log("Data source IDs:", dataSourceIds);
        
        if (!modelName || dataSourceIds.length === 0) {
          console.log("ERROR: Model name and at least one data source are required");
          return json<ActionData>({ 
            error: "Model name and at least one data source are required" 
          }, { status: 400 });
        }

        console.log(`Calling createProjectTrainingJob with projectId: ${projectId}, modelName: ${modelName}, dataSourceIds: ${dataSourceIds}`);
        
        try {
          const trainingJob = await createProjectTrainingJob(
            projectId,
            modelName,
            dataSourceIds
          );
          console.log("Training job created:", trainingJob);

          const response = { 
            success: true, 
            trainingJob 
          };
          console.log("Returning response:", response);

          return json<ActionData>(response);
        } catch (trainingError) {
          console.error("Error during createProjectTrainingJob:", trainingError);
          return json<ActionData>({ 
            error: trainingError instanceof Error ? trainingError.message : "Failed to start training"
          }, { status: 500 });
        }
      }

      case "editDataSource": {
        console.log("--- EDIT DATA SOURCE ACTION ---");
        const dataSourceId = formData.get("dataSourceId") as string;
        const dataSourceTypeId = formData.get("dataSourceTypeId") as string;
        const name = formData.get("name") as string;
        
        console.log("Data source ID:", dataSourceId);
        console.log("Data source type ID:", dataSourceTypeId);
        console.log("Name:", name);
        
        if (!dataSourceId || !dataSourceTypeId) {
          console.log("ERROR: Data source ID and type ID are required");
          return json<ActionData>({ 
            error: "Data source ID and type ID are required" 
          }, { status: 400 });
        }

        try {
          // Get the data source type to know which fields to extract
          const apiDataSourceTypes = await getDataSourceTypes();
          const dataSourceTypes = getUnifiedDataSourceTypes(apiDataSourceTypes);
          const dataSourceType = dataSourceTypes.find(ds => ds.id === dataSourceTypeId);
          
          if (!dataSourceType) {
            console.log("ERROR: Invalid data source type");
            return json<ActionData>({ 
              error: "Invalid data source type" 
            }, { status: 400 });
          }

          // Build configuration object from form data based on required fields
          const configuration: Record<string, any> = {};
          for (const field of dataSourceType.required_fields) {
            const value = formData.get(field.name);
            if (!field.optional && !value) {
              console.log(`ERROR: Missing required field: ${field.name}`);
              return json<ActionData>({ 
                error: `Missing required field: ${field.name}` 
              }, { status: 400 });
            }
            if (value) {
              configuration[field.name] = value;
            }
          }

          

          // Update the data source
          const updatedDataSource = await updateProjectDataSource(
            projectId,
            dataSourceId,
            name,
            configuration
          );
          

          const response = { 
            success: true,
            message: "Data source updated successfully",
            dataSourceId,
            _action: "editDataSource"
          };
          

          return json<ActionData>(response);
        } catch (updateError) {
          console.error("Error during updateProjectDataSource:", updateError);
          return json<ActionData>({ 
            success: false,
            error: updateError instanceof Error ? updateError.message : "Failed to update data source",
            message: updateError instanceof Error ? updateError.message : "Failed to update data source",
            dataSourceId,
            _action: "editDataSource"
          }, { status: 500 });
        }
      }

      case "validateCredentials": {
        console.log("--- VALIDATE CREDENTIALS ACTION ---");
        const dataSourceTypeId = formData.get("dataSourceTypeId") as string;
        
        
        if (!dataSourceTypeId) {
          console.log("ERROR: Data source type ID is required");
          return json<ActionData>({ 
            error: "Data source type ID is required" 
          }, { status: 400 });
        }

        try {
          // Get the data source type to know which fields to extract
          const apiDataSourceTypes = await getDataSourceTypes();
          const dataSourceTypes = getUnifiedDataSourceTypes(apiDataSourceTypes);
          const dataSourceType = dataSourceTypes.find(ds => ds.id === dataSourceTypeId);
          
          if (!dataSourceType) {
            console.log("ERROR: Invalid data source type");
            return json<ActionData>({ 
              error: "Invalid data source type" 
            }, { status: 400 });
          }

          // Build configuration object from form data based on required fields
          const configuration: Record<string, any> = {};
          for (const field of dataSourceType.required_fields) {
            const value = formData.get(field.name);
            if (!field.optional && !value) {
              console.log(`ERROR: Missing required field: ${field.name}`);
              return json<ActionData>({ 
                error: `Missing required field: ${field.name}` 
              }, { status: 400 });
            }
            if (value) {
              configuration[field.name] = value;
            }
          }

          console.log("Configuration for validation:", configuration);

          // Validate the credentials
          const result = await validateDataSourceCredentials(
            dataSourceTypeId,
            configuration
          );
          
          console.log("Validation result:", result);

          const response = { 
            success: result.success,
            message: result.message,
            _action: "validateCredentials"
          };
          console.log("Returning response:", response);

          return json<ActionData>(response);
        } catch (validationError) {
          console.error("Error during validateDataSourceCredentials:", validationError);
          return json<ActionData>({ 
            success: false,
            error: validationError instanceof Error ? validationError.message : "Failed to validate credentials",
            message: validationError instanceof Error ? validationError.message : "Failed to validate credentials",
            _action: "validateCredentials"
          }, { status: 500 });
        }
      }

      case "deleteDataSource": {
        console.log("--- DELETE DATA SOURCE ACTION ---");
        const dataSourceId = formData.get("dataSourceId") as string;
        const deleteS3Object = formData.get("deleteS3Object") === "true";
        
        console.log("Data source ID:", dataSourceId);
        console.log("Delete S3 object:", deleteS3Object);
        
        if (!dataSourceId) {
          console.log("ERROR: Data source ID is required");
          return json<ActionData>({ 
            error: "Data source ID is required" 
          }, { status: 400 });
        }

        try {
          // Delete the data source
          const success = await deleteProjectDataSource(
            projectId,
            dataSourceId,
            deleteS3Object
          );
          
          console.log("Data source deletion result:", success);

          if (success) {
            const response = { 
              success: true,
              message: "Data source deleted successfully",
              dataSourceId,
              _action: "deleteDataSource"
            };
            console.log("Returning response:", response);

            return json<ActionData>(response);
          } else {
            return json<ActionData>({ 
              success: false,
              error: "Failed to delete data source",
              message: "Failed to delete data source",
              dataSourceId,
              _action: "deleteDataSource"
            }, { status: 500 });
          }
        } catch (deleteError) {
          console.error("Error during deleteProjectDataSource:", deleteError);
          return json<ActionData>({ 
            success: false,
            error: deleteError instanceof Error ? deleteError.message : "Failed to delete data source",
            message: deleteError instanceof Error ? deleteError.message : "Failed to delete data source",
            dataSourceId,
            _action: "deleteDataSource"
          }, { status: 500 });
        }
      }

      case "createDataSource": {
        console.log("--- CREATE DATA SOURCE ACTION ---");
        const dataSourceTypeId = formData.get("dataSourceTypeId") as string;
        const name = formData.get("name") as string;
        const file = formData.get("file") as File;
        
        console.log("Data source type ID:", dataSourceTypeId);
        console.log("Name:", name);
        console.log("File:", file ? `${file.name} (${file.size} bytes, ${file.type})` : "No file");
        console.log("File instanceof File:", file instanceof File);
        console.log("File constructor:", file?.constructor?.name);
        
        if (!dataSourceTypeId || !name) {
          console.log("ERROR: Data source type ID and name are required");
          return json<ActionData>({ 
            success: false,
            error: "Data source type ID and name are required",
            _action: "createDataSource" 
          }, { status: 400 });
        }

        try {
          // Get the data source type to know which fields to extract
          const apiDataSourceTypes = await getDataSourceTypes();
          const dataSourceTypes = getUnifiedDataSourceTypes(apiDataSourceTypes);
          const dataSourceType = dataSourceTypes.find(ds => ds.id === dataSourceTypeId);
          
          if (!dataSourceType) {
            console.log("ERROR: Invalid data source type");
            return json<ActionData>({ 
              success: false,
              error: "Invalid data source type",
              _action: "createDataSource" 
            }, { status: 400 });
          }

          // Check if this is a file-based data source
          const fileDataSources = ['csv_upload', 'xlsx_upload', 'generic_file_upload'];
          const isFileDataSource = fileDataSources.includes(dataSourceTypeId);

          let createdDataSource;

          if (isFileDataSource) {
            if (!file || !(file instanceof File)) {
              console.log("ERROR: File is required for file-based data sources");
              console.log("File type:", typeof file);
              console.log("File value:", file);
              return json<ActionData>({ 
                success: false,
                error: "File is required for file-based data sources",
                _action: "createDataSource" 
              }, { status: 400 });
            }

            console.log(`Processing file upload for ${dataSourceTypeId}`);
            
            // Handle file upload data sources
            switch (dataSourceTypeId) {
              case 'csv_upload':
                createdDataSource = await uploadCsvDataSource(projectId, name, file);
                break;
              case 'xlsx_upload':
                createdDataSource = await uploadExcelDataSource(projectId, name, file);
                break;
              case 'generic_file_upload':
                // Auto-detect file type and route to appropriate handler
                const fileName = file.name.toLowerCase();
                const fileType = file.type.toLowerCase();
                
                if (fileName.endsWith('.csv') || fileType.includes('csv')) {
                  console.log('Detected CSV file, routing to CSV upload');
                  createdDataSource = await uploadCsvDataSource(projectId, name, file);
                } else if (fileName.endsWith('.xlsx') || fileName.endsWith('.xls') || fileType.includes('spreadsheet') || fileType.includes('excel')) {
                  console.log('Detected Excel file, routing to Excel upload');
                  createdDataSource = await uploadExcelDataSource(projectId, name, file);
                } else {
                  console.log('Detected generic file, routing to generic upload');
                  // Determine category based on file type
                  const category = fileName.endsWith('.pdf') || fileName.endsWith('.doc') || fileName.endsWith('.docx') || fileName.endsWith('.txt') || fileName.endsWith('.md') ? 'document' : 'document';
                  createdDataSource = await uploadGenericFileDataSource(projectId, name, file, category);
                }
                break;
              default:
                throw new Error(`Unsupported file data source type: ${dataSourceTypeId}`);
            }
          } else {
            // Handle connection-based data sources
            const configuration: Record<string, any> = {};
            for (const field of dataSourceType.required_fields) {
              const value = formData.get(field.name);
              if (!field.optional && !value) {
                console.log(`ERROR: Missing required field: ${field.name}`);
                return json<ActionData>({ 
                  success: false,
                  error: `Missing required field: ${field.name}`,
                  _action: "createDataSource" 
                }, { status: 400 });
              }
              if (value) {
                configuration[field.name] = value;
              }
            }

            console.log("Configuration:", configuration);

            // Create the data source directly without validation
            console.log("Creating data source...");

            createdDataSource = await createProjectDataSource(
              projectId,
              dataSourceTypeId,
              name,
              configuration
            );
          }
          
          console.log("Data source created:", createdDataSource);

          const response = { 
            success: true,
            message: "Data source created successfully",
            dataSourceId: createdDataSource.id,
            _action: "createDataSource"
          };
          console.log("Returning response:", response);

          return json<ActionData>(response);
        } catch (createError) {
          console.error("Error during createDataSource:", createError);
          return json<ActionData>({ 
            success: false,
            error: createError instanceof Error ? createError.message : "Failed to create data source",
            message: createError instanceof Error ? createError.message : "Failed to create data source",
            _action: "createDataSource"
          }, { status: 500 });
        }
      }

      case "uploadCsv": {
        console.log("--- UPLOAD CSV FILES ACTION ---");
        const projectId = formData.get("projectId")?.toString() || "";
        const name = formData.get("name")?.toString() || "";
        const description = formData.get("description")?.toString() || undefined;
        
        // Get all files from the 'file' field in the form data (which is what we use in the frontend for both single and multi-file uploads)
        let filesEntries = formData.getAll("file");
        
        // Log all form entries for debugging
        console.log("All form entries:");
        for (const [key, value] of formData.entries()) {
          const valueType = Object.prototype.toString.call(value);
          if (valueType === '[object File]' || valueType === '[object Blob]') {
            console.log(`  ${key}: File(${(value as any).name || 'blob'}, ${(value as Blob).size} bytes)`);
          } else {
            console.log(`  ${key}: ${String(value)}`);
          }
        }
        
        console.log("Project ID:", projectId);
        console.log("Name base:", name);
        const possibleFieldNames = ['file', 'files', 'files[]'];
        let allFiles: any[] = [];
        for (const fieldName of possibleFieldNames) {
          const files = formData.getAll(fieldName);
          for (const file of files) {
            // Check if file is a File or Blob using a safer approach
            const isFileOrBlob = file && (typeof file === 'object') && 
              (Object.prototype.toString.call(file) === '[object File]' || 
               Object.prototype.toString.call(file) === '[object Blob]');
               
            if (isFileOrBlob) {
              allFiles.push(file);
              console.log(`Found file in '${fieldName}': ${(file as any).name || 'blob'}, ${(file as Blob).size} bytes, ${(file as any).type || 'unknown type'}`);
            }
          }
        }
        if (allFiles.length > 0) {
          filesEntries = allFiles;
        }
        console.log("Project ID:", projectId);
        console.log("Name base:", name);
        console.log("Description:", description);
        console.log("Number of files from 'files[]':", filesEntries.length);
        
        // Comprehensive attempt to get files from the form data
        // Try all possible field names and create a combined array
        // We prioritize 'file' since that's what we're using in the frontend now
        if (!projectId || !name) {
          console.log("ERROR: Project ID and name are required");
          return json<ActionData>({ 
            success: false,
            error: "Project ID and name are required",
            _action: "uploadCsv" 
          }, { status: 400 });
        }
        if (filesEntries.length === 0) {
          console.log("ERROR: No files provided");
          return json<ActionData>({ 
            success: false,
            error: "No files provided",
            _action: "uploadCsv" 
          }, { status: 400 });
        }  
        // Check one more time by looking at ALL form entries for ANY file
        if (filesEntries.length === 0) {
          console.log("Trying one last approach - checking all form entries for files");
          for (const [key, value] of formData.entries()) {
            const valueType = Object.prototype.toString.call(value);
            if (valueType === '[object File]' || valueType === '[object Blob]') {
              const fileObj = value as File;
              if (fileObj && fileObj.size > 0) {
                console.log(`Found file in unexpected field '${key}': ${(fileObj as any).name || 'blob'}, ${fileObj.size} bytes`);
                filesEntries.push(fileObj);
              }
            }
          }
        }
        
        console.log("Final file count after exhaustive search:", filesEntries.length);
        
        if (!projectId || !name) {
          console.log("ERROR: Project ID and name are required");
          return json<ActionData>({ 
            success: false,
            error: "Project ID and name are required",
            _action: "uploadCsv" 
          }, { status: 400 });
        }
        
        if (filesEntries.length === 0) {
          console.log("ERROR: No files provided");
          return json<ActionData>({ 
            success: false,
            error: "No files provided",
            _action: "uploadCsv" 
          }, { status: 400 });
        }
        
        if (filesEntries.length > 10) {
          console.log("ERROR: Too many files (max 10)");
          return json<ActionData>({ 
            success: false,
            error: "Maximum 10 files can be uploaded at once",
            _action: "uploadCsv" 
          }, { status: 400 });
        }
        
        try {
          // Process each file and collect results
          const uploadPromises: Promise<FileUploadResult>[] = [];
          
          // Process each file
          for (let i = 0; i < filesEntries.length; i++) {
            const file = filesEntries[i] as File;
            
            if (!file || !(file instanceof File)) {
              console.log(`ERROR: File ${i} is not a valid file:`, file);
              uploadPromises.push(Promise.resolve({
                name: `File ${i}`,
                status: "error",
                error: "Invalid file format"
              }));
              continue;
            }
            
            // Generate a unique name for each file if multiple files
            const fileName = file.name;
            const uniqueName = filesEntries.length > 1 
              ? `${fileName}` 
              : name;
            
            // Get data source type from form
            const dataSourceTypeId = formData.get("dataSourceTypeId") as string || "csv_upload";
            console.log(`Processing file ${i+1}/${filesEntries.length}: ${fileName} as ${uniqueName} with type ${dataSourceTypeId}`);
            
            // Create upload promise based on the data source type
            let uploadPromise;
            
            if (dataSourceTypeId === 'generic_file_upload') {
              // For generic files like markdown, pdf, etc.
              console.log(`Using generic file upload for ${fileName}`);
              uploadPromise = createProjectDataSource(
                projectId,
                dataSourceTypeId,
                uniqueName,
                { file_upload: true }
              )
              .then(dataSource => ({
                name: fileName,
                status: "success" as const,
                dataSourceId: dataSource.id
              }))
              .catch(error => ({
                name: fileName,
                status: "error" as const,
                error: error?.message || "Failed to upload file"
              }));
            } else if (dataSourceTypeId === 'xlsx_upload') {
              // For Excel files
              console.log(`Using Excel file upload for ${fileName}`);
              uploadPromise = createProjectDataSource(
                projectId,
                dataSourceTypeId,
                uniqueName,
                { file_upload: true }
              )
              .then(dataSource => ({
                name: fileName,
                status: "success" as const,
                dataSourceId: dataSource.id
              }))
              .catch(error => ({
                name: fileName,
                status: "error" as const,
                error: error?.message || "Failed to upload Excel file"
              }));
            } else {
              // Default to CSV upload for csv_upload type
              console.log(`Using CSV upload for ${fileName}`);
              uploadPromise = uploadCsvDataSource(projectId, uniqueName, file, description)
                .then(dataSource => ({
                  name: fileName,
                  status: "success" as const,
                  dataSourceId: dataSource.id
                }))
                .catch(error => ({
                  name: fileName,
                  status: "error" as const,
                  error: error?.message || "Failed to upload file"
                }));
            }
            
            uploadPromises.push(uploadPromise);
          }
          
          // Wait for all uploads to complete
          const results = await Promise.all(uploadPromises);
          console.log("Upload results:", results);
          
          // Check if any uploads succeeded
          const anySuccess = results.some(r => r.status === "success");
          
          return json<ActionData>({
            success: anySuccess,
            message: anySuccess 
              ? results.every(r => r.status === "success")
                ? "All files uploaded successfully"
                : "Some files were uploaded successfully"
              : "Failed to upload any files",
            results,
            _action: "uploadCsv"
          });
        } catch (error) {
          console.error("Error during CSV uploads:", error);
          return json<ActionData>({ 
            success: false,
            error: error instanceof Error ? error.message : "Failed to upload CSV files",
            message: error instanceof Error ? error.message : "Failed to upload CSV files",
            _action: "uploadCsv"
          }, { status: 500 });
        }
      }
      
      default:
        console.log("ERROR: Invalid action type:", actionType);
        return json<ActionData>({ 
          success: false,
          error: "Invalid action",
          _action: actionType as string
        }, { status: 400 });
      
    }
  } catch (error) {
    console.error("=== ACTION FUNCTION ERROR ===");
    console.error("Error details:", error);
    console.error("Error stack:", error instanceof Error ? error.stack : "No stack trace");
    
    return json<ActionData>({ 
      error: error instanceof Error ? error.message : "An error occurred" 
    }, { status: 500 });
  } finally {
    console.log("=== ACTION FUNCTION END ===");
  }
}

export default function IntegrationsPage() {
  const { projectId, dataSources, dataSourceTypes, trainingJobs, metadata } = useLoaderData<typeof loader>();
  const actionData = useActionData<typeof action>();

  // Use two separate fetchers - one for training jobs and one for form submissions
  const trainingJobsFetcher = useFetcher<typeof loader>();
  const formFetcher = useFetcher();
  
  // Use Remix's fetched data or fallback to loader data
  const currentTrainingJobs = trainingJobsFetcher.data?.trainingJobs || trainingJobs;
  
  // State for data source modals
  const [editingDataSource, setEditingDataSource] = useState<DataSourceCredential | null>(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [deletingDataSource, setDeletingDataSource] = useState<DataSourceCredential | null>(null);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [viewingFolderDataSource, setViewingFolderDataSource] = useState<DataSourceCredential | null>(null);
  const [isFolderFilesModalOpen, setIsFolderFilesModalOpen] = useState(false);
  
  // State for data preview drawer
  const [previewParams, setPreviewParams] = useState<PreviewRequest | null>(null);

  // State for notification alerts
  const [alert, setAlert] = useState<{status: 'success' | 'error' | null, message: string}>({ 
    status: null, 
    message: '' 
  });
  const [alertDismissing, setAlertDismissing] = useState(false);

  // Handle GitHub OAuth callback messages from URL params
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const urlParams = new URLSearchParams(window.location.search);
      const success = urlParams.get('success');
      const error = urlParams.get('error');
      const username = urlParams.get('username');
      const message = urlParams.get('message');

      if (success === 'github_connected' && username) {
        setAlert({
          status: 'success',
          message: `Successfully connected GitHub account @${username}!`
        });
        
        // Clean up URL params
        window.history.replaceState({}, '', window.location.pathname);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
          dismissAlert();
        }, 5000);
      } else if (error === 'github_oauth_failed') {
        setAlert({
          status: 'error',
          message: message || 'Failed to connect GitHub account'
        });
        
        // Clean up URL params
        window.history.replaceState({}, '', window.location.pathname);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
          dismissAlert();
        }, 5000);
      }
    }
  }, []);

  // Function to handle animated alert dismissal
  const dismissAlert = () => {
    setAlertDismissing(true);
    setTimeout(() => {
      setAlert({ status: null, message: '' });
      setAlertDismissing(false);
    }, 300); // Match the animation duration
  };

  // Refresh training jobs data when form is submitted successfully
  useEffect(() => {
    if (formFetcher.state === "idle" && 
        formFetcher.data && 
        typeof formFetcher.data === 'object' &&
        formFetcher.data !== null &&
        'trainingJob' in formFetcher.data &&
        (formFetcher.data as ActionData)._action === "startTraining") {
      // Instead of fetching, just update local state or show a message
      console.log("Training job started successfully");
      // Don't call trainingJobsFetcher.load("/integrations");
    }
  }, [formFetcher.state, formFetcher.data]);
  
  // Update when action data changes (redirect from another form)
  useEffect(() => {
    if (actionData?.trainingJob) {
      // Instead of fetching, just update local state
      console.log("Training job data received");
      // Don't call trainingJobsFetcher.load("/integrations");
    }
  }, [actionData]);
  
  // Update alert when form submission completes
  useEffect(() => {
    // Check if we have a completed form submission with data
    if (formFetcher.state === "idle" && formFetcher.data) {
      // Type assertion for formFetcher.data
      const data = formFetcher.data as ActionData;
      
      console.log("=== ACTION RESPONSE DEBUG ===");
      console.log("Action data:", data);
      console.log("Action:", data._action);
      console.log("Success:", data.success);
      console.log("Error:", data.error);
      
      // Handle training job results
      if (data._action === "startTraining") {
        if (data.success) {
          setAlert({
            status: 'success',
            message: "Training started successfully!"
          });
        } else if (data.error) {
          console.error("Training failed with error:", data.error);
          setAlert({
            status: 'error',
            message: data.error || "Failed to start training"
          });
        } else {
          console.error("Unknown training response:", data);
          setAlert({
            status: 'error',
            message: "Unknown error occurred while starting training"
          });
        }
        
        // Auto-dismiss alert after 5 seconds
        setTimeout(() => {
          dismissAlert();
        }, 5000);
      }
      
      // Handle data source upload/creation/edit results
      else if (data._action === "uploadCsv" || data._action === "createDataSource" || data._action === "editDataSource") {
        if (data.success) {
          setAlert({
            status: 'success',
            message: data.message || (data._action === "editDataSource" ? "Data source updated successfully" : "Data source created successfully")
          });
        } else if (data.error) {
          setAlert({
            status: 'error',
            message: data.error || (data._action === "editDataSource" ? "Failed to update data source" : "Failed to create data source")
          });
        }
        
        // Auto-dismiss alert after 5 seconds
        setTimeout(() => {
          dismissAlert();
        }, 5000);
      }
    }
  }, [formFetcher.state, formFetcher.data]);

  // Handle delete success
  useEffect(() => {
    if (formFetcher.state === "idle" && formFetcher.data) {
      const data = formFetcher.data as ActionData;
      
      if (data._action === "deleteDataSource") {
        if (data.success) {
          setAlert({
            status: 'success',
            message: "Data source deleted successfully"
          });
        } else if (data.error) {
          setAlert({
            status: 'error',
            message: data.error || "Failed to delete data source"
          });
        }
        
        // Auto-dismiss alert after 5 seconds
        setTimeout(() => {
          dismissAlert();
        }, 5000);
      }
    }
  }, [formFetcher.state, formFetcher.data]);

  // Create integrations list with connection status
  const integrations: IntegrationType[] = dataSourceTypes.map(type => ({
    ...type,
    connected: dataSources.some(ds => ds.type === type.id),
    configuredSources: dataSources.filter(ds => ds.type === type.id)
  }));

  // Ensure we always use ALL available data sources for training
  const allDataSources = dataSources || [];
  const connectedDataSources = allDataSources.filter(ds => ds.id && ds.name); // Only include valid data sources
  
  const latestTrainingJob = currentTrainingJobs.length > 0 
    ? currentTrainingJobs.sort((a: TrainingJob, b: TrainingJob) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0]
    : null;

  const handleStartTraining = () => {
    console.log("=== START TRAINING DEBUG ===");
    console.log("Raw dataSources from loader:", dataSources);
    console.log("All data sources:", allDataSources);
    console.log("Connected data sources:", connectedDataSources);
    console.log("Connected data sources length:", connectedDataSources.length);
    console.log("Project ID:", projectId);
    
    // Always use ALL available data sources for training
    const dataSourcesForTraining = allDataSources.length > 0 ? allDataSources : connectedDataSources;
    
    if (dataSourcesForTraining.length === 0) {
      console.log("ERROR: No data sources available for training");
      setAlert({
        status: 'error',
        message: "No data sources found. Please connect a data source first."
      });
      return;
    }
    
    const formData = new FormData();
    formData.append("_action", "startTraining");
    formData.append("projectId", projectId);
    formData.append("modelName", `Training-${Date.now()}`);
    
    console.log("Adding ALL data source IDs for training:");
    dataSourcesForTraining.forEach((ds, index) => {
      if (ds && ds.id) {
        console.log(`  ${index}: ${ds.id} (${ds.name || 'Unknown'})`);
        formData.append("dataSourceIds[]", ds.id);
      }
    });
    
    const formEntries = Object.fromEntries(formData.entries());
    console.log("Form data entries:", formEntries);
    console.log("All dataSourceIds being sent:", formData.getAll("dataSourceIds[]"));
    console.log("Total data sources being sent:", formData.getAll("dataSourceIds[]").length);
    
    formFetcher.submit(formData, { method: "post" });
  };

  const handleRetrain = (job: TrainingJob) => {
    console.log("=== RETRAIN DEBUG ===");
    console.log("Retraining with ALL available data sources:", allDataSources.length);
    
    const formData = new FormData();
    formData.append("_action", "startTraining");
    formData.append("projectId", projectId);
    formData.append("modelName", `Retrain-${Date.now()}`);
    
    // Always use ALL available data sources for retraining
    allDataSources.forEach((ds, index) => {
      if (ds && ds.id) {
        console.log(`  Retrain DS ${index}: ${ds.id} (${ds.name || 'Unknown'})`);
        formData.append("dataSourceIds[]", ds.id);
      }
    });
    
    console.log("Retrain data sources count:", formData.getAll("dataSourceIds[]").length);
    formFetcher.submit(formData, { method: "post" });
  };

  const handleEdit = (dataSource: DataSourceCredential) => {
    setEditingDataSource(dataSource);
    setIsEditModalOpen(true);
  };

  const handleCloseEditModal = () => {
    setIsEditModalOpen(false);
    setEditingDataSource(null);
  };

  const handleDelete = (dataSource: DataSourceCredential) => {
    setDeletingDataSource(dataSource);
    setIsDeleteModalOpen(true);
  };

  const handleCloseDeleteModal = () => {
    setIsDeleteModalOpen(false);
    setDeletingDataSource(null);
  };

  const handleDeleteSuccess = () => {
    // Refresh the page to update the data sources list
  };

  const handleViewFiles = (dataSource: DataSourceCredential) => {
    setViewingFolderDataSource(dataSource);
    setIsFolderFilesModalOpen(true);
  };

  const handleCloseFolderFilesModal = () => {
    setIsFolderFilesModalOpen(false);
    setViewingFolderDataSource(null);
  };

  // Left Column Content
  const leftColumn = (
    <div className="space-y-8">
      {/* Connected Data Sources Section */}
      <ContentSection
        title="Connected Data Sources"
        description="Manage and monitor your connected data sources"
        variant="card"
        spacing="normal"
        headerAction={
          <AddDataSourceButton
            availableIntegrations={dataSourceTypes}
            projectId={projectId}

          />
        }
      >
        <ConnectedDataSourcesTable
          dataSources={connectedDataSources}
          dataSourceTypes={dataSourceTypes}
          projectId={projectId}
          onEdit={handleEdit}
          onDelete={handleDelete}
          onTest={(dataSource: DataSourceCredential) => {
            console.log("Testing data source:", dataSource);
            // The DataSourceActions component handles the actual request
            // This callback is just for logging/notification purposes
          }}
          onViewFiles={handleViewFiles}
        />
      </ContentSection>

      {/* Sandbox Data Browser */}
      {metadata.status === "available" && (
        <DataBrowserPanel
          status={metadata.status}
          lastScannedAt={metadata.last_scanned_at}
          providers={metadata.providers}
          onPreview={setPreviewParams}
        />
      )}
    </div>
  );

  // Right Column Content
  const rightColumn = (
    <div className="space-y-8">
      {/* Training Status Section */}
      <ContentSection
        variant="card"
        spacing="normal"
      >
        {latestTrainingJob ? (
          <TrainingProgress
            job={latestTrainingJob}
            onRetrain={handleRetrain}
          />
        ) : (
          <EmptyState
            icon={CpuChipIcon}
            title={connectedDataSources.length > 0 ? "Ready to Scan" : "Connect Data Sources"}
            description={connectedDataSources.length > 0
              ? "Scan your data sources to improve responses."
              : "Connect data sources first to start scanning your data."
            }
            action={connectedDataSources.length > 0 ? {
              label: "Start Scanning",
              onClick: handleStartTraining
            } : undefined}
            variant="training"
            className="py-12"
          />
        )}
      </ContentSection>

      {/* Training History Section */}
      <ContentSection
        title="Recent Data Scans"
        variant="card"
        spacing="normal"
      >
        <TrainingJobsList
          trainingJobs={currentTrainingJobs.slice(0, 3)}
          onViewDetails={(job) => {
            console.log("View job details:", job);
            // TODO: Implement view details logic
          }}
          isLoading={trainingJobsFetcher.state !== "idle"}
        />
      </ContentSection>
    </div>
  );

  return (
    <>
      {/* Enhanced Alert Banner */}
      {alert.status && (
        <div className={`mb-4 px-4 py-3 rounded-lg shadow-md border-l-4 transition-all duration-300 ease-in-out transform ${
          alertDismissing ? 'opacity-0 scale-95 translate-y-2' : 'opacity-100 scale-100 translate-y-0'
        } ${
          alert.status === 'success' 
            ? 'bg-gradient-to-r from-green-50 to-emerald-50 border-green-400 text-green-900' 
            : 'bg-gradient-to-r from-red-50 to-rose-50 border-red-400 text-red-900'
        }`} role="alert">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <div className={`flex-shrink-0 mr-3 p-0.5 rounded-full ${
                alert.status === 'success' ? 'bg-green-100' : 'bg-red-100'
              }`}>
                {alert.status === 'success' ? (
                  <CheckCircleIcon className="h-5 w-5 text-green-600" aria-hidden="true" />
                ) : (
                  <ExclamationCircleIcon className="h-5 w-5 text-red-600" aria-hidden="true" />
                )}
              </div>
              <div className="flex-1">
                <span className="font-medium text-sm">
                  {alert.status === 'success' ? 'Success: ' : 'Error: '}
                  <span className="font-normal opacity-90">{alert.message}</span>
                </span>
              </div>
            </div>
            <button
              onClick={dismissAlert}
              className={`flex-shrink-0 ml-3 p-1 rounded-full transition-colors duration-200 ${
                alert.status === 'success' 
                  ? 'hover:bg-green-200 text-green-600' 
                  : 'hover:bg-red-200 text-red-600'
              }`}
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      )}
      
      <IntegrationsLayout
        leftColumn={leftColumn}
        rightColumn={rightColumn}
      />
      
      {/* Edit Modal */}
      {editingDataSource && (
        <DataSourceEditModal
          isOpen={isEditModalOpen}
          onClose={handleCloseEditModal}
          dataSource={editingDataSource}
          dataSourceType={dataSourceTypes.find(type => type.id === editingDataSource.type)!}
          projectId={projectId}
        />
      )}

      {/* Delete Modal */}
      {deletingDataSource && (
        <DataSourceDeleteModal
          isOpen={isDeleteModalOpen}
          onClose={handleCloseDeleteModal}
          onSuccess={handleDeleteSuccess}
          dataSource={deletingDataSource}
          dataSourceType={dataSourceTypes.find(type => type.id === deletingDataSource.type)!}
          projectId={projectId}
        />
      )}

      {/* Folder Files Modal */}
      {viewingFolderDataSource && (
        <FolderFilesModal
          isOpen={isFolderFilesModalOpen}
          onClose={handleCloseFolderFilesModal}
          dataSourceId={viewingFolderDataSource.id}
          dataSourceName={viewingFolderDataSource.name}
          projectId={projectId}
        />
      )}

      {/* Data Preview Drawer */}
      <DataPreviewDrawer
        projectId={projectId}
        previewParams={previewParams}
        onClose={() => setPreviewParams(null)}
      />
    </>
  );
}
