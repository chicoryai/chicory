import { PlusIcon, XMarkIcon, ClockIcon, CheckCircleIcon, ExclamationCircleIcon } from "@heroicons/react/24/outline";
import { useState } from "react";
import { useFetcher } from "@remix-run/react";
import type { TrainingJob, DataSourceCredential } from "~/services/chicory.server";

interface ProjectTrainingPanelProps {
  projectId: string;
  trainingJobs: TrainingJob[];
  dataSources: DataSourceCredential[];
}

export function ProjectTrainingPanel({ projectId, trainingJobs, dataSources }: ProjectTrainingPanelProps) {
  const [showTrainingForm, setShowTrainingForm] = useState(false);
  const [selectedModel, setSelectedModel] = useState("default");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectedDataSources, setSelectedDataSources] = useState<string[]>([]);
  const [description, setDescription] = useState("");
  const fetcher = useFetcher();

  // Available models for training
  const availableModels = [
    { id: "default", name: "Default Model" },
    { id: "gpt-3.5", name: "GPT-3.5" },
    { id: "gpt-4", name: "GPT-4" }
  ];

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

  // Toggle data source selection
  const toggleDataSource = (dataSourceId: string) => {
    setSelectedDataSources(prev => 
      prev.includes(dataSourceId)
        ? prev.filter(id => id !== dataSourceId)
        : [...prev, dataSourceId]
    );
  };

  // Handle form submission
  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    
    if (selectedDataSources.length === 0) {
      alert("Please select at least one data source for training");
      return;
    }
    
    setIsSubmitting(true);
    
    fetcher.submit(
      {
        _action: "createTrainingJob",
        model_name: selectedModel,
        description: description,
        data_source_ids: JSON.stringify(selectedDataSources)
      },
      { method: "post" }
    );
    
    // Reset form after submission
    setShowTrainingForm(false);
    setIsSubmitting(false);
    setSelectedDataSources([]);
    setDescription("");
  };

  // Get data source icon
  const getDataSourceIcon = (dataSource: DataSourceCredential) => {
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
    if (knownTypes.includes(dataSource.type)) {
      return `/icons/${dataSource.type}.svg`;
    }
    
    // Otherwise, use the generic icon
    return "/icons/generic-integration.svg";
  };

  return (
    <div className="h-full mt-6">
      <div className="p-6 bg-gray-900 rounded-lg">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-sm font-medium text-white">Model Training</h2>
          <button 
            className="text-gray-400 hover:text-gray-300 p-1 rounded-full hover:bg-gray-800"
            onClick={() => setShowTrainingForm(!showTrainingForm)}
          >
            {showTrainingForm ? (
              <XMarkIcon className="h-5 w-5" />
            ) : (
              <PlusIcon className="h-5 w-5" />
            )}
          </button>
        </div>
        
        {/* Training Form - Slides down when add button is clicked */}
        <div 
          className={`transition-all duration-300 ease-in-out overflow-hidden ${
            showTrainingForm ? 'max-h-[800px] opacity-100 mb-6' : 'max-h-0 opacity-0'
          }`}
        >
          <div className="bg-gray-800 rounded-lg p-4 mb-2">
            <h3 className="text-sm font-medium text-white mb-3">Start New Training Job</h3>
            <form onSubmit={handleSubmit}>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Select Model
                </label>
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="w-full p-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-1 focus:ring-gray-500"
                >
                  {availableModels.map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.name}
                    </option>
                  ))}
                </select>
              </div>
              
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Description (Optional)
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full p-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-1 focus:ring-gray-500 resize-none"
                  rows={2}
                  placeholder="Enter a description for this training job"
                />
              </div>
              
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Select Data Sources for Training
                </label>
                {dataSources.length === 0 ? (
                  <div className="text-sm text-gray-400 p-3 bg-gray-700 rounded-md">
                    No data sources available. Add data sources to your project first.
                  </div>
                ) : (
                  <div className="grid grid-cols-2 gap-2 max-h-40 overflow-y-auto p-2 bg-gray-700 rounded-md">
                    {dataSources.map((source) => (
                      <div 
                        key={source.id}
                        className={`flex items-center p-2 rounded cursor-pointer ${
                          selectedDataSources.includes(source.id) 
                            ? 'bg-blue-900/30 border border-blue-700' 
                            : 'hover:bg-gray-600'
                        }`}
                        onClick={() => toggleDataSource(source.id)}
                      >
                        <input
                          type="checkbox"
                          checked={selectedDataSources.includes(source.id)}
                          onChange={() => {}} // Handled by the div onClick
                          className="mr-2"
                        />
                        <div className="flex items-center">
                          <img 
                            src={getDataSourceIcon(source)} 
                            alt={source.name || 'Data source'}
                            className="w-5 h-5 mr-2" 
                          />
                          <span className="text-sm text-white truncate max-w-[120px]">
                            {source.name || source.type}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              
              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={isSubmitting || dataSources.length === 0 || selectedDataSources.length === 0}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                >
                  {isSubmitting ? "Starting..." : "Start Training"}
                </button>
              </div>
            </form>
          </div>
        </div>
        
        {trainingJobs.length === 0 ? (
          <div className="flex items-center justify-center py-10 mt-4">
            <div className="text-center">
              <div className="flex justify-center mb-5">
                <div className="h-12 w-12 flex items-center justify-center">
                  <ClockIcon className="h-7 w-7 text-gray-500" />
                </div>
              </div>
              <p className="text-sm text-gray-400 mb-1">
                No training jobs yet.
              </p>
              <p className="text-sm text-gray-400">
                Train a custom model on your project data
              </p>
              <p className="text-sm text-gray-400">
                to improve responses for your specific use case.
              </p>
            </div>
          </div>
        ) : (
          <div className="mt-4">
            <h3 className="text-sm font-medium text-white mb-3">Training Jobs</h3>
            <div className="space-y-3">
              {trainingJobs.map((job) => (
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
                      {formatDate(job.created_at)}
                    </span>
                  </div>
                  <div className="mt-2">
                    <div className="flex items-center">
                      <span className="text-xs text-gray-400 mr-2">Status:</span>
                      <span className="text-xs capitalize text-white">{job.status.replace('_', ' ')}</span>
                    </div>
                    {job.completed_at && (
                      <div className="flex items-center mt-1">
                        <span className="text-xs text-gray-400 mr-2">Completed:</span>
                        <span className="text-xs text-white">{formatDate(job.completed_at)}</span>
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
          </div>
        )}
      </div>
    </div>
  );
}
