import { auth } from "~/auth/auth.server";
import { initBaseAuth } from "@propelauth/node";

// Initialize the PropelAuth Node.js API client
const propelAuth = initBaseAuth({
  authUrl: process.env.REMIX_PUBLIC_AUTH_URL || "",
  apiKey: process.env.PROPELAUTH_API_KEY || "",
});

export async function createOrganization(name: string, userId: string) {
  try {
    console.log('Creating organization with name:', name);
    console.log('API URL:', process.env.REMIX_PUBLIC_AUTH_URL);
    console.log('API Key available:', !!process.env.PROPELAUTH_API_KEY);
    
    // Use the PropelAuth Node.js library to create an organization
    const result = await propelAuth.createOrg({
      name
    });
    
    console.log('Organization created successfully:', result);
    
    // Add the user to the organization as an Owner
    try {
      console.log('Adding user to the newly created organization:', userId, result.orgId);
      await propelAuth.addUserToOrg({
        userId,
        orgId: result.orgId,
        role: "Owner"
      });
      console.log('User added to organization successfully');
    } catch (addError) {
      console.error("Error adding user to organization:", addError);
      // We don't throw here as the org was already created successfully
    }
    
    return result;
  } catch (error) {
    console.error("Error creating organization:", error);
    throw error;
  }
}

// For testing - this version just logs but doesn't make the API call
export async function createOrganizationTest(name: string, userId: string) {
  try {
    console.log('TEST MODE: Would create organization with name:', name);
    console.log('API URL:', process.env.REMIX_PUBLIC_AUTH_URL);
    console.log('API Key available:', !!process.env.PROPELAUTH_API_KEY);
    
    // Return a mock successful response
    return {
      orgId: "test-org-id-" + Date.now(),
      name: name
    };
  } catch (error) {
    console.error("Test error:", error);
    throw error;
  }
}

export async function addUserToOrg(userId: string, orgId: string, role: string = "Owner"): Promise<any> {
  try {
    console.log('Adding user to organization:', userId, orgId, role);
    
    // Use the PropelAuth Node.js library to add a user to an organization
    const result = await propelAuth.addUserToOrg({
      userId,
      orgId,
      role
    });
    
    console.log('User added to organization successfully:', result);
    return result;
  } catch (error) {
    console.error("Error adding user to organization:", error);
    throw error;
  }
}

/**
 * Update a user's metadata using the PropelAuth Node.js library
 * @param userId The ID of the user to update
 * @param metadata The metadata to update (firstName, lastName, etc.)
 * @returns A boolean indicating whether the update was successful
 */
/**
 * Create an API key for an organization
 * @param orgId The ID of the organization to create an API key for
 * @param resourceId The ID of the resource (agent or gateway) to associate with this API key
 * @param resourceType The type of resource ('agent' or 'gateway'), defaults to 'agent' for backward compatibility
 * @param expiresAtSeconds Optional expiration time in seconds (default: never expires)
 * @returns The created API key information
 */
export async function createApiKey(
  orgId: string,
  resourceId: string,
  resourceType: 'agent' | 'gateway' = 'agent',
  expiresAtSeconds?: number
): Promise<{ apiKeyId: string; apiKeyToken: string }> {
  try {
    console.log(`Creating API key for organization: ${orgId}, ${resourceType}: ${resourceId}`);
    
    // Build metadata based on resource type
    const metadata: Record<string, any> = {
      created_at: new Date().toISOString()
    };
    
    if (resourceType === 'agent') {
      metadata.agent_id = resourceId;
    } else if (resourceType === 'gateway') {
      metadata.gateway_id = resourceId;
    }
    
    // Use the PropelAuth Node.js library to create an API key
    const result = await propelAuth.createApiKey({
      orgId,
      expiresAtSeconds: expiresAtSeconds,
      metadata
    });
    
    console.log('API key created successfully');
    
    return {
      apiKeyId: result.apiKeyId,
      apiKeyToken: result.apiKeyToken
    };
  } catch (error) {
    console.error("Error creating API key:", error);
    throw error;
  }
}

export async function updateUserMetadata(
  userId: string, 
  metadata: {
    firstName?: string;
    lastName?: string;
    pictureUrl?: string;
    username?: string;
    properties?: Record<string, any>;
    updatePasswordRequired?: boolean;
    legacyUserId?: string;
  }
): Promise<boolean> {
  try {
    console.log('Updating user metadata for user:', userId);
    
    // Based on the PropelAuth documentation, we need to use updateUserMetadata
    await propelAuth.updateUserMetadata(userId, metadata);
    
    console.log('User metadata updated successfully');
    return true;
  } catch (error) {
    console.error("Error updating user metadata:", error);
    throw error;
  }
}

/**
 * Fetch complete user data including profile information from PropelAuth
 * @param userId The ID of the user to fetch
 * @param includeOrgs Whether to include organization information (default: true)
 * @returns The complete user data or null if not found
 */
export async function fetchUserData(userId: string, includeOrgs: boolean = true) {
  try {
    console.log('Fetching user data for user:', userId);
    
    // Use the PropelAuth Node.js library to fetch user metadata
    const userData = await propelAuth.fetchUserMetadataByUserId(userId, includeOrgs);
    
    console.log('User data fetched successfully');
    return userData;
  } catch (error) {
    console.error("Error fetching user data:", error);
    throw error;
  }
}

/**
 * Invite a user to an organization using the PropelAuth Node.js library
 * @param email The email of the user to invite
 * @param orgId The ID of the organization to invite the user to
 * @param role The role to assign to the user in the organization
 * @returns A boolean indicating whether the invitation was successful
 */
export async function inviteUserToOrg(
  email: string, 
  orgId: string, 
  role: string
): Promise<boolean> {
  try {
    console.log('Inviting user to organization:', email, orgId, role);
    
    // Use the PropelAuth Node.js library to invite a user to an organization
    await propelAuth.inviteUserToOrg({
      email,
      orgId,
      role
    });
    
    console.log('User invitation sent successfully');
    return true;
  } catch (error) {
    console.error("Error inviting user to organization:", error);
    throw error;
  }
}

/**
 * Fetch users in an organization from PropelAuth
 * @param orgId The ID of the organization to fetch users for
 * @param pageSize The number of users to return per page (default: 100)
 * @param pageNumber The page number to return (default: 0)
 * @returns The users in the organization
 */
export async function fetchUsersInOrg(
  orgId: string,
  pageSize: number = 100,
  pageNumber: number = 0
) {
  try {
    console.log('Fetching users in organization:', orgId);
    
    // Use the PropelAuth Node.js library to fetch users in an organization
    const result = await propelAuth.fetchUsersInOrg({
      orgId,
      pageSize,
      pageNumber
    });
    
    console.log('Users fetched successfully');
    return result;
  } catch (error) {
    console.error("Error fetching users in organization:", error);
    throw error;
  }
}

/**
 * Fetch organization details from PropelAuth
 * @param orgId The ID of the organization to fetch
 * @returns The organization details
 */
export async function fetchOrgDetails(orgId: string) {
  try {
    console.log('Fetching organization details:', orgId);
    
    // Use the PropelAuth Node.js library to fetch organization details
    const result = await propelAuth.fetchOrg(orgId);
    
    console.log('Organization details fetched successfully');
    return result;
  } catch (error) {
    console.error("Error fetching organization details:", error);
    throw error;
  }
}

/**
 * Validate an API key from an Authorization header
 * @param request The request object containing the Authorization header
 * @returns The validated user and organization details or null if invalid
 */
export async function validateApiKeyFromRequest(request: Request) {
  try {
    // Extract the Authorization header
    const authHeader = request.headers.get('Authorization');

    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      console.log('Missing or invalid Authorization header');
      return null;
    }

    // Extract the API key from the Authorization header
    const apiKey = authHeader.substring(7); // Remove 'Bearer ' prefix

    if (!apiKey) {
      console.log('Empty API key');
      return null;
    }

    // Validate the API key using PropelAuth
    const validationResult = await propelAuth.validateApiKey(apiKey);

    // Return the validation result which includes user and org information
    return validationResult;
  } catch (error) {
    console.error('Error validating API key:', error);
    return null;
  }
}

/**
 * Change a user's role in an organization
 * @param userId The ID of the user whose role should be changed
 * @param orgId The ID of the organization
 * @param newRole The new role to assign (Owner, Admin, or Member)
 * @returns A boolean indicating whether the role change was successful
 */
export async function changeUserRoleInOrg(
  userId: string,
  orgId: string,
  newRole: string
): Promise<boolean> {
  try {
    console.log('Changing user role in organization:', userId, orgId, newRole);

    // Use the PropelAuth Node.js library to change the user's role
    await propelAuth.changeUserRoleInOrg({
      userId,
      orgId,
      role: newRole
    });

    console.log('User role updated successfully');
    return true;
  } catch (error) {
    console.error("Error changing user role in organization:", error);
    throw error;
  }
}

/**
 * Remove a user from an organization
 * @param userId The ID of the user to remove
 * @param orgId The ID of the organization
 * @returns A boolean indicating whether the removal was successful
 */
export async function removeUserFromOrg(
  userId: string,
  orgId: string
): Promise<boolean> {
  try {
    console.log('Removing user from organization:', userId, orgId);

    // Use the PropelAuth Node.js library to remove the user from the organization
    await propelAuth.removeUserFromOrg({
      userId,
      orgId
    });

    console.log('User removed from organization successfully');
    return true;
  } catch (error) {
    console.error("Error removing user from organization:", error);
    throw error;
  }
}