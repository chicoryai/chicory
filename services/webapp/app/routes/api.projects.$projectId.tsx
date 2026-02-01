import { json } from "@remix-run/node";
import type { ActionFunctionArgs } from "@remix-run/node";
import { auth } from "~/auth/auth.server";
import { updateProject, getProjectById } from "~/services/chicory.server";

export async function action({ request, params }: ActionFunctionArgs) {
  const { projectId } = params;

  if (!projectId) {
    return json({ error: "Project ID is required" }, { status: 400 });
  }

  // Only allow PATCH requests
  if (request.method !== "PATCH") {
    return json({ error: "Method not allowed" }, { status: 405 });
  }

  // Authenticate user
  const user = await auth.getUser(request, {});
  if (!user) {
    return json({ error: "Authentication required" }, { status: 401 });
  }

  try {
    const body = await request.json();
    const { members } = body;

    // Validate members field
    if (!members || !Array.isArray(members)) {
      return json({ error: "Members must be an array" }, { status: 400 });
    }

    if (members.length === 0) {
      return json({ error: "At least one member is required" }, { status: 400 });
    }

    // Validate that all members are valid UUIDs
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    const invalidMembers = members.filter((id: string) => !uuidRegex.test(id));
    if (invalidMembers.length > 0) {
      return json({ error: "All member IDs must be valid UUIDs" }, { status: 400 });
    }

    // Update the project with new members
    const updatedProject = await updateProject(
      projectId,
      undefined, // name
      undefined, // description
      members    // members
    );

    return json({ success: true, project: updatedProject });
  } catch (error) {
    console.error("Error updating project members:", error);
    return json({ error: "Failed to update project members" }, { status: 500 });
  }
}
