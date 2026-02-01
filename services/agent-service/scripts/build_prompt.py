#!/usr/bin/env python3
"""
Build script to generate and validate the agent system prompt.

This script:
1. Reads the CLAUDE.md template
2. Validates tool names match config
3. Outputs a clean system prompt for debugging/testing
4. Can output in different formats (raw, JSON, escaped)

Usage:
    python scripts/build_prompt.py [--format raw|json|escaped] [--validate] [--output FILE]
"""

import argparse
import json
import re
import sys
from pathlib import Path


# Chicory MCP tool names (must match app/core/config.py)
CHICORY_MCP_TOOLS = [
    # Project management
    "mcp__chicory__chicory_list_projects",
    "mcp__chicory__chicory_get_context",
    # Agent management
    "mcp__chicory__chicory_create_agent",
    "mcp__chicory__chicory_list_agents",
    "mcp__chicory__chicory_get_agent",
    "mcp__chicory__chicory_update_agent",
    "mcp__chicory__chicory_deploy_agent",
    "mcp__chicory__chicory_execute_agent",
    "mcp__chicory__chicory_list_agent_tasks",
    "mcp__chicory__chicory_get_agent_task",
    # Evaluation management
    "mcp__chicory__chicory_create_evaluation",
    "mcp__chicory__chicory_list_evaluations",
    "mcp__chicory__chicory_get_evaluation",
    "mcp__chicory__chicory_execute_evaluation",
    "mcp__chicory__chicory_get_evaluation_result",
    "mcp__chicory__chicory_list_evaluation_runs",
    "mcp__chicory__chicory_add_evaluation_test_cases",
    "mcp__chicory__chicory_delete_evaluation",
    # Data source / Integration management
    "mcp__chicory__chicory_list_data_source_types",
    "mcp__chicory__chicory_list_data_sources",
    "mcp__chicory__chicory_get_data_source",
    "mcp__chicory__chicory_create_data_source",
    "mcp__chicory__chicory_update_data_source",
    "mcp__chicory__chicory_delete_data_source",
    "mcp__chicory__chicory_validate_credentials",
    "mcp__chicory__chicory_test_connection",
    # Folder/File management
    "mcp__chicory__chicory_list_folder_files",
    "mcp__chicory__chicory_get_folder_file",
    "mcp__chicory__chicory_delete_folder_file",
]


def load_claude_md() -> str:
    """Load the CLAUDE.md file content."""
    claude_md_path = Path(__file__).parent.parent / ".claude" / "CLAUDE.md"

    if not claude_md_path.exists():
        print(f"ERROR: CLAUDE.md not found at {claude_md_path}", file=sys.stderr)
        sys.exit(1)

    return claude_md_path.read_text()


def validate_tool_names(content: str) -> list[str]:
    """
    Validate that tool names in CLAUDE.md match the configured tools.

    Returns list of issues found.
    """
    issues = []

    # Check each configured tool is mentioned
    for tool in CHICORY_MCP_TOOLS:
        if tool not in content:
            issues.append(f"WARNING: Configured tool '{tool}' not found in CLAUDE.md")

    # Check for short tool names that might cause issues
    short_names = [
        "chicory_list_projects",
        "chicory_get_context",
        "chicory_create_agent",
        "chicory_list_agents",
        "chicory_get_agent",
        "chicory_update_agent",
        "chicory_deploy_agent",
        "chicory_execute_agent",
        "chicory_list_agent_tasks",
        "chicory_get_agent_task",
        "chicory_create_evaluation",
        "chicory_list_evaluations",
        "chicory_get_evaluation",
        "chicory_execute_evaluation",
        "chicory_get_evaluation_result",
        "chicory_list_evaluation_runs",
        "chicory_add_evaluation_test_cases",
        "chicory_delete_evaluation",
    ]

    for short_name in short_names:
        # Check if short name appears without the mcp__ prefix
        # This is a simple heuristic - look for the short name not preceded by mcp__chicory__
        pattern = rf'(?<!mcp__chicory__){short_name}'
        matches = re.findall(pattern, content)
        if matches:
            issues.append(f"WARNING: Found short tool name '{short_name}' without full prefix")

    return issues


def get_prompt_stats(content: str) -> dict:
    """Get statistics about the prompt."""
    lines = content.split('\n')

    # Count sections
    sections = [l for l in lines if l.startswith('## ')]

    # Count XML tags
    xml_tags = set(re.findall(r'<(\w+)[^>]*>', content))

    # Estimate tokens (rough: ~4 chars per token)
    estimated_tokens = len(content) // 4

    return {
        "characters": len(content),
        "lines": len(lines),
        "sections": len(sections),
        "xml_tags": list(xml_tags),
        "estimated_tokens": estimated_tokens,
        "tools_mentioned": sum(1 for t in CHICORY_MCP_TOOLS if t in content),
        "total_tools_configured": len(CHICORY_MCP_TOOLS),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Build and validate the agent system prompt"
    )
    parser.add_argument(
        "--format",
        choices=["raw", "json", "escaped"],
        default="raw",
        help="Output format (default: raw)"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate tool names and report issues"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show prompt statistics"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file (default: stdout)"
    )

    args = parser.parse_args()

    # Load content
    content = load_claude_md()

    # Validate if requested
    if args.validate:
        print("=" * 60, file=sys.stderr)
        print("VALIDATION RESULTS", file=sys.stderr)
        print("=" * 60, file=sys.stderr)

        issues = validate_tool_names(content)
        if issues:
            for issue in issues:
                print(issue, file=sys.stderr)
            print(f"\nFound {len(issues)} issue(s)", file=sys.stderr)
        else:
            print("All tool names validated successfully!", file=sys.stderr)

        print("=" * 60, file=sys.stderr)
        print(file=sys.stderr)

    # Show stats if requested
    if args.stats:
        stats = get_prompt_stats(content)
        print("=" * 60, file=sys.stderr)
        print("PROMPT STATISTICS", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print(f"Characters: {stats['characters']:,}", file=sys.stderr)
        print(f"Lines: {stats['lines']:,}", file=sys.stderr)
        print(f"Sections: {stats['sections']}", file=sys.stderr)
        print(f"Estimated tokens: ~{stats['estimated_tokens']:,}", file=sys.stderr)
        print(f"Tools mentioned: {stats['tools_mentioned']}/{stats['total_tools_configured']}", file=sys.stderr)
        print(f"XML tags used: {', '.join(sorted(stats['xml_tags']))}", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print(file=sys.stderr)

    # Format output
    if args.format == "json":
        output = json.dumps({
            "system_prompt": content,
            "stats": get_prompt_stats(content),
        }, indent=2)
    elif args.format == "escaped":
        output = content.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    else:
        output = content

    # Write output
    if args.output:
        Path(args.output).write_text(output)
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
