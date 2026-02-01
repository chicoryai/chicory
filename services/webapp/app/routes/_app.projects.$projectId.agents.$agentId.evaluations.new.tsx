import { json, redirect } from "@remix-run/node";
import type { LoaderFunctionArgs, ActionFunctionArgs } from "@remix-run/node";
import { useLoaderData, Link, useParams, Form, useNavigate, useFetcher } from "@remix-run/react";
import { useState, useRef } from "react";
import { ArrowLeftIcon, DocumentArrowUpIcon } from "@heroicons/react/24/outline";
import { getUserOrgDetails } from "~/auth/auth.server";
import { getAgent, createEvaluation } from "~/services/chicory.server";
import { Button } from "~/components/Button";
import { EvaluationCSVUploadModal } from "~/components/EvaluationCSVUploadModal";

export async function loader({ request, params }: LoaderFunctionArgs) {
  const { agentId, projectId } = params;
  
  if (!agentId || !projectId) {
    throw new Response("Agent ID and Project ID are required", { status: 400 });
  }
  
  const userDetails = await getUserOrgDetails(request);
  if (userDetails instanceof Response) return userDetails;
  
  const agent = await getAgent(projectId, agentId);
  
  if (!agent) {
    throw new Response("Agent not found", { status: 404 });
  }
  
  return json({ agent, projectId });
}

export async function action({ request, params }: ActionFunctionArgs) {
  const { agentId, projectId } = params;
  
  if (!agentId || !projectId) {
    throw new Response("Agent ID and Project ID are required", { status: 400 });
  }
  
  const userDetails = await getUserOrgDetails(request);
  if (userDetails instanceof Response) return userDetails;
  
  const formData = await request.formData();
  
  // Validate required fields
  const name = formData.get("name") as string;
  const criteria = formData.get("criteria") as string;
  const csvFile = formData.get("csv_file") as File;
  
  if (!name || !criteria || !csvFile) {
    return json({ error: "Name, criteria, and CSV file are required" }, { status: 400 });
  }
  
  try {
    // Create FormData for the API call
    const apiFormData = new FormData();
    apiFormData.append("name", name);
    apiFormData.append("criteria", criteria);
    
    const description = formData.get("description") as string;
    if (description) {
      apiFormData.append("description", description);
    }
    
    apiFormData.append("csv_file", csvFile);
    
    const evaluation = await createEvaluation(projectId, agentId, apiFormData);
    
    return redirect(`/projects/${projectId}/agents/${agentId}/evaluations/${evaluation.id}`);
  } catch (error) {
    console.error("Failed to create evaluation:", error);
    return json({ error: "Failed to create evaluation" }, { status: 500 });
  }
}

export default function NewEvaluation() {
  const { agent, projectId } = useLoaderData<typeof loader>();
  const params = useParams();
  const navigate = useNavigate();
  const fetcher = useFetcher();
  const [showCSVModal, setShowCSVModal] = useState(false);
  const [csvFile, setCSVFile] = useState<File | null>(null);
  const formRef = useRef<HTMLFormElement>(null);

  const handleCSVUpload = async (file: File) => {
    setCSVFile(file);
    setShowCSVModal(false);
  };

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    if (!csvFile) {
      e.preventDefault();
      alert("Please upload a CSV file with test cases");
      return;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Navigation */}
        <div className="mb-6">
          <Link
            to={`/projects/${params.projectId}/agents/${params.agentId}/evaluations`}
            className="inline-flex items-center text-sm text-gray-600 dark:text-gray-400 hover:text-purple-600 dark:hover:text-purple-400"
          >
            <ArrowLeftIcon className="h-4 w-4 mr-1" />
            Back to Evaluations
          </Link>
        </div>

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Create New Evaluation
          </h1>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            Create an evaluation to test {agent.name}'s performance with custom test cases
          </p>
        </div>

        {/* Form */}
        <Form 
          ref={formRef}
          method="post" 
          encType="multipart/form-data"
          onSubmit={handleSubmit}
          className="space-y-6"
        >
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
            {/* Name Field */}
            <div className="mb-6">
              <label 
                htmlFor="name" 
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
              >
                Evaluation Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                id="name"
                name="name"
                required
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                placeholder="e.g., Customer Support Quality Test"
              />
            </div>

            {/* Description Field */}
            <div className="mb-6">
              <label 
                htmlFor="description" 
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
              >
                Description
              </label>
              <textarea
                id="description"
                name="description"
                rows={3}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                placeholder="Describe what this evaluation tests..."
              />
            </div>

            {/* Criteria Field */}
            <div className="mb-6">
              <label 
                htmlFor="criteria" 
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
              >
                Evaluation Criteria <span className="text-red-500">*</span>
              </label>
              <textarea
                id="criteria"
                name="criteria"
                required
                rows={4}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                placeholder="Define the criteria for evaluating the agent's responses. What makes a response good or bad?"
              />
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                Be specific about what you expect from the agent's responses
              </p>
            </div>

            {/* CSV Upload */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Test Cases <span className="text-red-500">*</span>
              </label>
              
              {csvFile ? (
                <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <DocumentArrowUpIcon className="h-6 w-6 text-green-600 dark:text-green-400" />
                      <div>
                        <p className="font-medium text-gray-900 dark:text-white">
                          {csvFile.name}
                        </p>
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          {(csvFile.size / 1024).toFixed(2)} KB
                        </p>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => setCSVFile(null)}
                      className="text-sm text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
                    >
                      Remove
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => setShowCSVModal(true)}
                  className="w-full p-6 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg hover:border-purple-400 dark:hover:border-purple-500 transition-colors"
                >
                  <DocumentArrowUpIcon className="h-8 w-8 mx-auto text-gray-400 mb-2" />
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Click to upload CSV file with test cases
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                    Required columns: task, expected_output, evaluation_guideline
                  </p>
                </button>
              )}
              
              {/* Hidden file input for form submission */}
              {csvFile && (
                <input
                  type="file"
                  name="csv_file"
                  className="hidden"
                  ref={(input) => {
                    if (input && csvFile) {
                      const dataTransfer = new DataTransfer();
                      dataTransfer.items.add(csvFile);
                      input.files = dataTransfer.files;
                    }
                  }}
                />
              )}
            </div>

            {/* Error Message */}
            {fetcher.data?.error && (
              <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg mb-6">
                <p className="text-sm text-red-600 dark:text-red-400">
                  {fetcher.data.error}
                </p>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-3">
            <Button
              type="button"
              variant="tertiary"
              onClick={() => navigate(`/projects/${params.projectId}/agents/${params.agentId}/evaluations`)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              disabled={fetcher.state === "submitting"}
            >
              {fetcher.state === "submitting" ? "Creating..." : "Create Evaluation"}
            </Button>
          </div>
        </Form>

        {/* CSV Upload Modal */}
        <EvaluationCSVUploadModal
          isOpen={showCSVModal}
          onClose={() => setShowCSVModal(false)}
          onUpload={handleCSVUpload}
        />
      </div>
    </div>
  );
}
