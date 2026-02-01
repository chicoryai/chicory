import { useState, useCallback, useMemo } from "react";
import {
  FolderIcon,
  FolderOpenIcon,
  DocumentIcon,
  ChevronRightIcon,
  ChevronDownIcon,
  ArrowDownTrayIcon,
  TrashIcon,
  MagnifyingGlassIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";

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

interface FileBrowserProps {
  dataSourceId: string;
  projectId: string;
  files: FileEntry[];
  tree?: TreeNode;
  rootFolderName: string;
  totalFiles: number;
  totalSize: number;
  onFileSelect?: (file: FileEntry) => void;
  onFileDelete?: (file: FileEntry) => void;
  onFileDownload?: (file: FileEntry) => void;
}

// File extension to icon color mapping
const extensionColors: Record<string, string> = {
  ts: "text-blue-500",
  tsx: "text-blue-500",
  js: "text-yellow-500",
  jsx: "text-yellow-500",
  py: "text-green-500",
  json: "text-orange-500",
  md: "text-purple-500",
  css: "text-pink-500",
  scss: "text-pink-500",
  html: "text-red-500",
  sql: "text-cyan-500",
  yml: "text-gray-500",
  yaml: "text-gray-500",
};

// Format file size
function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// Get file icon color based on extension
function getFileColor(extension: string): string {
  const ext = extension.replace(".", "").toLowerCase();
  return extensionColors[ext] || "text-gray-400";
}

// TreeNode component for recursive rendering
function TreeNodeComponent({
  node,
  path,
  files,
  expandedPaths,
  toggleExpanded,
  selectedFileId,
  onFileSelect,
  onFileDelete,
  onFileDownload,
  searchQuery,
}: {
  node: TreeNode;
  path: string;
  files: FileEntry[];
  expandedPaths: Set<string>;
  toggleExpanded: (path: string) => void;
  selectedFileId: string | null;
  onFileSelect?: (file: FileEntry) => void;
  onFileDelete?: (file: FileEntry) => void;
  onFileDownload?: (file: FileEntry) => void;
  searchQuery: string;
}) {
  const isExpanded = expandedPaths.has(path);
  const isDirectory = node.type === "directory";
  const depth = path.split("/").length - 1;

  // Find the actual file entry if this is a file
  const fileEntry = useMemo(() => {
    if (node.type === "file" && node.id) {
      return files.find((f) => f.id === node.id);
    }
    return null;
  }, [node, files]);

  // Check if this item matches search
  const matchesSearch =
    searchQuery === "" ||
    node.name.toLowerCase().includes(searchQuery.toLowerCase());

  // For directories, check if any children match
  const hasMatchingChildren = useMemo(() => {
    if (!isDirectory || searchQuery === "") return true;

    const checkChildren = (n: TreeNode): boolean => {
      if (n.name.toLowerCase().includes(searchQuery.toLowerCase())) {
        return true;
      }
      if (n.children) {
        return Object.values(n.children).some(checkChildren);
      }
      return false;
    };

    return Object.values(node.children || {}).some(checkChildren);
  }, [isDirectory, node.children, searchQuery]);

  // Hide if no match and no matching children
  if (searchQuery && !matchesSearch && !hasMatchingChildren) {
    return null;
  }

  const handleClick = () => {
    if (isDirectory) {
      toggleExpanded(path);
    } else if (fileEntry && onFileSelect) {
      onFileSelect(fileEntry);
    }
  };

  const handleDownload = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (fileEntry && onFileDownload) {
      onFileDownload(fileEntry);
    }
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (fileEntry && onFileDelete) {
      onFileDelete(fileEntry);
    }
  };

  const isSelected = fileEntry && selectedFileId === fileEntry.id;

  return (
    <div>
      <div
        className={`flex items-center gap-1 py-1 px-2 rounded cursor-pointer group ${
          isSelected
            ? "bg-lime-100 dark:bg-lime-900/30"
            : "hover:bg-gray-100 dark:hover:bg-gray-800"
        }`}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
        onClick={handleClick}
      >
        {/* Expand/collapse icon for directories */}
        {isDirectory ? (
          <span className="w-4 h-4 flex items-center justify-center">
            {isExpanded ? (
              <ChevronDownIcon className="h-3 w-3 text-gray-400" />
            ) : (
              <ChevronRightIcon className="h-3 w-3 text-gray-400" />
            )}
          </span>
        ) : (
          <span className="w-4" />
        )}

        {/* Icon */}
        {isDirectory ? (
          isExpanded ? (
            <FolderOpenIcon className="h-4 w-4 text-yellow-500 flex-shrink-0" />
          ) : (
            <FolderIcon className="h-4 w-4 text-yellow-500 flex-shrink-0" />
          )
        ) : (
          <DocumentIcon
            className={`h-4 w-4 flex-shrink-0 ${getFileColor(
              node.extension || ""
            )}`}
          />
        )}

        {/* Name */}
        <span
          className={`text-sm truncate flex-1 ${
            isSelected
              ? "text-lime-700 dark:text-lime-300"
              : "text-gray-700 dark:text-gray-300"
          }`}
        >
          {node.name}
        </span>

        {/* File size */}
        {!isDirectory && node.size !== undefined && (
          <span className="text-xs text-gray-400 mr-2">
            {formatSize(node.size)}
          </span>
        )}

        {/* Action buttons for files */}
        {!isDirectory && (
          <div className="hidden group-hover:flex items-center gap-1">
            {onFileDownload && (
              <button
                onClick={handleDownload}
                className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
                title="Download"
              >
                <ArrowDownTrayIcon className="h-4 w-4 text-gray-500" />
              </button>
            )}
            {onFileDelete && (
              <button
                onClick={handleDelete}
                className="p-1 hover:bg-red-100 dark:hover:bg-red-900/30 rounded"
                title="Delete"
              >
                <TrashIcon className="h-4 w-4 text-red-500" />
              </button>
            )}
          </div>
        )}
      </div>

      {/* Children */}
      {isDirectory && isExpanded && node.children && (
        <div>
          {Object.entries(node.children)
            .sort(([, a], [, b]) => {
              // Directories first, then files
              if (a.type !== b.type) {
                return a.type === "directory" ? -1 : 1;
              }
              return a.name.localeCompare(b.name);
            })
            .map(([childName, childNode]) => (
              <TreeNodeComponent
                key={childName}
                node={childNode}
                path={path ? `${path}/${childName}` : childName}
                files={files}
                expandedPaths={expandedPaths}
                toggleExpanded={toggleExpanded}
                selectedFileId={selectedFileId}
                onFileSelect={onFileSelect}
                onFileDelete={onFileDelete}
                onFileDownload={onFileDownload}
                searchQuery={searchQuery}
              />
            ))}
        </div>
      )}
    </div>
  );
}

export default function FileBrowser({
  dataSourceId,
  projectId,
  files,
  tree,
  rootFolderName,
  totalFiles,
  totalSize,
  onFileSelect,
  onFileDelete,
  onFileDownload,
}: FileBrowserProps) {
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(
    new Set([rootFolderName])
  );
  const [selectedFileId, setSelectedFileId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  // Build tree from files if not provided
  const fileTree = useMemo(() => {
    if (tree) return tree;

    const root: TreeNode = {
      name: rootFolderName,
      type: "directory",
      children: {},
    };

    for (const file of files) {
      const parts = file.relative_path.split("/");
      let current = root.children!;

      for (let i = 0; i < parts.length - 1; i++) {
        const part = parts[i];
        if (!current[part]) {
          current[part] = {
            name: part,
            type: "directory",
            path: parts.slice(0, i + 1).join("/"),
            children: {},
          };
        }
        current = current[part].children!;
      }

      const filename = parts[parts.length - 1];
      current[filename] = {
        name: filename,
        type: "file",
        path: file.relative_path,
        id: file.id,
        size: file.file_size,
        content_type: file.content_type,
        extension: file.file_extension,
      };
    }

    return root;
  }, [tree, files, rootFolderName]);

  const toggleExpanded = useCallback((path: string) => {
    setExpandedPaths((prev) => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  }, []);

  const handleFileSelect = useCallback(
    (file: FileEntry) => {
      setSelectedFileId(file.id);
      if (onFileSelect) {
        onFileSelect(file);
      }
    },
    [onFileSelect]
  );

  const expandAll = useCallback(() => {
    const allPaths = new Set<string>();

    const collectPaths = (node: TreeNode, path: string) => {
      if (node.type === "directory") {
        allPaths.add(path);
        if (node.children) {
          Object.entries(node.children).forEach(([name, child]) => {
            collectPaths(child, path ? `${path}/${name}` : name);
          });
        }
      }
    };

    collectPaths(fileTree, rootFolderName);
    setExpandedPaths(allPaths);
  }, [fileTree, rootFolderName]);

  const collapseAll = useCallback(() => {
    setExpandedPaths(new Set([rootFolderName]));
  }, [rootFolderName]);

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="bg-gray-50 dark:bg-gray-800 px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <FolderIcon className="h-5 w-5 text-yellow-500" />
            <span className="font-medium text-gray-800 dark:text-gray-200">
              {rootFolderName}
            </span>
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            {totalFiles} files ({formatSize(totalSize)})
          </div>
        </div>

        {/* Search and controls */}
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <MagnifyingGlassIcon className="absolute left-2 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search files..."
              className="w-full pl-8 pr-8 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200 focus:outline-none focus:ring-1 focus:ring-lime-500"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-2 top-1/2 transform -translate-y-1/2"
              >
                <XMarkIcon className="h-4 w-4 text-gray-400 hover:text-gray-600" />
              </button>
            )}
          </div>
          <button
            onClick={expandAll}
            className="px-2 py-1.5 text-xs text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 border border-gray-300 dark:border-gray-600 rounded"
          >
            Expand all
          </button>
          <button
            onClick={collapseAll}
            className="px-2 py-1.5 text-xs text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 border border-gray-300 dark:border-gray-600 rounded"
          >
            Collapse all
          </button>
        </div>
      </div>

      {/* Tree view */}
      <div className="max-h-96 overflow-y-auto p-2">
        <TreeNodeComponent
          node={fileTree}
          path={rootFolderName}
          files={files}
          expandedPaths={expandedPaths}
          toggleExpanded={toggleExpanded}
          selectedFileId={selectedFileId}
          onFileSelect={handleFileSelect}
          onFileDelete={onFileDelete}
          onFileDownload={onFileDownload}
          searchQuery={searchQuery}
        />
      </div>
    </div>
  );
}
