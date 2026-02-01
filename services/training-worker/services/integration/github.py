import os
import requests

from git import Repo
from services.utils.logger import logger


def get_repositories(github_access_token, github_base_url="https://api.github.com"):
    """
    Fetch repositories using either GitHub App installation or PAT token.
    
    Priority:
    1. Try GitHub App installation (returns only user-selected repos)
    2. Fallback to PAT token (returns all accessible repos)
    """
    headers = {
        "Authorization": f"token {github_access_token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    # First, test the token by getting user info
    user_response = requests.get(f"{github_base_url}/user", headers=headers)
    if user_response.status_code != 200:
        logger.error(f"Token validation failed: {user_response.status_code} - {user_response.text}")
        raise Exception(f"Invalid GitHub token or API access denied: {user_response.status_code}")

    user_info = user_response.json()
    logger.info(f"Authenticated as: {user_info.get('login', 'Unknown')}")

    # Try to get GitHub App installation first
    logger.info("Checking for GitHub App installation...")
    installations_response = requests.get(
        f"{github_base_url}/user/installations",
        headers=headers
    )
    
    # Check if this is a GitHub App token with installations
    if installations_response.status_code == 200:
        installations_data = installations_response.json()
        installations = installations_data.get("installations", [])
        
        if installations:
            # GitHub App flow - fetch only selected repositories
            logger.info(f"GitHub App installation found. Using installation-based repository access.")
            return _get_repositories_from_installation(github_access_token, github_base_url, headers, installations)
    
    # Fallback to PAT token flow
    logger.info("No GitHub App installation found. Using Personal Access Token (PAT) flow.")
    logger.info("This will fetch all repositories the token has access to.")
    return _get_repositories_from_pat(github_access_token, github_base_url, headers)


def _get_repositories_from_installation(github_access_token, github_base_url, headers, installations):
    """
    Fetch repositories from GitHub App installation (only user-selected repos)
    """
    # Use the first installation (typically there's only one for a user)
    installation_id = installations[0]["id"]
    logger.info(f"Using installation ID: {installation_id}")

    repos = []
    page = 1
    
    logger.info("Fetching repositories from GitHub App installation (user-selected repos only)...")
    
    while True:
        params = {
            "page": page,
            "per_page": 100
        }

        # Use installation repositories endpoint - this ONLY returns selected repos
        response = requests.get(
            f"{github_base_url}/user/installations/{installation_id}/repositories",
            headers=headers,
            params=params
        )

        if response.status_code == 200:
            data = response.json()
            repositories = data.get("repositories", [])
            
            if not repositories:
                break
                
            repos.extend(repositories)
            logger.info(f"Retrieved {len(repositories)} selected repos from page {page}")
            page += 1
        else:
            logger.error(f"Failed to fetch installation repositories: {response.status_code} - {response.text}")
            break

    if not repos:
        logger.warning("No repositories found in installation. User may not have selected any repos.")

    # Log repository visibility breakdown
    public_count = sum(1 for repo in repos if not repo.get('private', False))
    private_count = sum(1 for repo in repos if repo.get('private', False))
    logger.info(f"Found {len(repos)} selected repositories: {public_count} public, {private_count} private")

    return repos


def _get_repositories_from_pat(github_access_token, github_base_url, headers):
    """
    Fetch all repositories accessible via Personal Access Token (PAT)
    This includes public and private repos based on token permissions
    """
    repos = []
    page = 1

    # Try different endpoints to get all repositories
    endpoints_to_try = [
        f"{github_base_url}/user/repos",  # User's repositories
    ]

    for endpoint in endpoints_to_try:
        logger.info(f"Trying PAT endpoint: {endpoint}")
        page = 1
        repos_from_endpoint = []

        while True:
            # Include parameters to get both public and private repos
            params = {
                "page": page,
                "per_page": 100,
                "visibility": "private",
                "affiliation": "owner,collaborator,organization_member"
            }

            response = requests.get(endpoint, headers=headers, params=params)

            if response.status_code == 200:
                data = response.json()
                if not data:
                    break
                repos_from_endpoint.extend(data)
                logger.info(f"Retrieved {len(data)} repos from page {page}")
                page += 1
            else:
                logger.warning(f"Failed to fetch from {endpoint}: {response.status_code} - {response.text}")
                break

        if repos_from_endpoint:
            repos = repos_from_endpoint
            logger.info(f"Successfully retrieved {len(repos)} repositories from {endpoint}")
            break

    if not repos:
        logger.error("No repositories found. Check token permissions.")

    # Log repository visibility breakdown
    public_count = sum(1 for repo in repos if not repo.get('private', False))
    private_count = sum(1 for repo in repos if repo.get('private', False))
    logger.info(f"Found {len(repos)} total repositories via PAT: {public_count} public, {private_count} private")

    return repos


def test_token_permissions(github_access_token, github_base_url="https://api.github.com"):
    """
    Test what permissions the GitHub App OAuth token has
    """
    headers = {
        "Authorization": f"token {github_access_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Check token scopes
    response = requests.get(f"{github_base_url}/user", headers=headers)
    if response.status_code == 200:
        scopes = response.headers.get('X-OAuth-Scopes', 'No scopes found')
        logger.info(f"Token scopes: {scopes}")

        # For fine-grained tokens, check rate limit info which includes token type
        rate_limit_response = requests.get(f"{github_base_url}/rate_limit", headers=headers)
        if rate_limit_response.status_code == 200:
            rate_info = rate_limit_response.json()
            logger.info(f"Rate limit info: {rate_info}")
    else:
        logger.error(f"Token test failed: {response.status_code} - {response.text}")


def clone_repo(repo_url, repo_name, clone_dir, github_username, github_access_token):
    """
    Clone a repository with proper authentication.
    Supports both GitHub App OAuth tokens and Personal Access Tokens (PAT).
    """
    repo_path = os.path.join(clone_dir, repo_name)

    # For both GitHub App OAuth tokens and PAT tokens, use username:token authentication
    # For fine-grained PATs, you can use the token as username
    # For classic PATs and OAuth tokens, use username:token
    authenticated_repo_url = repo_url.replace(
        "https://",
        f"https://{github_username}:{github_access_token}@"
    )

    if not os.path.exists(repo_path):
        logger.info(f"Cloning {repo_name}...")
        try:
            Repo.clone_from(authenticated_repo_url, repo_path)
            logger.info(f"Successfully cloned {repo_name}")
        except Exception as e:
            logger.error(f"Failed to clone {repo_name}: {str(e)}")
            raise
    else:
        logger.info(f"{repo_name} already exists. Skipping...")

