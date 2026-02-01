import { json } from "@remix-run/node";
import { BaseActionHandler } from './base';
import { createProjectWithDefaultGateway, updateMcpGateway } from '~/services/chicory.server';
import { createApiKey } from '~/utils/propelauth.server';
import { auth } from '~/auth/auth.server';

export class ProjectHandler extends BaseActionHandler {
  async handle(request: Request): Promise<Response> {
    // Authenticate user
    const user = await auth.getUser(request, {});
    if (!user) {
      return json({ error: "Authentication required" }, { status: 401 });
    }

    const formData = await request.formData();
    const name = formData.get("name") as string;
    const description = formData.get("description") as string;
    const organizationId = formData.get("organizationId") as string;

    if (!name || !organizationId) {
      return json({ error: "Name and organization ID are required" }, { status: 400 });
    }

    try {
      // Create the project with default gateway
      const { project, gateway } = await createProjectWithDefaultGateway({
        name,
        organization_id: organizationId,
        description: description || undefined,
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
}
