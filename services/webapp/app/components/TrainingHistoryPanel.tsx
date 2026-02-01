import { Disclosure } from "@headlessui/react";
import { motion, AnimatePresence } from "framer-motion";
import { useState, useEffect } from "react";
import { 
  ChevronUpIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon,
  ClockIcon,
  ExclamationCircleIcon
} from '@heroicons/react/24/outline';
import type { TrainingJob } from "~/services/chicory.server";

interface TrainingHistoryPanelProps {
  trainingJobs: TrainingJob[];
  formatDate: (dateString: string) => string;
  calculateDuration: (startDate: string, endDate?: string) => string;
}

export default function TrainingHistoryPanel({
  trainingJobs,
  formatDate,
  calculateDuration
}: TrainingHistoryPanelProps) {
  // Sort training jobs by created_at in descending order (newest first)
  const sortedJobs = [...trainingJobs].sort((a, b) => {
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });
  
  return (
    <Disclosure as="div" className="mt-8" defaultOpen={true}>
      {({ open }) => (
        <>
          <Disclosure.Button className="flex w-full justify-between items-center px-4 py-3 text-sm font-medium text-left text-gray-900 dark:text-white rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 focus:outline-none focus-visible:ring focus-visible:ring-lime-500 focus-visible:ring-opacity-75">
            <span>Training History</span>
            <ChevronUpIcon
              className={`${
                open ? 'transform rotate-180' : ''
              } w-5 h-5 text-gray-500`}
            />
          </Disclosure.Button>
          <AnimatePresence>
            {open && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3 }}
                className="px-1 pt-5 pb-2"
              >
                {sortedJobs.length > 0 ? (
                  <div className="space-y-4 max-h-96 overflow-y-auto pr-1">
                    {sortedJobs.map((job: TrainingJob) => (
                      <div 
                        key={job.id} 
                        className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-600"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex items-start">
                            <div className="flex-shrink-0 mt-0.5">
                              {job.status === "completed" && <CheckCircleIcon className="h-5 w-5 text-green-500" />}
                              {job.status === "failed" && <XCircleIcon className="h-5 w-5 text-red-500" />}
                              {job.status === "in_progress" && <ArrowPathIcon className="h-5 w-5 text-blue-500 animate-spin" />}
                              {job.status === "pending" && <ClockIcon className="h-5 w-5 text-gray-500" />}
                            </div>
                            <div className="ml-3">
                              <p className="text-sm font-medium text-gray-900 dark:text-white">
                                {job.model_name || "Default Model"} Training
                              </p>
                              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                                {formatDate(job.created_at)}
                              </p>
                            </div>
                          </div>
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                            ${job.status === "completed" ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200" : ""}
                            ${job.status === "failed" ? "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200" : ""}
                            ${job.status === "in_progress" ? "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200" : ""}
                            ${job.status === "pending" ? "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300" : ""}
                          `}>
                            {job.status === "in_progress" ? "In Progress" : 
                             job.status === "completed" ? "Completed" :
                             job.status === "failed" ? "Failed" : "Pending"}
                          </span>
                        </div>
                        
                        {/* Show error message if failed */}
                        {job.status === "failed" && job.error_message && (
                          <div className="mt-3 text-xs text-red-500 dark:text-red-400 bg-red-50 dark:bg-red-900/30 p-3 rounded">
                            <ExclamationCircleIcon className="inline-block h-3 w-3 mr-1" />
                            {job.error_message}
                          </div>
                        )}
                        
                        {/* Show duration if completed */}
                        {job.status === "completed" && job.completed_at && (
                          <div className="mt-3 text-xs text-gray-500 dark:text-gray-400">
                            Duration: {calculateDuration(job.created_at, job.completed_at)}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-900 rounded-xl p-8 text-center mt-3 border border-gray-200 dark:border-gray-700">
                    {/* Icon */}
                    <div className="flex justify-center mb-4">
                      <div className="bg-white dark:bg-gray-800 rounded-full p-3 shadow-md">
                        <ClockIcon className="h-8 w-8 text-gray-400 dark:text-gray-500" />
                      </div>
                    </div>
                    
                    {/* Text */}
                    <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                      No Training History
                    </h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-4 max-w-sm mx-auto">
                      Once you start training your model, you'll see the training progress and history here.
                    </p>
                    
                    {/* Decorative elements */}
                    <div className="flex justify-center space-x-2 opacity-40">
                      <div className="w-2 h-2 bg-gray-300 dark:bg-gray-600 rounded-full"></div>
                      <div className="w-2 h-2 bg-gray-300 dark:bg-gray-600 rounded-full"></div>
                      <div className="w-2 h-2 bg-gray-300 dark:bg-gray-600 rounded-full"></div>
                    </div>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </>
      )}
    </Disclosure>
  );
}
