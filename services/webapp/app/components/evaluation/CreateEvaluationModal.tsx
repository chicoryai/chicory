/**
 * CreateEvaluationModal Component
 * Modal for creating new evaluations with CSV upload
 */

import { useState, FormEvent, useEffect } from 'react';
import { useFetcher } from '@remix-run/react';
import { Modal } from '~/components/ui/Modal';
import { Button } from '~/components/Button';
import { CsvUploader } from './CsvUploader';
import type { ParsedData } from './CsvUploader';

interface CreateEvaluationModalProps {
  isOpen: boolean;
  onClose: () => void;
  agentId: string;
  projectId: string;
}

interface FormErrors {
  name?: string;
  criteria?: string;
  csvFile?: string;
  general?: string;
}

export function CreateEvaluationModal({
  isOpen,
  onClose,
  agentId,
  projectId
}: CreateEvaluationModalProps) {
  const fetcher = useFetcher<{ success?: boolean; error?: string }>();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [criteria, setCriteria] = useState('');
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [csvPreview, setCsvPreview] = useState<ParsedData | null>(null);
  const [errors, setErrors] = useState<FormErrors>({});
  
  const isSubmitting = fetcher.state === 'submitting';
  const isSuccess = fetcher.data?.success;
  
  // Validate form
  const validateForm = (): boolean => {
    const newErrors: FormErrors = {};
    
    if (!name || name.length < 3) {
      newErrors.name = 'Name must be at least 3 characters';
    } else if (name.length > 100) {
      newErrors.name = 'Name must be less than 100 characters';
    }
    
    if (!criteria || criteria.length < 10) {
      newErrors.criteria = 'Evaluation criteria must be at least 10 characters';
    } else if (criteria.length > 1000) {
      newErrors.criteria = 'Evaluation criteria must be less than 1000 characters';
    }
    
    if (!csvFile) {
      newErrors.csvFile = 'Please upload a CSV file with test cases';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };
  
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    
    // Prevent double submission
    if (isSubmitting) {
      console.log('Evaluation creation already in progress');
      return;
    }
    
    if (!validateForm()) {
      return;
    }
    
    const formData = new FormData();
    formData.append('intent', 'create-evaluation');
    formData.append('name', name);
    formData.append('description', description);
    formData.append('criteria', criteria);
    if (csvFile) {
      formData.append('csv_file', csvFile);
    }
    
    console.log('Submitting evaluation creation form for agent:', agentId);
    
    fetcher.submit(formData, {
      method: 'post',
      action: `/projects/${projectId}/agents/${agentId}/evaluations`,
      encType: 'multipart/form-data',
      preventScrollReset: true
    });
  };
  
  const handleFileSelect = (file: File, preview: ParsedData) => {
    setCsvFile(file);
    setCsvPreview(preview);
    setErrors(prev => ({ ...prev, csvFile: undefined }));
  };
  
  const handleFileError = (message: string) => {
    setErrors(prev => ({ ...prev, csvFile: message }));
    setCsvFile(null);
    setCsvPreview(null);
  };
  
  const handleClose = () => {
    // Don't reset if we're still submitting
    if (isSubmitting) return;
    
    // Reset form
    setName('');
    setDescription('');
    setCriteria('');
    setCsvFile(null);
    setCsvPreview(null);
    setErrors({});
    onClose();
  };
  
  // Close modal on success using useEffect to avoid state update issues
  useEffect(() => {
    if (isSuccess) {
      // Small delay to ensure state updates complete
      const timer = setTimeout(() => {
        handleClose();
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [isSuccess]);
  
  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Create Evaluation"
      panelClassName="w-full max-w-2xl"
    >
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Name field */}
        <div>
          <label htmlFor="eval-name" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            Evaluation Name *
          </label>
          <input
            id="eval-name"
            type="text"
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              setErrors(prev => ({ ...prev, name: undefined }));
            }}
            className={`mt-1 block w-full rounded-md shadow-sm px-3 py-2
              ${errors.name 
                ? 'border-red-300 focus:border-red-500 focus:ring-red-500' 
                : 'border-gray-300 dark:border-gray-600 focus:border-purple-500 focus:ring-purple-500'
              }
              bg-whitePurple-50 dark:bg-gray-800 dark:text-white sm:text-sm`}
            placeholder="e.g., Customer Support Evaluation"
            aria-required="true"
            aria-invalid={!!errors.name}
            aria-describedby={errors.name ? 'name-error' : undefined}
          />
          {errors.name && (
            <p id="name-error" className="mt-1 text-sm text-red-600 dark:text-red-400" role="alert">
              {errors.name}
            </p>
          )}
        </div>
        
        {/* Description field */}
        <div>
          <label htmlFor="eval-description" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            Description (Optional)
          </label>
          <textarea
            id="eval-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 shadow-sm px-3 py-2
              focus:border-purple-500 focus:ring-purple-500 bg-whitePurple-50 dark:bg-gray-800 dark:text-white sm:text-sm"
            placeholder="Brief description of this evaluation..."
          />
        </div>
        
        {/* Criteria field */}
        <div>
          <label htmlFor="eval-criteria" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            Evaluation Criteria *
          </label>
          <textarea
            id="eval-criteria"
            value={criteria}
            onChange={(e) => {
              setCriteria(e.target.value);
              setErrors(prev => ({ ...prev, criteria: undefined }));
            }}
            rows={6}
            className={`mt-1 block w-full rounded-md shadow-sm px-3 py-2
              ${errors.criteria 
                ? 'border-red-300 focus:border-red-500 focus:ring-red-500' 
                : 'border-gray-300 dark:border-gray-600 focus:border-purple-500 focus:ring-purple-500'
              }
              bg-whitePurple-50 dark:bg-gray-800 dark:text-white sm:text-sm`}
            placeholder="Describe the criteria for evaluating agent responses..."
            aria-required="true"
            aria-invalid={!!errors.criteria}
            aria-describedby={errors.criteria ? 'criteria-error' : undefined}
          />
          {errors.criteria && (
            <p id="criteria-error" className="mt-1 text-sm text-red-600 dark:text-red-400" role="alert">
              {errors.criteria}
            </p>
          )}
        </div>
        
        {/* CSV Upload */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Test Cases (CSV) *
          </label>
          <CsvUploader
            onFileSelect={handleFileSelect}
            onError={handleFileError}
            required={true}
          />
          {errors.csvFile && (
            <p className="mt-1 text-sm text-red-600 dark:text-red-400" role="alert">
              {errors.csvFile}
            </p>
          )}
          {csvPreview && (
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
              {csvPreview.rows.length} test cases ready to import
            </p>
          )}
        </div>
        
        {/* Error message from server */}
        {fetcher.data?.error && (
          <div className="rounded-md bg-red-50 dark:bg-red-900/20 p-4">
            <p className="text-sm text-red-800 dark:text-red-200">
              {fetcher.data.error}
            </p>
          </div>
        )}
        
        {/* Form actions */}
        <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
          <Button
            type="button"
            variant="secondary"
            onClick={handleClose}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <>
                <span className="animate-spin inline-block mr-2">
                  <svg className="h-4 w-4" viewBox="0 0 24 24">
                    <circle 
                      className="opacity-25" 
                      cx="12" 
                      cy="12" 
                      r="10" 
                      stroke="currentColor" 
                      strokeWidth="4"
                      fill="none"
                    />
                    <path 
                      className="opacity-75" 
                      fill="currentColor" 
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                </span>
                Creating...
              </>
            ) : (
              'Create Evaluation'
            )}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
