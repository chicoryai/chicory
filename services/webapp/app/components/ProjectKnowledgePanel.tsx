import { BookOpenIcon, PlusIcon, XMarkIcon, ClockIcon, CheckCircleIcon, ExclamationCircleIcon, BeakerIcon } from "@heroicons/react/24/outline";
import { useState, useRef } from "react";
import { useFetcher } from "@remix-run/react";
import type { DataSourceCredential, DataSourceTypeDefinition, DataSourceFieldDefinition, TrainingJob } from "~/services/chicory.server";
import DataSourceModal from "~/components/DataSourceModal";
import DataSourceEditModal from "~/components/DataSourceEditModal";
import CsvUploadModal from "~/components/CsvUploadModal";

interface ProjectKnowledgePanelProps {
  projectId: string;
  dataSources: DataSourceCredential[];
  dataSourceTypes: DataSourceTypeDefinition[];
  trainingJobs: TrainingJob[];
}

export function ProjectKnowledgePanel({ projectId, dataSources, dataSourceTypes, trainingJobs }: ProjectKnowledgePanelProps) {
  const [hoveredSource, setHoveredSource] = useState<string | null>(null);
  const [showDataSourceGrid, setShowDataSourceGrid] = useState(false);
  const [selectedDataSource, setSelectedDataSource] = useState<DataSourceTypeDefinition | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedExistingSource, setSelectedExistingSource] = useState<DataSourceCredential | null>(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isCsvUploadModalOpen, setIsCsvUploadModalOpen] = useState(false);
  const [selectedDataSources, setSelectedDataSources] = useState<string[]>([]);
  const [isTraining, setIsTraining] = useState(false);
  const [isTrainingMode, setIsTrainingMode] = useState(false);
  const fetcher = useFetcher();
  
  // Get the most recent training job
  const latestTrainingJob = trainingJobs.length > 0 
    ? trainingJobs.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0]
    : null;

  // Function to determine icon based on data source type
  const getDataSourceIcon = (dataSource: DataSourceCredential | DataSourceTypeDefinition) => {
    // For DataSourceCredential objects
    if ('type' in dataSource && dataSource.type) {
      const typeId = dataSource.type;
      
      // Check if the icon exists in our public/icons directory
      const knownTypes = [
        "github", 
        "google_docs", 
        "csv_upload", 
        "xlsx_upload", 
        "databricks", 
        "direct_upload"
      ];
      
      // If the type matches a known type, use that icon
      if (knownTypes.includes(typeId)) {
        return `/icons/${typeId}.svg`;
      }
    } 
    // For DataSourceTypeDefinition objects
    else if ('id' in dataSource && dataSource.id) {
      const typeId = dataSource.id;
      
      // Check if the icon exists in our public/icons directory
      const knownTypes = [
        "github", 
        "google_docs", 
        "csv_upload", 
        "xlsx_upload", 
        "databricks", 
        "direct_upload"
      ];
      
      // If the type matches a known type, use that icon
      if (knownTypes.includes(typeId)) {
        return `/icons/${typeId}.svg`;
      }
    }
    
    // Otherwise, use the generic icon
    return "/icons/generic-integration.svg";
  };

  const handleDataSourceClick = (dataSource: DataSourceTypeDefinition) => {
    // Check if this is the CSV upload data source type
    if (dataSource.id === "csv_upload") {
      setIsCsvUploadModalOpen(true);
    } else {
      setSelectedDataSource(dataSource);
      setIsModalOpen(true);
    }
  };

  const handleExistingDataSourceClick = (dataSource: DataSourceCredential) => {
    // Only open edit modal if not in training selection mode
    if (!isTrainingMode) {
      setSelectedExistingSource(dataSource);
      setIsEditModalOpen(true);
    }
  };

  // Find data source type for a given data source
  const findDataSourceType = (dataSource: DataSourceCredential): DataSourceTypeDefinition | undefined => {
    return dataSourceTypes.find(type => type.id === dataSource.type);
  };

  // Prepare data source for modal
  const prepareDataSourceForModal = (dataSource: DataSourceTypeDefinition) => {
    return {
      id: dataSource.id,
      name: dataSource.name,
      requiredFields: dataSource.required_fields
    };
  };

  // Toggle data source selection for training
  const toggleDataSourceSelection = (dataSourceId: string) => {
    setSelectedDataSources(prev => 
      prev.includes(dataSourceId)
        ? prev.filter(id => id !== dataSourceId)
        : [...prev, dataSourceId]
    );
  };

  // Start training with selected data sources
  const startTraining = () => {
    if (selectedDataSources.length === 0) {
      alert("Please select at least one data source for training");
      return;
    }

    setIsTraining(true);
    
    fetcher.submit(
      {
        _action: "createTrainingJob",
        model_name: "default",
        description: "",
        data_source_ids: JSON.stringify(selectedDataSources)
      },
      { method: "post" }
    );
  };

  // Cancel training mode
  const cancelTrainingMode = () => {
    setIsTrainingMode(false);
    setSelectedDataSources([]);
  };

  // Format date for display
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: 'numeric',
      hour12: true
    }).format(date);
  };

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

  // Reset training state when fetcher completes
  if (fetcher.state === "idle" && isTraining) {
    setIsTraining(false);
    setSelectedDataSources([]);
    setIsTrainingMode(false);
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-6 pb-12">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-sm font-medium text-white">Project knowledge</h2>
          <button 
            className="text-purple-400 hover:text-purple-300 p-1 rounded-full hover:bg-gray-800 dark:hover:bg-lime-900 dark:text-lime-400"
            onClick={() => setShowDataSourceGrid(!showDataSourceGrid)}
          >
            {showDataSourceGrid ? (
              <XMarkIcon className="h-5 w-5" />
            ) : (
              <PlusIcon className="h-5 w-5" />
            )}
          </button>
        </div>
        
        {/* Data Source Type Grid - Slides down when add button is clicked */}
        <div 
          className={`transition-all duration-300 ease-in-out overflow-hidden ${
            showDataSourceGrid ? 'max-h-96 opacity-100 mb-6' : 'max-h-0 opacity-0'
          }`}
        >
          <div className="bg-gray-800 rounded-lg p-4 mb-2">
            <h3 className="text-sm font-medium text-white mb-3">Add Knowledge Source</h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
              {dataSourceTypes.map((sourceType) => (
                <button
                  key={sourceType.id}
                  onClick={() => handleDataSourceClick(sourceType)}
                  className="flex flex-col items-center p-3 rounded-lg hover:bg-gray-700 transition-colors cursor-pointer"
                >
                  <img 
                    src={getDataSourceIcon(sourceType)} 
                    alt={sourceType.name}
                    className="w-10 h-10"
                  />
                </button>
              ))}
            </div>
          </div>
        </div>
        
        <div className="mb-6">
          <div className="flex items-center justify-between text-sm text-gray-400 mb-2">
            <span>Set project instructions</span>
            <span className="text-xs bg-gray-800 px-2 py-0.5 rounded">Optional</span>
          </div>
          <textarea 
            className="w-full h-24 p-3 border border-gray-700 rounded-md bg-gray-800 text-white resize-none focus:outline-none focus:ring-1 focus:ring-gray-600"
            placeholder="Add instructions for Chicory..."
          ></textarea>
        </div>
        
        {dataSources.length === 0 ? (
          <div className="flex items-center justify-center py-10 mt-4">
            <div className="text-center">
              <div className="flex justify-center mb-5">
                <div className="h-12 w-12 flex items-center justify-center">
                  <BookOpenIcon className="h-7 w-7 text-gray-500" />
                </div>
              </div>
              <p className="text-sm text-gray-400 mb-1">
                No knowledge added yet. Add PDFs, documents, or
              </p>
              <p className="text-sm text-gray-400">
                other text to the project knowledge base that Claude
              </p>
              <p className="text-sm text-gray-400">
                will reference in every project conversation.
              </p>
            </div>
          </div>
        ) : (
          <div className="mt-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-medium text-white">Connected Knowledge Sources</h3>
              
              {isTrainingMode ? (
                <div className="flex items-center space-x-2">
                  <button
                    onClick={cancelTrainingMode}
                    className="flex items-center text-xs bg-gray-700 hover:bg-gray-600 text-white px-3 py-1 rounded-md"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={startTraining}
                    disabled={isTraining || selectedDataSources.length === 0}
                    className="flex items-center text-xs bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded-md disabled:opacity-50"
                  >
                    {isTraining ? (
                      <>
                        <ClockIcon className="h-3 w-3 mr-1" />
                        Training...
                      </>
                    ) : (
                      <>Train Model</>
                    )}
                  </button>
                </div>
              ) : (
                <div className="flex items-center">
                  {latestTrainingJob && (
                    <div className="relative mr-2 group">
                      <div className="cursor-help">
                        {getStatusIcon(latestTrainingJob.status)}
                      </div>
                      
                      {/* Popover */}
                      <div className="absolute right-full top-1/2 transform -translate-y-1/2 mr-2 bg-gray-800 text-white text-xs py-2 px-3 rounded shadow-lg whitespace-nowrap z-10 opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none">
                        <div className="font-medium mb-1">Latest training: {latestTrainingJob.model_name}</div>
                        <div className="text-gray-400 mb-1">{formatDate(latestTrainingJob.created_at)}</div>
                        <div className="flex items-center">
                          <span className="text-gray-400 mr-2">Status:</span>
                          <span className={`capitalize ${
                            latestTrainingJob.status === 'completed' ? 'text-green-500' : 
                            latestTrainingJob.status === 'failed' ? 'text-red-500' : 
                            'text-yellow-500'
                          }`}>
                            {latestTrainingJob.status.replace('_', ' ')}
                          </span>
                        </div>
                        {latestTrainingJob.error_message && (
                          <div className="mt-1 text-red-400 max-w-xs overflow-hidden text-ellipsis">
                            Error: {latestTrainingJob.error_message}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                  <button
                    onClick={() => setIsTrainingMode(true)}
                    className="flex items-center text-xs bg-gray-700 hover:bg-gray-600 text-white px-3 py-1 rounded-md"
                  >
                    <BeakerIcon className="h-3 w-3 mr-1" />
                    Train
                  </button>
                </div>
              )}
            </div>
            
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-6 pb-8">
              {dataSources.map((source) => (
                <div 
                  key={source.id} 
                  className="relative flex flex-col items-center"
                  onMouseEnter={() => setHoveredSource(source.id)}
                  onMouseLeave={() => setHoveredSource(null)}
                >
                  {isTrainingMode && (
                    <div className="absolute top-0 right-0 z-10">
                      <input
                        type="checkbox"
                        checked={selectedDataSources.includes(source.id)}
                        onChange={() => toggleDataSourceSelection(source.id)}
                        className="h-4 w-4 rounded border-gray-600 text-blue-600 focus:ring-blue-500"
                      />
                    </div>
                  )}
                  
                  <div
                    onClick={() => isTrainingMode ? toggleDataSourceSelection(source.id) : handleExistingDataSourceClick(source)}
                    className={`flex flex-col items-center focus:outline-none rounded-lg p-2 cursor-pointer ${
                      isTrainingMode && selectedDataSources.includes(source.id) 
                        ? 'bg-blue-900/30 border border-blue-700' 
                        : isTrainingMode ? 'hover:bg-gray-700' : 'hover:bg-gray-800'
                    }`}
                  >
                    <img 
                      src={getDataSourceIcon(source)} 
                      alt={source.name || 'Data source'}
                      className="w-10 h-10" 
                    />
                  </div>
                  
                  {hoveredSource === source.id && !isTrainingMode && (
                    <div className="absolute z-10 top-full mt-2 left-1/2 transform -translate-x-1/2 bg-gray-800 text-white text-xs py-1 px-2 rounded shadow-lg whitespace-nowrap">
                      <div className="flex items-center gap-1.5">
                        <span className={`h-2 w-2 rounded-full ${source.status === 'configured' ? 'bg-green-500' : 'bg-yellow-500'}`}></span>
                        <span>{source.status}</span>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
        
        {/* Data Source Configuration Modal */}
        {selectedDataSource && (
          <DataSourceModal
            isOpen={isModalOpen}
            onClose={() => setIsModalOpen(false)}
            dataSource={prepareDataSourceForModal(selectedDataSource)}
            projectId={projectId}
          />
        )}

        {/* Data Source Edit Modal */}
        {selectedExistingSource && (
          <DataSourceEditModal
            isOpen={isEditModalOpen}
            onClose={() => {
              setIsEditModalOpen(false);
              setSelectedExistingSource(null);
            }}
            dataSource={selectedExistingSource}
            dataSourceType={findDataSourceType(selectedExistingSource) || {
              id: selectedExistingSource.type,
              name: selectedExistingSource.name || 'Data Source',
              category: 'document',
              required_fields: []
            }}
            projectId={projectId}
          />
        )}

        {/* CSV Upload Modal */}
        <CsvUploadModal
          isOpen={isCsvUploadModalOpen}
          onClose={() => setIsCsvUploadModalOpen(false)}
          projectId={projectId}
        />
      </div>
    </div>
  );
}
