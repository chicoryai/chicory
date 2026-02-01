import { useState, useEffect, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { DataSourceCredential } from '~/services/chicory.server';
import { ConnectionNode } from '~/components/RadialHub/ConnectionNode';
import { ConnectionDetailPanel } from '~/components/RadialHub/ConnectionDetailPanel';
import { FilterButton } from '~/components/RadialHub/FilterButton';

// Custom hook for radial layout calculations
function useRadialLayout(itemCount: number, radius = 200) {
  return useMemo(() => {
    if (itemCount === 0) return [];
    
    // For a single item, place it at the top
    if (itemCount === 1) {
      return [{ angle: 0, radian: 0, x: 0, y: -radius }];
    }
    
    return Array.from({ length: itemCount }).map((_, i) => {
      // Start from the top (270 degrees in standard math, which is -90 in CSS rotation)
      // and go clockwise
      const angle = ((i / itemCount) * 360) - 90;
      const radian = (angle * Math.PI) / 180;
      return {
        angle,
        radian,
        x: Math.cos(radian) * radius,
        y: Math.sin(radian) * radius,
      };
    });
  }, [itemCount, radius]);
};

// Group data sources by type
const groupDataSourcesByType = (dataSources: DataSourceCredential[]) => {
  return dataSources.reduce((acc, dataSource) => {
    const type = dataSource.type.includes('_') 
      ? dataSource.type.split('_')[0] 
      : dataSource.type;
    
    if (!acc[type]) {
      acc[type] = [];
    }
    acc[type].push(dataSource);
    return acc;
  }, {} as Record<string, DataSourceCredential[]>);
};

// Get unique categories from data sources
const getUniqueCategories = (dataSources: DataSourceCredential[]) => {
  const categories = dataSources.map(ds => {
    // Extract category from type if available
    if (ds.type.includes('_')) {
      return ds.type.split('_')[0];
    }
    return ds.type;
  });
  
  return Array.from(new Set(categories));
};

interface RadialHubProps {
  dataSources: DataSourceCredential[];
  onEdit: (dataSource: DataSourceCredential) => void;
  onDelete: (dataSource: DataSourceCredential) => void;
}

export function RadialHub({ dataSources, onEdit, onDelete }: RadialHubProps) {
  const [selectedNode, setSelectedNode] = useState<DataSourceCredential | null>(null);
  const [activeFilter, setActiveFilter] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  
  // Filter data sources based on active filter
  const filteredDataSources = activeFilter 
    ? dataSources.filter(ds => {
        const category = ds.type.includes('_') 
          ? ds.type.split('_')[0] 
          : ds.type;
        return category === activeFilter;
      })
    : dataSources;
  
  // Get unique categories for filter buttons
  const categories = getUniqueCategories(dataSources);
  
  // Handle window resize
  const [containerSize, setContainerSize] = useState({ width: 0, height: 0 });
  
  useEffect(() => {
    const updateSize = () => {
      if (containerRef.current) {
        const { width, height } = containerRef.current.getBoundingClientRect();
        setContainerSize({ 
          width, 
          height 
        });
      }
    };
    
    // Initial size
    updateSize();
    
    // Add resize listener
    window.addEventListener('resize', updateSize);
    
    // Cleanup
    return () => window.removeEventListener('resize', updateSize);
  }, []);
  
  // Calculate radius based on container size (responsive)
  const radius = Math.min(
    containerSize.width ? (containerSize.width / 2) * 0.6 : 200,
    containerSize.height ? (containerSize.height / 2) * 0.6 : 200,
    // Default fallback
    200
  );
  
  // Calculate positions for nodes using our custom hook
  const nodePositions = useRadialLayout(filteredDataSources.length, radius);
  
  return (
    <div className="flex flex-col h-full">
      {/* Filter buttons */}
      <div className="flex flex-wrap gap-2 mb-4">
        <FilterButton
          label="All"
          count={dataSources.length}
          isActive={activeFilter === null}
          onClick={() => setActiveFilter(null)}
        />
        {categories.map(category => {
          const count = dataSources.filter(ds => {
            const dsCategory = ds.type.includes('_') 
              ? ds.type.split('_')[0] 
              : ds.type;
            return dsCategory === category;
          }).length;
          
          return (
            <FilterButton
              key={category}
              label={category.charAt(0).toUpperCase() + category.slice(1)}
              count={count}
              isActive={activeFilter === category}
              onClick={() => setActiveFilter(category)}
            />
          );
        })}
      </div>
      
      <div className="flex flex-col lg:flex-row gap-6 h-full">
        {/* Visualization container */}
        <div 
          ref={containerRef} 
          className="relative flex-grow bg-gray-50 dark:bg-gray-800/40 rounded-lg p-4 min-h-[500px] md:min-h-[600px]"
        >
          {/* Center positioning container */}
          <div className="absolute inset-0 flex items-center justify-center">
            {/* Main hub container - this is the center of our radial layout */}
            <div className="relative" style={{ width: radius * 2 + 100, height: radius * 2 + 100 }}>
              {/* Connection lines - using SVG for better rendering */}
              <svg 
                className="absolute top-0 left-0 w-full h-full z-0"
                style={{ overflow: 'visible' }}
              >
                {nodePositions.map((position, index) => {
                  const dataSource = filteredDataSources[index];
                  const isSelected = selectedNode?.id === dataSource.id;
                  
                  return (
                    <motion.line
                      key={`line-${dataSource.id}`}
                      x1="50%"
                      y1="50%"
                      x2={`calc(50% + ${position.x}px)`}
                      y2={`calc(50% + ${position.y}px)`}
                      stroke={isSelected ? '#84cc16' : '#94a3b8'}
                      strokeWidth={isSelected ? 2 : 1}
                      strokeOpacity={isSelected ? 0.8 : 0.3}
                      strokeDasharray={isSelected ? 'none' : '4,4'}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.3 }}
                    />
                  );
                })}
              </svg>
              
              {/* Center hub with count */}
              <motion.div 
                className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-36 w-36 rounded-full bg-gradient-to-br from-lime-300 to-lime-600 flex items-center justify-center shadow-xl z-20"
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: 'spring', stiffness: 300, damping: 25 }}
                whileHover={{ scale: 1.05 }}
              >
                {/* Inner glow effect */}
                <div className="absolute inset-1 rounded-full bg-gradient-to-t from-lime-400/20 to-white/10 blur-sm"></div>
                
                {/* Content */}
                <div className="text-center relative z-10">
                  <h2 className="text-4xl font-bold text-white">{filteredDataSources.length}</h2>
                  <p className="text-white text-sm font-medium tracking-wide">Sources</p>
                </div>
              </motion.div>
              
              {/* Data source nodes */}
              <AnimatePresence>
                {nodePositions.map((position, index) => {
                  const dataSource = filteredDataSources[index];
                  return (
                    <div 
                      key={`node-container-${dataSource.id}`}
                      className="absolute top-1/2 left-1/2 z-10"
                      style={{
                        transform: `translate(-50%, -50%) translate(${position.x}px, ${position.y}px)`,
                      }}
                    >
                      <ConnectionNode
                        dataSource={dataSource}
                        position={position}
                        isSelected={selectedNode?.id === dataSource.id}
                        onClick={() => setSelectedNode(
                          selectedNode?.id === dataSource.id ? null : dataSource
                        )}
                      />
                    </div>
                  );
                })}
              </AnimatePresence>
            </div>
          </div>
        </div>
        
        {/* Detail panel */}
        <div className="w-full lg:w-80 flex-shrink-0">
          <AnimatePresence>
            {selectedNode ? (
              <ConnectionDetailPanel
                dataSource={selectedNode}
                onEdit={() => onEdit(selectedNode)}
                onDelete={() => onDelete(selectedNode)}
                onClose={() => setSelectedNode(null)}
              />
            ) : (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="bg-gray-50 dark:bg-gray-800/40 rounded-lg p-6 h-full"
              >
                <div className="flex flex-col items-center justify-center h-full text-center">
                  <svg 
                    className="w-16 h-16 text-gray-300 dark:text-gray-600 mb-4" 
                    fill="none" 
                    viewBox="0 0 24 24" 
                    stroke="currentColor"
                  >
                    <path 
                      strokeLinecap="round" 
                      strokeLinejoin="round" 
                      strokeWidth={1} 
                      d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" 
                    />
                  </svg>
                  <p className="text-gray-500 dark:text-gray-400">
                    Select a data source to view details
                  </p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
