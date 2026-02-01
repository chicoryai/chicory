import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { XMarkIcon } from '@heroicons/react/24/outline';

interface OrgMember {
  userId: string;
  email: string;
  firstName?: string;
  lastName?: string;
}

interface AddMembersModalProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string;
  projectName: string;
  currentMembers: string[];
  availableMembers: OrgMember[];
  onSuccess: (updatedMembers: string[]) => void;
}

export function AddMembersModal({
  isOpen,
  onClose,
  projectId,
  projectName,
  currentMembers,
  availableMembers,
  onSuccess
}: AddMembersModalProps) {
  const [selectedMembers, setSelectedMembers] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Initialize selected members with current members when modal opens
  useEffect(() => {
    if (isOpen) {
      setSelectedMembers([...currentMembers]);
      setError(null);
    }
  }, [isOpen, currentMembers]);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);

    // Validate that at least one member is selected
    if (selectedMembers.length === 0) {
      setError('At least one member must be selected');
      setIsSubmitting(false);
      return;
    }

    try {
      const response = await fetch(`/api/projects/${projectId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          members: selectedMembers
        }),
      });

      const result = await response.json();

      if (response.ok && result.success) {
        onSuccess(selectedMembers);
        onClose();
      } else {
        setError(result.error || 'Failed to update project members');
      }
    } catch (error) {
      console.error('Error updating project members:', error);
      setError('Failed to update project members. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setSelectedMembers([...currentMembers]);
    setError(null);
    onClose();
  };

  const toggleMember = (userId: string) => {
    setSelectedMembers(prev => {
      if (prev.includes(userId)) {
        return prev.filter(id => id !== userId);
      } else {
        return [...prev, userId];
      }
    });
  };

  const getMemberDisplayName = (member: OrgMember) => {
    if (member.firstName || member.lastName) {
      return `${member.firstName || ''} ${member.lastName || ''}`.trim();
    }
    return member.email;
  };

  if (!isOpen) return null;

  const addedCount = selectedMembers.filter(id => !currentMembers.includes(id)).length;
  const removedCount = currentMembers.filter(id => !selectedMembers.includes(id)).length;

  const modalContent = (
    <div className="fixed inset-0 z-[9999] overflow-y-auto">
      <div className="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
        <div className="fixed inset-0 bg-black bg-opacity-50 backdrop-blur-sm transition-opacity" onClick={handleClose} />

        <div className="relative transform overflow-hidden rounded-2xl bg-gradient-to-br from-white to-gray-50 dark:from-gray-800 dark:to-gray-900 px-6 pb-6 pt-6 text-left shadow-2xl transition-all sm:my-8 sm:w-full sm:max-w-lg border border-gray-200 dark:border-gray-700">
          <div className="absolute right-0 top-0 hidden pr-6 pt-6 sm:block">
            <button
              type="button"
              className="rounded-full p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:text-gray-300 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-colors"
              onClick={handleClose}
            >
              <span className="sr-only">Close</span>
              <XMarkIcon className="h-5 w-5" aria-hidden="true" />
            </button>
          </div>

          <div className="sm:flex sm:items-start">
            <div className="mt-3 text-center sm:ml-0 sm:mt-0 sm:text-left w-full">
              <h3 className="text-xl font-bold leading-6 text-gray-900 dark:text-white mb-2">
                Manage Project Members
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
                Check to add or uncheck to remove members from <span className="font-semibold">{projectName}</span>
              </p>

              <div className="mt-4">
                <form onSubmit={handleSubmit}>
                  <div className="mb-6">
                    <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                      Project Members *
                    </label>
                    <div className="max-h-96 overflow-y-auto rounded-xl border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700/50">
                      {availableMembers.length === 0 ? (
                        <div className="p-4 text-sm text-gray-500 dark:text-gray-400 text-center">
                          No members available
                        </div>
                      ) : (
                        <div className="divide-y divide-gray-200 dark:divide-gray-600">
                          {availableMembers.map((member) => {
                            const isCurrentlySelected = selectedMembers.includes(member.userId);
                            const wasOriginallySelected = currentMembers.includes(member.userId);
                            const isChanged = isCurrentlySelected !== wasOriginallySelected;

                            return (
                              <label
                                key={member.userId}
                                className={`flex items-center px-4 py-3 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer transition-colors ${
                                  isChanged ? 'bg-blue-50 dark:bg-blue-900/20' : ''
                                }`}
                              >
                                <input
                                  type="checkbox"
                                  checked={isCurrentlySelected}
                                  onChange={() => toggleMember(member.userId)}
                                  className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 dark:border-gray-600 dark:bg-gray-700"
                                />
                                <div className="ml-3 flex-1">
                                  <div className="flex items-center gap-2">
                                    <div className="text-sm font-medium text-gray-900 dark:text-white">
                                      {getMemberDisplayName(member)}
                                    </div>
                                    {isChanged && (
                                      <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300">
                                        {isCurrentlySelected ? 'Adding' : 'Removing'}
                                      </span>
                                    )}
                                  </div>
                                  <div className="text-xs text-gray-500 dark:text-gray-400">
                                    {member.email}
                                  </div>
                                </div>
                              </label>
                            );
                          })}
                        </div>
                      )}
                    </div>
                    <div className="mt-2 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                      <span>{selectedMembers.length} member(s) selected</span>
                      {(addedCount > 0 || removedCount > 0) && (
                        <span className="text-blue-600 dark:text-blue-400">
                          {addedCount > 0 && `+${addedCount}`}
                          {addedCount > 0 && removedCount > 0 && ', '}
                          {removedCount > 0 && `-${removedCount}`}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-4 space-y-3 space-y-reverse sm:space-y-0">
                    <button
                      type="button"
                      onClick={handleClose}
                      disabled={isSubmitting}
                      className="inline-flex justify-center rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-6 py-3 text-sm font-semibold text-gray-700 dark:text-gray-300 shadow-sm hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={isSubmitting || selectedMembers.length === 0}
                      className="inline-flex justify-center rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 px-6 py-3 text-sm font-semibold text-white shadow-lg hover:shadow-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-lg transition-all duration-200 transform hover:scale-[1.02]"
                    >
                      {isSubmitting ? (
                        <>
                          <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          Updating...
                        </>
                      ) : (
                        'Update Members'
                      )}
                    </button>
                  </div>

                  {error && (
                    <div className="mt-4 p-4 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl">
                      <div className="flex items-center">
                        <svg className="h-5 w-5 text-red-400 mr-2" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clipRule="evenodd" />
                        </svg>
                        <p className="text-sm font-medium text-red-700 dark:text-red-300">{error}</p>
                      </div>
                    </div>
                  )}
                </form>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  // Use portal to render at document root to avoid stacking context issues
  return typeof document !== 'undefined' ? createPortal(modalContent, document.body) : null;
}
