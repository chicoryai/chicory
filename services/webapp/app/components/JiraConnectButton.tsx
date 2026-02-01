/**
 * Jira Connect Button Component
 *
 * Handles the OAuth flow for connecting a Jira account.
 * Fetches OAuth config from backend and redirects user to Atlassian.
 */

import { useState, useEffect } from "react";
import {
  CheckCircleIcon,
  ExclamationCircleIcon,
} from "@heroicons/react/24/solid";

interface JiraConnectButtonProps {
  projectId: string;
  onError?: (error: string) => void;
  buttonClassName?: string;
  buttonText?: string;
  scopes?: string[];
}

interface OAuthConfig {
  client_id: string;
  authorization_url: string;
  configured: boolean;
  scopes: string;
}

export function JiraConnectButton({
  projectId,
  onError,
  buttonClassName,
  buttonText = "Connect Jira Account",
}: JiraConnectButtonProps) {
  const [loading, setLoading] = useState(false);
  const [oauthConfig, setOauthConfig] = useState<OAuthConfig | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Fetch OAuth configuration on mount
  useEffect(() => {
    async function fetchOAuthConfig() {
      try {
        // Call webapp's own backend route (not external API)
        const response = await fetch("/api/jira/oauth/config");

        if (!response.ok) {
          throw new Error("Failed to fetch OAuth configuration");
        }

        const config = await response.json();

        if (!config.configured) {
          throw new Error(config.error || "Jira OAuth not configured");
        }

        setOauthConfig(config);
      } catch (err) {
        const errorMessage =
          err instanceof Error
            ? err.message
            : "Failed to load Jira OAuth configuration";
        setError(errorMessage);
        onError?.(errorMessage);
      }
    }

    fetchOAuthConfig();
  }, [onError]);

  const handleConnect = () => {
    if (!oauthConfig) {
      const errorMessage = "OAuth configuration not loaded";
      setError(errorMessage);
      onError?.(errorMessage);
      return;
    }

    setLoading(true);

    try {
      // Build the callback URL (same origin as webapp)
      const callbackUrl = `${window.location.origin}/api/jira/oauth/callback`;

      // Build state parameter with project_id
      const stateParams = new URLSearchParams({
        project_id: projectId,
      });
      const state = stateParams.toString();

      // Build Atlassian OAuth URL
      const authParams = new URLSearchParams({
        audience: "api.atlassian.com",
        client_id: oauthConfig.client_id,
        scope: oauthConfig.scopes,
        redirect_uri: callbackUrl,
        state: state,
        response_type: "code",
        prompt: "consent",
      });

      const authUrl = `${
        oauthConfig.authorization_url
      }?${authParams.toString()}`;

      // Redirect to Atlassian OAuth
      console.log("Redirecting to Atlassian OAuth:", authUrl);
      window.location.href = authUrl;
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to initiate OAuth flow";
      setError(errorMessage);
      onError?.(errorMessage);
      setLoading(false);
    }
  };

  if (error) {
    return (
      <div className="rounded-md bg-red-50 p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <ExclamationCircleIcon
              className="h-5 w-5 text-red-400"
              aria-hidden="true"
            />
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">
              Jira OAuth Error
            </h3>
            <div className="mt-2 text-sm text-red-700">
              <p>{error}</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!oauthConfig) {
    return (
      <div className="animate-pulse">
        <div className="h-10 bg-gray-200 rounded"></div>
      </div>
    );
  }

  const defaultButtonClass =
    "inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed";

  return (
    <button
      type="button"
      onClick={handleConnect}
      disabled={loading}
      className={buttonClassName || defaultButtonClass}
    >
      {loading ? (
        <>
          <svg
            className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            ></circle>
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            ></path>
          </svg>
          Connecting...
        </>
      ) : (
        <>
          <img className="mr-3 h-5 w-5" src="/icons/jira.svg" alt="Jira icon" />
          {buttonText}
        </>
      )}
    </button>
  );
}

/**
 * Jira Connection Status Component
 *
 * Displays the current Jira connection status with site and user info
 */

interface JiraConnectionStatusProps {
  siteName: string;
  displayName: string;
  avatarUrl?: string;
  siteUrl?: string;
  connectedAt?: string;
  onDisconnect?: () => void;
}

export function JiraConnectionStatus({
  siteName,
  displayName,
  avatarUrl,
  siteUrl,
  connectedAt,
  onDisconnect,
}: JiraConnectionStatusProps) {
  return (
    <div className="rounded-md bg-green-50 p-4">
      <div className="flex">
        <div className="flex-shrink-0">
          <CheckCircleIcon
            className="h-5 w-5 text-green-400"
            aria-hidden="true"
          />
        </div>
        <div className="ml-3 flex-1">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {avatarUrl && (
                <img
                  src={avatarUrl}
                  alt={displayName}
                  className="h-8 w-8 rounded-full"
                />
              )}
              <div>
                <h3 className="text-sm font-medium text-green-800">
                  Connected to Jira
                </h3>
                <p className="mt-1 text-sm text-green-700">
                  {displayName} - {siteName}
                </p>
                {siteUrl && (
                  <p className="mt-1 text-xs text-green-600">
                    <a
                      href={siteUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="hover:underline"
                    >
                      {siteUrl}
                    </a>
                  </p>
                )}
                {connectedAt && (
                  <p className="mt-1 text-xs text-green-600">
                    Connected {new Date(connectedAt).toLocaleDateString()}
                  </p>
                )}
              </div>
            </div>
            {onDisconnect && (
              <button
                type="button"
                onClick={onDisconnect}
                className="text-sm font-medium text-green-800 hover:text-green-900"
              >
                Disconnect
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
