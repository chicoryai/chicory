import type { LoaderFunctionArgs, ActionFunctionArgs } from "@remix-run/node";
import { json } from "@remix-run/node";
import { getFolderFile, deleteFolderFile } from "~/services/chicory.server";
import { verifyProjectAccess } from "~/utils/rbac.server";

export async function loader({ request, params }: LoaderFunctionArgs) {
  const { projectId, dataSourceId, fileId } = params;

  if (!projectId || !dataSourceId || !fileId) {
    return json({ error: "Project ID, Data Source ID, and File ID are required" }, { status: 400 });
  }

  await verifyProjectAccess(request, projectId);

  try {
    const result = await getFolderFile(projectId, dataSourceId, fileId);
    return json(result);
  } catch (error) {
    console.error("Error fetching file details:", error);
    return json(
      { error: error instanceof Error ? error.message : "Failed to fetch file details" },
      { status: 500 }
    );
  }
}

export async function action({ request, params }: ActionFunctionArgs) {
  const { projectId, dataSourceId, fileId } = params;

  if (!projectId || !dataSourceId || !fileId) {
    return json({ error: "Project ID, Data Source ID, and File ID are required" }, { status: 400 });
  }

  await verifyProjectAccess(request, projectId);

  if (request.method === "DELETE") {
    try {
      await deleteFolderFile(projectId, dataSourceId, fileId);
      return json({ success: true, message: "File deleted successfully" });
    } catch (error) {
      console.error("Error deleting file:", error);
      return json(
        { error: error instanceof Error ? error.message : "Failed to delete file" },
        { status: 500 }
      );
    }
  }

  return json({ error: "Method not allowed" }, { status: 405 });
}
