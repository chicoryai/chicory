import { initRemixAuth } from '@propelauth/remix'
import { redirect } from '@remix-run/node'
import { getProjectsByOrgId } from '~/services/chicory.server'

export const auth = initRemixAuth({
    authUrl: process.env.REMIX_PUBLIC_AUTH_URL!,
    integrationApiKey: process.env.PROPELAUTH_API_KEY!,
    verifierKey: process.env.PROPELAUTH_VERIFIER_KEY!,
    redirectUri: process.env.PROPELAUTH_REDIRECT_URI!,
})


export const getUserOrgDetails = async (request: Request) => {
    const user = await auth.getUser(request, {});
    if (!user) {
        return redirect("/api/auth/login");
    }
    
    // Get the active org ID, or the first org ID if active is not set
    let orgId = user.activeOrgId;
    
    // If no active org, get the first org from orgIdToUserOrgInfo
    if (!orgId && user.orgIdToUserOrgInfo) {
        const orgIds = Object.keys(user.orgIdToUserOrgInfo);
        if (orgIds.length > 0) {
            orgId = orgIds[0];
        }
    }
    
    // If we have an org ID, fetch its projects
    if (orgId) {
        try {
            const projects = await getProjectsByOrgId(orgId);
            if (projects && projects.length > 0) {
                return {
                    ...user,
                    project: projects[0],
                    orgId
                };
            }

            return {
                ...user,
                orgId
            };
        } catch (error) {
            console.error(`Error fetching projects for org ${orgId}:`, error);
        }
    }
    
    return user;
}
