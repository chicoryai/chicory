import { useState } from "react";
import { Form, useActionData, useLoaderData } from "@remix-run/react";
import { json, redirect } from "@remix-run/node";
import type { ActionFunctionArgs, LoaderFunctionArgs } from "@remix-run/node";
import { auth } from "~/auth/auth.server";
import { Switch } from "@headlessui/react";
import { ThemeToggle } from "~/components/ThemeToggle";

interface Preferences {
  emailNotifications: boolean;
  desktopNotifications: boolean;
  theme: string;
}

export async function loader({ request }: LoaderFunctionArgs) {
  // Get the authenticated user
  const user = await auth.getUser(request, {});
  
  if (!user) {
    return redirect("/api/auth/login");
  }
  
  // In a real app, you would fetch user preferences from a database
  // For now, we'll use mock data
  const preferences: Preferences = {
    emailNotifications: true,
    desktopNotifications: false,
    theme: "system", // system, light, dark
  };
  
  return json({ user, preferences });
}

type ActionData = 
  | { success: true; message: string; preferences: { emailNotifications: boolean; desktopNotifications: boolean } }
  | { success: false; error: string };

export async function action({ request }: ActionFunctionArgs) {
  const user = await auth.getUser(request, {});
  
  if (!user) {
    return json({ success: false, error: "Unauthorized" } as ActionData, { status: 401 });
  }
  
  const formData = await request.formData();
  const emailNotifications = formData.get("emailNotifications") === "on";
  const desktopNotifications = formData.get("desktopNotifications") === "on";
  
  try {
    // In a real app, you would save these preferences to a database
    // For now, we'll just return success
    
    return json({ 
      success: true, 
      message: "App settings updated successfully",
      preferences: {
        emailNotifications,
        desktopNotifications,
      }
    } as ActionData);
  } catch (error) {
    console.error("Error updating app settings:", error);
    return json({ success: false, error: "Failed to update app settings" } as ActionData, { status: 500 });
  }
}

function classNames(...classes: string[]) {
  return classes.filter(Boolean).join(' ');
}

export default function AppSettings() {
  const { user, preferences } = useLoaderData<typeof loader>();
  const actionData = useActionData<ActionData>();
  
  const [emailNotifications, setEmailNotifications] = useState(
    actionData?.success ? actionData.preferences.emailNotifications : preferences.emailNotifications
  );
  const [desktopNotifications, setDesktopNotifications] = useState(
    actionData?.success ? actionData.preferences.desktopNotifications : preferences.desktopNotifications
  );
  
  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">App Settings</h2>
      
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
      
      <Form method="post" className="space-y-8">
        <div className="bg-gray-50 dark:bg-gray-700/30 rounded-lg p-6">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Appearance</h3>
          
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">Theme</h4>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Choose between light, dark, or system theme
              </p>
            </div>
            <ThemeToggle />
          </div>
        </div>
        
        <div className="bg-gray-50 dark:bg-gray-700/30 rounded-lg p-6">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Notifications</h3>
          
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">Email Notifications</h4>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Receive email notifications for important updates
                </p>
              </div>
              <Switch
                checked={emailNotifications}
                onChange={setEmailNotifications}
                name="emailNotifications"
                className={classNames(
                  emailNotifications ? 'bg-purple-500' : 'bg-gray-200 dark:bg-gray-600',
                  'relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2'
                )}
              >
                <span className="sr-only">Email notifications</span>
                <span
                  aria-hidden="true"
                  className={classNames(
                    emailNotifications ? 'translate-x-5' : 'translate-x-0',
                    'pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out'
                  )}
                />
              </Switch>
            </div>
          </div>
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
    </div>
  );
}
