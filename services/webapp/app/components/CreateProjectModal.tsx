import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from "@remix-run/react";
import { XMarkIcon } from '@heroicons/react/24/outline';
import { Button } from './Button';
import { useProject } from '~/contexts/project-context';

interface OrgMember {
  userId: string;
  email: string;
  firstName?: string;
  lastName?: string;
}

interface CreateProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  organizationId: string;
  redirectOnCreate?: boolean;
  onSuccess?: () => void;
  availableMembers?: OrgMember[];
  currentUserId?: string;
}

export function CreateProjectModal({ isOpen, onClose, organizationId, redirectOnCreate = true, onSuccess, availableMembers = [], currentUserId }: CreateProjectModalProps) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [selectedMembers, setSelectedMembers] = useState<string[]>([]);
  const { addProject } = useProject();
  const navigate = useNavigate();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Auto-select current user when modal opens
  useEffect(() => {
    if (isOpen && currentUserId && !selectedMembers.includes(currentUserId)) {
      setSelectedMembers([currentUserId]);
    }
  }, [isOpen, currentUserId]);

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

    const formData = new FormData();
    formData.append('name', name);
    formData.append('description', description);
    formData.append('organizationId', organizationId);
    formData.append('members', JSON.stringify(selectedMembers));
    
    try {
      const response = await fetch('/api/projects', {
        method: 'POST',
        body: formData,
      });
      
      const result = await response.json();
      
      if (result.success && result.project) {
        addProject(result.project);
        setName('');
        setDescription('');
        onClose();
        onSuccess?.();
        if (redirectOnCreate) {
          navigate(`/projects/${result.project.id}/agents`);
        }
      } else {
        setError(result.error || 'Failed to create project');
      }
    } catch (error) {
      console.error('Error creating project:', error);
      setError('Failed to create project. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setName('');
    setDescription('');
    setSelectedMembers([]);
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
                Create New Project
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
                Set up a new project to organize your data sources, agents, and workflows.
              </p>
              <div className="mt-4">
                <form onSubmit={handleSubmit}>

                  
                  <div className="mb-6">
                    <label htmlFor="name" className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                      Project Name *
                    </label>
                    <input
                      type="text"
                      id="name"
                      name="name"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      required
                      className="block w-full rounded-xl border-0 py-3 px-4 text-gray-900 dark:text-white shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-gray-600 placeholder:text-gray-500 focus:ring-2 focus:ring-inset focus:ring-indigo-500 dark:focus:ring-indigo-400 sm:text-sm sm:leading-6 dark:bg-gray-700 bg-gray-50 dark:bg-gray-700/50 transition-all duration-200 hover:bg-white dark:hover:bg-gray-700"
                      placeholder="Enter a descriptive project name"
                    />
                  </div>
                  
                  <div className="mb-6">
                    <label htmlFor="description" className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                      Description (optional)
                    </label>
                    <textarea
                      id="description"
                      name="description"
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      rows={4}
                      className="block w-full rounded-xl border-0 py-3 px-4 text-gray-900 dark:text-white shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-gray-600 placeholder:text-gray-500 focus:ring-2 focus:ring-inset focus:ring-indigo-500 dark:focus:ring-indigo-400 sm:text-sm sm:leading-6 dark:bg-gray-700 bg-gray-50 dark:bg-gray-700/50 transition-all duration-200 hover:bg-white dark:hover:bg-gray-700 resize-none"
                      placeholder="Describe what this project will be used for..."
                    />
                  </div>

                  <div className="mb-8">
                    <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                      Project Members *
                    </label>
                    <div className="max-h-48 overflow-y-auto rounded-xl border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700/50">
                      {availableMembers.length === 0 ? (
                        <div className="p-4 text-sm text-gray-500 dark:text-gray-400 text-center">
                          No members available
                        </div>
                      ) : (
                        <div className="divide-y divide-gray-200 dark:divide-gray-600">
                          {availableMembers.map((member) => (
                            <label
                              key={member.userId}
                              className="flex items-center px-4 py-3 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer transition-colors"
                            >
                              <input
                                type="checkbox"
                                checked={selectedMembers.includes(member.userId)}
                                onChange={() => toggleMember(member.userId)}
                                className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 dark:border-gray-600 dark:bg-gray-700"
                              />
                              <div className="ml-3 flex-1">
                                <div className="text-sm font-medium text-gray-900 dark:text-white">
                                  {getMemberDisplayName(member)}
                                </div>
                                <div className="text-xs text-gray-500 dark:text-gray-400">
                                  {member.email}
                                </div>
                              </div>
                            </label>
                          ))}
                        </div>
                      )}
                    </div>
                    <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                      Select at least one member for this project. {selectedMembers.length} member(s) selected.
                    </p>
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
                      disabled={isSubmitting || !name.trim()}
                      className="inline-flex justify-center rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 px-6 py-3 text-sm font-semibold text-white shadow-lg hover:shadow-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-lg transition-all duration-200 transform hover:scale-[1.02]"
                    >
                      {isSubmitting ? (
                        <>
                          <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          Creating...
                        </>
                      ) : (
                        'Create Project'
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
