import React, { Fragment, useMemo } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import AuditTrailItem from './AuditTrailItem';
import type { TrailItem, ToolResultBlock, UserMessageData } from '~/types/auditTrail';
import { extractToolResultBlocks, parseStructuredData, shouldDisplayTrailItem } from '~/types/auditTrail';

interface AuditTrailModalProps {
  isOpen: boolean;
  onClose: () => void;
  agentTrail: TrailItem[];
  taskId: string;
  isLoading?: boolean;
  error?: string | null;
}

const AuditTrailModal: React.FC<AuditTrailModalProps> = ({ 
  isOpen, 
  onClose, 
  agentTrail,
  isLoading = false,
  error = null
}) => {
  const visibleTrail = useMemo(
    () => agentTrail.filter(item => shouldDisplayTrailItem(item)),
    [agentTrail]
  );

  // Build a map of tool results by tool_use_id for linking
  const toolResultsMap = useMemo(() => {
    const map = new Map<string, ToolResultBlock>();
    
    agentTrail.forEach(item => {
      if (item.message_type === 'UserMessage') {
        const parsed = parseStructuredData(item.structured_data);
        if (parsed && typeof parsed === 'object' && (parsed as any).type === 'UserMessage') {
          const results = extractToolResultBlocks(parsed as UserMessageData);
          results.forEach(result => {
            if (result.tool_use_id) {
              map.set(result.tool_use_id, result);
            }
          });
        }
      }
    });
    
    return map;
  }, [agentTrail]);

  return (
    <Transition.Root show={isOpen} as={Fragment}>
      <Dialog as="div" className="fixed z-50 inset-0 overflow-y-auto" onClose={onClose}>
        <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
          <Transition.Child
            as={Fragment}
            enter="ease-out duration-300"
            enterFrom="opacity-0"
            enterTo="opacity-100"
            leave="ease-in duration-200"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <div className="fixed inset-0 transition-opacity" aria-hidden="true">
              <div className="absolute inset-0 bg-gray-500 dark:bg-gray-900 opacity-75"></div>
            </div>
          </Transition.Child>

          {/* This element is to trick the browser into centering the modal contents. */}
          <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">
            &#8203;
          </span>
          
          <Transition.Child
            as={Fragment}
            enter="ease-out duration-300"
            enterFrom="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
            enterTo="opacity-100 translate-y-0 sm:scale-100"
            leave="ease-in duration-200"
            leaveFrom="opacity-100 translate-y-0 sm:scale-100"
            leaveTo="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
          >
            <div className="inline-block align-bottom bg-white dark:bg-gray-800 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-4xl sm:w-full">
              {/* Header */}
              <div className="bg-gray-50 dark:bg-gray-900 px-6 py-4 border-b border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                    <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                      Execution Trail
                    </h3>
                  </div>
                  <button
                    onClick={onClose}
                    className="text-gray-400 hover:text-gray-500 dark:hover:text-gray-300"
                  >
                    <XMarkIcon className="h-6 w-6" />
                  </button>
                </div>
              </div>

              {/* Body - Scrollable trail list */}
              <div className="audit-trail-scroll px-6 py-4 max-h-[70vh]">
                {isLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <div className="flex items-center space-x-2 text-gray-500 dark:text-gray-400">
                      <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-purple-500"></div>
                      <span>Loading audit trail...</span>
                    </div>
                  </div>
                ) : error ? (
                  <div className="flex items-center justify-center py-8">
                    <div className={`${error.includes('not yet available') ? 'text-yellow-500 dark:text-yellow-400' : 'text-red-500 dark:text-red-400'} text-center`}>
                      <div className="mb-2">
                        {error.includes('not yet available') ? '⏳' : '⚠️'}
                      </div>
                      <div>{error}</div>
                      {error.includes('not yet available') && (
                        <div className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                          The audit trail is uploaded after task completion.
                          <br />
                          Check back once the task has finished.
                        </div>
                      )}
                    </div>
                  </div>
                ) : visibleTrail.length === 0 ? (
                  <div className="flex items-center justify-center py-8">
                    <div className="text-gray-500 dark:text-gray-400">
                      No audit trail data available
                    </div>
                  </div>
                ) : (
                  <div className="space-y-0">
                    {visibleTrail.map((item, index) => (
                      <AuditTrailItem
                        key={`${item.id}-${item.message_id}`}
                        item={item}
                        toolResults={toolResultsMap}
                      />
                    ))}
                  </div>
                )}
              </div>

              <div className="bg-gray-50 dark:bg-gray-900 px-6 py-3 border-t border-gray-200 dark:border-gray-700 flex justify-end">
                <button
                  onClick={onClose}
                  className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 dark:focus:ring-offset-gray-800"
                >
                  Close
                </button>
              </div>
            </div>
          </Transition.Child>
        </div>
      </Dialog>
    </Transition.Root>
  );
};

export default AuditTrailModal;
