import { useEffect, useState } from "react";

interface DeploymentLoaderProps {
  toolName?: string;
  className?: string;
}

export function DeploymentLoader({ toolName, className = "" }: DeploymentLoaderProps) {
  const [dots, setDots] = useState(1);
  const [deploymentPhase, setDeploymentPhase] = useState(0);
  
  const phases = [
    "Initializing deployment",
    "Configuring environment",
    "Loading tool definition",
    "Establishing connection",
    "Validating configuration",
    "Finalizing deployment"
  ];
  
  // Animate dots
  useEffect(() => {
    const interval = setInterval(() => {
      setDots(prev => (prev >= 3 ? 1 : prev + 1));
    }, 500);
    return () => clearInterval(interval);
  }, []);
  
  // Cycle through deployment phases
  useEffect(() => {
    const interval = setInterval(() => {
      setDeploymentPhase(prev => (prev >= phases.length - 1 ? 0 : prev + 1));
    }, 3000);
    return () => clearInterval(interval);
  }, [phases.length]);
  
  return (
    <div className={`flex flex-col items-center justify-center h-full ${className}`}>
      {/* Animated deployment icon */}
      <div className="relative mb-4 mt-4">
        <div className="w-16 h-16 relative">
          {/* Outer ring animation */}
          <div className="absolute inset-0 rounded-full border-2 border-indigo-200 dark:border-indigo-800 animate-pulse" />
          
          {/* Middle ring animation */}
          <div className="absolute inset-2 rounded-full border-2 border-indigo-400 dark:border-indigo-600 animate-spin-slow" />
          
          {/* Inner circle with icon */}
          <div className="absolute inset-4 rounded-full bg-indigo-500 dark:bg-indigo-600 flex items-center justify-center animate-pulse">
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
            </svg>
          </div>
          
          {/* Floating particles */}
          <div className="absolute -inset-2">
            <div className="absolute top-0 left-1/2 w-1 h-1 bg-indigo-400 rounded-full animate-float-up" />
            <div className="absolute top-1/2 right-0 w-1 h-1 bg-indigo-400 rounded-full animate-float-right" 
              style={{ animationDelay: '0.5s' }} />
            <div className="absolute bottom-0 left-1/2 w-1 h-1 bg-indigo-400 rounded-full animate-float-down" 
              style={{ animationDelay: '1s' }} />
            <div className="absolute top-1/2 left-0 w-1 h-1 bg-indigo-400 rounded-full animate-float-left" 
              style={{ animationDelay: '1.5s' }} />
          </div>
        </div>
      </div>
      
      {/* Tool name */}
      {toolName && (
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 pt-2 my-2">
          {toolName}
        </h3>
      )}
      
      {/* Deployment status */}
      <div className="text-center">
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
          Deploying tool{'.'.repeat(dots)}
        </p>
      </div>
      
      <style jsx>{`
        @keyframes spin-slow {
          from {
            transform: rotate(0deg);
          }
          to {
            transform: rotate(360deg);
          }
        }
        
        @keyframes float-up {
          0%, 100% {
            transform: translateY(0) translateX(-50%);
            opacity: 0;
          }
          20% {
            opacity: 1;
          }
          80% {
            opacity: 1;
          }
          100% {
            transform: translateY(-20px) translateX(-50%);
            opacity: 0;
          }
        }
        
        @keyframes float-right {
          0%, 100% {
            transform: translateX(0) translateY(-50%);
            opacity: 0;
          }
          20% {
            opacity: 1;
          }
          80% {
            opacity: 1;
          }
          100% {
            transform: translateX(20px) translateY(-50%);
            opacity: 0;
          }
        }
        
        @keyframes float-down {
          0%, 100% {
            transform: translateY(0) translateX(-50%);
            opacity: 0;
          }
          20% {
            opacity: 1;
          }
          80% {
            opacity: 1;
          }
          100% {
            transform: translateY(20px) translateX(-50%);
            opacity: 0;
          }
        }
        
        @keyframes float-left {
          0%, 100% {
            transform: translateX(0) translateY(-50%);
            opacity: 0;
          }
          20% {
            opacity: 1;
          }
          80% {
            opacity: 1;
          }
          100% {
            transform: translateX(-20px) translateY(-50%);
            opacity: 0;
          }
        }
        
        @keyframes fade-in-out {
          0%, 100% {
            opacity: 0.7;
          }
          50% {
            opacity: 1;
          }
        }
        
        .animate-spin-slow {
          animation: spin-slow 3s linear infinite;
        }
        
        .animate-float-up {
          animation: float-up 2s ease-in-out infinite;
        }
        
        .animate-float-right {
          animation: float-right 2s ease-in-out infinite;
        }
        
        .animate-float-down {
          animation: float-down 2s ease-in-out infinite;
        }
        
        .animate-float-left {
          animation: float-left 2s ease-in-out infinite;
        }
        
        .animate-fade-in-out {
          animation: fade-in-out 2s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
}