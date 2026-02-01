import requests
import logging
from typing import Dict, Optional, List, Any

# Configure logging
logger = logging.getLogger(__name__)


def validate_credentials(access_token: Optional[str] = None) -> Dict[str, Any]:
    """
    Validate GitHub OAuth credentials and repository access

    Supports GitHub App OAuth tokens only.
LegacyPAT(PersonalAccessToken)supporthasbeenremoved.
    Args:
        access_token: GitHub OAuth access token (obtained via OAuth flow
    Returns:
        Dict with status (success/error) and message
    """
    if not access_token:
        logger.error("No GitHub access token provided")
        return {
            "status": "error",
            "message": "GitHub OAuth access token is required. Please connect your GitHub account.",
            "details": None,
        }

    logger.info("Validating GitHub OAuth token")
    headers = {"Authorization": f"token {access_token}"}
    base_url = "https://api.github.com"

    try:
        # Test authentication
        logger.info("Testing GitHub authentication...")
        response = requests.get(f"{base_url}/user", headers=headers)

        if response.status_code != 200:
            logger.error(f"Authentication failed with status {response.status_code}")
            logger.error(f"Response: {response.text}")
            return {
                "status": "error",
                "message": f"GitHub authentication failed: {response.json().get('message', 'Unknown error')}",
                "details": response.json()
                if response.headers.get("content-type", "").startswith(
                    "application/json"
                )
                else None,
            }

        username = response.json().get("login")
        logger.info(f"Authentication successful for user: {username}")

        # Test repository access (limit to 5 for validation)
        logger.info("Testing repository access...")
        repos_response = requests.get(
            f"{base_url}/user/repos", headers=headers, params={"per_page": 5}
        )

        if repos_response.status_code != 200:
            logger.error(
                f"Repository listing failed with status {repos_response.status_code}"
            )
            return {
                "status": "error",
                "message": f"Failed to list repositories: {repos_response.json().get('message', 'Unknown error')}",
                "details": repos_response.json()
                if repos_response.headers.get("content-type", "").startswith(
                    "application/json"
                )
                else None,
            }

        repos = repos_response.json()
        repo_count = len(repos)
        logger.info(f"Successfully accessed {repo_count} repositories")

        # Prepare success response with details
        return {
            "status": "success",
            "message": f"GitHub connection successful for user {username}",
            "details": {
                "username": username,
                "accessible_repos": repo_count,
                "sample_repos": [
                    {
                        "name": repo["name"],
                        "full_name": repo["full_name"],
                        "url": repo["html_url"],
                    }
                    for repo in repos[:5]
                ],
            },
        }

    except Exception as e:
        logger.error(f"GitHub connection error: {str(e)}")
        return {
            "status": "error",
            "message": f"Connection error: {str(e)}",
            "details": None,
        }
