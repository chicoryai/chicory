import React, { useState } from 'react';
import {
  ChevronRightIcon,
  ChevronDownIcon,
  CircleStackIcon,
  FolderIcon,
  TableCellsIcon,
  ServerIcon,
  EyeIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline';
import type { MetadataTreeNode } from '~/services/chicory.server';

export interface PreviewRequest {
  path: string;
  name: string;
}

interface DataBrowserPanelProps {
  status: "available" | "no_scan";
  lastScannedAt: string | null;
  providers: MetadataTreeNode[];
  onPreview?: (params: PreviewRequest) => void;
}

function formatDate(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return dateStr;
  }
}

function formatBytes(bytes: number | null | undefined): string {
  if (bytes == null) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

function canPreview(node: MetadataTreeNode): boolean {
  return node.type === 'table' && !!node.preview_path;
}

function TreeNode({
  node,
  depth = 0,
  onPreview,
}: {
  node: MetadataTreeNode;
  depth?: number;
  onPreview?: (params: PreviewRequest) => void;
}) {
  const [expanded, setExpanded] = useState(depth < 1);
  const hasChildren = node.children && node.children.length > 0;
  const isLeaf = node.type === 'table';
  const isPreviewable = canPreview(node);

  const icon = (() => {
    if (node.type === 'provider') return <ServerIcon className="w-4 h-4 text-purple-500 flex-shrink-0" />;
    if (node.type === 'table' && node.preview_path?.endsWith('.md')) return <DocumentTextIcon className="w-4 h-4 text-green-500 flex-shrink-0" />;
    if (node.type === 'table') return <TableCellsIcon className="w-4 h-4 text-blue-400 flex-shrink-0" />;
    return <FolderIcon className="w-4 h-4 text-yellow-500 flex-shrink-0" />;
  })();

  const handleClick = () => {
    if (isPreviewable && onPreview) {
      onPreview({
        path: node.preview_path!,
        name: node.name,
      });
    } else if (hasChildren) {
      setExpanded(!expanded);
    }
  };

  return (
    <div>
      <button
        onClick={handleClick}
        className={`w-full flex items-center gap-1.5 py-1 px-2 text-sm rounded transition-colors group ${
          isPreviewable
            ? 'cursor-pointer hover:bg-purple-50 dark:hover:bg-purple-900/20'
            : hasChildren
            ? 'cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800'
            : 'cursor-default'
        }`}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
      >
        {hasChildren ? (
          expanded ? (
            <ChevronDownIcon className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
          ) : (
            <ChevronRightIcon className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
          )
        ) : (
          <span className="w-3.5 flex-shrink-0" />
        )}
        {icon}
        <span className={`truncate font-medium ${
          isPreviewable ? 'text-purple-700 dark:text-purple-300' : 'text-gray-800 dark:text-gray-200'
        }`}>
          {node.name}
        </span>
        {isPreviewable && (
          <EyeIcon className="w-3.5 h-3.5 text-purple-400 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
        )}
        {isLeaf && node.size_bytes != null && node.size_bytes > 0 && (
          <span className="ml-auto text-xs text-gray-400 flex-shrink-0">
            {formatBytes(node.size_bytes)}
          </span>
        )}
        {!isLeaf && hasChildren && (
          <span className="ml-auto text-xs text-gray-400 flex-shrink-0">
            {countLeaves(node)} items
          </span>
        )}
      </button>
      {expanded && hasChildren && (
        <div>
          {node.children!.map((child, i) => (
            <TreeNode key={`${child.name}-${child.type}-${i}`} node={child} depth={depth + 1} onPreview={onPreview} />
          ))}
        </div>
      )}
    </div>
  );
}

function countLeaves(node: MetadataTreeNode): number {
  if (node.type === 'table') return 1;
  if (!node.children) return 0;
  return node.children.reduce((sum, child) => sum + countLeaves(child), 0);
}

export default function DataBrowserPanel({ status, lastScannedAt, providers, onPreview }: DataBrowserPanelProps) {
  const [isOpen, setIsOpen] = useState(false);

  if (status === 'no_scan') {
    return null;
  }

  const totalTables = providers.reduce((sum, p) => sum + countLeaves(p), 0);

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 dark:bg-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
      >
        <div className="flex items-center gap-2">
          <CircleStackIcon className="w-5 h-5 text-purple-500" />
          <span className="text-sm font-semibold text-gray-900 dark:text-white">
            Browse Sandbox Data
          </span>
          <span className="text-xs text-gray-500 bg-gray-200 dark:bg-gray-700 px-2 py-0.5 rounded-full">
            {totalTables} items across {providers.length} {providers.length === 1 ? 'source' : 'sources'}
          </span>
        </div>
        <div className="flex items-center gap-3">
          {lastScannedAt && (
            <span className="text-xs text-gray-400">
              Scanned {formatDate(lastScannedAt)}
            </span>
          )}
          {isOpen ? (
            <ChevronDownIcon className="w-4 h-4 text-gray-400" />
          ) : (
            <ChevronRightIcon className="w-4 h-4 text-gray-400" />
          )}
        </div>
      </button>

      {/* Tree content */}
      {isOpen && (
        <div className="max-h-96 overflow-y-auto py-2 bg-white dark:bg-gray-900">
          {providers.map((provider, i) => (
            <TreeNode key={`${provider.name}-${provider.type}-${i}`} node={provider} depth={0} onPreview={onPreview} />
          ))}
        </div>
      )}
    </div>
  );
}
