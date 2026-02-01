import { json } from "@remix-run/node";
import type { LoaderFunctionArgs } from "@remix-run/node";

const BASE_URL = process.env.CHICORY_API_URL || "http://localhost:8000";

export async function loader({ params, request }: LoaderFunctionArgs) {
  const { projectId, agentId, taskId } = params;

  if (!projectId || !agentId || !taskId) {
    return json({ error: "Missing required parameters", artifacts: [] }, { status: 400 });
  }

  try {
    // Forward auth headers if present (backend validates project/agent ownership)
    const headers: Record<string, string> = {};
    const authHeader = request.headers.get("Authorization");
    if (authHeader) {
      headers["Authorization"] = authHeader;
    }

    const response = await fetch(
      `${BASE_URL}/projects/${projectId}/agents/${agentId}/tasks/${taskId}/artifacts`,
      { headers }
    );

    if (!response.ok) {
      console.error("Failed to fetch artifacts:", response.status, response.statusText);
      return json({ error: `Backend returned ${response.status}`, artifacts: [] }, { status: response.status });
    }

    const data = await response.json();
    return json(data);
  } catch (error) {
    console.error("Error fetching artifacts:", error);
    return json({ error: "Failed to fetch artifacts", artifacts: [] }, { status: 502 });
  }
}
