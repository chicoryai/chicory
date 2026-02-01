import { useState, useEffect } from "react";
import { XMarkIcon } from "@heroicons/react/24/outline";
import FileBrowser from "./FileBrowser";

interface FileEntry {
  id: string;
  relative_path: string;
  filename: string;
  file_extension: string;
  file_size: number;
  content_type: string;
  depth: number;
  parent_path: string;
  preview_supported: boolean;
  created_at: string;
}

interface TreeNode {
  name: string;
  type: "file" | "directory";
  path?: string;
  id?: string;
  size?: number;
  content_type?: string;
  extension?: string;
  children?: Record<string, TreeNode>;
}

interface FolderFilesResponse {
  data_source_id: string;
  name: string;
  total_files: number;
  total_size: number;
  files: FileEntry[];
  tree: TreeNode;
}

interface FolderFilesModalProps {
  isOpen: boolean;
  onClose: () => void;
  dataSourceId: string;
  dataSourceName: string;
  projectId: string;
}

export default function FolderFilesModal({
  isOpen,
  onClose,
  dataSourceId,
  dataSourceName,
  projectId,
}: FolderFilesModalProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [folderData, setFolderData] = useState<FolderFilesResponse | null>(null);

  useEffect(() => {
    if (isOpen && dataSourceId) {
      fetchFolderFiles();
    }
  }, [isOpen, dataSourceId]);

  const fetchFolderFiles = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `/api/projects/${projectId}/data-sources/${dataSourceId}/files`
      );
      if (!response.ok) {
        throw new Error("Failed to fetch folder files");
      }
      const data = await response.json();
      setFolderData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load files");
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = (file: FileEntry) => {
    console.log("Selected file:", file);
    // Could open a preview modal here
  };

  const [actionError, setActionError] = useState<string | null>(null);

  const handleFileDownload = async (file: FileEntry) => {
    setActionError(null);
    try {
      const response = await fetch(
        `/api/projects/${projectId}/data-sources/${dataSourceId}/files/${file.id}`
      );
      if (!response.ok) {
        throw new Error("Failed to get download URL");
      }
      const data = await response.json();
      if (data.download_url) {
        window.open(data.download_url, "_blank");
      }
    } catch (err) {
      console.error("Download failed:", err);
      setActionError('Failed to download file. Please try again.');
    }
  };

  const handleFileDelete = async (file: FileEntry) => {
    if (!confirm(`Are you sure you want to delete "${file.filename}"?`)) {
      return;
    }
    setActionError(null);
    try {
      const response = await fetch(
        `/api/projects/${projectId}/data-sources/${dataSourceId}/files/${file.id}`,
        { method: "DELETE" }
      );
      if (!response.ok) {
        throw new Error("Failed to delete file");
      }
      // Refresh the file list
      fetchFolderFiles();
    } catch (err) {
      console.error("Delete failed:", err);
      setActionError('Failed to delete file. Please try again.');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 transition-opacity"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative w-full max-w-4xl bg-white dark:bg-gray-900 rounded-xl shadow-2xl transform transition-all">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                {dataSourceName}
              </h2>
              {folderData && (
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  {folderData.total_files} files
                </p>
              )}
            </div>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              <XMarkIcon className="h-5 w-5" />
            </button>
          </div>

          {/* Action Error */}
          {actionError && <div className="px-4 py-2 text-sm text-red-700 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded">{actionError}</div>}

          {/* Content */}
          <div className="p-6 max-h-[70vh] overflow-y-auto">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500"></div>
                <span className="ml-3 text-gray-600 dark:text-gray-400">
                  Loading files...
                </span>
              </div>
            ) : error ? (
              <div className="text-center py-12">
                <p className="text-red-500 mb-4">{error}</p>
                <button
                  onClick={fetchFolderFiles}
                  className="px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 transition-colors"
                >
                  Retry
                </button>
              </div>
            ) : folderData ? (
              <FileBrowser
                dataSourceId={dataSourceId}
                projectId={projectId}
                files={folderData.files}
                tree={folderData.tree}
                rootFolderName={folderData.name || dataSourceName}
                totalFiles={folderData.total_files}
                totalSize={folderData.total_size}
                onFileSelect={handleFileSelect}
                onFileDownload={handleFileDownload}
                onFileDelete={handleFileDelete}
              />
            ) : (
              <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                No files found
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
