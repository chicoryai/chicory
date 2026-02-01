import { useState } from "react";
import type { TrainingJob, ChatThread } from "~/services/chicory.server";
import { RecentChatsList } from "~/components/RecentChatsList";
import { TrainingJobsList } from "~/components/TrainingJobsList";

interface ProjectTabbedPanelProps {
  chatThreads: ChatThread[];
  trainingJobs: TrainingJob[];
}

export function ProjectTabbedPanel({ chatThreads, trainingJobs }: ProjectTabbedPanelProps) {
  const [activeTab, setActiveTab] = useState<'chats' | 'training'>('chats');
  
  // Format chat threads for the RecentChatsList component
  const formattedChatThreads = chatThreads.map(thread => ({
    id: thread.id,
    title: thread.title,
    lastMessageTime: thread.updated_at // Use updated_at as the last message time
  }));
  
  return (
    <div className="mt-4">
      {/* Tab navigation */}
      <div className="flex border-b border-gray-700 mb-4">
        <button
          className={`py-2 px-4 text-sm font-medium ${
            activeTab === 'chats' 
              ? 'text-white border-b-2 border-blue-500' 
              : 'text-gray-400 hover:text-gray-300'
          }`}
          onClick={() => setActiveTab('chats')}
        >
          Recent Chats
        </button>
        <button
          className={`py-2 px-4 text-sm font-medium ${
            activeTab === 'training' 
              ? 'text-white border-b-2 border-blue-500' 
              : 'text-gray-400 hover:text-gray-300'
          }`}
          onClick={() => setActiveTab('training')}
        >
          Training Jobs
          {trainingJobs.length > 0 && (
            <span className="ml-2 bg-gray-700 text-xs px-2 py-0.5 rounded-full">
              {trainingJobs.length}
            </span>
          )}
        </button>
      </div>
      
      {/* Tab content */}
      <div className="mt-2">
        {activeTab === 'chats' ? (
          <RecentChatsList chatThreads={formattedChatThreads} />
        ) : (
          <TrainingJobsList trainingJobs={trainingJobs} />
        )}
      </div>
    </div>
  );
}
