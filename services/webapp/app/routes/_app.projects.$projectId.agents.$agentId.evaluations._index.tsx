import { json } from "@remix-run/node";
import type { LoaderFunctionArgs, ActionFunctionArgs } from "@remix-run/node";
import { useLoaderData, useFetcher, useSearchParams } from "@remix-run/react";
import { useState, useEffect, useCallback, useRef } from "react";
import { getUserOrgDetails } from "~/auth/auth.server";
import { 
  getEvaluations,
  getEvaluationStats,
  createEvaluation,
  deleteEvaluation,
  updateEvaluation,
  startEvaluationRun,
  getTestCases,
  getRunHistory,
  getLatestRun,
  addTestCase,
  updateTestCase,
  deleteTestCase,
  type Evaluation,
  type EvaluationRun,
  type TestCase
} from "~/services/chicory.server";
import { useAgentContext } from "./_app.projects.$projectId.agents.$agentId";
import { EvaluationLayout } from "~/components/evaluation/layouts/EvaluationLayout";
import { SplitViewLayout } from "~/components/evaluation/layouts/SplitViewLayout";
import { EvaluationCard } from "~/components/evaluation/cards/EvaluationCard";
import { MetricsBar } from "~/components/evaluation/metrics/MetricsBar";
import { TestCaseTable } from "~/components/evaluation/tables/TestCaseTable";
import { RunHistoryTimeline } from "~/components/evaluation/timeline/RunHistoryTimeline";
import { DetailPanel } from "~/components/evaluation/shared/DetailPanel";
import { EmptyState } from "~/components/evaluation/shared/EmptyState";
import { TabPanel } from "~/components/evaluation/shared/TabPanel";
import { SearchBar } from "~/components/evaluation/shared/SearchBar";
import { FilterChips } from "~/components/evaluation/shared/FilterChips";
import { EvaluationOverview } from "~/components/evaluation/shared/EvaluationOverview";
import { EvaluationSettings } from "~/components/evaluation/shared/EvaluationSettings";
import { CreateEvaluationModal } from "~/components/evaluation/CreateEvaluationModal";
import { Toast, type ToastType } from "~/components/Toast";
import { ConfirmationModal } from "~/components/ConfirmationModal";
import { 
  DocumentTextIcon, 
  PlayIcon, 
  ChartBarIcon, 
  BeakerIcon
} from "@heroicons/react/24/outline";

// Helper function to calculate evaluation statistics
function calculateEvaluationStats(
  evaluations: Evaluation[],
  allRuns: EvaluationRun[],
  allTestCasesMap: Record<string, TestCase[]>
) {
  // Calculate total evaluations
  const totalEvaluations = evaluations.length;
  
  // Calculate total runs
  const totalRuns = allRuns.length;
  
  // Calculate total test cases
  const totalTestCases = Object.values(allTestCasesMap)
    .reduce((sum, cases) => sum + cases.length, 0);
  
  // Calculate average pass rate from test case results
  let totalScore = 0;
  let scoredRuns = 0;
  allRuns.forEach(run => {
    if (run.overall_score !== null && run.overall_score !== undefined) {
      totalScore += run.overall_score;
      scoredRuns++;
    }
  });
  const avgPassRate = scoredRuns > 0 ? Math.round((totalScore / scoredRuns) * 100) : 0;
  
  return {
    totalEvaluations,
    totalRuns,
    avgPassRate,
    totalTestCases
  };
}

export async function loader({ request, params }: LoaderFunctionArgs) {
  const { agentId, projectId } = params;
  
  if (!agentId || !projectId) {
    throw new Response("Missing required parameters", { status: 400 });
  }

  const userDetails = await getUserOrgDetails(request);
  if (userDetails instanceof Response) {
    return userDetails;
  }

  const orgId = 'orgId' in userDetails ? (userDetails as any).orgId : undefined;
  if (!orgId) {
    throw new Response("Organization access required", { status: 403 });
  }
  
  // Get selected evaluation from URL params
  const url = new URL(request.url);
  const selectedEvalId = url.searchParams.get('evaluation');
  
  // Fetch evaluations first
  const evaluationsData = await getEvaluations(projectId, agentId, { limit: 20 });
  const evaluations = evaluationsData?.evaluations || [];
  
  // Fetch all test cases and runs for all evaluations to calculate accurate stats
  const allTestCasesMap: Record<string, TestCase[]> = {};
  const allRuns: EvaluationRun[] = [];
  const latestRuns: Record<string, EvaluationRun> = {};
  
  if (evaluations.length > 0) {
    const promises = evaluations.map(async (evaluation: Evaluation) => {
      try {
        // Fetch test cases for this evaluation
        const testCasesData = await getTestCases(projectId, agentId, evaluation.id, { limit: 100 });
        if (testCasesData?.test_cases) {
          allTestCasesMap[evaluation.id] = testCasesData.test_cases;
        }
        
        // Fetch run history for this evaluation
        const runHistoryData = await getRunHistory(projectId, agentId, evaluation.id, { limit: 50 });
        if (runHistoryData?.runs) {
          allRuns.push(...runHistoryData.runs);
          // Store the latest run (first in the list as it's sorted by date)
          if (runHistoryData.runs.length > 0) {
            latestRuns[evaluation.id] = runHistoryData.runs[0];
          }
        }
      } catch (error) {
        console.error(`Failed to fetch data for evaluation ${evaluation.id}:`, error);
      }
    });
    await Promise.all(promises);
  }
  
  // Calculate real stats from the fetched data
  const calculatedStats = calculateEvaluationStats(evaluations, allRuns, allTestCasesMap);
  
  // If evaluation selected, get its specific data
  let selectedEval = null;
  let selectedTestCases = null;
  let selectedRunHistory = null;
  
  if (selectedEvalId && evaluations.length > 0) {
    const foundEval = evaluations.find((e: Evaluation) => e.id === selectedEvalId);
    if (foundEval) {
      selectedEval = foundEval;
      selectedTestCases = allTestCasesMap[selectedEvalId] || [];
      // Get run history for selected evaluation
      const runHistoryData = await getRunHistory(projectId, agentId, selectedEvalId);
      selectedRunHistory = runHistoryData?.runs || [];
    }
  }
  
  return json({
    evaluations,
    stats: calculatedStats,
    selectedEvaluation: selectedEval,
    testCases: selectedTestCases || [],
    runHistory: selectedRunHistory || [],
    latestRuns
  });
}

export async function action({ request, params }: ActionFunctionArgs) {
  const { agentId, projectId } = params;
  const formData = await request.formData();
  const intent = formData.get('intent');
  const userDetails = await getUserOrgDetails(request);
  if (userDetails instanceof Response) {
    return userDetails;
  }
  
  if (!projectId || !agentId) {
    throw new Response("Missing required parameters", { status: 400 });
  }
  
  switch (intent) {
    case 'create-evaluation': {
      const name = formData.get('name') as string;
      const description = formData.get('description') as string;
      const criteria = formData.get('criteria') as string;
      const csvFile = formData.get('csv_file') as File;

      const apiFormData = new FormData();
      apiFormData.append('name', name);
      apiFormData.append('criteria', criteria);
      apiFormData.append('csv_file', csvFile);
      if (description) {
        apiFormData.append('description', description);
      }

      const result = await createEvaluation(projectId, agentId, apiFormData);
      return json({ success: true, evaluation: result });
    }

    case 'create-evaluation-with-tasks': {
      const name = formData.get('name') as string;
      const description = formData.get('description') as string;
      const criteria = formData.get('criteria') as string;
      const tasksJson = formData.get('tasks') as string;

      if (!name || !criteria) {
        return json({ error: 'Name and criteria are required' }, { status: 400 });
      }

      try {
        // Parse tasks from JSON
        const tasks = tasksJson ? JSON.parse(tasksJson) as Array<{
          userQuery: string;
          response: string;
          source?: string;
          timestamp: string;
        }> : [];

        // Generate CSV content with tasks
        let csvContent = 'task,expected_output,evaluation_guideline\n';

        // Add each task as a CSV row
        for (const task of tasks) {
          // Escape CSV fields by wrapping in quotes and escaping internal quotes
          const escapeCsvField = (field: string) => {
            if (!field) return '""';
            const escaped = field.replace(/"/g, '""');
            return `"${escaped}"`;
          };

          const taskField = escapeCsvField(task.userQuery);
          const outputField = escapeCsvField(task.response);
          // Use empty guideline since user can fill it later
          const guidelineField = '""';

          csvContent += `${taskField},${outputField},${guidelineField}\n`;
        }

        // Create CSV file
        const csvBlob = new Blob([csvContent], { type: 'text/csv' });
        const csvFile = new File([csvBlob], 'evaluation-tasks.csv', { type: 'text/csv' });

        // Create evaluation with CSV file
        const apiFormData = new FormData();
        apiFormData.append('name', name);
        apiFormData.append('criteria', criteria);
        apiFormData.append('csv_file', csvFile);
        if (description) {
          apiFormData.append('description', description);
        }

        const result = await createEvaluation(projectId, agentId, apiFormData);
        return json({ success: true, evaluation: result });
      } catch (error) {
        console.error('Failed to create evaluation:', error);
        return json({ error: 'Failed to create evaluation' }, { status: 500 });
      }
    }
    
    case 'run-evaluation': {
      const evaluationId = formData.get('evaluation_id') as string;
      const run = await startEvaluationRun(projectId, agentId, evaluationId);
      return json({ success: true, run });
    }
    
    case 'delete-evaluation': {
      const evaluationId = formData.get('evaluation_id') as string;
      await deleteEvaluation(projectId, agentId, evaluationId);
      return json({ success: true });
    }
    
    case 'update-test-case': {
      const testCaseId = formData.get('test_case_id') as string;
      const evaluationId = formData.get('evaluation_id') as string;
      const updates = JSON.parse(formData.get('updates') as string);
      
      if (!evaluationId || !testCaseId) {
        throw new Response("Missing required parameters", { status: 400 });
      }
      
      try {
        const updatedTestCase = await updateTestCase(
          projectId,
          agentId,
          evaluationId,
          testCaseId,
          updates
        );
        return json({ success: true, testCase: updatedTestCase });
      } catch (error) {
        console.error('Failed to update test case:', error);
        return json({ error: 'Failed to update test case' }, { status: 500 });
      }
    }
    
    case 'delete-test-case': {
      const testCaseId = formData.get('test_case_id') as string;
      const evaluationId = formData.get('evaluation_id') as string;
      
      if (!evaluationId || !testCaseId) {
        throw new Response("Missing required parameters", { status: 400 });
      }
      
      try {
        await deleteTestCase(
          projectId,
          agentId,
          evaluationId,
          testCaseId
        );
        return json({ success: true });
      } catch (error) {
        console.error('Failed to delete test case:', error);
        return json({ error: 'Failed to delete test case' }, { status: 500 });
      }
    }
    
    case 'add-test-case': {
      const evaluationId = formData.get('evaluation_id') as string;
      const task = formData.get('task') as string;
      const expectedOutput = formData.get('expected_output') as string;
      const evaluationGuideline = formData.get('evaluation_guideline') as string;

      if (!evaluationId || !task || !expectedOutput) {
        return json({ error: 'Missing required fields' }, { status: 400 });
      }

      try {
        const testCase = await addTestCase(
          projectId,
          agentId,
          evaluationId,
          {
            task,
            expected_output: expectedOutput,
            evaluation_guideline: evaluationGuideline || null
          }
        );
        return json({ success: true, testCase });
      } catch (error) {
        console.error('Failed to add test case:', error);
        return json({ error: 'Failed to add test case' }, { status: 500 });
      }
    }
    
    case 'bulk-action': {
      const action = formData.get('action') as string;
      const evaluationId = formData.get('evaluation_id') as string;
      const ids = JSON.parse(formData.get('ids') as string) as string[];
      
      if (!evaluationId) {
        throw new Response("Missing evaluation ID", { status: 400 });
      }
      
      if (action === 'delete') {
        try {
          // Delete all selected test cases
          await Promise.all(
            ids.map(id => deleteTestCase(projectId, agentId, evaluationId, id))
          );
          return json({ success: true });
        } catch (error) {
          console.error('Failed to delete test cases:', error);
          return json({ error: 'Failed to delete test cases' }, { status: 500 });
        }
      }
      
      return json({ error: 'Invalid bulk action' }, { status: 400 });
    }
    
    case 'update-evaluation-settings': {
      const evaluationId = formData.get('evaluation_id') as string;
      const name = formData.get('name') as string;
      const description = formData.get('description') as string;
      const criteria = formData.get('criteria') as string;
      
      if (!evaluationId || !name) {
        return json({ error: 'Evaluation ID and name are required' }, { status: 400 });
      }
      
      try {
        const updatedEvaluation = await updateEvaluation(
          projectId,
          agentId,
          evaluationId,
          {
            name,
            description: description || undefined,
            criteria: criteria || undefined
          }
        );
        return json({ success: true, evaluation: updatedEvaluation });
      } catch (error) {
        console.error('Failed to update evaluation settings:', error);
        return json({ error: 'Failed to update evaluation settings' }, { status: 500 });
      }
    }
    
    default:
      throw new Response("Invalid intent", { status: 400 });
  }
}

// Maximum number of concurrent SSE connections to prevent CPU overload
const MAX_CONCURRENT_SSE_CONNECTIONS = 5;

export default function EvaluationsRoute() {
  const { evaluations, stats, selectedEvaluation, testCases, runHistory, latestRuns: initialLatestRuns } = useLoaderData<typeof loader>();
  const { agent, projectId } = useAgentContext();
  const fetcher = useFetcher<{ success?: boolean; error?: string; testCase?: TestCase; run?: EvaluationRun; evaluation?: Evaluation }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedId, setSelectedId] = useState(selectedEvaluation?.id);
  const [activeTab, setActiveTab] = useState('overview');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filters, setFilters] = useState<string[]>([]);
  const [toast, setToast] = useState<{ message: string; type: ToastType } | null>(null);
  const [loadingTestCaseId, setLoadingTestCaseId] = useState<string | null>(null);
  const [latestRuns, setLatestRuns] = useState<Record<string, EvaluationRun>>(initialLatestRuns);
  const [currentEvaluation, setCurrentEvaluation] = useState(selectedEvaluation);
  
  // Add state for live run history updates
  const [liveRunHistory, setLiveRunHistory] = useState(runHistory);
  
  // Initialize active runs from latest runs that are still running
  const initialActiveRuns: Record<string, { id: string; status: string; completed: number; total: number }> = {};
  Object.entries(initialLatestRuns).forEach(([evalId, run]) => {
    const typedRun = run as EvaluationRun;
    if (typedRun.status === 'running' || typedRun.status === 'pending') {
      initialActiveRuns[evalId] = {
        id: typedRun.id,
        status: typedRun.status,
        completed: typedRun.completed_test_cases || 0,
        total: typedRun.total_test_cases || 0
      };
    }
  });
  
  const [activeRuns, setActiveRuns] = useState<Record<string, { id: string; status: string; completed: number; total: number }>>(initialActiveRuns); 
  const [deleteConfirm, setDeleteConfirm] = useState<{ 
    isOpen: boolean; 
    type: 'single' | 'bulk' | 'evaluation';
    id?: string;
    ids?: string[];
    name?: string;
  }>({ isOpen: false, type: 'single' });
  
  // Filter evaluations based on search and filters
  const filteredEvaluations = evaluations.filter((evaluation: Evaluation) => {
    const matchesSearch = searchQuery === '' || 
      evaluation.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (evaluation.description && evaluation.description.toLowerCase().includes(searchQuery.toLowerCase()));
    
    // Apply status filters
    if (filters.length > 0) {
      const lastRun = latestRuns[evaluation.id];
      const hasActiveFilter = filters.includes('active');
      const hasCompletedFilter = filters.includes('completed');
      const hasFailedFilter = filters.includes('failed');
      const hasRecentFilter = filters.includes('recent');
      
      let matchesFilter = false;
      
      if (hasActiveFilter && lastRun?.status === 'running') {
        matchesFilter = true;
      }
      
      if (hasCompletedFilter && lastRun?.status === 'completed') {
        matchesFilter = true;
      }
      
      if (hasFailedFilter && lastRun?.status === 'failed') {
        matchesFilter = true;
      }
      
      if (hasRecentFilter) {
        const sevenDaysAgo = new Date();
        sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
        const createdDate = new Date(evaluation.created_at);
        if (createdDate >= sevenDaysAgo) {
          matchesFilter = true;
        }
      }
      
      return matchesSearch && matchesFilter;
    }
    
    return matchesSearch;
  });
  
  // Update URL when selection changes
  useEffect(() => {
    if (selectedId) {
      const params = new URLSearchParams(searchParams);
      params.set('evaluation', selectedId);
      setSearchParams(params, { replace: true });
    }
  }, [selectedId]);
  
  // Update current evaluation when selection changes
  useEffect(() => {
    const selected = evaluations.find((e: Evaluation) => e.id === selectedId);
    if (selected) {
      setCurrentEvaluation(selected);
    }
  }, [selectedId, evaluations]);
  
  // Update liveRunHistory when runHistory changes (e.g., when evaluation changes)
  useEffect(() => {
    setLiveRunHistory(runHistory);
  }, [runHistory]);

  // Track SSE connections and monitoring state
  const eventSourcesRef = useRef<Record<string, EventSource>>({});
  const monitoringRuns = useRef<Set<string>>(new Set());
  const retryCountersRef = useRef<Record<string, number>>({});

  // Ref to track runs state to avoid circular dependency
  // These refs are updated in the effect to track the current state without causing re-renders
  const activeRunsRef = useRef(activeRuns);
  const liveRunHistoryRef = useRef(liveRunHistory);

  // Helper function to create SSE connection for a single run
  // Memoized with stable dependencies to prevent unnecessary re-creation
  const createEventSourceForRun = useCallback((run: EvaluationRun, retryCount = 0) => {
    if (run.status !== 'running' && run.status !== 'pending') return;

    // Atomic check-and-set to prevent duplicate connections
    if (monitoringRuns.current.has(run.id)) {
      console.log('[SSE] Skipping duplicate connection for run:', run.id);
      return;
    }

    // Check connection limit
    const currentConnections = monitoringRuns.current.size;
    if (currentConnections >= MAX_CONCURRENT_SSE_CONNECTIONS) {
      console.log('[SSE] Connection limit reached. Skipping run:', run.id, 'Max connections:', MAX_CONCURRENT_SSE_CONNECTIONS);
      return;
    }

    // Mark as monitoring BEFORE creating connection to prevent race conditions
    monitoringRuns.current.add(run.id);

    const maxRetries = 3;
    const streamUrl = `/api/projects/${projectId}/agents/${agent.id}/evaluations/${run.evaluation_id}/run/stream?runId=${run.id}`;
    console.log('[SSE] Creating EventSource for run', run.id, 'connections:', currentConnections + 1, '/', MAX_CONCURRENT_SSE_CONNECTIONS, 'status:', run.status);

    const eventSource = new EventSource(streamUrl);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        // Reset retry counter on successful message
        retryCountersRef.current[run.id] = 0;

        if (data.type === 'connected') {
          console.log('[SSE] Connected for run:', run.id);
        } else if (data.type === 'progress' && data.data.fullRun) {
          // Update the specific run in liveRunHistory
          setLiveRunHistory((prev: EvaluationRun[]) =>
            prev.map((r: EvaluationRun) =>
              r.id === data.data.runId ? data.data.fullRun : r
            )
          );

          // Update latestRuns for card display
          setLatestRuns(prev => ({
            ...prev,
            [run.evaluation_id]: data.data.fullRun
          }));

          // Update activeRuns for real-time progress display
          setActiveRuns(prev => ({
            ...prev,
            [run.evaluation_id]: {
              id: run.id,
              status: data.data.status,
              completed: data.data.completed,
              total: data.data.total
            }
          }));

          // If run completed, close the connection and remove from activeRuns
          if (data.data.status === 'completed' || data.data.status === 'failed') {
            console.log('[SSE] Run completed, closing connection:', run.id);

            // Remove from activeRuns
            setActiveRuns(prev => {
              const newRuns = { ...prev };
              delete newRuns[run.evaluation_id];
              return newRuns;
            });

            monitoringRuns.current.delete(run.id);
            eventSource.close();
            delete eventSourcesRef.current[run.id];
            delete retryCountersRef.current[run.id];
          }
        } else if (data.type === 'process_complete') {
          console.log('[SSE] Process complete for run:', run.id);

          // Update with final results
          setLiveRunHistory((prev: EvaluationRun[]) =>
            prev.map((r: EvaluationRun) =>
              r.id === data.data.runId ? data.data.fullRun : r
            )
          );

          setLatestRuns(prev => ({
            ...prev,
            [run.evaluation_id]: data.data.fullRun
          }));

          // Remove from activeRuns
          setActiveRuns(prev => {
            const newRuns = { ...prev };
            delete newRuns[run.evaluation_id];
            return newRuns;
          });

          // Close connection
          monitoringRuns.current.delete(run.id);
          eventSource.close();
          delete eventSourcesRef.current[run.id];
          delete retryCountersRef.current[run.id];
        } else if (data.type === 'error') {
          console.warn('[SSE] Server error for run:', run.id, 'error:', data.error);
        } else if (data.type === 'timeout') {
          console.log('[SSE] Timeout for run:', run.id);
          monitoringRuns.current.delete(run.id);
          eventSource.close();
          delete eventSourcesRef.current[run.id];
          delete retryCountersRef.current[run.id];
        }
      } catch (error) {
        console.error('[SSE] Error parsing data:', error);
      }
    };

    eventSource.onerror = (error) => {
      console.error('[SSE] Connection error for run:', run.id, error);
      eventSource.close();
      delete eventSourcesRef.current[run.id];

      // Retry with exponential backoff
      const currentRetry = retryCountersRef.current[run.id] || 0;
      if (currentRetry < maxRetries) {
        retryCountersRef.current[run.id] = currentRetry + 1;
        const delay = Math.pow(2, currentRetry) * 1000; // 1s, 2s, 4s
        console.log('[SSE] Retrying connection for run', run.id, 'in', delay, 'ms');

        // Remove from monitoring to allow retry
        monitoringRuns.current.delete(run.id);

        setTimeout(() => {
          createEventSourceForRun(run, currentRetry + 1);
        }, delay);
      } else {
        console.log('[SSE] Max retries reached for run:', run.id);
        monitoringRuns.current.delete(run.id);
        delete retryCountersRef.current[run.id];
      }
    };

    eventSourcesRef.current[run.id] = eventSource;
  }, [agent.id, projectId]);

  // Handle action results
  useEffect(() => {
    if (fetcher.data?.success) {
      const intent = fetcher.formData?.get('intent');
      if (intent === 'update-test-case') {
        setToast({ message: 'Test case updated successfully', type: 'success' });
      } else if (intent === 'delete-test-case') {
        setToast({ message: 'Test case deleted successfully', type: 'success' });
      } else if (intent === 'bulk-action') {
        const action = fetcher.formData?.get('action');
        if (action === 'delete') {
          setToast({ message: 'Test cases deleted successfully', type: 'success' });
        }
      } else if (intent === 'create-evaluation') {
        setToast({ message: 'Evaluation created successfully', type: 'success' });
        setShowCreateModal(false);
      } else if (intent === 'run-evaluation' && fetcher.data?.run) {
        // Update the latest run for this evaluation
        const evaluationId = fetcher.formData?.get('evaluation_id') as string;
        if (evaluationId && fetcher.data.run) {
          const run = fetcher.data.run as EvaluationRun;

          // Update the latestRuns state with the new run
          setLatestRuns(prev => ({
            ...prev,
            [evaluationId]: run
          }));

          // Add to active runs if it's running or pending
          if (run.status === 'running' || run.status === 'pending') {
            console.log('[Run Started] Adding active run for evaluation:', evaluationId, 'status:', run.status, 'run id:', run.id);
            setActiveRuns(prev => ({
              ...prev,
              [evaluationId]: {
                id: run.id,
                status: run.status,
                completed: run.completed_test_cases || 0,
                total: run.total_test_cases || 0
              }
            }));

            // Directly create SSE connection for the new run
            // This avoids circular dependency issues with effects
            if (!monitoringRuns.current.has(run.id)) {
              console.log('[Run Started] Creating SSE connection for new run:', run.id);
              createEventSourceForRun(run);
            }
          }

          // Add new run to liveRunHistory if it's for current evaluation and has valid data
          if ((run.evaluation_id === currentEvaluation?.id || evaluationId === currentEvaluation?.id) &&
              run.status && // Ensure run has a valid status
              run.total_test_cases !== undefined && run.total_test_cases > 0) { // Ensure valid test count
            setLiveRunHistory((prev: EvaluationRun[]) => [run, ...prev]); // Add at beginning (newest first)
            console.log('[Run Started] Added to liveRunHistory for timeline');
          }
        }
        setToast({ message: 'Evaluation run started successfully', type: 'success' });
      } else if (intent === 'update-evaluation-settings' && fetcher.data?.evaluation) {
        const updatedEvaluation = fetcher.data.evaluation;
        // Update the current evaluation
        setCurrentEvaluation(updatedEvaluation);
        setToast({ message: 'Evaluation settings saved successfully', type: 'success' });
      }
    } else if (fetcher.data?.error) {
      setToast({ message: fetcher.data.error, type: 'error' });
    }
    setLoadingTestCaseId(null);
  }, [fetcher.data, fetcher.formData, currentEvaluation, createEventSourceForRun]);
  
  const handleRun = useCallback((evaluationId: string) => {
    fetcher.submit(
      { intent: 'run-evaluation', evaluation_id: evaluationId },
      { method: 'post' }
    );
  }, [fetcher]);

  // Update refs whenever state changes (without causing re-renders)
  useEffect(() => {
    activeRunsRef.current = activeRuns;
  }, [activeRuns]);

  useEffect(() => {
    liveRunHistoryRef.current = liveRunHistory;
  }, [liveRunHistory]);

  // Consolidated effect to manage SSE connections for all active runs
  // Only runs on mount and when evaluation changes (NOT when activeRuns/liveRunHistory update)
  useEffect(() => {
    console.log('[SSE Effect] Running for evaluation:', currentEvaluation?.id);

    // Collect all runs that need monitoring from both sources
    const runsToMonitor: EvaluationRun[] = [];

    // Add runs from activeRuns (these are shown on evaluation cards)
    Object.entries(activeRunsRef.current).forEach(([evalId, activeRunInfo]) => {
      if (activeRunInfo.status === 'running' || activeRunInfo.status === 'pending') {
        // Create a minimal run object with the information we have
        // The full run data will be fetched by the SSE endpoint
        runsToMonitor.push({
          id: activeRunInfo.id,
          evaluation_id: evalId,
          status: activeRunInfo.status,
          completed_test_cases: activeRunInfo.completed,
          total_test_cases: activeRunInfo.total
        } as EvaluationRun);
      }
    });

    // Add runs from liveRunHistory (these are shown in the timeline)
    if (currentEvaluation) {
      liveRunHistoryRef.current.forEach((run: EvaluationRun) => {
        if (run.status === 'running' || run.status === 'pending') {
          // Check if we already have this run from activeRuns
          const alreadyAdded = runsToMonitor.some(r => r.id === run.id);
          if (!alreadyAdded) {
            runsToMonitor.push(run);
          }
        }
      });
    }

    console.log('[SSE Effect] Found', runsToMonitor.length, 'runs to monitor');

    // Create connections for runs that aren't already being monitored
    runsToMonitor.forEach(run => {
      if (!monitoringRuns.current.has(run.id)) {
        console.log('[SSE] Starting monitoring for run:', run.id);
        createEventSourceForRun(run);
      }
    });

    // Cleanup: Close connections when evaluation changes
    return () => {
      console.log('[SSE Effect] Cleanup running for evaluation:', currentEvaluation?.id);

      // Close connections for runs not in the new evaluation
      const runIdsToKeep = new Set(runsToMonitor.map(r => r.id));
      const connectionsToClose: string[] = [];

      monitoringRuns.current.forEach(runId => {
        if (!runIdsToKeep.has(runId)) {
          connectionsToClose.push(runId);
        }
      });

      if (connectionsToClose.length > 0) {
        console.log('[SSE Effect] Closing', connectionsToClose.length, 'connections');
        connectionsToClose.forEach(runId => {
          const eventSource = eventSourcesRef.current[runId];
          if (eventSource) {
            console.log('[SSE] Closing connection for run:', runId);
            eventSource.close();
            delete eventSourcesRef.current[runId];
            monitoringRuns.current.delete(runId);
            delete retryCountersRef.current[runId];
          }
        });
      }
    };
  }, [currentEvaluation, createEventSourceForRun]); // NOTE: NOT including activeRuns/liveRunHistory to avoid circular dependency

  // Cleanup effect that runs when component unmounts
  useEffect(() => {
    return () => {
      const connectionCount = Object.keys(eventSourcesRef.current).length;
      console.log('[SSE] Component unmounting, closing', connectionCount, 'connections');

      if (connectionCount > 0) {
        const runIds = Object.keys(eventSourcesRef.current);
        console.log('[SSE] Closing connections for runs:', runIds);

        Object.values(eventSourcesRef.current).forEach(source => {
          source.close();
        });
      }

      eventSourcesRef.current = {};
      monitoringRuns.current.clear();
      retryCountersRef.current = {};

      console.log('[SSE] All connections closed and cleaned up');
    };
  }, []);

  const handleDelete = useCallback((evaluationId: string, evaluationName?: string) => {
    setDeleteConfirm({ 
      isOpen: true, 
      type: 'evaluation', 
      id: evaluationId,
      name: evaluationName
    });
  }, []);
  
  const handleEditTestCase = useCallback((id: string, updates: Partial<TestCase>) => {
    if (!currentEvaluation) return;
    fetcher.submit(
      { 
        intent: 'update-test-case', 
        test_case_id: id, 
        evaluation_id: currentEvaluation.id,
        updates: JSON.stringify(updates) 
      },
      { method: 'post' }
    );
  }, [fetcher, currentEvaluation]);
  
  const handleDeleteTestCase = useCallback((id: string) => {
    if (!currentEvaluation) return;
    setDeleteConfirm({ 
      isOpen: true, 
      type: 'single', 
      id 
    });
  }, [currentEvaluation]);
  
  const handleBulkAction = useCallback((action: string, ids: string[]) => {
    if (!currentEvaluation) return;
    
    if (action === 'delete' && ids.length > 0) {
      setDeleteConfirm({ 
        isOpen: true, 
        type: 'bulk', 
        ids 
      });
    }
  }, [currentEvaluation]);
  
  const handleSaveSettings = useCallback(async (settings: { name: string; description: string; criteria: string }) => {
    if (!currentEvaluation) {
      throw new Error('No evaluation selected');
    }
    
    return new Promise<void>((resolve, reject) => {
      fetcher.submit(
        { 
          intent: 'update-evaluation-settings', 
          evaluation_id: currentEvaluation.id,
          name: settings.name,
          description: settings.description,
          criteria: settings.criteria
        },
        { method: 'post' }
      );
      
      // Watch for the result in a separate effect
      const checkResult = setInterval(() => {
        if (fetcher.state === 'idle') {
          clearInterval(checkResult);
          if (fetcher.data?.success) {
            resolve();
          } else if (fetcher.data?.error) {
            reject(new Error(fetcher.data.error));
          }
        }
      }, 100);
      
      // Timeout after 10 seconds
      setTimeout(() => {
        clearInterval(checkResult);
        reject(new Error('Save operation timed out'));
      }, 10000);
    });
  }, [currentEvaluation, fetcher]);
  
  const getLastRun = useCallback((evaluationId: string) => {
    const run = latestRuns[evaluationId];
    if (!run) return undefined;
    
    return {
      score: run.overall_score ? Math.round(run.overall_score * 100) : 0,
      status: run.status,
      date: run.started_at
    };
  }, [latestRuns]);
  
  return (
    <EvaluationLayout particleBackground={true}>
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
      <SplitViewLayout
        metricsBar={
          <MetricsBar metrics={[
            { label: 'Total Evaluations', value: stats.totalEvaluations, icon: DocumentTextIcon, color: 'purple' },
            { label: 'Total Runs', value: stats.totalRuns, icon: PlayIcon, color: 'lime' },
            { label: 'Avg Pass Rate', value: `${stats.avgPassRate}%`, icon: ChartBarIcon, color: 'green' },
            { label: 'Total Test Cases', value: stats.totalTestCases, icon: BeakerIcon, color: 'amber' }
          ]} />
        }
        evaluationList={
          <div className="space-y-3">
            <div className="mb-4 space-y-3">
              <SearchBar onSearch={setSearchQuery} />
              <FilterChips filters={filters} onChange={setFilters} />
            </div>
            
            {filteredEvaluations.length > 0 ? (
              filteredEvaluations.map((evaluation: Evaluation) => (
                <EvaluationCard
                  key={evaluation.id}
                  evaluation={evaluation}
                  selected={evaluation.id === selectedId}
                  lastRun={getLastRun(evaluation.id)}
                  activeRun={activeRuns[evaluation.id]}
                  onSelect={setSelectedId}
                  onRun={handleRun}
                  onDelete={(id) => handleDelete(id, evaluation.name)}
                />
              ))
            ) : (
              <div className="text-center py-8 text-gray-400">
                {searchQuery ? 'No evaluations found' : 'No evaluations yet'}
              </div>
            )}
          </div>
        }
        detailView={
          currentEvaluation ? (
            <DetailPanel
              evaluation={currentEvaluation}
              activeTab={activeTab}
              onTabChange={setActiveTab}
            >
              <TabPanel value="overview" current={activeTab}>
                <EvaluationOverview evaluation={currentEvaluation} runs={runHistory} />
              </TabPanel>
              <TabPanel value="test-cases" current={activeTab}>
                <TestCaseTable 
                  testCases={testCases}
                  onEdit={handleEditTestCase}
                  onDelete={handleDeleteTestCase}
                  onBulkAction={handleBulkAction}
                  onAddTestCase={(testCase) => {
                    if (!currentEvaluation) return;
                    fetcher.submit(
                      {
                        intent: 'add-test-case',
                        evaluation_id: currentEvaluation.id,
                        task: testCase.task || '',
                        expected_output: testCase.expected_output || '',
                        evaluation_guideline: testCase.evaluation_guideline || ''
                      },
                      { method: 'post' }
                    );
                  }}
                  onExportCSV={() => {
                    // TODO: Implement CSV export
                    console.log('Export CSV not yet implemented');
                  }}
                />
              </TabPanel>
              <TabPanel value="runs" current={activeTab}>
                <RunHistoryTimeline runs={liveRunHistory} testCases={testCases} />
              </TabPanel>
              <TabPanel value="settings" current={activeTab}>
                <EvaluationSettings 
                  evaluation={currentEvaluation} 
                  onSave={handleSaveSettings}
                  isLoading={fetcher.state === 'submitting'}
                />
              </TabPanel>
            </DetailPanel>
          ) : (
            <EmptyState 
              icon={BeakerIcon}
              title="Select an evaluation"
              description="Choose an evaluation from the list to view details"
            />
          )
        }
        onCreateEvaluation={() => setShowCreateModal(true)}
      />
      
      {/* Create Evaluation Modal */}
      <CreateEvaluationModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        agentId={agent.id}
        projectId={projectId}
      />
      
      {/* Delete Confirmation Modal */}
      <ConfirmationModal
        isOpen={deleteConfirm.isOpen}
        onClose={() => setDeleteConfirm({ isOpen: false, type: 'single' })}
        onConfirm={() => {
          if (deleteConfirm.type === 'single' && deleteConfirm.id && currentEvaluation) {
            fetcher.submit(
              { 
                intent: 'delete-test-case', 
                test_case_id: deleteConfirm.id,
                evaluation_id: currentEvaluation.id
              },
              { method: 'post' }
            );
          } else if (deleteConfirm.type === 'bulk' && deleteConfirm.ids && currentEvaluation) {
            fetcher.submit(
              { 
                intent: 'bulk-action', 
                action: 'delete',
                evaluation_id: currentEvaluation.id,
                ids: JSON.stringify(deleteConfirm.ids) 
              },
              { method: 'post' }
            );
          } else if (deleteConfirm.type === 'evaluation' && deleteConfirm.id) {
            fetcher.submit(
              { intent: 'delete-evaluation', evaluation_id: deleteConfirm.id },
              { method: 'post' }
            );
          }
        }}
        title={
          deleteConfirm.type === 'evaluation' 
            ? 'Delete Evaluation'
            : deleteConfirm.type === 'bulk' 
            ? 'Delete Test Cases'
            : 'Delete Test Case'
        }
        message={
          deleteConfirm.type === 'evaluation' 
            ? `Are you sure you want to delete the evaluation "${deleteConfirm.name || 'this evaluation'}"? This action cannot be undone.`
            : deleteConfirm.type === 'bulk' 
            ? `Are you sure you want to delete ${deleteConfirm.ids?.length || 0} test case${(deleteConfirm.ids?.length || 0) > 1 ? 's' : ''}? This action cannot be undone.`
            : 'Are you sure you want to delete this test case? This action cannot be undone.'
        }
        confirmText="Delete"
        cancelText="Cancel"
        variant="danger"
      />
    </EvaluationLayout>
  );
}
