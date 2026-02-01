import { useEffect, useState } from 'react';
import { useFetcher } from '@remix-run/react';
import { Modal } from '~/components/ui/Modal';
import { AuditTrailPanel } from '~/components/panels/AuditTrailPanel';
import { MarkdownRenderer } from '~/components/MarkdownRenderer';
import type { TaskPair } from '~/components/ManageTable';
import type { TrailItem } from '~/types/auditTrail';
import { ClockIcon, UserIcon, CpuChipIcon, CalendarIcon, DocumentTextIcon } from '@heroicons/react/24/outline';

interface TaskDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  taskPair: TaskPair;
}

function formatTimestamp(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
}

function formatLatency(milliseconds: number): string {
  if (milliseconds < 1000) {
    return `${milliseconds.toFixed(0)}ms`;
  }
  return `${(milliseconds / 1000).toFixed(2)}s`;
}

export function TaskDetailsModal({ isOpen, onClose, taskPair }: TaskDetailsModalProps) {
  const [showAuditTrail, setShowAuditTrail] = useState(false);
  const auditTrailFetcher = useFetcher<{ trail: TrailItem[]; error?: string }>();

  // Extract audit trail URL from assistant metadata
  const auditTrailUrl = (taskPair.assistantTask.metadata as any)?.audit_trail;
  const s3Bucket = (taskPair.assistantTask.metadata as any)?.s3_bucket;
  const s3Key = (taskPair.assistantTask.metadata as any)?.s3_key;

  useEffect(() => {
    if (isOpen && auditTrailUrl && !auditTrailFetcher.data) {
      // Fetch audit trail data
      const params = new URLSearchParams();
      if (s3Bucket && s3Key) {
        params.set('bucket', s3Bucket);
        params.set('key', s3Key);
      } else {
        params.set('url', auditTrailUrl);
      }

      auditTrailFetcher.load(`/api/audit-trail/${taskPair.assistantTask.id}?${params.toString()}`);
      setShowAuditTrail(true); // Auto-show audit trail
    }
  }, [isOpen, auditTrailUrl, taskPair.assistantTask.id]);

  const auditTrail = auditTrailFetcher.data?.trail || [];
  const hasAuditTrail = auditTrailUrl && auditTrail.length > 0;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Task Execution Details"
      panelClassName="w-full max-w-6xl"
    >
      <div className="flex max-h-[70vh] overflow-hidden">
        {/* Main Content */}
        <div className={`flex-1 overflow-y-auto pr-4 ${showAuditTrail && hasAuditTrail ? 'border-r border-slate-200 dark:border-slate-700' : ''}`}>
          {/* Header Info */}
          <div className="mb-6 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm">
                <span className="font-semibold text-slate-600 dark:text-slate-400">Task ID:</span>
                <span className="font-mono text-xs text-purple-600 dark:text-purple-400">{taskPair.id}</span>
              </div>
              
              {/* Execution Trail Toggle Button */}
              {hasAuditTrail && !showAuditTrail && (
                <button
                  onClick={() => setShowAuditTrail(true)}
                  className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                >
                  <DocumentTextIcon className="h-4 w-4" />
                  Show Execution Trail
                </button>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="flex items-center gap-2">
                <CalendarIcon className="h-4 w-4 text-slate-400" />
                <div>
                  <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                    Timestamp
                  </div>
                  <div className="text-sm text-slate-900 dark:text-slate-100">
                    {formatTimestamp(taskPair.timestamp)}
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <ClockIcon className="h-4 w-4 text-slate-400" />
                <div>
                  <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                    Latency
                  </div>
                  <div className="font-mono text-sm text-slate-900 dark:text-slate-100">
                    {formatLatency(taskPair.latency)}
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                  Status: <span className="capitalize">{taskPair.status}</span>
                </span>
              </div>

              {taskPair.source && taskPair.source !== '-' && (
                <div className="flex items-center gap-2">
                  <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400">
                    Source: {taskPair.source}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* User Query */}
          <div className="mb-6">
            <div className="mb-2 flex items-center gap-2">
              <UserIcon className="h-4 w-4 text-slate-400" />
              <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-400">
                User Query
              </h3>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-800/50">
              <MarkdownRenderer
                content={taskPair.userQuery}
                variant="task"
                className="text-sm"
              />
            </div>
          </div>

          {/* Assistant Response */}
          <div className="mb-6">
            <div className="mb-2 flex items-center gap-2">
              <CpuChipIcon className="h-4 w-4 text-slate-400" />
              <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-400">
                Assistant Response
              </h3>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-800/50">
              <MarkdownRenderer
                content={taskPair.response}
                variant="task"
                className="text-sm"
              />
            </div>
          </div>


          {auditTrailFetcher.data?.error && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200">
              {auditTrailFetcher.data.error}
            </div>
          )}
        </div>

        {/* Audit Trail Panel */}
        {showAuditTrail && hasAuditTrail && (
          <div className="w-1/2 pl-4 flex flex-col overflow-hidden">
            <div className="flex-1 overflow-hidden rounded-lg border border-slate-200 dark:border-slate-700">
              <AuditTrailPanel
                auditTrail={auditTrail}
                onClose={() => setShowAuditTrail(false)}
                isStreaming={false}
              />
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
