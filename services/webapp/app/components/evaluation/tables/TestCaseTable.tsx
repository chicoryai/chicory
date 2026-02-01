import React, { useState } from 'react';
import type { TestCase } from '~/services/chicory.server';
import { Button } from '~/components/Button';
import { 
  ArrowUpTrayIcon as UploadIcon, 
  ArrowDownTrayIcon as DownloadIcon,
  PencilIcon,
  TrashIcon,
  CheckIcon,
  XMarkIcon,
  PlusIcon
} from '@heroicons/react/24/outline';

interface TestCaseTableProps {
  testCases: TestCase[];
  onEdit: (id: string, updates: Partial<TestCase>) => void;
  onDelete: (id: string) => void;
  onBulkAction: (action: string, ids: string[]) => void;
  onAddTestCase?: (testCase: Partial<TestCase>) => void;
  onImportCSV?: (file: File) => void;
  onExportCSV?: () => void;
}

interface TestCaseRowProps {
  testCase: TestCase;
  selected: boolean;
  onSelect: (selected: boolean) => void;
  onEdit: (updates: Partial<TestCase>) => void;
  onDelete: () => void;
}

function TestCaseRow({ testCase, selected, onSelect, onEdit, onDelete }: TestCaseRowProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedTask, setEditedTask] = useState(testCase.task || '');
  const [editedExpectedOutput, setEditedExpectedOutput] = useState(testCase.expected_output || '');
  const [editedGuideline, setEditedGuideline] = useState(testCase.evaluation_guideline || '');
  
  return (
    <tr className="hover:bg-gray-50 dark:hover:bg-purple-900/10 transition-colors">
      <td className="w-10 px-4 py-3">
        <input 
          type="checkbox"
          checked={selected}
          onChange={(e) => onSelect(e.target.checked)}
          className="rounded border-gray-300 dark:border-gray-600 text-purple-600 dark:text-purple-400 focus:ring-purple-500 dark:focus:ring-purple-400 accent-purple-600 dark:accent-purple-400"
        />
      </td>
      <td className="px-4 py-3">
        {isEditing ? (
          <input
            type="text"
            value={editedTask}
            onChange={(e) => setEditedTask(e.target.value)}
            onBlur={() => {
              // Don't save on blur, wait for explicit save
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                // Move to next field instead of saving
              }
              if (e.key === 'Escape') {
                setEditedTask(testCase.task || '');
                setEditedExpectedOutput(testCase.expected_output || '');
                setEditedGuideline(testCase.evaluation_guideline || '');
                setIsEditing(false);
              }
            }}
            className="w-full bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-2 py-1 rounded border border-gray-300 dark:border-purple-400/30 focus:border-purple-400 dark:focus:border-purple-400 focus:outline-none"
            autoFocus
          />
        ) : (
          <span className="text-gray-700 dark:text-gray-300">{testCase.task}</span>
        )}
      </td>
      <td className="px-4 py-3">
        {isEditing ? (
          <textarea
            value={editedExpectedOutput}
            onChange={(e) => setEditedExpectedOutput(e.target.value)}
            className="w-full bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-2 py-1 rounded border border-gray-300 dark:border-purple-400/30 focus:border-purple-400 dark:focus:border-purple-400 focus:outline-none text-sm"
            rows={2}
          />
        ) : (
          <span className="text-gray-700 dark:text-gray-300 text-sm">{testCase.expected_output}</span>
        )}
      </td>
      <td className="px-4 py-3">
        {isEditing ? (
          <textarea
            value={editedGuideline}
            onChange={(e) => setEditedGuideline(e.target.value)}
            className="w-full bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-2 py-1 rounded border border-gray-300 dark:border-purple-400/30 focus:border-purple-400 dark:focus:border-purple-400 focus:outline-none text-sm"
            rows={2}
          />
        ) : (
          <span className="text-gray-600 dark:text-gray-400 text-sm">{testCase.evaluation_guideline || '-'}</span>
        )}
      </td>
      <td className="w-32 px-4 py-3">
        <div className="flex gap-1">
          {isEditing ? (
            <>
              <button
                onClick={() => {
                  onEdit({ 
                    task: editedTask,
                    expected_output: editedExpectedOutput,
                    evaluation_guideline: editedGuideline
                  });
                  setIsEditing(false);
                }}
                className="p-1 text-green-600 hover:text-green-700 transition-colors"
                title="Save changes"
              >
                <CheckIcon className="w-4 h-4" />
              </button>
              <button
                onClick={() => {
                  setEditedTask(testCase.task || '');
                  setEditedExpectedOutput(testCase.expected_output || '');
                  setEditedGuideline(testCase.evaluation_guideline || '');
                  setIsEditing(false);
                }}
                className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
                title="Cancel editing"
              >
                <XMarkIcon className="w-4 h-4" />
              </button>
            </>
          ) : (
            <>
              <button
                onClick={() => setIsEditing(true)}
                className="p-1 text-gray-400 hover:text-purple-400 transition-colors"
                title="Edit test case"
              >
                <PencilIcon className="w-4 h-4" />
              </button>
              <button
                onClick={onDelete}
                className="p-1 text-gray-400 hover:text-red-400 transition-colors"
                title="Delete test case"
              >
                <TrashIcon className="w-4 h-4" />
              </button>
            </>
          )}
        </div>
      </td>
    </tr>
  );
}

export function TestCaseTable({ 
  testCases, 
  onEdit, 
  onDelete,
  onBulkAction,
  onAddTestCase,
  onImportCSV,
  onExportCSV
}: TestCaseTableProps) {
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newTestCase, setNewTestCase] = useState<Partial<TestCase>>({
    task: '',
    expected_output: '',
    evaluation_guideline: ''
  });
  
  const handleSelectAll = (checked: boolean) => {
    setSelectedIds(checked ? testCases.map(tc => tc.id) : []);
  };
  
  const handleSelectOne = (id: string, selected: boolean) => {
    setSelectedIds(prev => 
      selected 
        ? [...prev, id]
        : prev.filter(selectedId => selectedId !== id)
    );
  };
  
  return (
    <div className="relative">
      {/* Toolbar */}
      <div className="flex justify-between items-center mb-4">
        <div className="flex gap-2">
          <Button 
            size="sm" 
            variant="secondary"
            disabled={selectedIds.length === 0}
            onClick={() => {
              onBulkAction('delete', selectedIds);
              setSelectedIds([]);
            }}
          >
            Delete Selected ({selectedIds.length})
          </Button>
        </div>
        <div className="flex gap-2">
          {onAddTestCase && (
            <Button 
              size="sm" 
              variant="primary"
              onClick={() => setShowAddForm(true)}
            >
              <PlusIcon className="w-4 h-4 mr-1" />
              Add Test Case
            </Button>
          )}
          {onImportCSV && (
            <Button 
              size="sm" 
              variant="secondary"
              onClick={() => {
                const input = document.createElement('input');
                input.type = 'file';
                input.accept = '.csv';
                input.onchange = (e) => {
                  const file = (e.target as HTMLInputElement).files?.[0];
                  if (file) onImportCSV(file);
                };
                input.click();
              }}
            >
              <UploadIcon className="w-4 h-4 mr-1" />
              Import CSV
            </Button>
          )}
        </div>
      </div>
      
      {/* Add Test Case Form */}
      {showAddForm && onAddTestCase && (
        <div className="mb-4 p-4 bg-gray-50 dark:bg-purple-900/10 rounded-lg border border-gray-200 dark:border-purple-900/20">
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Add New Test Case</h3>
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                Task
              </label>
              <input
                type="text"
                value={newTestCase.task || ''}
                onChange={(e) => setNewTestCase({ ...newTestCase, task: e.target.value })}
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-purple-400/30 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:border-purple-400 dark:focus:border-purple-400 focus:outline-none focus:ring-1 focus:ring-purple-400"
                placeholder="What should the agent do?"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                Expected Output
              </label>
              <textarea
                value={newTestCase.expected_output || ''}
                onChange={(e) => setNewTestCase({ ...newTestCase, expected_output: e.target.value })}
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-purple-400/30 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:border-purple-400 dark:focus:border-purple-400 focus:outline-none focus:ring-1 focus:ring-purple-400"
                rows={2}
                placeholder="What output do you expect?"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                Evaluation Guideline
              </label>
              <textarea
                value={newTestCase.evaluation_guideline || ''}
                onChange={(e) => setNewTestCase({ ...newTestCase, evaluation_guideline: e.target.value })}
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-purple-400/30 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:border-purple-400 dark:focus:border-purple-400 focus:outline-none focus:ring-1 focus:ring-purple-400"
                rows={2}
                placeholder="How should the output be evaluated?"
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button
                size="sm"
                variant="tertiary"
                onClick={() => {
                  setShowAddForm(false);
                  setNewTestCase({ task: '', expected_output: '', evaluation_guideline: '' });
                }}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                variant="primary"
                onClick={() => {
                  if (newTestCase.task && newTestCase.expected_output) {
                    onAddTestCase(newTestCase);
                    setShowAddForm(false);
                    setNewTestCase({ task: '', expected_output: '', evaluation_guideline: '' });
                  }
                }}
                disabled={!newTestCase.task || !newTestCase.expected_output}
              >
                Add Test Case
              </Button>
            </div>
          </div>
        </div>
      )}
      
      {/* Table */}
      <div className="bg-white dark:bg-whitePurple-50/5 backdrop-blur-sm rounded-lg border border-gray-200 dark:border-purple-900/20 overflow-hidden">
        {testCases.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[800px]">
            <thead className="bg-gray-50 dark:bg-purple-900/10 border-b border-gray-200 dark:border-purple-900/20">
              <tr>
                <th className="w-10 px-4 py-3">
                  <input 
                    type="checkbox"
                    checked={selectedIds.length === testCases.length && testCases.length > 0}
                    onChange={(e) => handleSelectAll(e.target.checked)}
                    className="rounded border-gray-300 dark:border-gray-600 text-purple-600 dark:text-purple-400 focus:ring-purple-500 dark:focus:ring-purple-400 accent-purple-600 dark:accent-purple-400"
                  />
                </th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-700 dark:text-gray-300">Task</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-700 dark:text-gray-300">Expected Output</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-700 dark:text-gray-300">Guidelines</th>
                <th className="w-24 px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-purple-900/10">
              {testCases.map((testCase) => (
                <TestCaseRow
                  key={testCase.id}
                  testCase={testCase}
                  selected={selectedIds.includes(testCase.id)}
                  onSelect={(selected) => handleSelectOne(testCase.id, selected)}
                  onEdit={(updates) => onEdit(testCase.id, updates)}
                  onDelete={() => onDelete(testCase.id)}
                />
              ))}
            </tbody>
          </table>
          </div>
        ) : (
          <div className="p-12 text-center">
            <p className="text-gray-400">No test cases yet</p>
            <Button variant="primary" size="sm" className="mt-4">
              <UploadIcon className="w-4 h-4 mr-1" />
              Import Test Cases
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}