import { json } from "@remix-run/node";
import type { LoaderFunctionArgs } from "@remix-run/node";
import { getUserOrgDetails } from "~/auth/auth.server";
import { getMcpGateways } from "~/services/chicory.server";

export async function loader({ request, params }: LoaderFunctionArgs) {
  const { projectId } = params;

  if (!projectId) {
    return json({ error: "Project ID is required" }, { status: 400 });
  }

  const userDetails = await getUserOrgDetails(request);

  if (userDetails instanceof Response) {
    return userDetails;
  }

  try {
    const gateways = await getMcpGateways(projectId);
    return json(gateways);
  } catch (error) {
    console.error("Error fetching gateways:", error);
    return json({ error: "Failed to fetch gateways" }, { status: 500 });
  }
}
