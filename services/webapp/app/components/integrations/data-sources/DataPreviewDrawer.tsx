import React, { useEffect, useState } from 'react';
import {
  XMarkIcon,
  TableCellsIcon,
  DocumentIcon,
  LinkIcon,
} from '@heroicons/react/24/outline';
import type { DataSourcePreview } from '~/services/chicory.server';

interface DataPreviewDrawerProps {
  projectId: string;
  previewParams: {
    path: string;
    name: string;
  } | null;
  onClose: () => void;
}

function formatBytes(bytes: number | null | undefined): string {
  if (bytes == null) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

export default function DataPreviewDrawer({ projectId, previewParams, onClose }: DataPreviewDrawerProps) {
  const [preview, setPreview] = useState<DataSourcePreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isOpen = previewParams !== null;

  useEffect(() => {
    if (!previewParams) {
      setPreview(null);
      return;
    }

    const abortController = new AbortController();
    const params = new URLSearchParams();
    params.set('path', previewParams.path);

    setLoading(true);
    setError(null);

    fetch(`/api/projects/${projectId}/data-preview?${params.toString()}`, {
      signal: abortController.signal,
    })
      .then(res => {
        if (!res.ok) {
          return res.json().catch(() => ({})).then(data => {
            throw new Error(data.error || 'Preview not available');
          });
        }
        return res.json();
      })
      .then(data => {
        setPreview(data);
        setLoading(false);
      })
      .catch(err => {
        if (err.name !== 'AbortError') {
          setError(err.message);
          setLoading(false);
        }
      });

    return () => abortController.abort();
  }, [projectId, previewParams]);

  // Close on Escape
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [isOpen, onClose]);

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/20 z-40 transition-opacity"
          onClick={onClose}
        />
      )}

      {/* Drawer */}
      <div
        className={`fixed top-0 right-0 h-full w-full max-w-2xl bg-white dark:bg-gray-900 shadow-2xl z-50 transform transition-transform duration-300 ease-in-out ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        } flex flex-col`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            {preview?.type === 'markdown' ? (
              <DocumentIcon className="w-5 h-5 text-purple-500 flex-shrink-0" />
            ) : (
              <TableCellsIcon className="w-5 h-5 text-purple-500 flex-shrink-0" />
            )}
            <div className="min-w-0">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white truncate">
                {previewParams?.name || 'Preview'}
              </h2>
              {preview?.fqtn && (
                <p className="text-xs text-gray-400 font-mono truncate">{preview.fqtn}</p>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <XMarkIcon className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {loading && (
            <div className="flex items-center justify-center py-20">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500" />
            </div>
          )}

          {error && (
            <div className="p-6 text-center text-red-500">
              <p className="text-sm">{error}</p>
            </div>
          )}

          {preview && !loading && (
            <div className="divide-y divide-gray-100 dark:divide-gray-800">
              {/* Summary stats */}
              <div className="px-6 py-4">
                <div className="flex flex-wrap gap-4">
                  {preview.row_count != null && (
                    <Stat label="Rows" value={preview.row_count.toLocaleString()} />
                  )}
                  {preview.columns.length > 0 && (
                    <Stat label="Columns" value={preview.columns.length.toString()} />
                  )}
                  {preview.size_bytes != null && preview.size_bytes > 0 && (
                    <Stat label="Size" value={formatBytes(preview.size_bytes)} />
                  )}
                  {preview.type && (
                    <Stat label="Type" value={preview.type.replace(/_/g, ' ')} />
                  )}
                  {preview.created_date && (
                    <Stat label="Created" value={preview.created_date} />
                  )}
                </div>
                {preview.description && (
                  <p className="mt-3 text-sm text-gray-600 dark:text-gray-400">{preview.description}</p>
                )}
              </div>

              {/* Schema */}
              {preview.columns.length > 0 && (
                <div className="px-6 py-4">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
                    Schema ({preview.columns.length} columns)
                  </h3>
                  <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
                    <table className="min-w-full text-sm">
                      <thead>
                        <tr className="bg-gray-50 dark:bg-gray-800">
                          <th className="px-3 py-2 text-left font-medium text-gray-500 dark:text-gray-400">Name</th>
                          <th className="px-3 py-2 text-left font-medium text-gray-500 dark:text-gray-400">Type</th>
                          <th className="px-3 py-2 text-left font-medium text-gray-500 dark:text-gray-400">Nullable</th>
                          <th className="px-3 py-2 text-left font-medium text-gray-500 dark:text-gray-400">Description</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                        {preview.columns.map((col, i) => (
                          <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                            <td className="px-3 py-1.5 font-mono text-gray-900 dark:text-gray-200">{col.name}</td>
                            <td className="px-3 py-1.5">
                              <span className="inline-block px-1.5 py-0.5 text-xs bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded font-mono">
                                {col.type}
                              </span>
                            </td>
                            <td className="px-3 py-1.5 text-gray-500">
                              {col.nullable ? 'yes' : 'no'}
                            </td>
                            <td className="px-3 py-1.5 text-gray-500 dark:text-gray-400 max-w-xs truncate">
                              {col.description || '-'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Sample Data */}
              {preview.sample_rows.length > 0 && (
                <div className="px-6 py-4">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
                    Sample Data ({preview.sample_rows.length} rows)
                  </h3>
                  <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
                    <table className="min-w-full text-xs">
                      <thead>
                        <tr className="bg-gray-50 dark:bg-gray-800">
                          {preview.columns.map((col, i) => (
                            <th key={i} className="px-3 py-2 text-left font-medium text-gray-500 dark:text-gray-400 whitespace-nowrap">
                              {col.name}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                        {preview.sample_rows.map((row, ri) => (
                          <tr key={ri} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                            {preview.columns.map((col, ci) => (
                              <td key={ci} className="px-3 py-1.5 text-gray-700 dark:text-gray-300 whitespace-nowrap max-w-[200px] truncate">
                                {String(row[col.name] ?? '')}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Webfetch content */}
              {preview.content && (
                <div className="px-6 py-4">
                  {preview.source_url && /^https?:\/\//i.test(preview.source_url) && (
                    <div className="flex items-center gap-1.5 mb-3">
                      <LinkIcon className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
                      <a
                        href={preview.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-blue-500 hover:text-blue-700 truncate"
                      >
                        {preview.source_url}
                      </a>
                    </div>
                  )}
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
                    Content
                  </h3>
                  <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 max-h-[60vh] overflow-y-auto">
                    <pre className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap font-sans leading-relaxed">
                      {preview.content}
                    </pre>
                  </div>
                </div>
              )}

              {/* Empty states */}
              {preview.columns.length === 0 && preview.sample_rows.length === 0 && !preview.content && (
                <div className="px-6 py-12 text-center">
                  <DocumentIcon className="w-10 h-10 text-gray-300 mx-auto mb-3" />
                  <p className="text-sm text-gray-500">No schema or preview data available for this item.</p>
                </div>
              )}

              {preview.columns.length > 0 && preview.sample_rows.length === 0 && preview.type === 'table_card' && (
                <div className="px-6 py-6 text-center">
                  <DocumentIcon className="w-8 h-8 text-gray-300 mx-auto mb-2" />
                  <p className="text-xs text-gray-400">
                    Sample data not available from scan. Use the agent to query this table live.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col">
      <span className="text-xs text-gray-400 uppercase tracking-wide">{label}</span>
      <span className="text-sm font-medium text-gray-900 dark:text-white">{value}</span>
    </div>
  );
}
