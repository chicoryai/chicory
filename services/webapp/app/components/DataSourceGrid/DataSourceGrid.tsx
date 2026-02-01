import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { PencilIcon, TrashIcon, CheckCircleIcon } from '@heroicons/react/24/outline';
import { Tab } from '@headlessui/react';

// Import the DataSourceCredential type from chicory.server
import type { DataSourceCredential } from '~/services/chicory.server';

// Import the ConnectionDetailPanel component
import { ConnectionDetailPanel } from '../RadialHub/ConnectionDetailPanel';

interface DataSourceGridProps {
  dataSources: DataSourceCredential[];
  onEdit: (dataSource: DataSourceCredential) => void;
  onDelete: (dataSource: DataSourceCredential) => void;
}

const DataSourceGrid: React.FC<DataSourceGridProps> = ({ 
  dataSources, 
  onEdit, 
  onDelete 
}) => {
  const [selectedNode, setSelectedNode] = useState<DataSourceCredential | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  
  console.log(dataSources);
  // Group data sources by category
  const categories = useMemo(() => {
    const categoryMap: Record<string, DataSourceCredential[]> = { 'all': [] };
    
    dataSources.forEach(dataSource => {
      // Add to 'all' category
      categoryMap['all'].push(dataSource);
      
      // Add to specific category based on type
      // Extract category from type or use default
      let category = 'other';
      if (dataSource.type.includes('document')) {
        category = 'document';
      } else if (dataSource.type.includes('code')) {
        category = 'code';
      } else if (dataSource.type.includes('database') || dataSource.type.includes('sql')) {
        category = 'database';
      } else if (dataSource.type.includes('chat') || dataSource.type.includes('slack')) {
        category = 'chat';
      } else if (dataSource.type.includes("generic_file_upload")) {
        category = 'files';
      }
      
      if (!categoryMap[category]) {
        categoryMap[category] = [];
      }
      categoryMap[category].push(dataSource);
    });
    
    return categoryMap;
  }, [dataSources]);
  
  // Get filtered data sources based on selected category
  const filteredDataSources = useMemo(() => {
    return categories[selectedCategory] || [];
  }, [categories, selectedCategory]);

  // Determine status color and animation
  const getStatusStyles = (dataSource: DataSourceCredential) => {
    const status = dataSource.status?.toLowerCase() || 'active';
    
    switch (status) {
      case 'active':
      case 'configured':
        return {
          statusColor: 'bg-green-500',
          animation: 'animate-pulse-slow',
          ringColor: 'ring-green-400'  
        };
      case 'pending':
        return {
          statusColor: 'bg-yellow-500',
          animation: '',
          ringColor: 'ring-yellow-400'
        };
      case 'syncing':
        return {
          statusColor: 'bg-blue-500',
          animation: 'animate-pulse-fast',
          ringColor: 'ring-blue-400'
        };
      case 'error':
      case 'failed':
        return {
          statusColor: 'bg-red-500',
          animation: '',
          ringColor: 'ring-red-400'
        };
      default:
        return {
          statusColor: 'bg-gray-500',
          animation: '',
          ringColor: 'ring-gray-400'
        };
    }
  };
  
  // Get node type abbreviation (for display)
  const getNodeTypeAbbreviation = (type: string) => {
    // Handle special cases
    if (type === 'csv_upload') return 'CSV';
    if (type === 'generic_file_upload') return 'FILE';
    if (type === 'database') return 'DB';
    if (type === 'sql') return 'SQL';
    if (type === 'mongodb') return 'MDB';
    
    // Default: take first two letters and capitalize
    return type.substring(0, 2).toUpperCase();
  };

  // Get category names for tabs
  const categoryNames = useMemo(() => {
    return Object.keys(categories).map(category => {
      // Format category name
      if (category === 'all') return 'All';
      return category.charAt(0).toUpperCase() + category.slice(1);
    });
  }, [categories]);
  
  return (
    <div className="relative">
      {/* Category tabs styled as pill buttons - only shown when no node is selected */}
      {!selectedNode && (
        <Tab.Group onChange={(index) => setSelectedCategory(Object.keys(categories)[index])}>
          <Tab.List className="flex flex-wrap gap-2 mb-8">
            {Object.keys(categories).map((category, index) => (
              <Tab
                key={category}
                className={({ selected }) =>
                  `px-4 py-2 rounded-full text-sm font-medium transition-all 
                  ${selected
                    ? 'bg-lime-500 text-white shadow-md'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                  }`
                }
              >
                {categoryNames[index]} ({categories[category].length})
              </Tab>
            ))}
          </Tab.List>
        </Tab.Group>
      )}
      
      {/* Conditional rendering based on selection state */}
      {selectedNode ? (
        /* Connection details panel - replaces grid when a node is selected */
        <AnimatePresence>
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="w-full"
            key="details-panel"
          >
            <ConnectionDetailPanel 
              dataSource={selectedNode}
              onClose={() => setSelectedNode(null)}
              onEdit={() => onEdit(selectedNode)}
              onDelete={() => onDelete(selectedNode)}
            />
          </motion.div>
        </AnimatePresence>
      ) : (
        /* Grid of data source nodes - shown when no node is selected */
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-6">
          {filteredDataSources.map((dataSource) => {
            const isSelected = selectedNode?.id === dataSource.id;
            const statusStyles = getStatusStyles(dataSource);
            
            return (
              <motion.div
                key={dataSource.id}
                initial={{ opacity: 0, scale: 0 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0 }}
                transition={{ type: 'spring', stiffness: 300, damping: 25 }}
                className="flex flex-col items-center"
              >
                {/* Node */}
                <motion.div
                  className={`w-[60px] h-[60px] rounded-full cursor-pointer relative
                    ${isSelected 
                      ? `ring-3 ${statusStyles.ringColor} shadow-node-selected` 
                      : `hover:ring-2 hover:${statusStyles.ringColor} hover:shadow-node`
                    }
                    bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-700 dark:to-gray-800
                    flex items-center justify-center
                    transition-all duration-300 hover:scale-110
                  `}
                  style={{
                    boxShadow: isSelected ? '0 0 15px rgba(132, 204, 22, 0.5)' : 'none'
                  }}
                  onClick={() => setSelectedNode(dataSource)}
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.95 }}
                  role="button"
                  tabIndex={0}
                  aria-label={`${dataSource.name} data source`}
                  aria-pressed={isSelected}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      setSelectedNode(dataSource);
                      e.preventDefault();
                    }
                  }}
                >
                  {/* Icon and type abbreviation */}
                  <div className="relative w-full h-full flex items-center justify-center">
                    {/* Type abbreviation */}
                    <div className="text-base font-bold text-gray-700 dark:text-gray-200">
                      {getNodeTypeAbbreviation(dataSource.type)}
                    </div>
                    
                    {/* Connection check icon for active connections */}
                    {dataSource.status === 'active' && (
                      <motion.div 
                        className="absolute -bottom-1 -right-1 bg-white dark:bg-gray-800 rounded-full p-0.5"
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ delay: 0.2 }}
                      >
                        <CheckCircleIcon className="w-4 h-4 text-green-500" />
                      </motion.div>
                    )}
                  </div>
                  
                  {/* Status indicator */}
                  <div 
                    className={`absolute -top-1 -right-1 w-4 h-4 rounded-full ${statusStyles.statusColor} ${statusStyles.animation} border-2 border-white dark:border-gray-800`}
                  />
                </motion.div>
                
                {/* Data source name (shown below node) */}
                <span className="mt-2 text-xs text-center text-gray-700 dark:text-gray-300 font-medium">
                  {dataSource.name}
                </span>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default DataSourceGrid;
