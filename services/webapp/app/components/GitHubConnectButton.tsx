/**
 * GitHub Connect Button Component
 *
 * Handles the OAuth flow for connecting a GitHub account.
 * Fetches OAuth config from backend and redirects user to GitHub.
 */

import { useState, useEffect } from "react";
import {
  CheckCircleIcon,
  ExclamationCircleIcon,
} from "@heroicons/react/24/solid";

interface GitHubConnectButtonProps {
  projectId: string;
  onError?: (error: string) => void;
  buttonClassName?: string;
  buttonText?: string;
}

interface OAuthConfig {
  client_id: string;
  authorization_url: string;
  configured: boolean;
}

export function GitHubConnectButton({
  projectId,
  onError,
  buttonClassName,
  buttonText = "Connect GitHub Account",
}: GitHubConnectButtonProps) {
  const [loading, setLoading] = useState(false);
  const [oauthConfig, setOauthConfig] = useState<OAuthConfig | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Fetch OAuth configuration on mount
  useEffect(() => {
    async function fetchOAuthConfig() {
      try {
        // Call webapp's own backend route (not external API)
        const response = await fetch("/api/github/oauth/config");

        if (!response.ok) {
          throw new Error("Failed to fetch OAuth configuration");
        }

        const config = await response.json();

        if (!config.configured) {
          throw new Error(config.error || "GitHub OAuth not configured");
        }

        setOauthConfig(config);
      } catch (err) {
        const errorMessage =
          err instanceof Error
            ? err.message
            : "Failed to load GitHub OAuth configuration";
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
      const callbackUrl = `${window.location.origin}/api/github/oauth/callback`;

      // Build state parameter with project_id
      const stateParams = new URLSearchParams({
        project_id: projectId,
      });
      const state = stateParams.toString();

      // Build GitHub App installation URL
      const authParams = new URLSearchParams({
        client_id: oauthConfig.client_id,
        redirect_uri: callbackUrl,
        state: state,
      });

      const authUrl = `${
        oauthConfig.authorization_url
      }?${authParams.toString()}`;

      // Redirect to GitHub App installation
      console.log("Redirecting to GitHub App installation:", authUrl);
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
              GitHub OAuth Error
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
    "inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-gray-900 hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-900 disabled:opacity-50 disabled:cursor-not-allowed";

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
          <svg className="mr-2 h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
          </svg>
          {buttonText}
        </>
      )}
    </button>
  );
}

/**
 * GitHub Connection Status Component
 *
 * Displays the current GitHub connection status with user info
 */

interface GitHubConnectionStatusProps {
  username: string;
  avatarUrl?: string;
  connectedAt?: string;
  onDisconnect?: () => void;
}

export function GitHubConnectionStatus({
  username,
  avatarUrl,
  connectedAt,
  onDisconnect,
}: GitHubConnectionStatusProps) {
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
                  alt={username}
                  className="h-8 w-8 rounded-full"
                />
              )}
              <div>
                <h3 className="text-sm font-medium text-green-800">
                  Connected to GitHub
                </h3>
                <p className="mt-1 text-sm text-green-700">@{username}</p>
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
