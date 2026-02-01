import type { LoaderFunctionArgs } from "@remix-run/node";
import { json } from "@remix-run/node";
import { getFolderFiles } from "~/services/chicory.server";
import { verifyProjectAccess } from "~/utils/rbac.server";

export async function loader({ request, params }: LoaderFunctionArgs) {
  const { projectId, dataSourceId } = params;

  if (!projectId || !dataSourceId) {
    return json({ error: "Project ID and Data Source ID are required" }, { status: 400 });
  }

  await verifyProjectAccess(request, projectId);

  try {
    const result = await getFolderFiles(projectId, dataSourceId);
    return json(result);
  } catch (error) {
    console.error("Error fetching folder files:", error);
    return json(
      { error: error instanceof Error ? error.message : "Failed to fetch folder files" },
      { status: 500 }
    );
  }
}
