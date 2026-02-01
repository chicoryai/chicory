import { useState } from "react";
import { Form, useActionData, useLoaderData } from "@remix-run/react";
import { redirect, json } from "@remix-run/node";
import type { ActionFunctionArgs, LoaderFunctionArgs } from "@remix-run/node";
import { auth, getUserOrgDetails } from "~/auth/auth.server";
import { UserCircleIcon } from "@heroicons/react/24/outline";

// Define the user type to match PropelAuth's structure
interface User {
  userId: string;
  email: string;
  firstName?: string;
  lastName?: string;
  pictureUrl?: string;
  // Add other properties as needed
  project?: {
    id: string;
    name: string;
  };
}

export async function loader({ request }: LoaderFunctionArgs) {
  // Get the authenticated user
  const userDetails = await getUserOrgDetails(request);
  if (!userDetails) {
    return redirect("/api/auth/login");
  }
  
  return json({ user: userDetails as User });
}

type ActionData = 
  | { success: true; message: string }
  | { success: false; error: string };

export async function action({ request }: ActionFunctionArgs) {
  const user = await auth.getUser(request, {});
  
  if (!user) {
    return json({ success: false, error: "Unauthorized" } as ActionData);
  }
  
  const formData = await request.formData();
  const firstName = formData.get("firstName") as string;
  const lastName = formData.get("lastName") as string;
  
  try {
    // Use PropelAuth's backend API to update the user's profile
    const updated = await auth.api.updateUserMetadata(
      user.userId,
      {
        firstName,
        lastName,
      }
    );
    if (updated) {
      return json({ success: true, message: "Profile updated successfully" } as ActionData);
    } else {
      return json({ success: false, error: "Failed to update profile" } as ActionData);
    }
  } catch (error) {
    console.error("Error updating profile:", error);
    return json({ success: false, error: "Failed to update profile" } as ActionData);
  }
}

export default function ProfileSettings() {
  const { user } = useLoaderData<typeof loader>();
  const actionData = useActionData<ActionData>();
  const [isEditing, setIsEditing] = useState(false);
  
  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Profile Settings</h2>
        <button
          type="button"
          onClick={() => setIsEditing(!isEditing)}
          className="px-4 py-2 text-sm font-medium text-white bg-purple-500 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
        >
          {isEditing ? "Cancel" : "Edit Profile"}
        </button>
      </div>
      
      {actionData?.success && (
        <div className="mb-4 p-4 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 rounded-md">
          {actionData.message}
        </div>
      )}
      
      {actionData?.success === false && actionData.error && (
        <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded-md">
          {actionData.error}
        </div>
      )}
      
      <div className="bg-whitePurple-100 dark:bg-gray-700/30 rounded-lg p-6 mb-6">
        {isEditing ? (
          <Form method="post" className="space-y-4">
            <div>
              <label htmlFor="firstName" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                First Name
              </label>
              <input
                type="text"
                id="firstName"
                name="firstName"
                defaultValue={user.firstName || ""}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-800 dark:text-white sm:text-sm"
              />
            </div>
            
            <div>
              <label htmlFor="lastName" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Last Name
              </label>
              <input
                type="text"
                id="lastName"
                name="lastName"
                defaultValue={user.lastName || ""}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-800 dark:text-white sm:text-sm"
              />
            </div>
            
            <div className="flex justify-end">
              <button
                type="submit"
                className="px-4 py-2 text-sm font-medium text-white bg-purple-500 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
              >
                Save Changes
              </button>
            </div>
          </Form>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-center mb-6">
              {user.pictureUrl ? (
                <img 
                  src={user.pictureUrl} 
                  alt={`${user.firstName || ''} ${user.lastName || ''}`}
                  className="h-24 w-24 rounded-full object-cover" 
                />
              ) : (
                <div className="h-24 w-24 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center">
                  <UserCircleIcon className="h-16 w-16 text-gray-400 dark:text-gray-500" />
                </div>
              )}
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">First Name</h3>
                <p className="mt-1 text-sm text-gray-900 dark:text-white">{user.firstName || "Not set"}</p>
              </div>
              
              <div>
                <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Last Name</h3>
                <p className="mt-1 text-sm text-gray-900 dark:text-white">{user.lastName || "Not set"}</p>
              </div>
              
              <div>
                <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Email</h3>
                <p className="mt-1 text-sm text-gray-900 dark:text-white">{user.email}</p>
              </div>
              
              <div>
                <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">User ID</h3>
                <p className="mt-1 text-sm text-gray-900 dark:text-white">{user.userId}</p>
              </div>
            </div>
          </div>
        )}
      </div>
      
      <div className="mt-6">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-3">Account Management</h3>
        <div className="space-y-3">
          <a 
            href="/api/auth/change-password" 
            className="block text-sm text-indigo-600 dark:text-indigo-400 hover:text-indigo-500 dark:hover:text-indigo-300"
          >
            Change Password
          </a>
          
          <a 
            href="/api/auth/manage-account" 
            className="block text-sm text-indigo-600 dark:text-indigo-400 hover:text-indigo-500 dark:hover:text-indigo-300"
          >
            Manage Account
          </a>
        </div>
      </div>
    </div>
  );
}
