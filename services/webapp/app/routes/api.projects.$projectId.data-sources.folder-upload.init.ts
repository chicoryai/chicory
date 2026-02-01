import type { ActionFunctionArgs } from "@remix-run/node";
import { json } from "@remix-run/node";
import { verifyProjectAccess } from "~/utils/rbac.server";
import { initFolderUpload } from "~/services/chicory.server";

export async function action({ request, params }: ActionFunctionArgs) {
  const { projectId } = params;
  if (!projectId) {
    return json({ error: "Project ID is required" }, { status: 400 });
  }

  await verifyProjectAccess(request, projectId);

  if (request.method !== "POST") {
    return json({ error: "Method not allowed" }, { status: 405 });
  }

  try {
    const formData = await request.formData();
    const name = formData.get("name") as string;
    const rootFolderName = formData.get("root_folder_name") as string;
    const category = formData.get("category") as string || "document";
    const totalFiles = parseInt(formData.get("total_files") as string, 10);
    const totalSize = parseInt(formData.get("total_size") as string, 10);
    const maxDepth = parseInt(formData.get("max_depth") as string, 10);
    const description = formData.get("description") as string | undefined;

    if (!name || !rootFolderName || isNaN(totalFiles) || isNaN(totalSize) || isNaN(maxDepth)) {
      return json({ detail: "Missing required fields" }, { status: 400 });
    }

    if (totalFiles < 0 || totalFiles > 1000) {
      return json({ detail: "Invalid total_files value" }, { status: 400 });
    }
    if (totalSize < 0 || totalSize > 500 * 1024 * 1024) {
      return json({ detail: "Invalid total_size value" }, { status: 400 });
    }
    if (maxDepth < 0 || maxDepth > 10) {
      return json({ detail: "Invalid max_depth value" }, { status: 400 });
    }

    const result = await initFolderUpload(projectId, name, rootFolderName, category, totalFiles, totalSize, maxDepth, description);
    return json(result, { status: 201 });
  } catch (error) {
    console.error("Error initializing folder upload:", error);
    return json(
      { detail: error instanceof Error ? error.message : "Failed to initialize upload" },
      { status: 500 }
    );
  }
}
