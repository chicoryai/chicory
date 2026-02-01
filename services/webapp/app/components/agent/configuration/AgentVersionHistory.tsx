import { useState, useEffect, useCallback } from "react";
import { ClockIcon, XMarkIcon } from "@heroicons/react/24/outline";
import { clsx } from "clsx";
import type { AgentVersion } from "~/services/chicory.server";
import { formatVersionName } from "~/utils/formatters";

type AgentVersionHistoryProps = {
  projectId: string;
  agentId: string;
  isOpen: boolean;
  onClose: () => void;
  onSelectVersion: (version: AgentVersion) => void;
  currentInstructions: string;
  currentOutputFormat: string;
};

export function AgentVersionHistory({
  projectId,
  agentId,
  isOpen,
  onClose,
  onSelectVersion,
  currentInstructions,
  currentOutputFormat,
}: AgentVersionHistoryProps) {
  const [versions, setVersions] = useState<AgentVersion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);

  const loadVersions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `/api/projects/${projectId}/agents/${agentId}/versions`
      );
      if (!response.ok) {
        throw new Error("Failed to load version history");
      }
      const data = await response.json();
      setVersions(data.versions || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load versions");
    } finally {
      setLoading(false);
    }
  }, [projectId, agentId]);

  useEffect(() => {
    if (isOpen) {
      loadVersions();
      // Set first version (current) as default selection
      setSelectedIndex(0);
    }
  }, [isOpen, loadVersions]);

  const handleVersionClick = (version: AgentVersion, index: number) => {
    setSelectedIndex(index);
  };

  const handleRestore = () => {
    if (selectedIndex !== null && selectedIndex !== 0 && versions[selectedIndex]) {
      onSelectVersion(versions[selectedIndex]);
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="relative flex h-[80vh] w-[90vw] max-w-6xl flex-col rounded-2xl bg-white shadow-2xl dark:bg-slate-900">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4 dark:border-slate-800">
          <div className="flex items-center gap-3">
            <ClockIcon className="h-6 w-6 text-purple-600" />
            <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100">
              Version History
            </h2>
          </div>
          <button
            onClick={onClose}
            className="rounded-full p-2 text-slate-500 transition hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex flex-1 overflow-hidden">
          {/* Version List */}
          <div className="w-80 border-r border-slate-200 dark:border-slate-800">
            <div className="overflow-y-auto p-4" style={{ height: "calc(80vh - 140px)" }}>
              {loading && (
                <div className="flex items-center justify-center py-8 text-slate-500">
                  Loading versions...
                </div>
              )}
              {error && (
                <div className="rounded-lg bg-red-50 p-4 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-400">
                  {error}
                </div>
              )}
              {!loading && !error && (
                <div className="space-y-2">
                  {/* All Versions (current is first) */}
                  {versions.map((version, index) => (
                    <button
                      key={index}
                      onClick={() => handleVersionClick(version, index)}
                      className={clsx(
                        "w-full rounded-lg border p-3 text-left transition",
                        selectedIndex === index
                          ? "border-purple-500 bg-purple-50 dark:bg-purple-900/20"
                          : "border-slate-200 hover:border-slate-300 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"
                      )}
                    >
                      <div className="flex flex-col gap-1">
                        <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                          {index === 0 ? "Current version" : formatVersionName(version.created_at)}
                        </span>
                        {version.updated_by_name && (
                          <span className="text-xs text-slate-500 dark:text-slate-400">
                            by {version.updated_by_name}
                          </span>
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Preview Panel */}
          <div className="flex-1 overflow-y-auto p-6">
            {selectedIndex === null ? (
              <div className="flex h-full items-center justify-center text-slate-500">
                Select a version to preview
              </div>
            ) : (
              <div className="space-y-6">
                <div>
                  <h3 className="mb-2 text-sm font-semibold uppercase tracking-wider text-slate-400">
                    Instructions
                  </h3>
                  <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-800">
                    <pre className="whitespace-pre-wrap text-sm text-slate-700 dark:text-slate-300">
                      {versions[selectedIndex]?.instructions || "(empty)"}
                    </pre>
                  </div>
                </div>
                <div>
                  <h3 className="mb-2 text-sm font-semibold uppercase tracking-wider text-slate-400">
                    Output Format
                  </h3>
                  <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-800">
                    <pre className="whitespace-pre-wrap text-sm text-slate-700 dark:text-slate-300">
                      {versions[selectedIndex]?.output_format || "(empty)"}
                    </pre>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end border-t border-slate-200 px-6 py-4 dark:border-slate-800">
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              Cancel
            </button>
            <button
              onClick={handleRestore}
              disabled={selectedIndex === null || selectedIndex === 0}
              className="rounded-lg bg-purple-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-purple-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Load This Version
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
