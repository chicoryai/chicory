import { ClockIcon, CheckCircleIcon, ExclamationCircleIcon } from "@heroicons/react/24/outline";
import type { TrainingJob } from "~/services/chicory.server";

interface TrainingJobsListProps {
  trainingJobs: TrainingJob[];
}

export function TrainingJobsList({ trainingJobs }: TrainingJobsListProps) {
  // Get status icon based on training job status
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />;
      case 'failed':
        return <ExclamationCircleIcon className="h-5 w-5 text-red-500" />;
      case 'in_progress':
      case 'pending':
      default:
        return <ClockIcon className="h-5 w-5 text-yellow-500" />;
    }
  };

  // Get status text color
  const getStatusTextColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-500';
      case 'failed':
        return 'text-red-500';
      case 'in_progress':
      case 'pending':
      default:
        return 'text-yellow-500';
    }
  };

  if (trainingJobs.length === 0) {
    return (
      <div className="flex items-center justify-center py-10">
        <div className="text-center">
          <div className="flex justify-center mb-5">
            <div className="h-12 w-12 flex items-center justify-center">
              <ClockIcon className="h-7 w-7 text-gray-500" />
            </div>
          </div>
          <p className="text-sm text-gray-400 mb-1">
            No training jobs yet
          </p>
          <p className="text-sm text-gray-400">
            Select data sources and start training to improve responses
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {trainingJobs
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        .map((job) => (
          <div 
            key={job.id} 
            className="bg-gray-800 rounded-lg p-4"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                {getStatusIcon(job.status)}
                <span className="ml-2 text-white font-medium">{job.model_name}</span>
              </div>
              <span className="text-xs text-gray-400">
                {job.created_at}
              </span>
            </div>
            <div className="mt-2">
              <div className="flex items-center">
                <span className="text-xs text-gray-400 mr-2">Status:</span>
                <span className={`text-xs capitalize ${getStatusTextColor(job.status)}`}>
                  {job.status.replace('_', ' ')}
                </span>
              </div>
              {job.completed_at && (
                <div className="flex items-center mt-1">
                  <span className="text-xs text-gray-400 mr-2">Completed:</span>
                  <span className="text-xs text-white">{job.completed_at}</span>
                </div>
              )}
              {job.error_message && (
                <div className="mt-2 p-2 bg-red-900/30 rounded border border-red-800 text-xs text-red-300">
                  {job.error_message}
                </div>
              )}
            </div>
          </div>
        ))}
    </div>
  );
}
