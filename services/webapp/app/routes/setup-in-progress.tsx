import { useEffect } from "react";
import { useNavigate } from "@remix-run/react";
import { json } from "@remix-run/node";
import type { LoaderFunctionArgs } from "@remix-run/node";

/**
 * This page serves as a temporary landing spot while the default project is being created
 */
export async function loader({ request }: LoaderFunctionArgs) {
  return json({});
}

export default function SetupInProgress() {
  const navigate = useNavigate();
  
  // After 3 seconds, redirect to the agents page
  // This gives time for the default project to be created
  useEffect(() => {
    const timer = setTimeout(() => {
      navigate("/");
    }, 3000);
    
    return () => clearTimeout(timer);
  }, [navigate]);
  
  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900">
      <div className="text-center p-8 max-w-md bg-white dark:bg-gray-800 rounded-lg shadow-md">
        <h1 className="text-2xl font-bold text-purple-600 dark:text-purple-400 mb-4">
          Setting up your workspace
        </h1>
        <div className="flex justify-center mb-6">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500"></div>
        </div>
        <p className="text-gray-700 dark:text-gray-300 mb-2">
          We're creating your default project...
        </p>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          You'll be redirected automatically in a few seconds.
        </p>
      </div>
    </div>
  );
}
