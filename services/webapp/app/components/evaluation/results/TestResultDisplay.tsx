import React from 'react';
import { AgentResponseView } from './AgentResponseView';
import { GraderResponseView } from './GraderResponseView';

interface TestResultDisplayProps {
  agentResponse: string;
  graderResponse: string;
  testCaseNumber?: number;
}

export function TestResultDisplay({ 
  agentResponse, 
  graderResponse,
  testCaseNumber 
}: TestResultDisplayProps) {

  return (
    <div className="w-full">
      {testCaseNumber && (
        <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
          Test Case {testCaseNumber}
        </h4>
      )}
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Agent Response - Left/Top */}
        <div className="flex flex-col">
          <AgentResponseView response={agentResponse} />
        </div>
        
        {/* Grader Response - Right/Bottom */}
        <div className="flex flex-col">
          <GraderResponseView response={graderResponse} />
        </div>
      </div>
    </div>
  );
}