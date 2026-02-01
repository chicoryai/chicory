import { redirect } from "@remix-run/node";
import type { LoaderFunctionArgs } from "@remix-run/node";
import { getUserOrgDetails } from "~/auth/auth.server";

import { getProjectsByOrgId, createProject} from "~/services/chicory.server";


export async function loader({ request }: LoaderFunctionArgs) {
  const userDetails = await getUserOrgDetails(request);

  if (userDetails instanceof Response) {
    return userDetails;
  }

  const orgId = 'orgId' in userDetails ? (userDetails as any).orgId : undefined;

  if (orgId) {
    const projects = await getProjectsByOrgId(orgId);

    if (projects.length > 0) {
      // Check if user is a member of any project
      const isMemberOfAny = projects.some(project =>
        project.members?.includes(userDetails.userId)
      );

      if (!isMemberOfAny) {
        return redirect("/workzone");
      }

      // Find first project user is a member of
      const firstProject = projects.find(project =>
        project.members?.includes(userDetails.userId)
      ) || projects[0];

      return redirect(`/projects/${firstProject.id}/agents`);
    } else {
      // No projects exist, create default project
      try {
        const defaultProject = await createProject({
          name: "Default Project",
          organization_id: orgId,
          description: "Automatically created default project",
          members: [userDetails.userId]
        });
        return redirect(`/projects/${defaultProject.id}/agents`);
      } catch (error) {
        console.error("Error creating default project:", error);
      }
    }
  }

  return redirect("/setup-in-progress");
}
