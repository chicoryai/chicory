import type { ActionFunctionArgs } from "@remix-run/node";
import { json } from "@remix-run/node";
import { verifyProjectAccess } from "~/utils/rbac.server";
import { uploadFolderFiles } from "~/services/chicory.server";

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
    const relativePaths = formData.get("relative_paths") as string;
    const files: File[] = [];

    for (const [key, value] of formData.entries()) {
      if (key === "files" && typeof value !== "string") {
        files.push(value);
      }
    }

    if (!relativePaths || files.length === 0) {
      return json({ detail: "Missing files or relative_paths" }, { status: 400 });
    }

    let paths: string[];
    try {
      paths = JSON.parse(relativePaths);
      if (!Array.isArray(paths)) {
        return json({ detail: "relative_paths must be a JSON array" }, { status: 400 });
      }
    } catch {
      return json({ detail: "Invalid JSON in relative_paths" }, { status: 400 });
    }

    for (const path of paths) {
      let decodedPath: string;
      try {
        decodedPath = decodeURIComponent(path);
      } catch {
        return json({ detail: "Invalid path detected" }, { status: 400 });
      }
      const normalizedPath = decodedPath.replace(/\\/g, '/').replace(/\/+/g, '/');
      if (normalizedPath.includes('..') || normalizedPath.startsWith('/') || normalizedPath.includes('\0')) {
        return json({ detail: "Invalid path detected" }, { status: 400 });
      }
    }

    if (paths.length !== files.length) {
      return json({ detail: "Mismatch between files and paths count" }, { status: 400 });
    }

    const result = await uploadFolderFiles(projectId, uploadId, files, paths);
    return json(result);
  } catch (error) {
    console.error("Error uploading folder files:", error);
    return json(
      { detail: error instanceof Error ? error.message : "Failed to upload files" },
      { status: 500 }
    );
  }
}
