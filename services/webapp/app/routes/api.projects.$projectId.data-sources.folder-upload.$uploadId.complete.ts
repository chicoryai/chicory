import type { ActionFunctionArgs } from "@remix-run/node";
import { json } from "@remix-run/node";
import { verifyProjectAccess } from "~/utils/rbac.server";
import { completeFolderUpload } from "~/services/chicory.server";

export async function action({ request, params }: ActionFunctionArgs) {
  const { projectId, uploadId } = params;
  if (!projectId || !uploadId) {
    return json({ error: "Project ID and Upload ID are required" }, { status: 400 });
  }

  await verifyProjectAccess(request, projectId);

  if (request.method !== "POST") {
    return json({ error: "Method not allowed" }, { status: 405 });
  }

  try {
    const formData = await request.formData();
    const description = formData.get("description") as string | undefined;

    const result = await completeFolderUpload(projectId, uploadId, description);
    return json(result);
  } catch (error) {
    console.error("Error completing folder upload:", error);
    return json(
      { detail: error instanceof Error ? error.message : "Failed to complete upload" },
      { status: 500 }
    );
  }
}
