import { json, redirect } from "@remix-run/node";
import type { LoaderFunctionArgs, ActionFunctionArgs } from "@remix-run/node";
import { useLoaderData, Link, useParams, useFetcher, useNavigate } from "@remix-run/react";
import { useState, useEffect } from "react";
import { ArrowLeftIcon, PlayIcon, PlusIcon, TrashIcon } from "@heroicons/react/24/outline";
import { getUserOrgDetails } from "~/auth/auth.server";
import { 
  getAgent,
  getEvaluation,
  getTestCases,
  getLatestRun,
  getRunHistory,
  startEvaluationRun,
  deleteEvaluation,
  addTestCase,
  deleteTestCase,
  updateTestCase
} from "~/services/chicory.server";
import { TestCaseTable } from "~/components/TestCaseTable";
import { EvaluationRunStatus } from "~/components/EvaluationRunStatus";
import { ScoreIndicator } from "~/components/ScoreIndicator";
import { StatusBadge } from "~/components/StatusBadge";
import { Button } from "~/components/Button";
import { Toast, type ToastType } from "~/components/Toast";

export async function loader({ request, params }: LoaderFunctionArgs) {
  const { agentId, evalId, projectId } = params;
  
  if (!agentId || !evalId || !projectId) {
    throw new Response("Agent ID, Evaluation ID, and Project ID are required", { status: 400 });
  }
  
  const userDetails = await getUserOrgDetails(request);
  if (userDetails instanceof Response) {
    return userDetails;
  }
  
  const orgId = 'orgId' in userDetails ? (userDetails as any).orgId : undefined;
  if (!orgId) {
    return redirect("/new");
  }
  
  // Parallel fetch evaluation details
  const [agent, evaluation, testCases, latestRun, runHistory] = await Promise.all([
    getAgent(projectId, agentId),
    getEvaluation(projectId, agentId, evalId),
    getTestCases(projectId, agentId, evalId, { limit: 100 }),
    getLatestRun(projectId, agentId, evalId),
    getRunHistory(projectId, agentId, evalId, { limit: 10 })
  ]);
  
  if (!agent || !evaluation) {
    throw new Response("Not found", { status: 404 });
  }
  
  return json({
    agent,
    evaluation,
    testCases: testCases.test_cases,
    latestRun,
    runHistory: runHistory.runs,
    projectId
  });
}

export async function action({ request, params }: ActionFunctionArgs) {
  const { agentId, evalId, projectId } = params;
  
  if (!agentId || !evalId || !projectId) {
    throw new Response("Agent ID, Evaluation ID, and Project ID are required", { status: 400 });
  }
  
  const userDetails = await getUserOrgDetails(request);
  if (userDetails instanceof Response) {
    return userDetails;
  }
  
  const formData = await request.formData();
  const intent = formData.get("intent") as string;
  
  switch (intent) {
    case "run": {
      try {
        const run = await startEvaluationRun(projectId, agentId, evalId);
        return json({ success: true, run });
      } catch (error) {
        console.error("Failed to start evaluation run:", error);
        return json({ error: "Failed to start run" }, { status: 500 });
      }
    }
    
    case "delete": {
      try {
        await deleteEvaluation(projectId, agentId, evalId);
        return redirect(`/projects/${projectId}/agents/${agentId}/evaluations`);
      } catch (error) {
        console.error("Failed to delete evaluation:", error);
        return json({ error: "Failed to delete evaluation" }, { status: 500 });
      }
    }
    
    case "add_test_case": {
      const task = formData.get("task") as string;
      const expectedOutput = formData.get("expected_output") as string;
      const evaluationGuideline = formData.get("evaluation_guideline") as string;
      
      if (!task || !expectedOutput || !evaluationGuideline) {
        return json({ error: "All fields are required" }, { status: 400 });
      }
      
      try {
        const testCase = await addTestCase(projectId, agentId, evalId, {
          task,
          expected_output: expectedOutput,
          evaluation_guideline: evaluationGuideline
        });
        return json({ success: true, testCase });
      } catch (error) {
        console.error("Failed to add test case:", error);
        return json({ error: "Failed to add test case" }, { status: 500 });
      }
    }
    
    case "delete_test_case": {
      const testCaseId = formData.get("test_case_id") as string;
      
      if (!testCaseId) {
        return json({ error: "Test case ID is required" }, { status: 400 });
      }
      
      try {
        await deleteTestCase(projectId, agentId, evalId, testCaseId);
        return json({ success: true });
      } catch (error) {
        console.error("Failed to delete test case:", error);
        return json({ error: "Failed to delete test case" }, { status: 500 });
      }
    }
    
    case "update_test_case": {
      const testCaseId = formData.get("test_case_id") as string;
      const task = formData.get("task") as string;
      const expectedOutput = formData.get("expected_output") as string;
      const evaluationGuideline = formData.get("evaluation_guideline") as string;
      
      if (!testCaseId) {
        return json({ error: "Test case ID is required" }, { status: 400 });
      }
      
      try {
        const updatedTestCase = await updateTestCase(projectId, agentId, evalId, testCaseId, {
          task,
          expected_output: expectedOutput,
          evaluation_guideline: evaluationGuideline
        });
        return json({ success: true, testCase: updatedTestCase });
      } catch (error) {
        console.error("Failed to update test case:", error);
        return json({ error: "Failed to update test case" }, { status: 500 });
      }
    }
    
    case "bulk_delete": {
      const testCaseIds = formData.get("test_case_ids") as string;
      
      if (!testCaseIds) {
        return json({ error: "Test case IDs are required" }, { status: 400 });
      }
      
      try {
        const ids = testCaseIds.split(',');
        await Promise.all(ids.map(id => deleteTestCase(projectId, agentId, evalId, id)));
        return json({ success: true });
      } catch (error) {
        console.error("Failed to delete test cases:", error);
        return json({ error: "Failed to delete test cases" }, { status: 500 });
      }
    }
    
    default:
      return json({ error: "Invalid action" }, { status: 400 });
  }
}

export default function EvaluationDetail() {
  const { agent, evaluation, testCases, latestRun, runHistory, projectId } = useLoaderData<typeof loader>();
  const params = useParams();
  const navigate = useNavigate();
  const fetcher = useFetcher();
  const [showAddTestCase, setShowAddTestCase] = useState(false);
  const [currentRun, setCurrentRun] = useState(latestRun);
  const [loadingTestCaseId, setLoadingTestCaseId] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; type: ToastType } | null>(null);

  // Update current run when action completes
  useEffect(() => {
    if (fetcher.data?.run) {
      setCurrentRun(fetcher.data.run);
    }
    
    // Handle success/error messages
    if (fetcher.data?.success) {
      if (fetcher.formData?.get('intent') === 'update_test_case') {
        setToast({ message: 'Test case updated successfully', type: 'success' });
      } else if (fetcher.formData?.get('intent') === 'delete_test_case') {
        setToast({ message: 'Test case deleted successfully', type: 'success' });
      } else if (fetcher.formData?.get('intent') === 'add_test_case') {
        setToast({ message: 'Test case added successfully', type: 'success' });
        setShowAddTestCase(false);
      }
    } else if (fetcher.data?.error) {
      setToast({ message: fetcher.data.error, type: 'error' });
    }
  }, [fetcher.data, fetcher.formData]);

  const handleRunEvaluation = () => {
    fetcher.submit(
      { intent: "run" },
      { method: "post" }
    );
  };

  const handleDeleteEvaluation = () => {
    if (confirm(`Are you sure you want to delete the evaluation "${evaluation.name}"? This action cannot be undone.`)) {
      fetcher.submit(
        { intent: "delete" },
        { method: "post" }
      );
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Navigation */}
        <div className="mb-6">
          <Link
            to={`/projects/${params.projectId}/agents/${params.agentId}/evaluations`}
            className="inline-flex items-center text-sm text-gray-600 dark:text-gray-400 hover:text-purple-600 dark:hover:text-purple-400"
          >
            <ArrowLeftIcon className="h-4 w-4 mr-1" />
            Back to Evaluations
          </Link>
        </div>

        {/* Header */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6 mb-6">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                {evaluation.name}
              </h1>
              {evaluation.description && (
                <p className="text-gray-600 dark:text-gray-400">
                  {evaluation.description}
                </p>
              )}
              <p className="text-sm text-gray-500 dark:text-gray-500 mt-2">
                Created {formatDate(evaluation.created_at)}
              </p>
            </div>
            
            <div className="flex items-center gap-2">
              <Button
                variant="primary"
                onClick={handleRunEvaluation}
                disabled={fetcher.state === "submitting" || currentRun?.status === 'running'}
              >
                <PlayIcon className="h-4 w-4 mr-1" />
                {currentRun?.status === 'running' ? 'Running...' : 'Run Evaluation'}
              </Button>
              
              <Button
                variant="tertiary"
                onClick={handleDeleteEvaluation}
              >
                <TrashIcon className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Evaluation Criteria */}
          <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
            <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Evaluation Criteria
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 whitespace-pre-wrap">
              {evaluation.criteria}
            </p>
          </div>
        </div>

        {/* Current Run Status */}
        {currentRun && (
          <div className="mb-6">
            <EvaluationRunStatus
              run={currentRun}
          streamUrl={currentRun.status === 'running' ? `/api/projects/${projectId}/agents/${agent.id}/evaluations/${evaluation.id}/run/stream` : undefined}
              onCancel={() => {
                // Implement cancel functionality if needed
              }}
            />
          </div>
        )}

        {/* Run History */}
        {runHistory.length > 0 && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6 mb-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Run History
            </h2>
            <div className="space-y-3">
              {runHistory.map((run) => (
                <div 
                  key={run.id}
                  className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-900/50 rounded-lg"
                >
                  <div className="flex items-center gap-4">
                    <StatusBadge status={run.status} size="sm" />
                    <span className="text-sm text-gray-600 dark:text-gray-400">
                      {formatDate(run.started_at)}
                    </span>
                    <span className="text-sm text-gray-600 dark:text-gray-400">
                      {run.completed_test_cases}/{run.total_test_cases} tests
                    </span>
                  </div>
                  
                  <div className="flex items-center gap-3">
                    {run.overall_score !== null && (
                      <ScoreIndicator
                        score={run.overall_score}
                        variant="numeric"
                        size="sm"
                      />
                    )}
                    <span className="text-sm text-gray-500">
                      {run.failed_test_cases} failed
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Test Cases */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Test Cases ({testCases.length})
            </h2>
            
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowAddTestCase(!showAddTestCase)}
            >
              <PlusIcon className="h-4 w-4 mr-1" />
              Add Test Case
            </Button>
          </div>

          {/* Add Test Case Form */}
          {showAddTestCase && (
            <div className="mb-6 p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
              <fetcher.Form method="post" className="space-y-4">
                <input type="hidden" name="intent" value="add_test_case" />
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Task
                  </label>
                  <textarea
                    name="task"
                    required
                    rows={2}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500"
                    placeholder="What should the agent do?"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Expected Output
                  </label>
                  <textarea
                    name="expected_output"
                    required
                    rows={2}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500"
                    placeholder="What output do you expect?"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Evaluation Guideline
                  </label>
                  <textarea
                    name="evaluation_guideline"
                    required
                    rows={2}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500"
                    placeholder="How should the output be evaluated?"
                  />
                </div>
                
                <div className="flex justify-end gap-2">
                  <Button
                    type="button"
                    variant="tertiary"
                    size="sm"
                    onClick={() => setShowAddTestCase(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    variant="primary"
                    size="sm"
                    disabled={fetcher.state === "submitting"}
                  >
                    {fetcher.state === "submitting" ? "Adding..." : "Add Test Case"}
                  </Button>
                </div>
              </fetcher.Form>
            </div>
          )}

          {/* Test Cases Table */}
          <TestCaseTable
            testCases={testCases}
            results={currentRun?.test_case_results}
            selectable={true}
            onEdit={(id, updates) => {
              fetcher.submit(
                { 
                  intent: "update_test_case", 
                  test_case_id: id,
                  task: updates.task || '',
                  expected_output: updates.expected_output || '',
                  evaluation_guideline: updates.evaluation_guideline || ''
                },
                { method: "post" }
              );
            }}
            onDelete={(id) => {
              if (confirm('Are you sure you want to delete this test case?')) {
                fetcher.submit(
                  { intent: "delete_test_case", test_case_id: id },
                  { method: "post" }
                );
              }
            }}
          />
        </div>
      </div>
    </div>
  );
}
