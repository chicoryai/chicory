"""
Jira provider for issue tracking and project management operations.
"""

import logging
import aiohttp
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, timezone
from dateutil import parser
import json

from providers.base import ToolsProvider

logger = logging.getLogger(__name__)


class JiraProvider(ToolsProvider):
    """
    Jira provider for issue tracking and project management using Jira Cloud REST API.
    Supports OAuth 2.0 authentication with token refresh.
    """

    def __init__(self):
        super().__init__()
        self.base_url: Optional[str] = None
        self.cloud_id: Optional[str] = None
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.account_id: Optional[str] = None
        self.expires_at: Optional[datetime] = None
        self.session: Optional[aiohttp.ClientSession] = None

    async def _initialize_client(self) -> None:
        """Initialize Jira API client with OAuth 2.0 credentials."""
        if not self.credentials:
            raise ValueError("No credentials provided")

        # Extract Jira connection parameters
        self.cloud_id = self.credentials.get("cloud_id")
        self.access_token = self.credentials.get("access_token")
        self.refresh_token = self.credentials.get("refresh_token")
        self.account_id = self.credentials.get("account_id")

        site_url = self.credentials.get("site_url")
        expires_in = self.credentials.get("expires_in", 3600)
        created_at = self.credentials.get("created_at")

        # Validate required parameters
        if not all([self.cloud_id, self.access_token, site_url]):
            raise ValueError("Missing required Jira credentials: cloud_id, access_token, site_url")

        # Set base URL for Jira Cloud API
        self.base_url = f"https://api.atlassian.com/ex/jira/{self.cloud_id}"

        # Calculate token expiration time
        # If we have created_at timestamp, calculate from token issue time
        # Otherwise fall back to calculating from now (less accurate)
        if created_at:
            try:
                # Parse ISO format timestamp from backend
                token_issued_at = parser.isoparse(created_at)
                self.expires_at = token_issued_at + timedelta(seconds=expires_in)
                logger.info(f"Token issued at {token_issued_at}, expires at {self.expires_at}")
            except Exception as e:
                logger.warning(f"Failed to parse created_at timestamp '{created_at}': {e}. Using current time instead.")
                self.expires_at = datetime.now() + timedelta(seconds=expires_in)
        else:
            logger.warning("No created_at timestamp available, calculating expiration from current time (may be inaccurate)")
            self.expires_at = datetime.now() + timedelta(seconds=expires_in)

        # Create HTTP session
        self.session = aiohttp.ClientSession()

        logger.info("Jira provider initialized successfully for cloud_id: %s", self.cloud_id)

    async def _ensure_token_valid(self) -> None:
        """Ensure access token is valid, refresh if expired."""
        if not self.expires_at:
            logger.warning("No expiration time set for access token")
            return

        # Get current time in UTC (timezone-aware)
        now = datetime.now(timezone.utc)

        # Make expires_at timezone-aware if it isn't already
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if now >= expires_at:
            logger.info(f"Access token expired (now: {now}, expires: {expires_at}), refreshing...")
            await self._refresh_access_token()
        else:
            time_remaining = expires_at - now
            logger.debug(f"Access token valid for {time_remaining.total_seconds():.0f} more seconds")

    async def _refresh_access_token(self) -> None:
        """
        Refresh the OAuth access token using refresh token.
        Note: This requires OAuth client credentials which may not be available.
        For now, we'll log a warning. In production, this should call the backend API
        to handle token refresh.
        """
        logger.warning("Token refresh not yet implemented. Access token may be expired.")
        # TODO: Implement token refresh by calling backend API endpoint
        # The backend should handle the OAuth refresh flow and update the data source
        # Example: PUT /projects/{project_id}/data-sources/{data_source_id}/refresh

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make authenticated request to Jira API."""
        self._ensure_initialized()
        await self._ensure_token_valid()

        url = f"{self.base_url}/rest/api/3/{endpoint.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        try:
            async with self.session.request(method, url, headers=headers, **kwargs) as response:
                if response.status == 401:
                    # Token might be expired, try refreshing once
                    await self._refresh_access_token()
                    headers["Authorization"] = f"Bearer {self.access_token}"
                    async with self.session.request(method, url, headers=headers, **kwargs) as retry_response:
                        return await self._handle_response(retry_response)

                return await self._handle_response(response)

        except Exception as e:
            logger.error(f"Jira API request failed: {e}", exc_info=True)
            return {"error": str(e)}

    async def _handle_response(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        """Handle API response and return JSON or error."""
        if response.status in [200, 201, 204]:
            if response.status == 204:
                return {"success": True}
            try:
                return await response.json()
            except:
                text = await response.text()
                return {"result": text} if text else {"success": True}
        else:
            error_text = await response.text()
            return {"error": f"HTTP {response.status}: {error_text}"}

    async def cleanup(self) -> None:
        """Clean up provider resources."""
        if self.session:
            await self.session.close()
        await super().cleanup()

    # =============================================================================
    # ISSUE OPERATIONS
    # =============================================================================

    async def search_issues(self, jql: str, max_results: int = 50, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Search for issues using JQL (Jira Query Language).

        Args:
            jql: JQL query string
            max_results: Maximum number of results to return
            fields: List of fields to return (default: all)

        Returns:
            Dictionary with search results
        """
        self._log_operation("search_issues", jql=jql, max_results=max_results)

        params = {
            "jql": jql,
            "maxResults": max_results
        }

        if fields:
            params["fields"] = ",".join(fields)

        result = await self._make_request("GET", "/search", params=params)
        return result

    async def get_issue(self, issue_key: str, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get details of a specific issue.

        Args:
            issue_key: Issue key (e.g., "PROJ-123")
            fields: List of fields to return (default: all)

        Returns:
            Dictionary with issue details
        """
        self._log_operation("get_issue", issue_key=issue_key)

        params = {}
        if fields:
            params["fields"] = ",".join(fields)

        result = await self._make_request("GET", f"/issue/{issue_key}", params=params)
        return result

    async def create_issue(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new issue.

        Args:
            fields: Dictionary of issue fields

        Returns:
            Dictionary with created issue details
        """
        self._log_operation("create_issue", fields=fields)

        payload = {"fields": fields}
        result = await self._make_request("POST", "/issue", json=payload)
        return result

    async def update_issue(self, issue_key: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing issue.

        Args:
            issue_key: Issue key (e.g., "PROJ-123")
            fields: Dictionary of fields to update

        Returns:
            Success or error message
        """
        self._log_operation("update_issue", issue_key=issue_key, fields=fields)

        payload = {"fields": fields}
        result = await self._make_request("PUT", f"/issue/{issue_key}", json=payload)
        return result

    async def transition_issue(self, issue_key: str, transition_id: str, fields: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Transition an issue to a new status.

        Args:
            issue_key: Issue key (e.g., "PROJ-123")
            transition_id: ID of the transition to perform
            fields: Optional fields to update during transition

        Returns:
            Success or error message
        """
        self._log_operation("transition_issue", issue_key=issue_key, transition_id=transition_id)

        payload = {"transition": {"id": transition_id}}
        if fields:
            payload["fields"] = fields

        result = await self._make_request("POST", f"/issue/{issue_key}/transitions", json=payload)
        return result

    async def get_transitions(self, issue_key: str) -> Dict[str, Any]:
        """
        Get available transitions for an issue.

        Args:
            issue_key: Issue key (e.g., "PROJ-123")

        Returns:
            Dictionary with available transitions
        """
        self._log_operation("get_transitions", issue_key=issue_key)

        result = await self._make_request("GET", f"/issue/{issue_key}/transitions")
        return result

    async def assign_issue(self, issue_key: str, account_id: str) -> Dict[str, Any]:
        """
        Assign an issue to a user.

        Args:
            issue_key: Issue key (e.g., "PROJ-123")
            account_id: Atlassian account ID of the user

        Returns:
            Success or error message
        """
        self._log_operation("assign_issue", issue_key=issue_key, account_id=account_id)

        payload = {"accountId": account_id}
        result = await self._make_request("PUT", f"/issue/{issue_key}/assignee", json=payload)
        return result

    # =============================================================================
    # PROJECT OPERATIONS
    # =============================================================================

    async def list_projects(self) -> Dict[str, Any]:
        """
        List all projects accessible to the user.

        Returns:
            List of projects
        """
        self._log_operation("list_projects")

        result = await self._make_request("GET", "/project")

        # If error, return it directly (don't wrap)
        if isinstance(result, dict) and "error" in result:
            return result

        # Otherwise, wrap the list in projects key
        return {"projects": result if isinstance(result, list) else []}

    async def get_project(self, project_key: str) -> Dict[str, Any]:
        """
        Get details of a specific project.

        Args:
            project_key: Project key (e.g., "PROJ")

        Returns:
            Dictionary with project details
        """
        self._log_operation("get_project", project_key=project_key)

        result = await self._make_request("GET", f"/project/{project_key}")
        return result

    async def get_issue_types(self, project_key: str) -> Dict[str, Any]:
        """
        Get issue types for a project.

        Args:
            project_key: Project key (e.g., "PROJ")

        Returns:
            List of issue types
        """
        self._log_operation("get_issue_types", project_key=project_key)

        result = await self._make_request("GET", f"/project/{project_key}")
        if "error" not in result:
            return {"issueTypes": result.get("issueTypes", [])}
        return result

    async def get_fields(self) -> Dict[str, Any]:
        """
        Get all fields (system and custom).

        Returns:
            List of fields
        """
        self._log_operation("get_fields")

        result = await self._make_request("GET", "/field")
        return {"fields": result if isinstance(result, list) else result}

    # =============================================================================
    # COMMENT OPERATIONS
    # =============================================================================

    async def add_comment(self, issue_key: str, body: str) -> Dict[str, Any]:
        """
        Add a comment to an issue.

        Args:
            issue_key: Issue key (e.g., "PROJ-123")
            body: Comment text

        Returns:
            Dictionary with created comment details
        """
        self._log_operation("add_comment", issue_key=issue_key)

        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": body
                            }
                        ]
                    }
                ]
            }
        }

        result = await self._make_request("POST", f"/issue/{issue_key}/comment", json=payload)
        return result

    async def get_comments(self, issue_key: str) -> Dict[str, Any]:
        """
        Get all comments for an issue.

        Args:
            issue_key: Issue key (e.g., "PROJ-123")

        Returns:
            Dictionary with comments
        """
        self._log_operation("get_comments", issue_key=issue_key)

        result = await self._make_request("GET", f"/issue/{issue_key}/comment")
        return result

    # =============================================================================
    # ATTACHMENT OPERATIONS
    # =============================================================================

    async def upload_attachment(self, issue_key: str, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Upload an attachment to an issue.

        Args:
            issue_key: Issue key (e.g., "PROJ-123")
            file_content: File content as bytes
            filename: Name of the file

        Returns:
            Dictionary with attachment details
        """
        self._log_operation("upload_attachment", issue_key=issue_key, filename=filename)

        # For attachments, we need different headers
        await self._ensure_token_valid()

        url = f"{self.base_url}/rest/api/3/issue/{issue_key}/attachments"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-Atlassian-Token": "no-check"
        }

        # Create form data
        data = aiohttp.FormData()
        data.add_field('file', file_content, filename=filename)

        try:
            async with self.session.post(url, headers=headers, data=data) as response:
                return await self._handle_response(response)
        except Exception as e:
            logger.error(f"Failed to upload attachment: {e}")
            return {"error": str(e)}

    # =============================================================================
    # AGILE/BOARD OPERATIONS
    # =============================================================================

    async def list_boards(self, project_key: Optional[str] = None) -> Dict[str, Any]:
        """
        List all boards, optionally filtered by project.

        Args:
            project_key: Optional project key to filter boards

        Returns:
            Dictionary with boards
        """
        self._log_operation("list_boards", project_key=project_key)

        # Note: Boards use agile API endpoint
        endpoint = "/board"
        params = {}
        if project_key:
            params["projectKeyOrId"] = project_key

        # Agile API is at /rest/agile/1.0, not /rest/api/3
        url = f"{self.base_url}/rest/agile/1.0{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"
        }

        try:
            async with self.session.get(url, headers=headers, params=params) as response:
                return await self._handle_response(response)
        except Exception as e:
            logger.error(f"Failed to list boards: {e}")
            return {"error": str(e)}

    async def list_sprints(self, board_id: int) -> Dict[str, Any]:
        """
        List all sprints for a board.

        Args:
            board_id: Board ID

        Returns:
            Dictionary with sprints
        """
        self._log_operation("list_sprints", board_id=board_id)

        url = f"{self.base_url}/rest/agile/1.0/board/{board_id}/sprint"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"
        }

        try:
            async with self.session.get(url, headers=headers) as response:
                return await self._handle_response(response)
        except Exception as e:
            logger.error(f"Failed to list sprints: {e}")
            return {"error": str(e)}

    async def get_sprint(self, sprint_id: int) -> Dict[str, Any]:
        """
        Get details of a specific sprint.

        Args:
            sprint_id: Sprint ID

        Returns:
            Dictionary with sprint details
        """
        self._log_operation("get_sprint", sprint_id=sprint_id)

        url = f"{self.base_url}/rest/agile/1.0/sprint/{sprint_id}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"
        }

        try:
            async with self.session.get(url, headers=headers) as response:
                return await self._handle_response(response)
        except Exception as e:
            logger.error(f"Failed to get sprint: {e}")
            return {"error": str(e)}

    async def get_backlog(self, board_id: int, max_results: int = 50) -> Dict[str, Any]:
        """
        Get backlog issues for a board.

        Args:
            board_id: Board ID
            max_results: Maximum number of results

        Returns:
            Dictionary with backlog issues
        """
        self._log_operation("get_backlog", board_id=board_id)

        url = f"{self.base_url}/rest/agile/1.0/board/{board_id}/backlog"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"
        }
        params = {"maxResults": max_results}

        try:
            async with self.session.get(url, headers=headers, params=params) as response:
                return await self._handle_response(response)
        except Exception as e:
            logger.error(f"Failed to get backlog: {e}")
            return {"error": str(e)}
