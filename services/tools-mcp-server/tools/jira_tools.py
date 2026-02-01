"""
Jira tools for issue tracking and project management operations.
"""

import logging
from typing import Any, Dict, List, Optional
import json

logger = logging.getLogger(__name__)


async def jira_search_issues_tool(project_id: str, jql: str, max_results: int = 50) -> str:
    """
    Search for issues using JQL (Jira Query Language).

    Args:
        project_id: Project ID for credential lookup
        jql: JQL query string (e.g., "project = DEMO AND status = 'In Progress'")
        max_results: Maximum number of results to return (default: 50)

    Returns:
        Formatted string with search results
    """
    # Import here to avoid circular dependency
    from server import get_provider

    try:
        provider = await get_provider(project_id, "jira")
        if not provider:
            return "Error: Could not get Jira provider for project"

        result = await provider.search_issues(jql, max_results)

        if "error" in result:
            return f"Error searching issues: {result['error']}"

        issues = result.get('issues', [])
        total = result.get('total', 0)

        output = f"Jira Issues (Total: {total}, Showing: {len(issues)})\n\n"

        if issues:
            for issue in issues:
                key = issue.get('key', 'Unknown')
                fields = issue.get('fields', {})
                summary = fields.get('summary', 'No summary')
                status = fields.get('status', {}).get('name', 'Unknown')
                issue_type = fields.get('issuetype', {}).get('name', 'Unknown')
                assignee = fields.get('assignee', {})
                assignee_name = assignee.get('displayName', 'Unassigned') if assignee else 'Unassigned'

                output += f"[{key}] {summary}\n"
                output += f"  Type: {issue_type} | Status: {status} | Assignee: {assignee_name}\n\n"
        else:
            output += "No issues found matching the query.\n"

        return output

    except Exception as e:
        logger.error(f"Error in jira_search_issues_tool: {e}")
        return f"Error: {str(e)}"


async def jira_get_issue_tool(project_id: str, issue_key: str) -> str:
    """
    Get details of a specific Jira issue.

    Args:
        project_id: Project ID for credential lookup
        issue_key: Issue key (e.g., "PROJ-123")

    Returns:
        Formatted string with issue details
    """
    from server import get_provider

    try:
        provider = await get_provider(project_id, "jira")
        if not provider:
            return "Error: Could not get Jira provider for project"

        result = await provider.get_issue(issue_key)

        if "error" in result:
            return f"Error getting issue: {result['error']}"

        key = result.get('key', 'Unknown')
        fields = result.get('fields', {})

        summary = fields.get('summary', 'No summary')
        description_content = fields.get('description', {})
        # Try to extract text from Atlassian Document Format
        description = "No description"
        if description_content and isinstance(description_content, dict):
            content = description_content.get('content', [])
            if content:
                # Simple extraction - just get text from first paragraph
                for item in content:
                    if item.get('type') == 'paragraph':
                        texts = [c.get('text', '') for c in item.get('content', []) if c.get('type') == 'text']
                        if texts:
                            description = ' '.join(texts)
                            break

        status = fields.get('status', {}).get('name', 'Unknown')
        issue_type = fields.get('issuetype', {}).get('name', 'Unknown')
        priority = fields.get('priority', {}).get('name', 'None')

        assignee = fields.get('assignee', {})
        assignee_name = assignee.get('displayName', 'Unassigned') if assignee else 'Unassigned'

        reporter = fields.get('reporter', {})
        reporter_name = reporter.get('displayName', 'Unknown') if reporter else 'Unknown'

        created = fields.get('created', 'Unknown')
        updated = fields.get('updated', 'Unknown')

        output = f"Issue: {key}\n"
        output += f"{'='*60}\n\n"
        output += f"Summary: {summary}\n"
        output += f"Type: {issue_type}\n"
        output += f"Status: {status}\n"
        output += f"Priority: {priority}\n"
        output += f"Assignee: {assignee_name}\n"
        output += f"Reporter: {reporter_name}\n"
        output += f"Created: {created}\n"
        output += f"Updated: {updated}\n\n"
        output += f"Description:\n{description}\n"

        return output

    except Exception as e:
        logger.error(f"Error in jira_get_issue_tool: {e}")
        return f"Error: {str(e)}"


async def jira_create_issue_tool(
    project_id: str,
    project_key: str,
    summary: str,
    issue_type: str,
    description: Optional[str] = None,
    priority: Optional[str] = None,
    assignee_account_id: Optional[str] = None
) -> str:
    """
    Create a new Jira issue.

    Args:
        project_id: Project ID for credential lookup
        project_key: Jira project key (e.g., "PROJ")
        summary: Issue summary/title
        issue_type: Issue type (e.g., "Task", "Bug", "Story")
        description: Optional issue description
        priority: Optional priority (e.g., "High", "Medium", "Low")
        assignee_account_id: Optional Atlassian account ID to assign

    Returns:
        Formatted string with created issue details
    """
    from server import get_provider

    try:
        provider = await get_provider(project_id, "jira")
        if not provider:
            return "Error: Could not get Jira provider for project"

        fields = {
            "project": {"key": project_key},
            "summary": summary,
            "issuetype": {"name": issue_type}
        }

        if description:
            fields["description"] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": description
                            }
                        ]
                    }
                ]
            }

        if priority:
            fields["priority"] = {"name": priority}

        if assignee_account_id:
            fields["assignee"] = {"accountId": assignee_account_id}

        result = await provider.create_issue(fields)

        if "error" in result:
            return f"Error creating issue: {result['error']}"

        key = result.get('key', 'Unknown')
        issue_id = result.get('id', 'Unknown')
        self_url = result.get('self', '')

        output = f"Issue created successfully!\n\n"
        output += f"Key: {key}\n"
        output += f"ID: {issue_id}\n"
        output += f"Summary: {summary}\n"
        output += f"Type: {issue_type}\n"

        return output

    except Exception as e:
        logger.error(f"Error in jira_create_issue_tool: {e}")
        return f"Error: {str(e)}"


async def jira_update_issue_tool(project_id: str, issue_key: str, fields: Dict[str, Any]) -> str:
    """
    Update an existing Jira issue.

    Args:
        project_id: Project ID for credential lookup
        issue_key: Issue key (e.g., "PROJ-123")
        fields: Dictionary of fields to update (e.g., {"summary": "New summary"})

    Returns:
        Success or error message
    """
    from server import get_provider

    try:
        provider = await get_provider(project_id, "jira")
        if not provider:
            return "Error: Could not get Jira provider for project"

        result = await provider.update_issue(issue_key, fields)

        if "error" in result:
            return f"Error updating issue: {result['error']}"

        return f"Issue {issue_key} updated successfully."

    except Exception as e:
        logger.error(f"Error in jira_update_issue_tool: {e}")
        return f"Error: {str(e)}"


async def jira_transition_issue_tool(project_id: str, issue_key: str, transition_id: str) -> str:
    """
    Transition a Jira issue to a new status.

    Args:
        project_id: Project ID for credential lookup
        issue_key: Issue key (e.g., "PROJ-123")
        transition_id: ID of the transition to perform

    Returns:
        Success or error message
    """
    from server import get_provider

    try:
        provider = await get_provider(project_id, "jira")
        if not provider:
            return "Error: Could not get Jira provider for project"

        result = await provider.transition_issue(issue_key, transition_id)

        if "error" in result:
            return f"Error transitioning issue: {result['error']}"

        return f"Issue {issue_key} transitioned successfully."

    except Exception as e:
        logger.error(f"Error in jira_transition_issue_tool: {e}")
        return f"Error: {str(e)}"


async def jira_get_transitions_tool(project_id: str, issue_key: str) -> str:
    """
    Get available transitions for a Jira issue.

    Args:
        project_id: Project ID for credential lookup
        issue_key: Issue key (e.g., "PROJ-123")

    Returns:
        Formatted string with available transitions
    """
    from server import get_provider

    try:
        provider = await get_provider(project_id, "jira")
        if not provider:
            return "Error: Could not get Jira provider for project"

        result = await provider.get_transitions(issue_key)

        if "error" in result:
            return f"Error getting transitions: {result['error']}"

        transitions = result.get('transitions', [])

        output = f"Available Transitions for {issue_key}:\n\n"

        if transitions:
            for transition in transitions:
                trans_id = transition.get('id', 'Unknown')
                name = transition.get('name', 'Unknown')
                to_status = transition.get('to', {}).get('name', 'Unknown')
                output += f"[{trans_id}] {name} → {to_status}\n"
        else:
            output += "No transitions available.\n"

        return output

    except Exception as e:
        logger.error(f"Error in jira_get_transitions_tool: {e}")
        return f"Error: {str(e)}"


async def jira_assign_issue_tool(project_id: str, issue_key: str, account_id: str) -> str:
    """
    Assign a Jira issue to a user.

    Args:
        project_id: Project ID for credential lookup
        issue_key: Issue key (e.g., "PROJ-123")
        account_id: Atlassian account ID of the user

    Returns:
        Success or error message
    """
    from server import get_provider

    try:
        provider = await get_provider(project_id, "jira")
        if not provider:
            return "Error: Could not get Jira provider for project"

        result = await provider.assign_issue(issue_key, account_id)

        if "error" in result:
            return f"Error assigning issue: {result['error']}"

        return f"Issue {issue_key} assigned successfully."

    except Exception as e:
        logger.error(f"Error in jira_assign_issue_tool: {e}")
        return f"Error: {str(e)}"


async def jira_list_projects_tool(project_id: str) -> str:
    """
    List all Jira projects accessible to the user.

    Args:
        project_id: Project ID for credential lookup

    Returns:
        Formatted string with list of projects
    """
    from server import get_provider

    try:
        provider = await get_provider(project_id, "jira")
        if not provider:
            return "Error: Could not get Jira provider for project"

        result = await provider.list_projects()

        if "error" in result:
            return f"Error listing projects: {result['error']}"

        projects = result.get('projects', [])

        output = f"Jira Projects ({len(projects)} found):\n\n"

        if projects:
            for proj in projects:
                key = proj.get('key', 'Unknown')
                name = proj.get('name', 'Unknown')
                proj_type = proj.get('projectTypeKey', 'Unknown')
                lead = proj.get('lead', {})
                lead_name = lead.get('displayName', 'Unknown') if lead else 'Unknown'

                output += f"[{key}] {name}\n"
                output += f"  Type: {proj_type} | Lead: {lead_name}\n\n"
        else:
            output += "No projects found.\n"

        return output

    except Exception as e:
        logger.error(f"Error in jira_list_projects_tool: {e}")
        return f"Error: {str(e)}"


async def jira_get_project_tool(project_id: str, project_key: str) -> str:
    """
    Get details of a specific Jira project.

    Args:
        project_id: Project ID for credential lookup
        project_key: Project key (e.g., "PROJ")

    Returns:
        Formatted string with project details
    """
    from server import get_provider

    try:
        provider = await get_provider(project_id, "jira")
        if not provider:
            return "Error: Could not get Jira provider for project"

        result = await provider.get_project(project_key)

        if "error" in result:
            return f"Error getting project: {result['error']}"

        key = result.get('key', 'Unknown')
        name = result.get('name', 'Unknown')
        description = result.get('description', 'No description')
        proj_type = result.get('projectTypeKey', 'Unknown')

        lead = result.get('lead', {})
        lead_name = lead.get('displayName', 'Unknown') if lead else 'Unknown'

        issue_types = result.get('issueTypes', [])

        output = f"Project: {key} - {name}\n"
        output += f"{'='*60}\n\n"
        output += f"Description: {description}\n"
        output += f"Type: {proj_type}\n"
        output += f"Lead: {lead_name}\n\n"
        output += f"Issue Types ({len(issue_types)}):\n"
        for it in issue_types:
            output += f"  - {it.get('name', 'Unknown')}\n"

        return output

    except Exception as e:
        logger.error(f"Error in jira_get_project_tool: {e}")
        return f"Error: {str(e)}"


async def jira_get_issue_types_tool(project_id: str, project_key: str) -> str:
    """
    Get issue types for a Jira project.

    Args:
        project_id: Project ID for credential lookup
        project_key: Project key (e.g., "PROJ")

    Returns:
        Formatted string with issue types
    """
    from server import get_provider

    try:
        provider = await get_provider(project_id, "jira")
        if not provider:
            return "Error: Could not get Jira provider for project"

        result = await provider.get_issue_types(project_key)

        if "error" in result:
            return f"Error getting issue types: {result['error']}"

        issue_types = result.get('issueTypes', [])

        output = f"Issue Types for {project_key} ({len(issue_types)} found):\n\n"

        if issue_types:
            for it in issue_types:
                name = it.get('name', 'Unknown')
                description = it.get('description', 'No description')
                subtask = it.get('subtask', False)
                output += f"- {name}"
                if subtask:
                    output += " (Subtask)"
                output += f"\n  {description}\n\n"
        else:
            output += "No issue types found.\n"

        return output

    except Exception as e:
        logger.error(f"Error in jira_get_issue_types_tool: {e}")
        return f"Error: {str(e)}"


async def jira_get_fields_tool(project_id: str) -> str:
    """
    Get all fields (system and custom) in Jira.

    Args:
        project_id: Project ID for credential lookup

    Returns:
        Formatted string with fields
    """
    from server import get_provider

    try:
        provider = await get_provider(project_id, "jira")
        if not provider:
            return "Error: Could not get Jira provider for project"

        result = await provider.get_fields()

        if "error" in result:
            return f"Error getting fields: {result['error']}"

        fields = result.get('fields', [])

        output = f"Jira Fields ({len(fields)} found):\n\n"

        system_fields = [f for f in fields if not f.get('custom', False)]
        custom_fields = [f for f in fields if f.get('custom', False)]

        output += f"System Fields ({len(system_fields)}):\n"
        for field in system_fields[:20]:  # Limit to first 20
            field_id = field.get('id', 'Unknown')
            name = field.get('name', 'Unknown')
            output += f"  {field_id}: {name}\n"

        output += f"\nCustom Fields ({len(custom_fields)}):\n"
        for field in custom_fields[:20]:  # Limit to first 20
            field_id = field.get('id', 'Unknown')
            name = field.get('name', 'Unknown')
            output += f"  {field_id}: {name}\n"

        return output

    except Exception as e:
        logger.error(f"Error in jira_get_fields_tool: {e}")
        return f"Error: {str(e)}"


async def jira_add_comment_tool(project_id: str, issue_key: str, comment: str) -> str:
    """
    Add a comment to a Jira issue.

    Args:
        project_id: Project ID for credential lookup
        issue_key: Issue key (e.g., "PROJ-123")
        comment: Comment text

    Returns:
        Success or error message
    """
    from server import get_provider

    try:
        provider = await get_provider(project_id, "jira")
        if not provider:
            return "Error: Could not get Jira provider for project"

        result = await provider.add_comment(issue_key, comment)

        if "error" in result:
            return f"Error adding comment: {result['error']}"

        comment_id = result.get('id', 'Unknown')
        return f"Comment added successfully to {issue_key} (ID: {comment_id})."

    except Exception as e:
        logger.error(f"Error in jira_add_comment_tool: {e}")
        return f"Error: {str(e)}"


async def jira_get_comments_tool(project_id: str, issue_key: str) -> str:
    """
    Get all comments for a Jira issue.

    Args:
        project_id: Project ID for credential lookup
        issue_key: Issue key (e.g., "PROJ-123")

    Returns:
        Formatted string with comments
    """
    from server import get_provider

    try:
        provider = await get_provider(project_id, "jira")
        if not provider:
            return "Error: Could not get Jira provider for project"

        result = await provider.get_comments(issue_key)

        if "error" in result:
            return f"Error getting comments: {result['error']}"

        comments = result.get('comments', [])
        total = result.get('total', 0)

        output = f"Comments for {issue_key} ({total} total):\n\n"

        if comments:
            for comment in comments:
                author = comment.get('author', {})
                author_name = author.get('displayName', 'Unknown') if author else 'Unknown'
                created = comment.get('created', 'Unknown')

                # Extract text from Atlassian Document Format
                body = comment.get('body', {})
                comment_text = "No text"
                if body and isinstance(body, dict):
                    content = body.get('content', [])
                    texts = []
                    for item in content:
                        if item.get('type') == 'paragraph':
                            para_texts = [c.get('text', '') for c in item.get('content', []) if c.get('type') == 'text']
                            texts.extend(para_texts)
                    if texts:
                        comment_text = ' '.join(texts)

                output += f"{author_name} ({created}):\n"
                output += f"{comment_text}\n\n"
        else:
            output += "No comments found.\n"

        return output

    except Exception as e:
        logger.error(f"Error in jira_get_comments_tool: {e}")
        return f"Error: {str(e)}"


async def jira_upload_attachment_tool(project_id: str, issue_key: str, file_content: str, filename: str) -> str:
    """
    Upload an attachment to a Jira issue.

    Args:
        project_id: Project ID for credential lookup
        issue_key: Issue key (e.g., "PROJ-123")
        file_content: File content as base64 string or text
        filename: Name of the file

    Returns:
        Success or error message
    """
    from server import get_provider
    import base64

    try:
        provider = await get_provider(project_id, "jira")
        if not provider:
            return "Error: Could not get Jira provider for project"

        # Try to decode if it's base64, otherwise use as bytes
        try:
            file_bytes = base64.b64decode(file_content)
        except:
            file_bytes = file_content.encode('utf-8')

        result = await provider.upload_attachment(issue_key, file_bytes, filename)

        if "error" in result:
            return f"Error uploading attachment: {result['error']}"

        return f"Attachment '{filename}' uploaded successfully to {issue_key}."

    except Exception as e:
        logger.error(f"Error in jira_upload_attachment_tool: {e}")
        return f"Error: {str(e)}"


async def jira_list_boards_tool(project_id: str, project_key: Optional[str] = None) -> str:
    """
    List all Jira boards, optionally filtered by project.

    Args:
        project_id: Project ID for credential lookup
        project_key: Optional project key to filter boards

    Returns:
        Formatted string with boards
    """
    from server import get_provider

    try:
        provider = await get_provider(project_id, "jira")
        if not provider:
            return "Error: Could not get Jira provider for project"

        result = await provider.list_boards(project_key)

        if "error" in result:
            return f"Error listing boards: {result['error']}"

        boards = result.get('values', [])
        total = result.get('total', 0)

        filter_msg = f" for project {project_key}" if project_key else ""
        output = f"Jira Boards{filter_msg} ({total} found):\n\n"

        if boards:
            for board in boards:
                board_id = board.get('id', 'Unknown')
                name = board.get('name', 'Unknown')
                board_type = board.get('type', 'Unknown')
                output += f"[{board_id}] {name} ({board_type})\n"
        else:
            output += "No boards found.\n"

        return output

    except Exception as e:
        logger.error(f"Error in jira_list_boards_tool: {e}")
        return f"Error: {str(e)}"


async def jira_list_sprints_tool(project_id: str, board_id: int) -> str:
    """
    List all sprints for a Jira board.

    Args:
        project_id: Project ID for credential lookup
        board_id: Board ID

    Returns:
        Formatted string with sprints
    """
    from server import get_provider

    try:
        provider = await get_provider(project_id, "jira")
        if not provider:
            return "Error: Could not get Jira provider for project"

        result = await provider.list_sprints(board_id)

        if "error" in result:
            return f"Error listing sprints: {result['error']}"

        sprints = result.get('values', [])
        total = result.get('total', 0)

        output = f"Sprints for Board {board_id} ({total} found):\n\n"

        if sprints:
            for sprint in sprints:
                sprint_id = sprint.get('id', 'Unknown')
                name = sprint.get('name', 'Unknown')
                state = sprint.get('state', 'Unknown')
                start_date = sprint.get('startDate', 'Not set')
                end_date = sprint.get('endDate', 'Not set')

                output += f"[{sprint_id}] {name} - {state}\n"
                output += f"  Start: {start_date} | End: {end_date}\n\n"
        else:
            output += "No sprints found.\n"

        return output

    except Exception as e:
        logger.error(f"Error in jira_list_sprints_tool: {e}")
        return f"Error: {str(e)}"


async def jira_get_sprint_tool(project_id: str, sprint_id: int) -> str:
    """
    Get details of a specific Jira sprint.

    Args:
        project_id: Project ID for credential lookup
        sprint_id: Sprint ID

    Returns:
        Formatted string with sprint details
    """
    from server import get_provider

    try:
        provider = await get_provider(project_id, "jira")
        if not provider:
            return "Error: Could not get Jira provider for project"

        result = await provider.get_sprint(sprint_id)

        if "error" in result:
            return f"Error getting sprint: {result['error']}"

        sprint_id = result.get('id', 'Unknown')
        name = result.get('name', 'Unknown')
        state = result.get('state', 'Unknown')
        start_date = result.get('startDate', 'Not set')
        end_date = result.get('endDate', 'Not set')
        complete_date = result.get('completeDate', 'Not completed')
        goal = result.get('goal', 'No goal set')

        output = f"Sprint: {name} ({sprint_id})\n"
        output += f"{'='*60}\n\n"
        output += f"State: {state}\n"
        output += f"Start Date: {start_date}\n"
        output += f"End Date: {end_date}\n"
        output += f"Complete Date: {complete_date}\n"
        output += f"Goal: {goal}\n"

        return output

    except Exception as e:
        logger.error(f"Error in jira_get_sprint_tool: {e}")
        return f"Error: {str(e)}"


async def jira_get_backlog_tool(project_id: str, board_id: int, max_results: int = 50) -> str:
    """
    Get backlog issues for a Jira board.

    Args:
        project_id: Project ID for credential lookup
        board_id: Board ID
        max_results: Maximum number of results (default: 50)

    Returns:
        Formatted string with backlog issues
    """
    from server import get_provider

    try:
        provider = await get_provider(project_id, "jira")
        if not provider:
            return "Error: Could not get Jira provider for project"

        result = await provider.get_backlog(board_id, max_results)

        if "error" in result:
            return f"Error getting backlog: {result['error']}"

        issues = result.get('issues', [])
        total = result.get('total', 0)

        output = f"Backlog for Board {board_id} (Total: {total}, Showing: {len(issues)}):\n\n"

        if issues:
            for issue in issues:
                key = issue.get('key', 'Unknown')
                fields = issue.get('fields', {})
                summary = fields.get('summary', 'No summary')
                issue_type = fields.get('issuetype', {}).get('name', 'Unknown')
                priority = fields.get('priority', {}).get('name', 'None')

                output += f"[{key}] {summary}\n"
                output += f"  Type: {issue_type} | Priority: {priority}\n\n"
        else:
            output += "No backlog issues found.\n"

        return output

    except Exception as e:
        logger.error(f"Error in jira_get_backlog_tool: {e}")
        return f"Error: {str(e)}"


__all__ = [
    "jira_search_issues_tool",
    "jira_get_issue_tool",
    "jira_create_issue_tool",
    "jira_update_issue_tool",
    "jira_transition_issue_tool",
    "jira_get_transitions_tool",
    "jira_assign_issue_tool",
    "jira_list_projects_tool",
    "jira_get_project_tool",
    "jira_get_issue_types_tool",
    "jira_get_fields_tool",
    "jira_add_comment_tool",
    "jira_get_comments_tool",
    "jira_upload_attachment_tool",
    "jira_list_boards_tool",
    "jira_list_sprints_tool",
    "jira_get_sprint_tool",
    "jira_get_backlog_tool"
]
