"""
Workspace management for agent conversations.

Handles working directory setup, .claude folder structure,
and cleanup for isolated agent workspaces.
"""
import json
import shutil
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Path to the source .claude directory with CLAUDE.md and skills
SOURCE_CLAUDE_DIR = Path(__file__).parent.parent.parent / ".claude"
SOURCE_SKILLS_DIR = SOURCE_CLAUDE_DIR / "skills"


@dataclass
class WorkspaceConfig:
    """Configuration for an agent workspace."""
    working_directory: str
    claude_directory: str
    skills_directory: str
    output_directory: str


class WorkspaceManager:
    """
    Manages working directories and .claude folder setup for agent conversations.

    Creates isolated workspaces per project/conversation with:
    - Working directory for agent operations
    - .claude/ folder with CLAUDE.md, settings.json
    - skills/ directory for skill definitions
    - output/ directory for generated files
    """

    def __init__(
        self,
        project_id: str,
        conversation_id: str,
        base_path: str = "/data/workspaces",
        mcp_servers: Optional[Dict[str, Any]] = None,
        mcp_tools: Optional[List[str]] = None,
    ):
        self.project_id = project_id
        self.conversation_id = conversation_id
        self.base_path = Path(base_path) / project_id / conversation_id
        self.mcp_servers = mcp_servers or {}
        self.mcp_tools = mcp_tools or []

    async def setup(self) -> WorkspaceConfig:
        """
        Create working directory and .claude structure.

        Returns:
            WorkspaceConfig with paths to all directories
        """
        logger.info(f"Setting up workspace for project={self.project_id}, conversation={self.conversation_id}")
        logger.info(f"[WORKSPACE] MCP servers configured: {bool(self.mcp_servers)}")
        logger.info(f"[WORKSPACE] MCP tools count: {len(self.mcp_tools)}")

        # Define directory paths
        working_dir = self.base_path / "work_dir"
        claude_dir = working_dir / ".claude"
        skills_dir = claude_dir / "skills"
        output_dir = working_dir / "output"

        # Create all directories
        for d in [working_dir, claude_dir, skills_dir, output_dir]:
            d.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created directory: {d}")

        # Copy default .claude files
        self._setup_claude_files(claude_dir)

        config = WorkspaceConfig(
            working_directory=str(working_dir),
            claude_directory=str(claude_dir),
            skills_directory=str(skills_dir),
            output_directory=str(output_dir),
        )

        logger.info(f"Workspace setup complete: {config.working_directory}")
        return config

    def _setup_claude_files(self, claude_dir: Path) -> None:
        """
        Setup .claude files with dynamic MCP configuration.

        Args:
            claude_dir: Path to the .claude directory
        """
        # Copy CLAUDE.md from source .claude directory
        claude_md_path = claude_dir / "CLAUDE.md"
        source_claude_md = SOURCE_CLAUDE_DIR / "CLAUDE.md"

        # Log the resolved path for debugging
        print(f"[WORKSPACE] SOURCE_CLAUDE_DIR resolved to: {SOURCE_CLAUDE_DIR}")
        print(f"[WORKSPACE] SOURCE_CLAUDE_DIR exists: {SOURCE_CLAUDE_DIR.exists()}")
        print(f"[WORKSPACE] source_claude_md path: {source_claude_md}")
        print(f"[WORKSPACE] source_claude_md exists: {source_claude_md.exists()}")

        if not claude_md_path.exists():
            if source_claude_md.exists():
                shutil.copy(source_claude_md, claude_md_path)
                logger.info(f"[WORKSPACE] Copied CLAUDE.md from {source_claude_md}")
                print(f"[WORKSPACE] Successfully copied CLAUDE.md ({source_claude_md.stat().st_size} bytes)")
            else:
                logger.warning(f"[WORKSPACE] Source CLAUDE.md not found at {source_claude_md}")
                print(f"[WORKSPACE] WARNING: Source CLAUDE.md not found!")
                # Create a minimal fallback
                claude_md_path.write_text("# Chicory Platform Agent\n\nNo CLAUDE.md template found.")
            logger.debug(f"Created {claude_md_path}")
        else:
            print(f"[WORKSPACE] CLAUDE.md already exists at {claude_md_path}")

        # Create settings.json with MCP configuration
        settings_path = claude_dir / "settings.json"
        if not settings_path.exists():
            settings_content = self._build_settings_json()
            settings_path.write_text(settings_content)
            logger.info(f"[WORKSPACE] Created {settings_path} with MCP config: {bool(self.mcp_servers)}")
            logger.debug(f"[WORKSPACE] Settings content:\n{settings_content}")

        # Copy default skills to workspace
        skills_dir = claude_dir / "skills"
        self._copy_default_skills(skills_dir)

    def _build_settings_json(self) -> str:
        """
        Build settings.json dynamically with MCP configuration.

        Returns:
            JSON string with sandbox, permissions, and MCP servers config
        """
        # Build base permissions
        permissions_allow = [
            "Bash",
            "Read",
            "Write",
            "Python",
            "Skill"
        ]

        # Add MCP tool permissions if configured
        if self.mcp_tools:
            permissions_allow.extend(self.mcp_tools)
            logger.info(f"[WORKSPACE] Added {len(self.mcp_tools)} MCP tool permissions")

        # Build settings dict
        settings_dict = {
            "sandbox": {
                "enabled": True,
                "autoAllowBashIfSandboxed": True,
                "excludedCommands": ["docker"],
                "network": {
                    "allowLocalBinding": True
                }
            },
            "permissions": {
                "allow": permissions_allow,
                "deny": []
            }
        }

        # Add MCP servers if configured
        if self.mcp_servers:
            settings_dict["mcpServers"] = self.mcp_servers
            logger.info(f"[WORKSPACE] Added MCP servers to settings.json: {list(self.mcp_servers.keys())}")
            for server_name, server_config in self.mcp_servers.items():
                logger.debug(f"[WORKSPACE]   {server_name}: {server_config.get('url', 'N/A')}")

        return json.dumps(settings_dict, indent=2)

    def _copy_default_skills(self, skills_dir: Path) -> None:
        """
        Copy default skills from source directory to workspace if not present.

        Skills are copied from SOURCE_SKILLS_DIR (typically /app/.claude/skills/)
        to the workspace's .claude/skills/ directory.

        Args:
            skills_dir: Path to the workspace's skills directory
        """
        if not SOURCE_SKILLS_DIR.exists():
            logger.debug(f"[WORKSPACE] No source skills directory at {SOURCE_SKILLS_DIR}")
            return

        copied_count = 0
        for skill in SOURCE_SKILLS_DIR.iterdir():
            if skill.is_dir() and (skill / "SKILL.md").exists():
                dest = skills_dir / skill.name
                if not dest.exists():
                    try:
                        shutil.copytree(skill, dest)
                        copied_count += 1
                        logger.info(f"[WORKSPACE] Copied skill '{skill.name}' to workspace")
                    except Exception as e:
                        logger.warning(f"[WORKSPACE] Failed to copy skill '{skill.name}': {e}")

        if copied_count > 0:
            logger.info(f"[WORKSPACE] Copied {copied_count} default skills to workspace")
        else:
            logger.debug(f"[WORKSPACE] No new skills to copy (all already present or none available)")

    def get_available_skills(self) -> list[str]:
        """
        Get list of available skills in the workspace.

        Returns:
            List of skill names (directory names in skills/)
        """
        skills_dir = self.base_path / "work_dir" / ".claude" / "skills"
        if not skills_dir.exists():
            return []

        skills = []
        for item in skills_dir.iterdir():
            if item.is_dir() and (item / "SKILL.md").exists():
                skills.append(item.name)

        return skills

    def cleanup(self) -> None:
        """Remove workspace after conversation ends."""
        if self.base_path.exists():
            try:
                shutil.rmtree(self.base_path)
                logger.info(f"Cleaned up workspace: {self.base_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup workspace {self.base_path}: {e}")

    def __enter__(self) -> "WorkspaceManager":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - cleanup workspace."""
        self.cleanup()
