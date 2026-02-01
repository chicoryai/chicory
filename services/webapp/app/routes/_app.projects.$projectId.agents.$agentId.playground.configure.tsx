/**
 * Playground Configure Route
 * Handles agent instruction and output format editing
 * Renders as a sidebar in the playground layout
 *
 * STATE MANAGEMENT:
 * - Draft state: What user is currently editing (draftInstructions, draftOutputFormat)
 * - Saved state: Derived from fetcher.data (if saved) OR agent context (initial)
 * - No complex sync logic - fetcher.data is source of truth after any save
 * - On success: Update draft to match saved values
 * - On error: Keep draft as-is so user can fix and retry
 */

import { useFetcher, useNavigate, useParams } from "@remix-run/react";
import { useCallback, useEffect, useMemo, useState, Component, type ReactNode } from "react";
import { XMarkIcon, ClockIcon } from "@heroicons/react/24/outline";
import { AgentOutputFormatEditor } from "~/components/agent/configuration/AgentOutputFormatEditor";
import { AgentSystemInstructionsEditor } from "~/components/agent/configuration/AgentSystemInstructionsEditor";
import { AgentVersionHistory } from "~/components/agent/configuration/AgentVersionHistory";
import type { AgentVersion } from "~/services/chicory.server";
import { useAgentContext } from "./_app.projects.$projectId.agents.$agentId";
import { useToast } from "~/hooks/useToast";
import { formatVersionName } from "~/utils/formatters";


/**
 * ErrorBoundary specifically for the configure panel
 * Prevents WAF errors from triggering the full-page error boundary
 */
class ConfigureErrorBoundary extends Component<
  { children: ReactNode; onError: (error: Error) => void },
  { hasError: boolean }
> {
  constructor(props: { children: ReactNode; onError: (error: Error) => void }) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error) {
    console.error('[CONFIGURE ERROR BOUNDARY] Caught error:', error);
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: any) {
    console.error('[CONFIGURE ERROR BOUNDARY] Error details:', {
      error,
      errorInfo,
      message: error.message,
      stack: error.stack
    });
    this.props.onError(error);
  }

  render() {
    if (this.state.hasError) {
      // Don't render anything - let the parent component handle the error display
      return this.props.children;
    }

    return this.props.children;
  }
}

/**
 * No loader - we get initial data from parent context via useAgentContext()
 * No revalidation - fetcher.data becomes source of truth after first save
 */
export function shouldRevalidate() {
  return false;
}

function PlaygroundConfigureContent() {
  const { agent } = useAgentContext();
  const params = useParams();
  const fetcher = useFetcher<{
    success?: boolean;
    error?: string;
    intent?: string;
    instructions?: string;
    outputFormat?: string;
  }>();
  const { showToast, ToastContainer } = useToast();
  const navigate = useNavigate();

  const agentId = agent.id;
  const projectId = params.projectId!;

  // Draft state - what the user is currently editing
  const [draftInstructions, setDraftInstructions] = useState(agent.instructions ?? "");
  const [draftOutputFormat, setDraftOutputFormat] = useState(agent.output_format ?? "");
  
  // Version history state
  const [isVersionHistoryOpen, setIsVersionHistoryOpen] = useState(false);

  // Sync draft state when agent changes (e.g., switching between agents)
  useEffect(() => {
    setDraftInstructions(agent.instructions ?? "");
    setDraftOutputFormat(agent.output_format ?? "");
  }, [agent.id]);

  // What's actually saved (from last successful save OR initial agent data)
  const savedInstructions = fetcher.data?.success ? (fetcher.data.instructions ?? "") : (agent.instructions ?? "");
  const savedOutputFormat = fetcher.data?.success ? (fetcher.data.outputFormat ?? "") : (agent.output_format ?? "");

  // Track if we're currently saving
  const isSaving = fetcher.state !== 'idle';

  // On successful save, update draft to match server response
  // On error, just show error (keep draft as-is so user can fix and retry)
  useEffect(() => {
    if (fetcher.state !== "idle" || !fetcher.data) {
      return;
    }

    const data = fetcher.data;

    if (data.success) {
      // Update draft to match what was saved
      setDraftInstructions(data.instructions ?? "");
      setDraftOutputFormat(data.outputFormat ?? "");
      showToast('Agent prompt saved successfully!', 'success', 3000);
    } else {
      // Show error, keep draft so user can edit and retry
      showToast(
        data.error || 'Failed to update instructions. Please try again.',
        'error',
        5000
      );
    }
  }, [fetcher.state, fetcher.data, showToast]);

  const MAX_INSTRUCTIONS_LENGTH = 20000;
  const isOverLimit = draftInstructions.length > MAX_INSTRUCTIONS_LENGTH;

  // Has changes if draft differs from saved
  const hasChanges = useMemo(
    () => draftInstructions !== savedInstructions || draftOutputFormat !== savedOutputFormat,
    [draftInstructions, savedInstructions, draftOutputFormat, savedOutputFormat]
  );

  // Simple onChange handlers - just update the draft
  const handleInstructionsChange = useCallback((value: string) => {
    setDraftInstructions(value);
  }, []);

  const handleOutputFormatChange = useCallback((value: string) => {
    setDraftOutputFormat(value);
  }, []);

  const handleSave = useCallback(() => {
    const formData = new FormData();
    formData.append("intent", "updateInstructions");
    formData.append("systemInstructions", draftInstructions);
    formData.append("outputFormat", draftOutputFormat);
    fetcher.submit(formData, { method: "post", action: ".." });
  }, [fetcher, draftInstructions, draftOutputFormat]);

  const handleReset = useCallback(() => {
    setDraftInstructions(savedInstructions);
    setDraftOutputFormat(savedOutputFormat);
  }, [savedInstructions, savedOutputFormat]);

  const handleClose = useCallback(() => {
    // Navigate back to playground with closed param to prevent auto-reopening
    navigate("..?closed=true", { relative: "path" });
  }, [navigate]);

  const handleOpenVersionHistory = useCallback(() => {
    setIsVersionHistoryOpen(true);
  }, []);

  const handleCloseVersionHistory = useCallback(() => {
    setIsVersionHistoryOpen(false);
  }, []);

  const handleSelectVersion = useCallback((version: AgentVersion) => {
    // Load the version into the draft state
    setDraftInstructions(version.instructions ?? "");
    setDraftOutputFormat(version.output_format ?? "");
    showToast(`Loaded version: ${formatVersionName(version.created_at)}. Click Save to apply.`, 'info', 5000);
  }, [showToast]);

  return (
    <>
      <ToastContainer />
      <AgentVersionHistory
        projectId={projectId}
        agentId={agentId}
        isOpen={isVersionHistoryOpen}
        onClose={handleCloseVersionHistory}
        onSelectVersion={handleSelectVersion}
        currentInstructions={savedInstructions}
        currentOutputFormat={savedOutputFormat}
      />
      <div className="flex h-full flex-col gap-6 overflow-hidden">
        <div className="flex-1 overflow-y-auto">
        <div className="flex h-full min-h-0 flex-col gap-6">
          <AgentSystemInstructionsEditor
            editorKey={`configure-instructions-${agentId}`}
            value={draftInstructions}
            onChange={handleInstructionsChange}
            variant="sidebar"
            className="flex-1 min-h-[320px]"
            actions={(
              <>
                <button
                  type="button"
                  onClick={handleOpenVersionHistory}
                  className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-purple-400 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800"
                  title="View version history"
                >
                  <ClockIcon className="h-4 w-4" />
                  History
                </button>
                <button
                  type="button"
                  onClick={handleSave}
                  disabled={!hasChanges || isSaving || isOverLimit}
                  className="inline-flex items-center justify-center rounded-lg bg-purple-600 px-4 py-2 text-sm font-semibold text-white shadow-sm shadow-purple-500/30 transition hover:bg-purple-500 focus:outline-none focus:ring-2 focus:ring-purple-400 disabled:cursor-not-allowed disabled:opacity-50"
                  title={isOverLimit ? 'Instructions exceed character limit' : undefined}
                >
                  {isSaving ? 'Saving…' : isOverLimit ? 'Over Limit' : 'Save'}
                </button>
                <button
                  type="button"
                  onClick={handleClose}
                  className="rounded-full p-2 text-slate-500 transition hover:bg-slate-200/60 hover:text-slate-700 focus:outline-none focus:ring-2 focus:ring-purple-400 dark:text-slate-300 dark:hover:bg-slate-800/80"
                >
                  <span className="sr-only">Close panel</span>
                  <XMarkIcon className="h-5 w-5" />
                </button>
              </>
            )}
          />
          <AgentOutputFormatEditor
            value={draftOutputFormat}
            onChange={handleOutputFormatChange}
            variant="sidebar"
            className="flex-shrink-0"
          />
        </div>
      </div>
      </div>
    </>
  );
}

export default function PlaygroundConfigure() {
  return (
    <ConfigureErrorBoundary onError={(error) => {
      console.error('[CONFIGURE] Error boundary triggered:', error);
    }}>
      <PlaygroundConfigureContent />
    </ConfigureErrorBoundary>
  );
}
