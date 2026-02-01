import { Modal } from "~/components/ui/Modal";
import { useState, useRef, useCallback, useEffect } from "react";
import {
  CloudArrowUpIcon,
  FolderIcon,
  CheckCircleIcon,
  XCircleIcon,
  DocumentIcon,
} from "@heroicons/react/24/outline";

// Constants
const MAX_FOLDER_SIZE = 500 * 1024 * 1024; // 500MB
const MAX_FILES = 1000;
const MAX_DEPTH = 10;
const BATCH_SIZE = 20; // Upload 20 files at a time

interface FolderUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string;
  category: "document" | "code";
  onSuccess?: (dataSourceId: string) => void;
}

interface FileWithWebkitPath extends File {
  webkitRelativePath?: string;
}

interface FileWithPath {
  file: File;
  relativePath: string;
}

type UploadState = "idle" | "validating" | "uploading" | "completing" | "done" | "error";

interface UploadProgress {
  totalFiles: number;
  uploadedFiles: number;
  failedFiles: number;
  currentBatch: number;
  totalBatches: number;
}

export default function FolderUploadModal({
  isOpen,
  onClose,
  projectId,
  category,
  onSuccess,
}: FolderUploadModalProps) {
  const [files, setFiles] = useState<FileWithPath[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const [uploadState, setUploadState] = useState<UploadState>("idle");
  const [progress, setProgress] = useState<UploadProgress>({
    totalFiles: 0,
    uploadedFiles: 0,
    failedFiles: 0,
    currentBatch: 0,
    totalBatches: 0,
  });
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [folderName, setFolderName] = useState("");

  const fileInputRef = useRef<HTMLInputElement>(null);
  const dropAreaRef = useRef<HTMLDivElement>(null);

  // Reset state when modal opens/closes
  useEffect(() => {
    if (isOpen) {
      setFiles([]);
      setUploadState("idle");
      setProgress({
        totalFiles: 0,
        uploadedFiles: 0,
        failedFiles: 0,
        currentBatch: 0,
        totalBatches: 0,
      });
      setError(null);
      setName("");
      setDescription("");
      setFolderName("");
    }
  }, [isOpen]);

  // Extract files from a directory entry recursively
  const extractFilesFromEntry = useCallback(
    async (
      entry: FileSystemEntry,
      path: string = ""
    ): Promise<FileWithPath[]> => {
      const results: FileWithPath[] = [];

      if (entry.isFile) {
        const fileEntry = entry as FileSystemFileEntry;
        const file = await new Promise<File>((resolve, reject) => {
          fileEntry.file(resolve, reject);
        });
        const relativePath = path ? `${path}/${entry.name}` : entry.name;
        results.push({ file, relativePath });
      } else if (entry.isDirectory) {
        const dirEntry = entry as FileSystemDirectoryEntry;
        const reader = dirEntry.createReader();

        const entries = await new Promise<FileSystemEntry[]>(
          (resolve, reject) => {
            const allEntries: FileSystemEntry[] = [];
            const readEntries = () => {
              reader.readEntries((entries) => {
                if (entries.length === 0) {
                  resolve(allEntries);
                } else {
                  allEntries.push(...entries);
                  readEntries();
                }
              }, reject);
            };
            readEntries();
          }
        );

        const newPath = path ? `${path}/${entry.name}` : entry.name;
        for (const childEntry of entries) {
          const childFiles = await extractFilesFromEntry(childEntry, newPath);
          results.push(...childFiles);
        }
      }

      return results;
    },
    []
  );

  // Validate folder structure
  const validateFiles = useCallback((files: FileWithPath[]): string | null => {
    if (files.length === 0) {
      return "No files found in the folder";
    }

    if (files.length > MAX_FILES) {
      return `Too many files (${files.length}). Maximum allowed: ${MAX_FILES}`;
    }

    const totalSize = files.reduce((sum, f) => sum + f.file.size, 0);
    if (totalSize > MAX_FOLDER_SIZE) {
      const sizeMB = (totalSize / (1024 * 1024)).toFixed(1);
      return `Folder too large (${sizeMB}MB). Maximum allowed: 500MB`;
    }

    const maxDepth = Math.max(
      ...files.map((f) => f.relativePath.split("/").length - 1)
    );
    if (maxDepth > MAX_DEPTH) {
      return `Folder too deep (${maxDepth} levels). Maximum allowed: ${MAX_DEPTH}`;
    }

    return null;
  }, []);

  // Handle folder selection via input
  const handleFolderSelect = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const selectedFiles = e.target.files;
      if (!selectedFiles || selectedFiles.length === 0) return;

      setUploadState("validating");
      setError(null);

      try {
        const filesWithPaths: FileWithPath[] = [];

        // Extract root folder name from webkitRelativePath
        let rootFolderName = "";

        for (let i = 0; i < selectedFiles.length; i++) {
          const file = selectedFiles[i];
          // webkitRelativePath gives us the path like "folderName/subfolder/file.txt"
          const relativePath = (file as FileWithWebkitPath).webkitRelativePath || file.name;

          if (!rootFolderName && relativePath.includes("/")) {
            rootFolderName = relativePath.split("/")[0];
          }

          // Remove the root folder name from the path for storage
          const pathWithoutRoot = relativePath.includes("/")
            ? relativePath.substring(relativePath.indexOf("/") + 1)
            : relativePath;

          // Skip OS metadata files
          const fileName = file.name;
          if (fileName === '.DS_Store' || fileName === 'Thumbs.db' || fileName === 'desktop.ini' || fileName.startsWith('._')) {
            continue;
          }

          filesWithPaths.push({
            file,
            relativePath: pathWithoutRoot,
          });
        }

        const validationError = validateFiles(filesWithPaths);
        if (validationError) {
          setError(validationError);
          setUploadState("error");
          return;
        }

        setFiles(filesWithPaths);
        setFolderName(rootFolderName || "uploaded-folder");
        setUploadState("idle");
      } catch (err) {
        setError(`Failed to process folder: ${err}`);
        setUploadState("error");
      }
    },
    [validateFiles]
  );

  // Handle drag and drop
  const handleDrop = useCallback(
    async (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      e.stopPropagation();
      setDragActive(false);

      const items = e.dataTransfer.items;
      if (!items || items.length === 0) return;

      setUploadState("validating");
      setError(null);

      try {
        const allFiles: FileWithPath[] = [];
        let rootFolderName = "";

        for (let i = 0; i < items.length; i++) {
          const item = items[i];
          const entry = item.webkitGetAsEntry();

          if (entry) {
            if (entry.isDirectory && !rootFolderName) {
              rootFolderName = entry.name;
            }

            const files = await extractFilesFromEntry(entry);
            // Filter out OS metadata files (same as file input handler)
            const filteredFiles = files.filter((f) => {
              const fileName = f.file.name;
              return !(
                fileName === ".DS_Store" ||
                fileName === "Thumbs.db" ||
                fileName === "desktop.ini" ||
                fileName.startsWith("._")
              );
            });
            allFiles.push(...filteredFiles);
          }
        }

        const validationError = validateFiles(allFiles);
        if (validationError) {
          setError(validationError);
          setUploadState("error");
          return;
        }

        setFiles(allFiles);
        setFolderName(rootFolderName || "uploaded-folder");
        setUploadState("idle");
      } catch (err) {
        setError(`Failed to process dropped items: ${err}`);
        setUploadState("error");
      }
    },
    [extractFilesFromEntry, validateFiles]
  );

  // Handle upload
  const handleUpload = useCallback(async () => {
    if (files.length === 0 || !name.trim()) {
      setError("Please select a folder and enter a name");
      return;
    }

    setUploadState("uploading");
    setError(null);

    const totalSize = files.reduce((sum, f) => sum + f.file.size, 0);
    const maxDepth = Math.max(
      ...files.map((f) => f.relativePath.split("/").length - 1)
    );
    const totalBatches = Math.ceil(files.length / BATCH_SIZE);

    setProgress({
      totalFiles: files.length,
      uploadedFiles: 0,
      failedFiles: 0,
      currentBatch: 0,
      totalBatches,
    });

    try {
      // Step 1: Initialize folder upload
      const initFormData = new FormData();
      initFormData.append("name", name.trim());
      initFormData.append("root_folder_name", folderName);
      initFormData.append("category", category);
      initFormData.append("total_files", files.length.toString());
      initFormData.append("total_size", totalSize.toString());
      initFormData.append("max_depth", maxDepth.toString());
      if (description.trim()) {
        initFormData.append("description", description.trim());
      }

      const initResponse = await fetch(
        `/api/projects/${projectId}/data-sources/folder-upload/init`,
        {
          method: "POST",
          body: initFormData,
        }
      );

      if (!initResponse.ok) {
        const errorData = await initResponse.json().catch(() => ({ detail: "Failed to initialize upload" }));
        const errorMessage = typeof errorData.detail === 'string' ? errorData.detail : "Failed to initialize upload";
        throw new Error(errorMessage);
      }

      const initData = await initResponse.json();
      const uploadId = initData.upload_id;

      // Step 2: Upload files in batches
      let uploadedCount = 0;
      let failedCount = 0;

      for (let batch = 0; batch < totalBatches; batch++) {
        const startIdx = batch * BATCH_SIZE;
        const endIdx = Math.min(startIdx + BATCH_SIZE, files.length);
        const batchFiles = files.slice(startIdx, endIdx);

        setProgress((prev) => ({
          ...prev,
          currentBatch: batch + 1,
        }));

        const uploadFormData = new FormData();
        const relativePaths: string[] = [];

        for (const { file, relativePath } of batchFiles) {
          uploadFormData.append("files", file);
          relativePaths.push(relativePath);
        }

        uploadFormData.append("relative_paths", JSON.stringify(relativePaths));

        const uploadResponse = await fetch(
          `/api/projects/${projectId}/data-sources/folder-upload/${uploadId}/files`,
          {
            method: "POST",
            body: uploadFormData,
          }
        );

        if (!uploadResponse.ok) {
          const errorData = await uploadResponse.json().catch(() => ({}));
          throw new Error(errorData.detail || "Failed to upload files");
        }

        const uploadData = await uploadResponse.json();
        uploadedCount += uploadData.files_uploaded || 0;
        failedCount += uploadData.files_failed || 0;

        setProgress((prev) => ({
          ...prev,
          uploadedFiles: uploadedCount,
          failedFiles: failedCount,
        }));
      }

      // Step 3: Complete the upload
      setUploadState("completing");

      const completeFormData = new FormData();
      if (description.trim()) {
        completeFormData.append("description", description.trim());
      }

      const completeResponse = await fetch(
        `/api/projects/${projectId}/data-sources/folder-upload/${uploadId}/complete`,
        {
          method: "POST",
          body: completeFormData,
        }
      );

      if (!completeResponse.ok) {
        const errorData = await completeResponse.json().catch(() => ({}));
        throw new Error(errorData.detail || "Failed to complete upload");
      }

      const completeData = await completeResponse.json();

      setUploadState("done");

      // Call success callback
      if (onSuccess) {
        onSuccess(completeData.data_source_id);
      }

      // Close modal after a brief delay
      setTimeout(() => {
        onClose();
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
      setUploadState("error");
    }
  }, [files, name, description, folderName, category, projectId, onSuccess, onClose]);

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

  // Format file size
  const formatSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // Get file count by extension
  const getFileStats = useCallback(() => {
    const stats: Record<string, number> = {};
    files.forEach((f) => {
      const ext = f.relativePath.split(".").pop()?.toLowerCase() || "other";
      stats[ext] = (stats[ext] || 0) + 1;
    });
    return Object.entries(stats)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);
  }, [files]);

  if (!isOpen) return null;

  const isUploading = uploadState === "uploading" || uploadState === "completing";
  const totalSize = files.reduce((sum, f) => sum + f.file.size, 0);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Upload ${category === "code" ? "Code" : "Document"} Folder`}
    >
      <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
        Upload an entire folder to use as a data source. The folder structure
        will be preserved.
      </p>

      {/* Name input */}
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
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={isUploading}
          className="w-full px-3 py-2 border border-gray-300 bg-white dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-lime-500 focus:border-lime-500 dark:bg-gray-700 dark:text-white disabled:opacity-50"
          placeholder="Enter a name for this data source"
        />
      </div>

      {/* Description input */}
      <div className="mb-4">
        <label
          htmlFor="description"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
        >
          Description
        </label>
        <textarea
          id="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          disabled={isUploading}
          rows={2}
          className="w-full px-3 py-2 border border-gray-300 bg-white dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-lime-500 focus:border-lime-500 dark:bg-gray-700 dark:text-white disabled:opacity-50"
          placeholder="Optional description"
        />
      </div>

      {/* Hidden folder input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFolderSelect}
        className="hidden"
        // @ts-expect-error -- webkitdirectory and directory are non-standard HTML attributes for folder selection
        webkitdirectory="true"
        directory=""
        multiple
        disabled={isUploading}
      />

      {/* Drop zone */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Folder <span className="text-red-500">*</span>
        </label>

        <div
          ref={dropAreaRef}
          className={`mt-1 flex justify-center px-6 pt-5 pb-6 border-2 ${
            dragActive
              ? "border-lime-500 bg-lime-50 dark:bg-lime-900/20"
              : "border-gray-300 dark:border-gray-600 border-dashed"
          } rounded-md cursor-pointer transition-colors duration-200 ${
            isUploading ? "opacity-50 pointer-events-none" : ""
          }`}
          onClick={handleBrowseClick}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <div className="space-y-1 text-center">
            {files.length === 0 ? (
              <>
                <FolderIcon
                  className={`mx-auto h-12 w-12 ${
                    dragActive ? "text-lime-500" : "text-gray-400"
                  }`}
                />
                <div className="flex flex-col sm:flex-row items-center justify-center text-sm text-gray-600 dark:text-gray-400">
                  <span className="relative cursor-pointer rounded-md font-medium text-lime-600 hover:text-lime-500">
                    Browse
                  </span>
                  <p className="pl-1">or drag and drop a folder</p>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Max 500MB, 1000 files, 10 levels deep
                </p>
              </>
            ) : (
              <div className="text-left w-full">
                <div className="flex items-center gap-2 mb-2">
                  <FolderIcon className="h-5 w-5 text-lime-500" />
                  <span className="font-medium text-gray-800 dark:text-gray-200">
                    {folderName}
                  </span>
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                  <p>
                    {files.length} files ({formatSize(totalSize)})
                  </p>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {getFileStats().map(([ext, count]) => (
                      <span
                        key={ext}
                        className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300"
                      >
                        .{ext}: {count}
                      </span>
                    ))}
                  </div>
                </div>
                {!isUploading && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setFiles([]);
                      setFolderName("");
                    }}
                    className="mt-2 text-xs text-red-500 hover:text-red-600"
                  >
                    Clear selection
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Progress indicator */}
      {isUploading && (
        <div className="mb-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-md">
          <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-2">
            <span>
              {uploadState === "completing"
                ? "Finalizing..."
                : `Uploading batch ${progress.currentBatch} of ${progress.totalBatches}`}
            </span>
            <span>
              {progress.uploadedFiles} / {progress.totalFiles} files
            </span>
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
            <div
              className="bg-lime-500 h-2 rounded-full transition-all duration-300"
              style={{
                width: `${(progress.uploadedFiles / progress.totalFiles) * 100}%`,
              }}
            />
          </div>
          {progress.failedFiles > 0 && (
            <p className="text-xs text-red-500 mt-1">
              {progress.failedFiles} file(s) failed
            </p>
          )}
        </div>
      )}

      {/* Success state */}
      {uploadState === "done" && (
        <div className="mb-4 p-4 bg-green-50 dark:bg-green-900/20 rounded-md flex items-center gap-2">
          <CheckCircleIcon className="h-5 w-5 text-green-500" />
          <span className="text-green-700 dark:text-green-400">
            Folder uploaded successfully!
          </span>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 rounded-md flex items-start gap-2">
          <XCircleIcon className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
          <span className="text-red-700 dark:text-red-400 text-sm">{error}</span>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex justify-end gap-3 mt-6">
        <button
          type="button"
          onClick={onClose}
          disabled={isUploading}
          className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lime-500 disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={handleUpload}
          disabled={
            isUploading ||
            files.length === 0 ||
            !name.trim() ||
            uploadState === "done"
          }
          className="px-4 py-2 text-sm font-medium text-white bg-lime-600 border border-transparent rounded-md shadow-sm hover:bg-lime-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lime-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isUploading ? "Uploading..." : "Upload Folder"}
        </button>
      </div>
    </Modal>
  );
}
