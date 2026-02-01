import { motion } from 'framer-motion';
import type { DataSourceCredential } from '~/services/chicory.server';
import { CheckCircleIcon } from '@heroicons/react/24/outline';

interface ConnectionNodeProps {
  dataSource: DataSourceCredential;
  position: { angle: number; radian: number; x: number; y: number };
  isSelected: boolean;
  onClick: () => void;
}

export function ConnectionNode({ 
  dataSource, 
  position, 
  isSelected, 
  onClick 
}: ConnectionNodeProps) {
  // Determine status color and animation
  const getStatusStyles = () => {
    const status = dataSource.status?.toLowerCase() || 'active';
    
    switch (status) {
      case 'active':
      case 'configured':
        return {
          bgColor: 'bg-green-500',
          animation: 'animate-pulse-slow',
          ringColor: 'ring-green-400'  
        };
      case 'pending':
        return {
          bgColor: 'bg-yellow-500',
          animation: '',
          ringColor: 'ring-yellow-400'
        };
      case 'syncing':
        return {
          bgColor: 'bg-blue-500',
          animation: 'animate-pulse-fast',
          ringColor: 'ring-blue-400'
        };
      case 'error':
      case 'failed':
        return {
          bgColor: 'bg-red-500',
          animation: '',
          ringColor: 'ring-red-400'
        };
      default:
        return {
          bgColor: 'bg-gray-500',
          animation: '',
          ringColor: 'ring-gray-400'
        };
    }
  };
  
  // Get node type abbreviation (for display)
  const getNodeTypeAbbreviation = () => {
    const type = dataSource.type;
    
    // Handle special cases
    if (type === 'csv_upload') return 'CSV';
    if (type === 'generic_file_upload') return 'FILE';
    if (type === 'database') return 'DB';
    if (type === 'sql') return 'SQL';
    if (type === 'mongodb') return 'MDB';
    
    // Default: take first two letters and capitalize
    return type.substring(0, 2).toUpperCase();
  };
  
  const statusStyles = getStatusStyles();
  
  const nodeSize = 60; // Size in pixels
  
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0 }}
      animate={{ 
        opacity: 1, 
        scale: 1
      }}
      exit={{ opacity: 0, scale: 0 }}
      transition={{ type: 'spring', stiffness: 300, damping: 25 }}
      className={`w-[60px] h-[60px] rounded-full cursor-pointer
        ${isSelected 
          ? `ring-3 ${statusStyles.ringColor} shadow-node-selected` 
          : `hover:ring-2 hover:${statusStyles.ringColor} hover:shadow-node`
        }
        bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-700 dark:to-gray-800
        flex items-center justify-center
        transition-all duration-300 hover:scale-110
      `}
      onClick={onClick}
      role="button"
      tabIndex={0}
      aria-label={`${dataSource.name} data source`}
      aria-pressed={isSelected}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          onClick();
          e.preventDefault();
        }
      }}
    >
      {/* Status indicator */}
      <div 
        className={`absolute -top-1 -right-1 w-4 h-4 rounded-full ${statusStyles.bgColor} ${statusStyles.animation}
          border border-white dark:border-gray-800 z-10`}
        aria-hidden="true"
      />
      
      {/* Icon or abbreviation */}
      <div className="flex items-center justify-center">
        <img
          src={`/icons/${dataSource.type}.svg`}
          alt={dataSource.type}
          className="h-8 w-8"
          onError={(e) => {
            // If image fails to load, show the abbreviation instead
            const target = e.target as HTMLImageElement;
            target.style.display = 'none';
            
            // Get the next element sibling and show it
            const sibling = target.nextElementSibling as HTMLElement;
            if (sibling) {
              sibling.style.display = 'flex';
            }
          }}
        />
        <div 
          className="text-lg font-bold text-gray-700 dark:text-gray-200 hidden"
          aria-hidden="true"
        >
          {getNodeTypeAbbreviation()}
        </div>
      </div>
      
      {/* Node label (only shown when selected) */}
      {isSelected && (
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 10 }}
          className="absolute -bottom-8 left-1/2 transform -translate-x-1/2 whitespace-nowrap bg-gray-800/80 text-white text-xs px-2 py-1 rounded-md"
        >
          {dataSource.name}
        </motion.div>
      )}
    </motion.div>
  );
}
