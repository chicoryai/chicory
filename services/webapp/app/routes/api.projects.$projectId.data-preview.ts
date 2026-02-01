import { json } from "@remix-run/node";
import type { LoaderFunctionArgs } from "@remix-run/node";
import { getDataSourcePreview } from "~/services/chicory.server";
import { verifyProjectAccess } from "~/utils/rbac.server";

export async function loader({ request, params }: LoaderFunctionArgs) {
  const { projectId } = params;
  if (!projectId) {
    return json({ error: "Project ID is required" }, { status: 400 });
  }

  await verifyProjectAccess(request, projectId);

  const url = new URL(request.url);
  const path = url.searchParams.get("path");

  if (!path) {
    return json({ error: "path parameter is required" }, { status: 400 });
  }

  // Path traversal protection: block literal, decoded, and URL-encoded variants
  let decodedPath: string;
  try {
    decodedPath = decodeURIComponent(path);
  } catch {
    // Malformed URI encoding (e.g. truncated UTF-8 like %E0%A4%A)
    return json({ error: "Invalid path encoding" }, { status: 400 });
  }

  if (
    path.includes('..') ||          // literal in original
    decodedPath.includes('..') ||   // decoded variant
    path.startsWith('/') ||
    decodedPath.startsWith('/') ||
    path.includes('%2e%2e') ||      // URL-encoded variants
    path.includes('%2E%2E') ||
    path.includes('%2e%2E') ||
    path.includes('%2E%2e')
  ) {
    return json({ error: "Invalid path parameter" }, { status: 400 });
  }

  const preview = await getDataSourcePreview(projectId, { path });
  if (!preview) {
    return json({ error: "Preview not available" }, { status: 404 });
  }

  return json(preview);
}
