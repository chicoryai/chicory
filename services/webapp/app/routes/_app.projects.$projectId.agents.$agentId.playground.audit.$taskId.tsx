/**
 * Playground Audit Trail Route
 * Displays audit trail for a specific task in the sidebar
 * Securely fetches S3 location from task metadata server-side
 */

import { json } from "@remix-run/node";
import type { LoaderFunctionArgs } from "@remix-run/node";
import { useLoaderData, useFetcher, useNavigate } from "@remix-run/react";
import { useEffect, useState, useRef } from "react";
import { AuditTrailPanel } from "~/components/panels/AuditTrailPanel";
import { getAgentTask } from "~/services/chicory.server";
import { getUserOrgDetails } from "~/auth/auth.server";
import type { TrailItem } from "~/types/auditTrail";

export async function loader({ request, params }: LoaderFunctionArgs) {
  const { agentId, projectId, taskId } = params;

  if (!agentId || !projectId || !taskId) {
    throw new Response("Agent ID, Project ID, and Task ID are required", { status: 400 });
  }

  // Auth validation
  const userDetails = await getUserOrgDetails(request);
  if (userDetails instanceof Response) {
    return userDetails;
  }

  try {
    // Fetch task to get S3 location from metadata (server-side only - never in URL)
    const task = await getAgentTask(projectId, agentId, taskId);

    if (!task) {
      throw new Response("Task not found", { status: 404 });
    }

    const metadata = task.metadata as Record<string, unknown> | undefined;

    // Extract S3 info from metadata
    const s3Bucket = typeof (metadata as any)?.s3_bucket === 'string'
      ? (metadata as any)?.s3_bucket
      : null;
    const s3Key = typeof (metadata as any)?.s3_key === 'string'
      ? (metadata as any)?.s3_key
      : null;
    const s3Url = typeof metadata?.audit_trail === 'string'
      ? metadata.audit_trail
      : typeof (metadata as any)?.s3_url === 'string'
        ? (metadata as any)?.s3_url
        : undefined;

    // Check if there's inline agent trail data (for streaming tasks)
    const inlineAgentTrail = Array.isArray((metadata as any)?.agent_trail)
      ? (metadata as any)?.agent_trail as TrailItem[]
      : undefined;

    return json({
      taskId: task.id,
      s3Bucket,
      s3Key,
      s3Url,
      inlineAgentTrail
    });
  } catch (error) {
    console.error("Error loading task for audit trail:", error);
    throw new Response("Failed to load task data", { status: 500 });
  }
}

export default function PlaygroundAudit() {
  const { taskId, s3Bucket, s3Key, s3Url, inlineAgentTrail } = useLoaderData<typeof loader>();
  const fetcher = useFetcher<{ trail?: TrailItem[]; error?: string }>();
  const navigate = useNavigate();
  const [agentTrail, setAgentTrail] = useState<TrailItem[]>(inlineAgentTrail || []);
  const hasFetchedRef = useRef(false);
  const lastTaskIdRef = useRef<string | null>(null);

  // Initialize/update state when inline trail data changes
  useEffect(() => {
    setAgentTrail(inlineAgentTrail || []);
  }, [inlineAgentTrail]);

  // Fetch audit trail from API (only once per taskId)
  useEffect(() => {
    // Reset fetch flag when taskId changes
    if (lastTaskIdRef.current !== taskId) {
      hasFetchedRef.current = false;
      lastTaskIdRef.current = taskId;
    }

    // Skip if already fetched or fetcher is busy
    if (hasFetchedRef.current || fetcher.state !== 'idle') {
      return;
    }

    hasFetchedRef.current = true;

    // Build query params for API (still uses s3 params but not exposed in browser URL)
    const params = new URLSearchParams();
    if (s3Bucket) params.set('bucket', s3Bucket);
    if (s3Key) params.set('key', s3Key);
    if (s3Url) params.set('url', s3Url);

    if (params.toString()) {
      fetcher.load(`/api/audit-trail/${taskId}?${params.toString()}`);
    } else {
      fetcher.load(`/api/audit-trail/${taskId}`);
    }
  }, [taskId, s3Bucket, s3Key, s3Url, fetcher]);

  // Update trail when fetcher returns data
  useEffect(() => {
    if (fetcher.data?.trail) {
      setAgentTrail(fetcher.data.trail);
    }
  }, [fetcher.data]);

  const isLoading = fetcher.state !== 'idle';
  const error = fetcher.data?.error;

  const handleClose = () => {
    // Navigate back to playground (closes sidebar)
    navigate("../..", { relative: "path" });
  };

  return (
    <div className="flex h-full flex-col overflow-y-auto rounded-2xl border border-slate-200 bg-white p-6 shadow-md shadow-purple-900/30 dark:border-slate-800 dark:bg-slate-900">
      <div className="flex-1 overflow-hidden rounded-xl bg-white shadow-inner dark:bg-slate-950/70">
        <AuditTrailPanel
          auditTrail={agentTrail}
          onClose={handleClose}
          isStreaming={isLoading}
        />
      </div>
      {error && (
        <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600 dark:border-red-700 dark:bg-red-900/30 dark:text-red-300">
          {error}
        </div>
      )}
    </div>
  );
}
