import { useFetcher } from "@remix-run/react";
import { useEffect, useState } from "react";
import { MagnifyingGlassIcon, PlusIcon, ArrowLeftIcon, ChevronDownIcon, ChevronUpIcon } from "@heroicons/react/24/outline";
import type { Evaluation } from "~/services/chicory.server";
import type { TaskPair } from "~/components/ManageTable";

interface AddTasksToEvaluationModalProps {
  isOpen: boolean;
  onClose: () => void;
  selectedTasks: TaskPair[];
  projectId: string;
  agentId: string;
}

type ModalView = 'select' | 'create';

export function AddTasksToEvaluationModal({
  isOpen,
  onClose,
  selectedTasks,
  projectId,
  agentId
}: AddTasksToEvaluationModalProps) {
  const fetcher = useFetcher<{ evaluations?: Evaluation[]; success?: boolean; error?: string; evaluation?: Evaluation }>();
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedEvaluationId, setSelectedEvaluationId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [view, setView] = useState<ModalView>('select');

  // Task management state
  const [tasksToSubmit, setTasksToSubmit] = useState<string[]>([]);
  const [taskSearchTerm, setTaskSearchTerm] = useState("");
  const [isTasksExpanded, setIsTasksExpanded] = useState(true);

  // Form state for creating new evaluation
  const [newEvalName, setNewEvalName] = useState("");
  const [newEvalDescription, setNewEvalDescription] = useState("");
  const [newEvalCriteria, setNewEvalCriteria] = useState("");
  const [formErrors, setFormErrors] = useState<{ name?: string; criteria?: string }>({});

  // Initialize tasks to submit when modal opens
  useEffect(() => {
    if (isOpen) {
      setTasksToSubmit(selectedTasks.map(t => t.id));
      setTaskSearchTerm("");
    }
  }, [isOpen, selectedTasks]);

  // Load evaluations when modal opens
  useEffect(() => {
    if (isOpen && !fetcher.data?.evaluations) {
      fetcher.load(`/api/projects/${projectId}/agents/${agentId}/evaluations`);
    }
  }, [isOpen, projectId, agentId]);

  const evaluations = fetcher.data?.evaluations || [];

  // Filter evaluations based on search term
  const filteredEvaluations = evaluations.filter(evaluation =>
    evaluation.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (evaluation.description && evaluation.description.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  // Filter and compute tasks to display
  const tasksToDisplay = selectedTasks.filter(task =>
    task.userQuery.toLowerCase().includes(taskSearchTerm.toLowerCase()) ||
    (task.source && task.source.toLowerCase().includes(taskSearchTerm.toLowerCase()))
  );

  const TASK_LIMIT = 25;

  const toggleTaskSelection = (taskId: string) => {
    setTasksToSubmit(prev => {
      if (prev.includes(taskId)) {
        return prev.filter(id => id !== taskId);
      } else if (prev.length >= TASK_LIMIT) {
        // Don't add if limit reached
        return prev;
      } else {
        return [...prev, taskId];
      }
    });
  };

  const selectAllTasks = () => {
    // Only select up to TASK_LIMIT tasks
    setTasksToSubmit(selectedTasks.slice(0, TASK_LIMIT).map(t => t.id));
  };

  const deselectAllTasks = () => {
    setTasksToSubmit([]);
  };

  // Close modal on successful submission
  useEffect(() => {
    if (fetcher.state === 'idle' && fetcher.data?.success) {
      setIsSubmitting(false);
      onClose();
      setSelectedEvaluationId(null);
      setSearchTerm("");
      setTaskSearchTerm("");
      setIsTasksExpanded(true);
      setView('select');
      setNewEvalName("");
      setNewEvalDescription("");
      setNewEvalCriteria("");
      setFormErrors({});
      // Reload the page to show updated data
      window.location.reload();
    }
  }, [fetcher.state, fetcher.data, onClose]);

  // Handle evaluation creation success
  useEffect(() => {
    if (fetcher.state === 'idle' && fetcher.data?.evaluation && view === 'create') {
      // Evaluation was created successfully, now add tasks to it
      const evaluationId = fetcher.data.evaluation.id;
      setSelectedEvaluationId(evaluationId);
      handleAddToEvaluation(evaluationId);
    }
  }, [fetcher.state, fetcher.data, view]);

  if (!isOpen) return null;

  const validateForm = (): boolean => {
    const errors: { name?: string; criteria?: string } = {};

    if (!newEvalName || newEvalName.length < 3) {
      errors.name = 'Name must be at least 3 characters';
    } else if (newEvalName.length > 100) {
      errors.name = 'Name must be less than 100 characters';
    }

    if (!newEvalCriteria || newEvalCriteria.length < 10) {
      errors.criteria = 'Evaluation criteria must be at least 10 characters';
    } else if (newEvalCriteria.length > 1000) {
      errors.criteria = 'Evaluation criteria must be less than 1000 characters';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleCreateEvaluation = () => {
    if (!validateForm()) return;

    setIsSubmitting(true);

    // Filter to only submit selected tasks
    const tasksToAdd = selectedTasks.filter(task => tasksToSubmit.includes(task.id));

    const formData = new FormData();
    formData.append("intent", "create-evaluation-with-tasks");
    formData.append("name", newEvalName);
    formData.append("description", newEvalDescription);
    formData.append("criteria", newEvalCriteria);
    formData.append("tasks", JSON.stringify(tasksToAdd.map(task => ({
      userQuery: task.userQuery,
      response: task.responseStripped || task.response,
      source: task.source,
      timestamp: task.timestamp
    }))));

    fetcher.submit(formData, {
      method: "post",
      action: `/projects/${projectId}/agents/${agentId}/evaluations`
    });
  };

  const handleAddToEvaluation = (evaluationId?: string) => {
    const evalId = evaluationId || selectedEvaluationId;
    if (!evalId || tasksToSubmit.length === 0) return;

    setIsSubmitting(true);

    // Filter to only submit selected tasks
    const tasksToAdd = selectedTasks.filter(task => tasksToSubmit.includes(task.id));

    const formData = new FormData();
    formData.append("intent", "add-tasks-to-evaluation");
    formData.append("evaluationId", evalId);
    formData.append("taskIds", JSON.stringify(tasksToAdd.map(t => t.id)));
    formData.append("tasks", JSON.stringify(tasksToAdd.map(task => ({
      userQuery: task.userQuery,
      response: task.responseStripped || task.response,
      source: task.source,
      timestamp: task.timestamp
    }))));

    fetcher.submit(formData, { method: "post" });
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-3xl max-h-[80vh] flex flex-col">
        {/* Header with back button */}
        <div className="flex items-center mb-4">
          {view === 'create' && (
            <button
              onClick={() => setView('select')}
              disabled={isSubmitting}
              className="mr-3 p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors disabled:opacity-50"
            >
              <ArrowLeftIcon className="h-5 w-5 text-gray-600 dark:text-gray-400" />
            </button>
          )}
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            {view === 'create' ? 'Create New Evaluation' : 'Add Tasks to Evaluation'}
          </h2>
        </div>

        {/* Selected tasks table */}
        <div className="mb-4 border border-purple-200 dark:border-purple-700 rounded-lg overflow-hidden">
          {/* Header */}
          <div className="bg-purple-50 dark:bg-purple-900/20 p-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setIsTasksExpanded(!isTasksExpanded)}
                  className="p-1 rounded hover:bg-purple-100 dark:hover:bg-purple-800 transition-colors"
                >
                  {isTasksExpanded ? (
                    <ChevronUpIcon className="h-5 w-5 text-purple-700 dark:text-purple-300" />
                  ) : (
                    <ChevronDownIcon className="h-5 w-5 text-purple-700 dark:text-purple-300" />
                  )}
                </button>
                <div>
                  <div className="text-sm font-medium text-purple-900 dark:text-purple-100">
                    Selected Tasks
                  </div>
                  <div className={`text-xs ${tasksToSubmit.length >= TASK_LIMIT ? 'text-amber-600 dark:text-amber-400 font-medium' : 'text-purple-700 dark:text-purple-300'}`}>
                    {tasksToSubmit.length} of {selectedTasks.length} selected (max {TASK_LIMIT})
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={selectAllTasks}
                  className="px-2 py-1 text-xs font-medium text-purple-700 dark:text-purple-300 hover:bg-purple-100 dark:hover:bg-purple-800 rounded transition-colors"
                >
                  Select All
                </button>
                <button
                  onClick={deselectAllTasks}
                  className="px-2 py-1 text-xs font-medium text-purple-700 dark:text-purple-300 hover:bg-purple-100 dark:hover:bg-purple-800 rounded transition-colors"
                >
                  Clear
                </button>
              </div>
            </div>

            {/* Limit warning */}
            {tasksToSubmit.length >= TASK_LIMIT && (
              <div className="mt-3 p-2 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded text-xs text-amber-800 dark:text-amber-200">
                ⚠️ Maximum limit of {TASK_LIMIT} tasks reached. Uncheck tasks to select different ones.
              </div>
            )}

            {/* Task search */}
            {isTasksExpanded && (
              <div className="mt-3 relative">
                <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-purple-400" />
                <input
                  type="text"
                  placeholder="Filter tasks..."
                  value={taskSearchTerm}
                  onChange={(e) => setTaskSearchTerm(e.target.value)}
                  className="w-full pl-9 pr-3 py-1.5 text-sm border border-purple-200 dark:border-purple-700 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-purple-500"
                />
              </div>
            )}
          </div>

          {/* Task table */}
          {isTasksExpanded && (
            <div className="max-h-60 overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 dark:bg-gray-900 sticky top-0">
                  <tr>
                    <th className="w-8 px-3 py-2 text-left">
                      <input
                        type="checkbox"
                        checked={tasksToSubmit.length === selectedTasks.length}
                        onChange={() => {
                          if (tasksToSubmit.length === selectedTasks.length) {
                            deselectAllTasks();
                          } else {
                            selectAllTasks();
                          }
                        }}
                        className="rounded border-gray-300 dark:border-gray-600 text-purple-600 focus:ring-purple-500"
                      />
                    </th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                      Task / Query
                    </th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wider w-32">
                      Response
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {tasksToDisplay.map((task) => (
                    <tr
                      key={task.id}
                      className={`hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors ${
                        tasksToSubmit.includes(task.id) ? 'bg-purple-50/50 dark:bg-purple-900/10' : ''
                      }`}
                    >
                      <td className="px-3 py-2">
                        <input
                          type="checkbox"
                          checked={tasksToSubmit.includes(task.id)}
                          onChange={() => toggleTaskSelection(task.id)}
                          disabled={!tasksToSubmit.includes(task.id) && tasksToSubmit.length >= TASK_LIMIT}
                          className="rounded border-gray-300 dark:border-gray-600 text-purple-600 focus:ring-purple-500 disabled:opacity-50 disabled:cursor-not-allowed"
                        />
                      </td>
                      <td className="px-3 py-2 text-gray-900 dark:text-gray-100">
                        <div className="max-w-md truncate" title={task.userQuery}>
                          {task.userQuery}
                        </div>
                      </td>
                      <td className="px-3 py-2 text-gray-600 dark:text-gray-400 text-xs">
                        <div className="max-w-xs truncate" title={task.response || 'N/A'}>
                          {task.response ? (
                            task.response.length > 150
                              ? `${task.response.substring(0, 150)}...`
                              : task.response
                          ) : 'N/A'}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {tasksToDisplay.length === 0 && (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400 text-sm">
                  {taskSearchTerm ? 'No tasks match your filter' : 'No tasks selected'}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Error display */}
        {fetcher.data?.error && (
          <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <p className="text-sm text-red-600 dark:text-red-400">
              {fetcher.data.error}
            </p>
          </div>
        )}

        {/* View: Select Existing Evaluation */}
        {view === 'select' && (
          <>
            {/* Search input */}
            <div className="relative mb-4">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search evaluations..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>

            {/* Loading state */}
            {fetcher.state === 'loading' && !fetcher.data?.evaluations && (
              <div className="flex-1 flex items-center justify-center py-8">
                <div className="text-gray-500 dark:text-gray-400">Loading evaluations...</div>
              </div>
            )}

            {/* Evaluations list */}
            {fetcher.data?.evaluations && (
              <div className="flex-1 overflow-y-auto mb-4 space-y-2">
                {filteredEvaluations.length === 0 ? (
                  <div className="text-center py-8">
                    <p className="text-gray-500 dark:text-gray-400 mb-4">
                      {searchTerm ? 'No evaluations found matching your search' : 'No evaluations available'}
                    </p>
                    {!searchTerm && (
                      <button
                        onClick={() => setView('create')}
                        className="inline-flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
                      >
                        <PlusIcon className="h-5 w-5" />
                        Create New Evaluation
                      </button>
                    )}
                  </div>
                ) : (
                  <>
                    {/* Create new button */}
                    <button
                      onClick={() => setView('create')}
                      className="w-full p-4 rounded-lg border-2 border-dashed border-gray-300 dark:border-gray-600 hover:border-purple-500 dark:hover:border-purple-500 hover:bg-purple-50 dark:hover:bg-purple-900/10 transition-colors flex items-center justify-center gap-2 text-gray-600 dark:text-gray-400 hover:text-purple-600 dark:hover:text-purple-400"
                    >
                      <PlusIcon className="h-5 w-5" />
                      <span className="font-medium">Create New Evaluation</span>
                    </button>

                    {/* Existing evaluations */}
                    {filteredEvaluations.map((evaluation) => (
                      <div
                        key={evaluation.id}
                        onClick={() => setSelectedEvaluationId(evaluation.id)}
                        className={`p-4 rounded-lg border cursor-pointer transition-colors ${
                          selectedEvaluationId === evaluation.id
                            ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/20'
                            : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700'
                        }`}
                      >
                        <div className="flex justify-between items-start">
                          <div className="flex-1">
                            <h3 className="font-medium text-sm text-gray-900 dark:text-gray-100">
                              {evaluation.name}
                            </h3>
                            {evaluation.description && (
                              <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                                {evaluation.description}
                              </p>
                            )}
                            <div className="mt-2 text-xs text-gray-500 dark:text-gray-500">
                              <span>ID: {evaluation.id.substring(0, 8)}...</span>
                            </div>
                          </div>
                          {selectedEvaluationId === evaluation.id && (
                            <div className="ml-2">
                              <svg className="h-5 w-5 text-purple-600 dark:text-purple-400" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                              </svg>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </>
                )}
              </div>
            )}

            {/* Action buttons */}
            <div className="flex justify-end space-x-3">
              <button
                onClick={onClose}
                disabled={isSubmitting}
                className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={() => handleAddToEvaluation()}
                disabled={!selectedEvaluationId || tasksToSubmit.length === 0 || isSubmitting}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSubmitting ? 'Adding...' : `Add ${tasksToSubmit.length} Task${tasksToSubmit.length !== 1 ? 's' : ''}`}
              </button>
            </div>
          </>
        )}

        {/* View: Create New Evaluation */}
        {view === 'create' && (
          <>
            <div className="flex-1 overflow-y-auto mb-4 space-y-4">
              {/* Name field */}
              <div>
                <label htmlFor="eval-name" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Evaluation Name *
                </label>
                <input
                  id="eval-name"
                  type="text"
                  value={newEvalName}
                  onChange={(e) => {
                    setNewEvalName(e.target.value);
                    setFormErrors(prev => ({ ...prev, name: undefined }));
                  }}
                  className={`w-full px-3 py-2 rounded-lg border ${
                    formErrors.name
                      ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                      : 'border-gray-300 dark:border-gray-600 focus:border-purple-500 focus:ring-purple-500'
                  } bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2`}
                  placeholder="e.g., Customer Support Evaluation"
                  disabled={isSubmitting}
                />
                {formErrors.name && (
                  <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                    {formErrors.name}
                  </p>
                )}
              </div>

              {/* Description field */}
              <div>
                <label htmlFor="eval-description" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Description (Optional)
                </label>
                <textarea
                  id="eval-description"
                  value={newEvalDescription}
                  onChange={(e) => setNewEvalDescription(e.target.value)}
                  rows={2}
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:border-purple-500 focus:ring-purple-500"
                  placeholder="Brief description of this evaluation..."
                  disabled={isSubmitting}
                />
              </div>

              {/* Criteria field */}
              <div>
                <label htmlFor="eval-criteria" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Evaluation Criteria *
                </label>
                <textarea
                  id="eval-criteria"
                  value={newEvalCriteria}
                  onChange={(e) => {
                    setNewEvalCriteria(e.target.value);
                    setFormErrors(prev => ({ ...prev, criteria: undefined }));
                  }}
                  rows={6}
                  className={`w-full px-3 py-2 rounded-lg border ${
                    formErrors.criteria
                      ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                      : 'border-gray-300 dark:border-gray-600 focus:border-purple-500 focus:ring-purple-500'
                  } bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2`}
                  placeholder="Describe the criteria for evaluating agent responses..."
                  disabled={isSubmitting}
                />
                {formErrors.criteria && (
                  <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                    {formErrors.criteria}
                  </p>
                )}
              </div>

              {/* Info message */}
              <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                <p className="text-sm text-blue-800 dark:text-blue-200">
                  {tasksToSubmit.length} task{tasksToSubmit.length !== 1 ? 's' : ''} will be added to this evaluation as test cases.
                </p>
              </div>
            </div>

            {/* Action buttons */}
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setView('select')}
                disabled={isSubmitting}
                className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
              >
                Back
              </button>
              <button
                onClick={handleCreateEvaluation}
                disabled={isSubmitting}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSubmitting ? 'Creating...' : 'Create & Add Tasks'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
