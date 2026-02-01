import { json } from "@remix-run/node";
import type { LoaderFunctionArgs } from "@remix-run/node";
import { getUserOrgDetails } from "~/auth/auth.server";
import { getAgentVersions, getAgentVersion } from "~/services/chicory.server";
import { fetchUserData } from "~/utils/propelauth.server";

/**
 * Loader for agent version history
 * Uses chicory.server.ts service functions for consistent API access
 */
export async function loader({ request, params }: LoaderFunctionArgs) {
  try {
    const { projectId, agentId } = params;

    if (!projectId || !agentId) {
      return json({ error: "Project ID and Agent ID are required" }, { status: 400 });
    }

    // Authenticate user
    const userDetails = await getUserOrgDetails(request);
    if (userDetails instanceof Response) {
      return userDetails;
    }

    // Get version index from URL if provided
    const url = new URL(request.url);
    const versionIndex = url.searchParams.get("index");

    // Get specific version or all versions
    if (versionIndex !== null) {
      const index = parseInt(versionIndex, 10);
      if (isNaN(index) || index < 0 || index > 29) {
        return json({ error: "Invalid version index (must be 0-29)" }, { status: 400 });
      }
      const version = await getAgentVersion(projectId, agentId, index);
      
      // Hydrate user data if updated_by exists
      // Backend returns 'updated_by' (user ID), we hydrate it to 'updated_by_name' for display
      if (version.updated_by) {
        try {
          const userData = await fetchUserData(version.updated_by, false);
          return json({
            ...version,
            updated_by_name: userData ? `${userData.firstName || ''} ${userData.lastName || ''}`.trim() || userData.email : null
          });
        } catch (error) {
          console.error("Error fetching user data:", error);
          // Return version without user name if fetch fails
        }
      }
      
      return json(version);
    } else {
      const versionsData = await getAgentVersions(projectId, agentId);
      
      // Hydrate user data for all versions
      // Backend returns 'updated_by' (user ID), we hydrate it to 'updated_by_name' for display
      const hydratedVersions = await Promise.all(
        versionsData.versions.map(async (version) => {
          if (version.updated_by) {
            try {
              const userData = await fetchUserData(version.updated_by, false);
              return {
                ...version,
                updated_by_name: userData ? `${userData.firstName || ''} ${userData.lastName || ''}`.trim() || userData.email : null
              };
            } catch (error) {
              console.error("Error fetching user data for version:", error);
              return version;
            }
          }
          return version;
        })
      );
      
      return json({
        versions: hydratedVersions,
        total_count: versionsData.total_count
      });
    }
  } catch (error) {
    console.error("Error fetching version history:", error);
    return json(
      { error: error instanceof Error ? error.message : "Failed to fetch version history" },
      { status: 500 }
    );
  }
}
