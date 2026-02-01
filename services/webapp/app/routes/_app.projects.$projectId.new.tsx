import { json, redirect } from "@remix-run/node";
import type { LoaderFunctionArgs, ActionFunctionArgs } from "@remix-run/node";
import { useState, useEffect } from "react";
import { Form, useSubmit, useLoaderData, useActionData, useNavigation } from "@remix-run/react";
import { getUserOrgDetails } from "~/auth/auth.server";
import { verifyProjectAccess } from "~/utils/rbac.server";
import { createAgent } from "~/services/chicory.server";
import { McpToolsInfoBanner } from "~/components/agents/McpToolsInfoBanner";

type LoaderData = {
  projectId: string | null;
  userId: string | null;
};

type ActionData = {
  errors?: {
    name?: string;
    general?: string;
  };
};

export async function loader({ request, params }: LoaderFunctionArgs) {
  const { projectId } = params;

  if (!projectId) {
    throw new Response("Project ID is required", { status: 400 });
  }

  // Verify user has access to this project
  const { user } = await verifyProjectAccess(request, projectId);

  // Return the project ID if available, otherwise null
  return json({
    projectId,
    userId: user.userId
  });
}

export async function action({ request, params, context }: ActionFunctionArgs) {
  const projectId = params.projectId;

  if (!projectId) {
    return json<ActionData>({
      errors: { general: "Project ID is required" }
    }, { status: 400 });
  }

  // Verify user has access to this project
  const { user } = await verifyProjectAccess(request, projectId);
  
  // Parse form data
  const formData = await request.formData();
  const step = formData.get("step") as string;
  
  if (step === "agent") {
    // Step 1: Create Agent
    const name = formData.get("name") as string;
    const description = formData.get("description") as string || undefined;
    
    const errors: ActionData["errors"] = {};
    
    if (!name || typeof name !== "string" || !name.trim()) {
      errors.name = "Agent name is required";
    }
    
    if (Object.keys(errors).length > 0) {
      return json<ActionData>({ errors }, { status: 400 });
    }

    try {
      // Create the agent with only name and description
      const agent = await createAgent(
        projectId,
        name,
        description,
        user.userId,
        undefined, // instructions
        undefined, // outputFormat
        undefined, // deployed
        undefined, // api_key
        undefined, // state
        undefined  // capabilities
      );
      
      // Redirect directly to playground
      return redirect(`/projects/${projectId}/agents/${agent.id}/playground`);
    } catch (error) {
      console.error("Error creating agent:", error);
      return json<ActionData>({ 
        errors: { general: "Failed to create agent. Please try again." } 
      }, { status: 500 });
    }
  }
  
  return json<ActionData>({ 
    errors: { general: "Invalid request" } 
  }, { status: 400 });
}

export default function NewAgent() {
  const submit = useSubmit();
  const { projectId } = useLoaderData<LoaderData>();
  const actionData = useActionData<ActionData>();
  const navigation = useNavigation();
  const isSubmitting = navigation.state === "submitting";
  
  // Form state for agent creation
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [showErrorMessage, setShowErrorMessage] = useState(false);
  
  // Handle errors
  useEffect(() => {
    if (actionData?.errors?.general) {
      setShowErrorMessage(true);
      
      // Auto-dismiss error message
      const timer = setTimeout(() => {
        setShowErrorMessage(false);
      }, 5000);
      
      return () => clearTimeout(timer);
    }
  }, [actionData?.errors?.general]);
  
  const handleAgentSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    
    const formData = new FormData();
    formData.append("step", "agent");
    formData.append("name", name);
    
    if (description) formData.append("description", description);
    
    submit(formData, { method: "post" });
  };
  
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-transparent dark:bg-gray-900 px-4">
      <div className="w-full max-w-2xl bg-transparent dark:bg-gray-900 rounded-lg p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Create New Agent
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Give your agent a name and description, then configure it in the playground
          </p>
        </div>
        
        {/* MCP Tools Info Banner */}
        <div className="mb-6">
          <McpToolsInfoBanner defaultExpanded={false} />
        </div>
        
        <div className="relative">
          {/* Display errors */}
          {actionData?.errors?.general && showErrorMessage && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-md transition-opacity duration-300">
              <div className="text-sm text-red-700">
                {actionData.errors.general}
              </div>
            </div>
          )}
          
          {/* Agent Creation Form */}
          <Form onSubmit={handleAgentSubmit} className="space-y-6">
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Name *
              </label>
              <input
                type="text"
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="mt-1 block w-full border border-gray-300 dark:border-gray-600 rounded-md py-2 px-3 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-purple-500 focus:border-purple-500"
                placeholder="e.g., Customer Support Agent, Data Analysis Assistant"
                required
              />
              <p className="mt-1.5 text-xs text-gray-500 dark:text-gray-400">
                Use a clear, descriptive name that reflects the agent's primary purpose
              </p>
            </div>
            
            <div>
              <label htmlFor="description" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Description
              </label>
              <textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
                className="mt-1 block w-full border border-gray-300 dark:border-gray-600 rounded-md py-2 px-3 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-purple-500 focus:border-purple-500"
                placeholder="Describe what this agent does"
              />
              <p className="mt-1.5 text-xs text-gray-500 dark:text-gray-400">
                After creation, you'll configure detailed prompts, add MCP tools, and test your agent in the playground
              </p>
            </div>
            
                  <div className="flex justify-end space-x-3 pt-4">
                    <button
                      type="submit"
                      className="px-4 py-2 bg-purple-500 text-white rounded-md hover:bg-purple-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 disabled:opacity-50 disabled:cursor-not-allowed"
                      disabled={!name.trim() || isSubmitting}
                    >
                      {isSubmitting ? 'Creating...' : 'Create Agent'}
                    </button>
                  </div>
                </Form>
        </div>
      </div>
    </div>
  );
}
