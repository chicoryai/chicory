import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  CheckCircleIcon, 
  XCircleIcon, 
  ArrowPathIcon, 
  ClockIcon,
  BeakerIcon,
  ArrowRightIcon,
  ExclamationCircleIcon
} from '@heroicons/react/24/outline';
import type { TrainingJob } from '~/services/chicory.server';
import { formatLocalDateTime, formatRelativeTime } from '~/utils/date';

interface TrainingJobStatusProps {
  latestJob?: TrainingJob | null;
  onTrain: () => void;
  isTrainingDisabled: boolean;
}

export default function TrainingJobStatus({ 
  latestJob, 
  onTrain,
  isTrainingDisabled 
}: TrainingJobStatusProps) {
  // Format date for display
  const formatDate = (dateString: string) => {
    return formatLocalDateTime(dateString, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZoneName: 'short'
    });
  };
  
  // Format current step text: capitalize first letter and replace underscores with spaces
  const formatCurrentStep = (step: string) => {
    if (!step) return '';
    return step
      .replace(/_/g, ' ') // Replace underscores with spaces
      .replace(/^\w/, (c) => c.toUpperCase()); // Capitalize first letter
  };
  
  // Get status icon based on job status
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon className="h-6 w-6 text-green-500" aria-hidden="true" />;
      case 'failed':
        return <XCircleIcon className="h-6 w-6 text-red-500" aria-hidden="true" />;
      case 'in_progress':
        return (
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
          >
            <ArrowPathIcon className="h-6 w-6 text-blue-500" aria-hidden="true" />
          </motion.div>
        );
      case 'pending':
      default:
        return <ClockIcon className="h-6 w-6 text-gray-500" aria-hidden="true" />;
    }
  };
  
  // Get status color based on job status
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-200 dark:bg-green-900/20 border-green-300 dark:border-green-800';
      case 'failed':
        return 'bg-red-50 dark:bg-red-900/20 border-red-100 dark:border-red-800';
      case 'in_progress':
        return 'bg-blue-50 dark:bg-blue-900/20 border-blue-100 dark:border-blue-800';
      case 'pending':
      default:
        return 'bg-gray-50 dark:bg-gray-800/40 border-gray-100 dark:border-gray-700';
    }
  };
  
  // Calculate progress percentage for in-progress jobs
  const getProgressPercentage = () => {
    if (!latestJob || !latestJob.progress) return 0;
    
    if (latestJob.progress.percent_complete !== undefined) {
      return latestJob.progress.percent_complete;
    }
    
    if (latestJob.progress.steps_completed !== undefined && latestJob.progress.total_steps !== undefined) {
      return Math.round((latestJob.progress.steps_completed / latestJob.progress.total_steps) * 100);
    }
    
    return latestJob.status === 'completed' ? 100 : 0;
  };
  
  // Check if training should be disabled based on the rules
  const shouldDisableTraining = () => {
    // Rule 1: Disabled if there are no connected data sources
    if (isTrainingDisabled) return true;
    
    // If no jobs yet, allow training (this fixes the issue)
    if (!latestJob) return false;
    
    // Rule 2: Disabled if the last run is not in a completed status
    if (latestJob.status !== 'completed' && latestJob.status !== 'failed') return true;
    
    // Rule 3: Disabled if it is within a 12-hour window of the last completed training
    if (latestJob.status === 'completed' && latestJob.updated_at) {
      const completedTime = new Date(latestJob.updated_at).getTime();
      const currentTime = new Date().getTime();
      const hoursSinceCompletion = (currentTime - completedTime) / (1000 * 60 * 60);
      
      // Disable if less than 12 hours have passed (fixed the logic)
      return hoursSinceCompletion < 12;
    }
    
    return false;
  };
  
  // Get a message explaining why training is disabled
  const getTrainingDisabledMessage = () => {
    if (isTrainingDisabled) {
      return "Connect at least one data source to train";
    }
    
    if (!latestJob) return "";
    
    if (latestJob.status !== 'completed') {
      return "Wait for the current training job to complete";
    }
    
    if (latestJob.status === 'completed' && latestJob.updated_at) {
      const completedTime = new Date(latestJob.updated_at).getTime();
      const currentTime = new Date().getTime();
      const hoursSinceCompletion = (currentTime - completedTime) / (1000 * 60 * 60);
      const hoursRemaining = Math.ceil(12 - hoursSinceCompletion);
      
      if (hoursSinceCompletion < 12) {
        return `Training available in ${hoursRemaining} hour${hoursRemaining !== 1 ? 's' : ''}`;
      }
    }
    
    return "";
  };
  
  // Get status text
  const getStatusText = (status: string) => {
    switch (status) {
      case 'completed':
        return 'Scan Completed';
      case 'failed':
        return 'Scan Failed';
      case 'in_progress':
        return 'Scan in Progress';
      case 'pending':
        return 'Scan Pending';
      default:
        return 'No Scan Available';
    }
  };

  return (
    <div className="w-full mb-8">
      <div className={`rounded-lg border ${latestJob ? getStatusColor(latestJob.status) : 'bg-gray-50 dark:bg-gray-800/40 border-gray-100 dark:border-gray-700'} p-6`}>
        <AnimatePresence mode="wait">
          {latestJob ? (
            <motion.div
              key="job-status"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.5 }}
              className="flex flex-col"
            >
              {/* Top section with status and progress bar */}
              <div className="flex items-start justify-between mb-6">
                <div className="flex items-center">
                  <div className="flex-shrink-0 mr-4">
                    {getStatusIcon(latestJob.status)}
                  </div>
                  <div>
                    <h2 className="text-2xl font-bold text-gray-900 dark:text-white tracking-tight">
                      {getStatusText(latestJob.status)}
                    </h2>
                    <p className="mt-1 text-base text-gray-500 dark:text-gray-400">
                      {latestJob.status === 'completed' 
                        ? `Completed on ${formatDate(latestJob.updated_at || latestJob.created_at)}` 
                        : latestJob.status === 'in_progress'
                          ? `Started ${formatRelativeTime(latestJob.created_at)}`
                          : `Last updated ${formatDate(latestJob.updated_at || latestJob.created_at)}`
                      }
                    </p>
                  </div>
                </div>
              </div>
              
              {/* Progress bar */}
              <div className="w-full bg-gray-100 dark:bg-gray-800/40 rounded-full h-2 mb-6">
                <motion.div 
                  className={`h-2 rounded-full ${
                    latestJob.status === 'completed' ? 'bg-green-500' : 
                    latestJob.status === 'failed' ? 'bg-red-500' : 
                    'bg-lime-500'
                  }`}
                  initial={{ width: 0 }}
                  animate={{ width: `${getProgressPercentage()}%` }}
                  transition={{ duration: 1, ease: "easeOut" }}
                />
              </div>
              
              {/* Current step (if in progress) */}
              {latestJob.status === 'in_progress' && latestJob.progress && latestJob.progress.current_step && (
                <div className="mb-6 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-md">
                  <p className="text-sm font-medium text-blue-700 dark:text-blue-300">
                    {formatCurrentStep(latestJob.progress.current_step)}
                  </p>
                </div>
              )}
              
              {/* Error message (if failed) */}
              {latestJob.status === 'failed' && latestJob.error && (
                <div className="mb-6 p-3 bg-red-100 dark:bg-red-900/30 rounded-md text-sm text-red-800 dark:text-red-200">
                  {latestJob.error}
                </div>
              )}
              
              {/* Train button and message */}
              <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
                {/* Progress steps info */}
                {latestJob.progress && latestJob.progress.steps_completed && latestJob.progress.total_steps && (
                  <div className="text-base font-medium text-gray-600 dark:text-gray-400">
                    {latestJob.progress.steps_completed}/{latestJob.progress.total_steps} steps completed
                  </div>
                )}
                
                {/* Train button section */}
                <div className="flex flex-col items-center sm:items-end">
                  <button
                    onClick={onTrain}
                    disabled={shouldDisableTraining()}
                    className="group inline-flex items-center justify-center px-6 py-3 border border-transparent text-base font-semibold rounded-lg shadow-md text-white bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 hover:scale-105 disabled:hover:scale-100"
                  >
                    <BeakerIcon className="w-5 h-5 mr-2 group-hover:animate-pulse" />
                    {latestJob.status === 'failed' ? 'Retry Training' : 'Train Again'}
                    <ArrowRightIcon className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
                  </button>
                  
                  {shouldDisableTraining() && (
                    <div className="mt-3 inline-flex items-center px-3 py-1 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-md">
                      <ClockIcon className="h-4 w-4 text-amber-500 mr-2" />
                      <p className="text-sm text-amber-700 dark:text-amber-300">
                        {getTrainingDisabledMessage()}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="no-job"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.5 }}
              className="flex flex-col"
            >
              {/* Header with Icon */}
              <div className="text-center mb-8">
                <div className="flex justify-center mb-4">
                  <div className="bg-gradient-to-br from-lime-100 to-lime-200 dark:from-lime-900/30 dark:to-lime-800/30 rounded-full p-4 shadow-lg">
                    <BeakerIcon className="h-12 w-12 text-lime-600 dark:text-lime-400" aria-hidden="true" />
                  </div>
                </div>
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white tracking-tight mb-2">
                  Ready to Train
                </h2>
                <p className="text-gray-600 dark:text-gray-400">
                  Start your first training job to create a custom model
                </p>
              </div>

              {/* Steps visualization with enhanced design */}
              <div className="w-full flex flex-col mb-8">
                <div className="flex items-center justify-center space-x-4 md:space-x-6 mb-6">
                  <div className="flex flex-col items-center">
                    <div className="w-12 h-12 rounded-full border-2 border-lime-300 dark:border-lime-600 flex items-center justify-center bg-lime-50 dark:bg-lime-900/20 shadow-sm">
                      <CheckCircleIcon className="h-6 w-6 text-lime-600 dark:text-lime-400" />
                    </div>
                    <span className="text-xs mt-2 text-center font-medium text-lime-600 dark:text-lime-400">Connect</span>
                  </div>
                  <div className="flex-1 h-px bg-gradient-to-r from-lime-300 to-gray-300 dark:from-lime-600 dark:to-gray-600"></div>
                  <div className="flex flex-col items-center">
                    <div className="w-12 h-12 rounded-full border-2 border-lime-300 dark:border-lime-600 flex items-center justify-center bg-lime-50 dark:bg-lime-900/20 shadow-sm">
                      <CheckCircleIcon className="h-6 w-6 text-lime-600 dark:text-lime-400" />
                    </div>
                    <span className="text-xs mt-2 text-center font-medium text-lime-600 dark:text-lime-400">Ingest</span>
                  </div>
                  <div className="flex-1 h-px bg-gradient-to-r from-gray-300 to-purple-300 dark:from-gray-600 dark:to-purple-600"></div>
                  <div className="flex flex-col items-center">
                    <div className="w-12 h-12 rounded-full border-2 border-purple-300 dark:border-purple-600 flex items-center justify-center bg-purple-50 dark:bg-purple-900/20 shadow-sm">
                      <span className="text-sm font-bold text-purple-600 dark:text-purple-400">3</span>
                    </div>
                    <span className="text-xs mt-2 text-center font-medium text-purple-600 dark:text-purple-400">Train</span>
                  </div>
                </div>
                
                <div className="bg-gradient-to-r from-lime-50 to-purple-50 dark:from-lime-900/10 dark:to-purple-900/10 rounded-xl p-4 border border-lime-200 dark:border-lime-800">
                  <p className="text-sm text-gray-700 dark:text-gray-300 text-center">
                    🎯 <strong>Next:</strong> Train your model with connected data sources to improve responses for your specific use case
                  </p>
                </div>
              </div>
              
              {/* Enhanced Start Training Button */}
              <div className="flex justify-center">
                <button
                  onClick={onTrain}
                  disabled={shouldDisableTraining()}
                  className="group inline-flex items-center px-8 py-4 border border-transparent text-lg font-semibold rounded-xl shadow-lg text-white bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 disabled:opacity-50 disabled:cursor-not-allowed transform transition-all duration-200 hover:scale-105 disabled:hover:scale-100"
                >
                  <BeakerIcon className="w-6 h-6 mr-3 group-hover:animate-pulse" />
                  Start Training
                  <ArrowRightIcon className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" />
                </button>
              </div>
              
              {shouldDisableTraining() && (
                <div className="mt-6 text-center">
                  <div className="inline-flex items-center px-4 py-2 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
                    <ExclamationCircleIcon className="h-5 w-5 text-amber-500 mr-2" />
                    <p className="text-sm text-amber-700 dark:text-amber-300">
                      {getTrainingDisabledMessage()}
                    </p>
                  </div>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
