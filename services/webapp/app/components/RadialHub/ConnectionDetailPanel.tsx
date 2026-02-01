import { motion } from 'framer-motion';
import type { DataSourceCredential } from '~/services/chicory.server';
import { 
  XMarkIcon, 
  PencilIcon, 
  TrashIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline';

interface ConnectionDetailPanelProps {
  dataSource: DataSourceCredential;
  onEdit: () => void;
  onDelete: () => void;
  onClose: () => void;
}

export function ConnectionDetailPanel({ 
  dataSource, 
  onEdit, 
  onDelete, 
  onClose 
}: ConnectionDetailPanelProps) {
  // Format date for display
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }).format(date);
  };

  // Calculate time since last access (mock data for now)
  const getLastAccessed = () => {
    // This would come from the API in a real implementation
    return '2 hours ago';
  };

  // Get status details
  const getStatusDetails = () => {
    const status = dataSource.status?.toLowerCase() || 'active';
    
    switch (status) {
      case 'active':
      case 'configured':
        return {
          label: 'Active',
          icon: <CheckCircleIcon className="h-5 w-5 text-green-500" />,
          color: 'text-green-500',
          bgColor: 'bg-green-100 dark:bg-green-900/30',
          percentage: 100,
          progressColor: 'bg-green-500'
        };
      case 'pending':
        return {
          label: 'Pending',
          icon: <ClockIcon className="h-5 w-5 text-yellow-500" />,
          color: 'text-yellow-500',
          bgColor: 'bg-yellow-100 dark:bg-yellow-900/30',
          percentage: 50,
          progressColor: 'bg-yellow-500'
        };
      case 'error':
      case 'failed':
        return {
          label: 'Error',
          icon: <ExclamationCircleIcon className="h-5 w-5 text-red-500" />,
          color: 'text-red-500',
          bgColor: 'bg-red-100 dark:bg-red-900/30',
          percentage: 0,
          progressColor: 'bg-red-500'
        };
      case 'syncing':
        return {
          label: 'Syncing',
          icon: <ArrowPathIcon className="h-5 w-5 text-blue-500 animate-spin-slow" />,
          color: 'text-blue-500',
          bgColor: 'bg-blue-100 dark:bg-blue-900/30',
          percentage: 75,
          progressColor: 'bg-blue-500'
        };
      default:
        return {
          label: 'Unknown',
          icon: <ClockIcon className="h-5 w-5 text-gray-500" />,
          color: 'text-gray-500',
          bgColor: 'bg-gray-100 dark:bg-gray-800',
          percentage: 0,
          progressColor: 'bg-gray-500'
        };
    }
  };

  const statusDetails = getStatusDetails();

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden h-full"
    >
      {/* Header */}
      <div className="flex justify-between items-center p-4 border-b border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white">
          Connection Details
        </h3>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-500 dark:hover:text-gray-300"
          aria-label="Close panel"
        >
          <XMarkIcon className="h-5 w-5" />
        </button>
      </div>

      {/* Content */}
      <div className="p-4">
        {/* Data source info */}
        <div className="flex items-center mb-6">
          <div className="flex-shrink-0 h-14 w-14 flex items-center justify-center rounded-full bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-700 dark:to-gray-800 shadow-md">
            <img
              src={`/icons/${dataSource.type}.svg`}
              alt={dataSource.type}
              className="h-8 w-8 "
              onError={(e) => {
                (e.target as HTMLImageElement).src = "/icons/generic-integration.svg";
              }}
            />
          </div>
          <div className="ml-4">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">
              {dataSource.name}
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Type: {dataSource.type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
            </p>
            <div className="mt-1">
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusDetails.bgColor} ${statusDetails.color.replace('text-', 'text-')}`}>
                {statusDetails.label}
              </span>
            </div>
          </div>
        </div>

        {/* Connection stats */}
        <div className="space-y-5">
          {/* Health status with improved progress bar */}
          <div>
            <div className="flex justify-between items-center mb-2">
              <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">Connection Health</h4>
              <span className={`flex items-center ${statusDetails.color}`}>
                {statusDetails.icon}
                <span className="ml-1 text-xs">{statusDetails.label}</span>
              </span>
            </div>
            <div className="relative h-2 w-full bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <motion.div 
                initial={{ width: 0 }}
                animate={{ width: `${statusDetails.percentage}%` }}
                transition={{ duration: 0.5 }}
                className={`absolute h-full ${statusDetails.progressColor} rounded-full`}
              />
              {statusDetails.percentage > 0 && statusDetails.percentage < 100 && (
                <div className="absolute h-full border-l border-white/30 dark:border-white/10" 
                  style={{ left: `${statusDetails.percentage}%` }} />
              )}
            </div>
          </div>

          {/* Connection details in a grid */}
          <div className="grid grid-cols-2 gap-4">
            {/* Added date */}
            <div className="bg-gray-50 dark:bg-gray-800/60 rounded-md p-3">
              <div className="text-xs uppercase text-gray-500 dark:text-gray-400 mb-1">
                Added
              </div>
              <div className="text-sm font-medium text-gray-900 dark:text-white">
                {formatDate(dataSource.created_at)}
              </div>
            </div>

            {/* Last accessed */}
            <div className="bg-gray-50 dark:bg-gray-800/60 rounded-md p-3">
              <div className="text-xs uppercase text-gray-500 dark:text-gray-400 mb-1">
                Last Accessed
              </div>
              <div className="text-sm font-medium text-gray-900 dark:text-white">
                {getLastAccessed()}
              </div>
            </div>
          </div>

          {/* Configuration details with improved styling */}
          {dataSource.configuration && (
            <div className="bg-gray-50 dark:bg-gray-800/60 rounded-md p-4">
              <div className="text-xs uppercase text-gray-500 dark:text-gray-400 mb-3 font-medium">
                Configuration Details
              </div>
              <div className="text-sm text-gray-900 dark:text-white space-y-2">
                {Object.entries(dataSource.configuration)
                  .filter(([key]) => !key.toLowerCase().includes('password') && !key.toLowerCase().includes('secret') && !key.toLowerCase().includes('token'))
                  .map(([key, value]) => (
                    <div key={key} className="flex justify-between items-center py-1 border-b border-gray-200 dark:border-gray-700 last:border-0">
                      <span className="text-gray-600 dark:text-gray-400 capitalize">{key.replace(/_/g, ' ')}:</span>
                      <span className="font-medium truncate max-w-[180px] text-right">
                        {typeof value === 'string' ? value : JSON.stringify(value)}
                      </span>
                    </div>
                  ))
                }
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="border-t border-gray-200 dark:border-gray-700 p-4 sticky bottom-0 bg-white dark:bg-gray-800">
        <div className="flex space-x-3">
          <button
            onClick={onEdit}
            className="flex-1 inline-flex justify-center items-center px-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lime-500 dark:focus:ring-offset-gray-800 transition-colors"
          >
            <PencilIcon className="h-4 w-4 mr-2" />
            Edit
          </button>
          <button
            onClick={onDelete}
            className="flex-1 inline-flex justify-center items-center px-4 py-2.5 border border-red-300 dark:border-red-700 rounded-md shadow-sm text-sm font-medium text-red-700 dark:text-red-400 bg-white dark:bg-gray-700 hover:bg-red-50 dark:hover:bg-red-900/20 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 dark:focus:ring-offset-gray-800 transition-colors"
          >
            <TrashIcon className="h-4 w-4 mr-2" />
            Delete
          </button>
        </div>
      </div>
    </motion.div>
  );
}
