import { json } from "@remix-run/node";
import type { ActionFunctionArgs } from "@remix-run/node";
import { auth } from "~/auth/auth.server";
import { createProjectWithDefaultGateway, updateMcpGateway } from "~/services/chicory.server";
import { createApiKey } from "~/utils/propelauth.server";

export async function action({ request }: ActionFunctionArgs) {
  // Only allow POST requests
  if (request.method !== "POST") {
    return json({ error: "Method not allowed" }, { status: 405 });
  }

  // Authenticate user
  const user = await auth.getUser(request, {});
  if (!user) {
    return json({ error: "Authentication required" }, { status: 401 });
  }

  try {
    const formData = await request.formData();
    const name = formData.get("name") as string;
    const description = formData.get("description") as string;
    const organizationId = formData.get("organizationId") as string;
    const membersJson = formData.get("members") as string;

    // Validate required fields
    if (!name || !organizationId) {
      return json({ error: "Name and organization ID are required" }, { status: 400 });
    }

    // Parse members array
    let members: string[] = [];
    if (membersJson) {
      try {
        members = JSON.parse(membersJson);
        if (!Array.isArray(members)) {
          return json({ error: "Members must be an array" }, { status: 400 });
        }
      } catch (e) {
        return json({ error: "Invalid members format" }, { status: 400 });
      }
    }

    // Validate that members is not empty (required by backend)
    if (members.length === 0) {
      return json({ error: "At least one member is required" }, { status: 400 });
    }

    // Create the project with default gateway
    const { project, gateway } = await createProjectWithDefaultGateway({
      name,
      organization_id: organizationId,
      description: description || undefined,
      members,
    });

    // If gateway was created, generate API key for it
    if (gateway) {
      try {
        const { apiKeyToken } = await createApiKey(
          organizationId, // Use org ID as we have it
          gateway.id,
          'gateway'
        );
        
        // Update gateway with API key
        await updateMcpGateway(project.id, gateway.id, {
          api_key: apiKeyToken
        });
      } catch (error) {
        console.error("Error generating API key for default gateway:", error);
        // Continue even if API key generation fails
      }
    }

    return json({ success: true, project });
  } catch (error) {
    console.error("Error creating project:", error);
    return json({ error: "Failed to create project" }, { status: 500 });
  }
}
