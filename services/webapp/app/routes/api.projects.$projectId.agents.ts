import { json } from "@remix-run/node";
import type { LoaderFunctionArgs } from "@remix-run/node";
import { getUserOrgDetails } from "~/auth/auth.server";
import { getAgents } from "~/services/chicory.server";

export async function loader({ request, params }: LoaderFunctionArgs) {
  try {
    const { projectId } = params;

    if (!projectId) {
      return json({ error: "Project ID is required" }, { status: 400 });
    }

    const userDetails = await getUserOrgDetails(request);
    if (userDetails instanceof Response) {
      return userDetails;
    }

    const agents = await getAgents(projectId);

    return json({ agents });
  } catch (error) {
    console.error("Error fetching agents:", error);
    return json({ error: "Failed to fetch agents" }, { status: 500 });
  }
}
