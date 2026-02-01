import { useState } from "react";
import { Form, useFetcher } from "@remix-run/react";
import { TrashIcon, PencilIcon, CheckIcon, XMarkIcon } from "@heroicons/react/24/outline";
import { StatusBadge } from "./StatusBadge";
import { ScoreIndicator } from "./ScoreIndicator";
import type { TestCase, TestCaseResult } from "~/services/chicory.server";

interface TestCaseTableProps {
  testCases: TestCase[];
  results?: TestCaseResult[];
  onEdit?: (id: string, updates?: Partial<TestCase>) => void;
  onDelete?: (id: string) => void;
  selectable?: boolean;
}

export function TestCaseTable({
  testCases,
  results = [],
  onEdit,
  onDelete,
  selectable = false
}: TestCaseTableProps) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [searchTerm, setSearchTerm] = useState("");
  const [sortBy, setSortBy] = useState<'task' | 'score' | 'status'>('task');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const fetcher = useFetcher();

  const resultsMap = new Map(results.map(r => [r.test_case_id, r]));

  const filteredTestCases = testCases.filter(tc =>
    tc.task.toLowerCase().includes(searchTerm.toLowerCase()) ||
    tc.expected_output.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const sortedTestCases = [...filteredTestCases].sort((a, b) => {
    let comparison = 0;
    
    switch (sortBy) {
      case 'task':
        comparison = a.task.localeCompare(b.task);
        break;
      case 'score':
        const scoreA = resultsMap.get(a.id)?.score || 0;
        const scoreB = resultsMap.get(b.id)?.score || 0;
        comparison = scoreA - scoreB;
        break;
      case 'status':
        const statusA = resultsMap.get(a.id)?.passed ? 1 : 0;
        const statusB = resultsMap.get(b.id)?.passed ? 1 : 0;
        comparison = statusA - statusB;
        break;
    }
    
    return sortOrder === 'asc' ? comparison : -comparison;
  });

  const handleSelectAll = () => {
    if (selectedIds.size === sortedTestCases.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(sortedTestCases.map(tc => tc.id)));
    }
  };

  const handleSelect = (id: string) => {
    const newSelected = new Set(selectedIds);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedIds(newSelected);
  };

  const handleSort = (column: 'task' | 'score' | 'status') => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('asc');
    }
  };

  const handleBulkDelete = () => {
    if (selectedIds.size === 0) return;
    
    if (confirm(`Are you sure you want to delete ${selectedIds.size} test case(s)?`)) {
      fetcher.submit(
        { 
          intent: "bulk_delete", 
          test_case_ids: Array.from(selectedIds).join(',')
        },
        { method: "post" }
      );
      setSelectedIds(new Set());
    }
  };

  return (
    <div className="w-full">
      {/* Search and Actions Bar */}
      <div className="mb-4 flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div className="flex-1 max-w-md">
          <input
            type="text"
            placeholder="Search test cases..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500 focus:border-transparent"
          />
        </div>
        
        {selectable && selectedIds.size > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {selectedIds.size} selected
            </span>
            <button
              onClick={handleBulkDelete}
              className="px-3 py-1.5 bg-red-500 hover:bg-red-600 text-white rounded-lg text-sm font-medium transition-colors"
            >
              Delete Selected
            </button>
          </div>
        )}
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-200 dark:border-gray-700">
              {selectable && (
                <th className="text-left p-3">
                  <input
                    type="checkbox"
                    checked={selectedIds.size === sortedTestCases.length && sortedTestCases.length > 0}
                    onChange={handleSelectAll}
                    className="rounded border-gray-300 dark:border-gray-600 text-purple-600 dark:text-purple-400 focus:ring-purple-500 dark:focus:ring-purple-400 bg-white dark:bg-gray-800 accent-purple-600 dark:accent-purple-400"
                  />
                </th>
              )}
              <th 
                className="text-left p-3 font-medium text-gray-700 dark:text-gray-300 cursor-pointer hover:text-purple-600 dark:hover:text-purple-400"
                onClick={() => handleSort('task')}
              >
                <div className="flex items-center gap-1">
                  Task
                  {sortBy === 'task' && (
                    <span className="text-xs">{sortOrder === 'asc' ? '↑' : '↓'}</span>
                  )}
                </div>
              </th>
              <th className="text-left p-3 font-medium text-gray-700 dark:text-gray-300">
                Expected Output
              </th>
              {results.length > 0 && (
                <>
                  <th 
                    className="text-left p-3 font-medium text-gray-700 dark:text-gray-300 cursor-pointer hover:text-purple-600 dark:hover:text-purple-400"
                    onClick={() => handleSort('status')}
                  >
                    <div className="flex items-center gap-1">
                      Status
                      {sortBy === 'status' && (
                        <span className="text-xs">{sortOrder === 'asc' ? '↑' : '↓'}</span>
                      )}
                    </div>
                  </th>
                  <th 
                    className="text-left p-3 font-medium text-gray-700 dark:text-gray-300 cursor-pointer hover:text-purple-600 dark:hover:text-purple-400"
                    onClick={() => handleSort('score')}
                  >
                    <div className="flex items-center gap-1">
                      Score
                      {sortBy === 'score' && (
                        <span className="text-xs">{sortOrder === 'asc' ? '↑' : '↓'}</span>
                      )}
                    </div>
                  </th>
                  <th className="text-left p-3 font-medium text-gray-700 dark:text-gray-300">
                    Time
                  </th>
                </>
              )}
              <th className="text-right p-3 font-medium text-gray-700 dark:text-gray-300">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedTestCases.map((testCase) => {
              const result = resultsMap.get(testCase.id);
              
              return (
                <tr 
                  key={testCase.id}
                  className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-900/50 transition-colors"
                >
                  {selectable && (
                    <td className="p-3">
                      <input
                        type="checkbox"
                        checked={selectedIds.has(testCase.id)}
                        onChange={() => handleSelect(testCase.id)}
                        className="rounded border-gray-300 dark:border-gray-600 text-purple-600 dark:text-purple-400 focus:ring-purple-500 dark:focus:ring-purple-400 bg-white dark:bg-gray-800 accent-purple-600 dark:accent-purple-400"
                      />
                    </td>
                  )}
                  <td className="p-3">
                    <div className="max-w-xs">
                      <p className="text-sm text-gray-900 dark:text-white font-medium truncate">
                        {testCase.task}
                      </p>
                      {testCase.evaluation_guideline && (
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 truncate">
                          {testCase.evaluation_guideline}
                        </p>
                      )}
                    </div>
                  </td>
                  <td className="p-3">
                    <p className="text-sm text-gray-600 dark:text-gray-400 max-w-xs truncate">
                      {testCase.expected_output}
                    </p>
                  </td>
                  {results.length > 0 && (
                    <>
                      <td className="p-3">
                        {result ? (
                          <div className="flex items-center gap-2">
                            {result.passed ? (
                              <CheckIcon className="h-4 w-4 text-green-500" />
                            ) : (
                              <XMarkIcon className="h-4 w-4 text-red-500" />
                            )}
                            <StatusBadge 
                              status={result.passed ? 'passed' : 'failed'} 
                              size="sm"
                            />
                          </div>
                        ) : (
                          <StatusBadge status="pending" size="sm" />
                        )}
                      </td>
                      <td className="p-3">
                        {result && (
                          <ScoreIndicator
                            score={result.score}
                            variant="numeric"
                            size="sm"
                          />
                        )}
                      </td>
                      <td className="p-3">
                        {result && (
                          <span className="text-sm text-gray-600 dark:text-gray-400">
                            {result.execution_time_ms}ms
                          </span>
                        )}
                      </td>
                    </>
                  )}
                  <td className="p-3">
                    <div className="flex items-center justify-end gap-2">
                      {onEdit && (
                        <button
                          onClick={() => onEdit(testCase.id)}
                          className="p-1.5 text-gray-500 hover:text-purple-600 dark:text-gray-400 dark:hover:text-purple-400 transition-colors"
                        >
                          <PencilIcon className="h-4 w-4" />
                        </button>
                      )}
                      {onDelete && (
                        <button
                          onClick={() => onDelete(testCase.id)}
                          className="p-1.5 text-gray-500 hover:text-red-600 dark:text-gray-400 dark:hover:text-red-400 transition-colors"
                        >
                          <TrashIcon className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        
        {sortedTestCases.length === 0 && (
          <div className="text-center py-12">
            <p className="text-gray-500 dark:text-gray-400">
              {searchTerm ? 'No test cases found matching your search.' : 'No test cases yet.'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}