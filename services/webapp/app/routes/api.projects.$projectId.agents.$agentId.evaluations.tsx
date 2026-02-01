import { json } from "@remix-run/node";
import type { LoaderFunctionArgs } from "@remix-run/node";
import { getUserOrgDetails } from "~/auth/auth.server";
import { getEvaluations } from "~/services/chicory.server";

export async function loader({ request, params }: LoaderFunctionArgs) {
  const { projectId, agentId } = params;

  if (!projectId || !agentId) {
    return json({ error: "Project ID and Agent ID are required" }, { status: 400 });
  }

  const userDetails = await getUserOrgDetails(request);

  if (userDetails instanceof Response) {
    return userDetails;
  }

  try {
    const evaluationList = await getEvaluations(projectId, agentId);
    return json({ evaluations: evaluationList.evaluations });
  } catch (error) {
    console.error("Error fetching evaluations:", error);
    return json({ error: "Failed to fetch evaluations" }, { status: 500 });
  }
}
