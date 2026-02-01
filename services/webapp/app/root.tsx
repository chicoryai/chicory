import {
  Links,
  Meta,
  Outlet,
  Scripts,
  ScrollRestoration,
  useLoaderData,
  useRouteError,
  isRouteErrorResponse,
} from "@remix-run/react";
import type { LinksFunction, LoaderFunctionArgs } from "@remix-run/node";
import { json } from "@remix-run/node";
import { RevalidateSession } from "@propelauth/remix/client";

import { ThemeProvider } from "~/contexts/theme-context";
import { getTheme } from "~/utils/theme.server";
import "./tailwind.css";

export const links: LinksFunction = () => [
  { rel: "preconnect", href: "https://fonts.googleapis.com" },
  {
    rel: "preconnect",
    href: "https://fonts.gstatic.com",
    crossOrigin: "anonymous",
  },
  {
    rel: "stylesheet",
    href: "https://fonts.googleapis.com/css2?family=Outfit:wght@100..900&display=swap",
  },
  {
    rel: "stylesheet",
    href: "https://fonts.googleapis.com/css2?family=Sora:wght@100..800&display=swap",
  },
  {
    rel: "stylesheet",
    href: "https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,200..800;1,200..800&display=swap",
  },
];

export async function loader({ request }: LoaderFunctionArgs) {
  const theme = await getTheme(request);
  return json({ theme });
}

type LoaderData = {
  theme: string | null;
};

export function Layout({ children }: { children: React.ReactNode }) {
  // Don't use useLoaderData in Layout - it's called for both success and error cases
  // The theme will be handled by the App component for success cases

  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <Meta />
        <Links />
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                // On page load or when changing themes, best to add inline in \`head\` to avoid FOUC
                if (localStorage.theme === 'dark' || (!localStorage.theme && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
                  document.documentElement.classList.add('dark');
                } else {
                  document.documentElement.classList.remove('dark');
                }
              })();
            `,
          }}
        />
      </head>
      <body>
        {children}
        <ScrollRestoration />
        <Scripts />
        <RevalidateSession />
      </body>
    </html>
  );
}

export default function App() {
  const data = useLoaderData<typeof loader>();
  const theme = data?.theme || null;

  return (
    <ThemeProvider specifiedTheme={theme}>
      <Outlet />
    </ThemeProvider>
  );
}

export function ErrorBoundary() {
  const error = useRouteError();

  // Handle 404s for Chrome DevTools and other tools
  if (isRouteErrorResponse(error) && error.status === 404) {
    // Silently ignore certain 404s that are expected
    const ignoredPaths = [
      '.well-known',
      'favicon.ico',
      'robots.txt',
      'sitemap.xml'
    ];

    if (error.data && typeof error.data === 'string' &&
      ignoredPaths.some(path => error.data.includes(path))) {
      // Return minimal response for ignored paths
      return <div />;
    }

    // Show proper 404 page for other routes
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="text-center max-w-md">
          <h1 className="text-6xl font-display font-bold text-gray-900 dark:text-white mb-4">404</h1>
          <p className="text-xl font-body text-gray-600 dark:text-gray-400 mb-6">
            Page not found
          </p>
          <a
            href="/"
            className="inline-flex items-center px-4 py-2 bg-purple-400 hover:bg-purple-500 text-white font-ui font-semibold rounded-lg transition-colors duration-200"
          >
            Return to Dashboard
          </a>
        </div>
      </div>
    );
  }

  // Check if it's a network error
  const isNetworkError = error instanceof Error &&
    (error.message.includes('fetch') ||
      error.message.includes('network') ||
      error.message.includes('Failed to fetch') ||
      error.message.toLowerCase().includes('connection'));

  // Handle network errors specifically
  if (isNetworkError) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50 dark:bg-gray-900 p-4">
        <div className="relative overflow-hidden rounded-lg p-6 max-w-md w-full border border-red-200 dark:border-red-700 bg-red-50 dark:bg-red-900/20 shadow-md">
          <div className="relative z-10">
            {/* Icon */}
            <div className="flex justify-center mb-4">
              <div className="rounded-full bg-red-100 dark:bg-red-900/40 p-3">
                <svg
                  className="w-8 h-8 text-red-600 dark:text-red-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M18.364 5.636a9 9 0 010 12.728m0 0l-2.829-2.829m2.829 2.829L21 21M15.536 8.464a5 5 0 010 7.072m0 0l-2.829-2.829m-4.243 2.829a4.978 4.978 0 01-1.414-2.83m-1.414 5.658a9 9 0 01-2.167-9.238m7.824 2.167a1 1 0 111.414 1.414m-1.414-1.414L3 3m8.293 8.293l1.414 1.414"
                  />
                </svg>
              </div>
            </div>

            {/* Title */}
            <h3 className="text-lg font-ui font-semibold text-red-900 dark:text-red-100 text-center mb-2">
              Connection Error
            </h3>

            {/* Message */}
            <p className="text-sm font-body text-red-700 dark:text-red-300 text-center mb-6">
              Unable to connect to the server. Please check your internet connection and try again.
            </p>

            {/* Retry Button */}
            <div className="flex justify-center">
              <button
                onClick={() => window.location.reload()}
                className="px-6 py-2 bg-purple-400 hover:bg-purple-500 text-white font-ui font-semibold rounded-lg transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-purple-400 focus:ring-offset-2"
              >
                Retry
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Handle other errors
  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="text-center max-w-md">
        <h1 className="text-2xl font-display font-bold text-gray-900 dark:text-white mb-4">
          Oops! Something went wrong
        </h1>
        <p className="font-body text-gray-600 dark:text-gray-400 mb-6">
          {error instanceof Error ? error.message : "An unexpected error occurred"}
        </p>
        <button
          onClick={() => window.location.reload()}
          className="inline-flex items-center px-4 py-2 bg-purple-400 hover:bg-purple-500 text-white font-ui font-semibold rounded-lg transition-colors duration-200"
        >
          Try Again
        </button>
      </div>
    </div>
  );
}
