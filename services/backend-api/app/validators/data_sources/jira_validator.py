import requests
import logging
from typing import Dict, Optional, Any

# Configure logging
logger = logging.getLogger(__name__)


def validate_credentials(access_token: Optional[str] = None, cloud_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Validate Jira OAuth credentials and API access

    Args:
        access_token: Jira OAuth access token (obtained via OAuth flow)
        cloud_id: Jira Cloud instance ID

    Returns:
        Dict with status (success/error) and message
    """
    if not access_token:
        logger.error("No Jira access token provided")
        return {
            "status": "error",
            "message": "Jira OAuth access token is required. Please connect your Jira account.",
            "details": None,
        }

    if not cloud_id:
        logger.error("No Jira cloud_id provided")
        return {
            "status": "error",
            "message": "Jira cloud_id is required.",
            "details": None,
        }

    logger.info(f"Validating Jira OAuth token for cloud_id: {cloud_id}")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    base_url = f"https://api.atlassian.com/ex/jira/{cloud_id}"

    try:
        # Test authentication by getting current user info
        logger.info("Testing Jira authentication...")
        response = requests.get(f"{base_url}/rest/api/3/myself", headers=headers)

        if response.status_code != 200:
            logger.error(f"Authentication failed with status {response.status_code}")
            logger.error(f"Response: {response.text}")
            return {
                "status": "error",
                "message": f"Jira authentication failed: {response.json().get('message', 'Unknown error')}",
                "details": response.json()
                if response.headers.get("content-type", "").startswith(
                    "application/json"
                )
                else None,
            }

        user_info = response.json()
        account_id = user_info.get("accountId")
        display_name = user_info.get("displayName", "Unknown")
        email = user_info.get("emailAddress", "")
        logger.info(f"Authentication successful for user: {display_name} ({account_id})")

        # Test project access (limit to 5 for validation)
        logger.info("Testing Jira project access...")
        projects_response = requests.get(
            f"{base_url}/rest/api/3/project/search",
            headers=headers,
            params={"maxResults": 5}
        )

        if projects_response.status_code != 200:
            logger.error(
                f"Project listing failed with status {projects_response.status_code}"
            )
            return {
                "status": "error",
                "message": f"Failed to list projects: {projects_response.json().get('message', 'Unknown error')}",
                "details": projects_response.json()
                if projects_response.headers.get("content-type", "").startswith(
                    "application/json"
                )
                else None,
            }

        projects_data = projects_response.json()
        projects = projects_data.get("values", [])
        project_count = len(projects)
        logger.info(f"Successfully accessed {project_count} projects")

        # Prepare success response with details
        return {
            "status": "success",
            "message": f"Jira connection successful for user {display_name}",
            "details": {
                "account_id": account_id,
                "display_name": display_name,
                "email": email,
                "accessible_projects": project_count,
                "sample_projects": [
                    {
                        "key": project["key"],
                        "name": project["name"],
                        "id": project["id"],
                    }
                    for project in projects[:5]
                ],
            },
        }

    except Exception as e:
        logger.error(f"Jira connection error: {str(e)}")
        return {
            "status": "error",
            "message": f"Connection error: {str(e)}",
            "details": None,
        }
