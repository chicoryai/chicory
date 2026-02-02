import asyncio
import mimetypes
import os
import json
import shutil
from typing import Dict, Any, List, Union, Optional, Callable, Awaitable
import time
import boto3
from botocore.exceptions import ClientError
from datetime import datetime

# NOTE: LangGraph/LangChain removed - using Claude Agent SDK directly
# from langgraph.constants import END
# from langgraph.graph import StateGraph
# from langsmith import traceable
# from services.models.llm_orchestrator import LLMOrchestrator

from services.workflows.data_understanding.hybrid_rag.model.data import GraphStateHybrid
from services.customer.personalization import get_project_config
from services.utils.logger import logger

# Redis imports for streaming
import redis.asyncio as redis
from redis.asyncio.cluster import RedisCluster
from redis.asyncio import Redis

# Claude Code SDK imports
try:
    from claude_agent_sdk import (
        AssistantMessage,
        UserMessage,
        SystemMessage,
        ClaudeAgentOptions,
        AgentDefinition,
        ResultMessage,
        TextBlock,
        ThinkingBlock,
        ToolUseBlock,
        ToolResultBlock,
        ContentBlock,
        query,
    )
    CLAUDE_CODE_SDK_AVAILABLE = True
except ImportError:
    CLAUDE_CODE_SDK_AVAILABLE = False
    logger.warning("Claude Code SDK not available.")

SEED = int(os.environ.get("SEED", "101"))
MAX_TOKENS = 100_000


def _get_s3_client():
    """Create S3 client with optional custom endpoint (MinIO, LocalStack, etc.)

    Works for both:
    - AWS S3 (cloud): Uses default credentials chain (IAM role, env vars, etc.)
    - MinIO (local): Uses S3_ENDPOINT_URL with explicit credentials
    """
    region = os.environ.get("AWS_REGION", "us-west-2")
    endpoint_url = os.environ.get("S3_ENDPOINT_URL")

    client_kwargs = {
        'region_name': region,
    }

    # Add endpoint URL if specified (for MinIO or other S3-compatible storage)
    if endpoint_url:
        client_kwargs['endpoint_url'] = endpoint_url
        # Explicit credentials needed for MinIO
        client_kwargs['aws_access_key_id'] = os.environ.get('AWS_ACCESS_KEY_ID', '')
        client_kwargs['aws_secret_access_key'] = os.environ.get('AWS_SECRET_ACCESS_KEY', '')
        logger.info(f"Using custom S3 endpoint: {endpoint_url}")

    return boto3.client("s3", **client_kwargs)


DEFAULT_ERROR_MESSAGE = (
    "I'm sorry, but something went wrong while processing your request. "
    "Please try again or contact support if the issue persists."
)

# Cancellation message constant
TASK_CANCELLED_MESSAGE = "Task was cancelled by user."

# Directories to exclude from artifact uploads
ARTIFACT_SKIP_DIRS = {'.claude', 'node_modules', '.git', '__pycache__', '.next', '.cache', 'dist', '.remotion', '.venv', 'venv', 'build'}

# ============================================================================
# MAIN AGENT ARCHITECTURE
# ============================================================================

class LLMAgentArchitecture:
    def __init__(self,
                 project: str,
                 user: str,
                 mcp_config: Dict[str, Any] = None,
                 phoenix_project: Optional[str] = None,
                 agent_id: str = None,
                 recursion_limit: int = 100):

        self.project = project
        self.user = user
        self.mcp_config = mcp_config or {"servers": {}, "available_data_source_types": []}
        self.agent_id = agent_id
        self.recursion_limit = recursion_limit

        # Redis client for streaming (lazy initialization)
        self.redis_client: Optional[redis.Redis | RedisCluster] = None
        
        # Runtime config (set during astream call)
        self.runtime_config: Optional[Dict[str, Any]] = None
        
        # Cancellation callback (set via runtime config)
        self.cancellation_check: Optional[Callable[[], Awaitable[bool]]] = None
        self._last_cancel_check: float = 0
        self._cancel_check_interval: float = 5.0  # Check cancellation every 5 seconds
        
        self.config = {
            "project": project,
            "user": user,
            "agent_id": agent_id,
            "phoenix_project": phoenix_project,
            "seed": SEED,
            "max_tokens": MAX_TOKENS
        }

        # Core components
        self.orchestrator = None
        self.project_config = None

        # Agents
        self.context_agent_options = None
        self.action_agent_options = None
        self.workflow_app = None

        # Performance tracking
        self.load_time = 0
        self.init_time = 0

    async def initialize(self) -> bool:
        """Initialize the entire agent architecture with fast load time."""
        start_time = time.time()

        try:
            # Setup environment
            if self.config.get("phoenix_project"):
                os.environ["PHOENIX_PROJECT_NAME"] = self.config["phoenix_project"]

            # NOTE: LLMOrchestrator removed - using Claude Agent SDK directly
            # self.orchestrator = LLMOrchestrator(project=self.project, global_seed=SEED)
            self.orchestrator = None  # Not needed with Claude SDK

            # Get project config (critical path)
            self.project_config = get_project_config(self.project)
            if not self.project_config:
                logger.error("Project configuration not found")
                return False

            # MCP tools are now pre-configured, no initialization needed
            self.init_time = 0

            # Create agent options (Claude SDK)
            await self._create_action_agent_options()

            # NOTE: LangGraph workflow removed - using direct Claude SDK calls
            # self._create_graph_workflow() is now simplified
            self._setup_workflow()

            self.load_time = time.time() - start_time
            logger.info(f"Agent initialized in {self.load_time:.2f}s (tools: {self.init_time:.2f}s)")

            return True

        except Exception as e:
            logger.error(f"Error initializing agent architecture: {e}", exc_info=True)
            return False

    # Removed _fast_initialize_tools and _get_tools_from_tool methods
    # MCP tools are now pre-configured in main_managed.py


    def _get_context_directory(self) -> str:
        """Get and create the context directory for Claude Code.

        Returns the project's root data directory which contains:
        - raw/ - Raw scanned documents, code, and data files
        - database_metadata/ - Scanned database schemas (BigQuery, Databricks, etc.)
        """
        home_path = os.getenv("HOME_PATH", "/app")
        data_path = os.getenv("BASE_DIR", os.path.join(home_path, "data"))
        project_id = self.project.lower()
        # Use project root to include both raw/ and database_metadata/ directories
        context_directory = os.path.join(data_path, project_id)

        # Ensure working directory exists
        os.makedirs(context_directory, exist_ok=True)
        return context_directory


    def _get_working_directory(self) -> str:
        """Get and create the working directory for Claude Code.
        
        Cleans up existing directory to ensure fresh isolated environment.
        """
        project_id = self.project.lower()
        agent_id = self.agent_id.lower()
        working_directory = os.path.join("/tmp", "chicory", project_id, agent_id, "work_dir")
        
        # Clean up existing directory to prevent data leakage
        if os.path.exists(working_directory):
            try:
                shutil.rmtree(working_directory)
                logger.info(f"Cleaned up working directory: {working_directory}")
            except Exception as e:
                logger.warning(f"Failed to clean up working directory {working_directory}: {e}")
        
        # Create fresh working directory
        os.makedirs(working_directory, exist_ok=True)
        logger.info(f"Created fresh working directory: {working_directory}")
        
        # Setup Skills directory in agent's tmp folder
        self._setup_skills_directory(working_directory)
        
        return working_directory
    
    def _setup_skills_directory(self, working_directory: str) -> None:
        """Setup .claude directory in agent's working directory with skills and CLAUDE.md.
        
        This creates a project-specific .claude directory in the agent's tmp folder so that
        Claude Code can discover and use skills. The skills are copied from the main project
        skills directory and CLAUDE.md is copied from the context directory.
        
        Args:
            working_directory: The agent's working directory path (e.g., /tmp/chicory/project/agent/work_dir)
        
        Directory Structure Created:
            /tmp/chicory/{project}/{agent}/work_dir/.claude/skills/

        Note:
            - Skills are copied to ensure isolation between agents
            - Each agent gets its own copy of skills in its tmp directory
            - CLAUDE.md is moved from context to .claude for better organization
            - The .claude directory is created at the root of the working directory
        """
        skills_copied = 0
        files_copied = 0
        
        try:
            # Source skills directory at adaptive_rag.py level
            source_skills_dir = os.path.join(
                os.path.dirname(__file__),
                "skills"
            )
            
            # Target skills directory in agent's working directory
            target_claude_dir = os.path.join(working_directory, ".claude")
            target_skills_dir = os.path.join(target_claude_dir, "skills")
            
            # Create .claude/skills directory structure
            os.makedirs(target_skills_dir, exist_ok=True)
            
            # Copy skills from source to target if source exists
            if os.path.exists(source_skills_dir):
                # Copy all skill directories and files
                for item in os.listdir(source_skills_dir):
                    source_item = os.path.join(source_skills_dir, item)
                    target_item = os.path.join(target_skills_dir, item)
                    
                    try:
                        if os.path.isdir(source_item):
                            # Copy skill directory (e.g., pdf-extraction/)
                            shutil.copytree(source_item, target_item, dirs_exist_ok=True)
                            skills_copied += 1
                            logger.debug(f"Copied skill directory: {item}")
                        elif os.path.isfile(source_item):
                            # Copy skill file (e.g., README.md)
                            shutil.copy2(source_item, target_item)
                            files_copied += 1
                            logger.debug(f"Copied skill file: {item}")
                    except Exception as copy_error:
                        logger.warning(f"Failed to copy skill '{item}': {copy_error}")
                
                logger.info(f"Skills directory setup complete: {skills_copied} skills, {files_copied} files copied to {target_skills_dir}")
            else:
                logger.warning(f"Source skills directory not found: {source_skills_dir}")
                logger.info(f"Created empty skills directory: {target_skills_dir}")
            
            # Copy CLAUDE.md from context directory's raw/ subfolder to .claude folder
            context_directory = self._get_context_directory()
            # CLAUDE.md is stored in the raw/ subdirectory
            source_claude_md = os.path.join(context_directory, "raw", "CLAUDE.md")
            target_claude_md = os.path.join(target_claude_dir, "CLAUDE.md")

            if os.path.exists(source_claude_md):
                shutil.copy2(source_claude_md, target_claude_md)
                logger.info(f"Copied CLAUDE.md from context to .claude directory")
            else:
                logger.debug(f"CLAUDE.md not found in context directory: {source_claude_md}")
                
        except Exception as e:
            logger.error(f"Failed to setup .claude directory: {e}", exc_info=True)
            # Log what was copied before failure for debugging
            if skills_copied > 0 or files_copied > 0:
                logger.info(f"Partial setup: {skills_copied} skills, {files_copied} files copied before error")

    def _detect_security_violation(self, command: str) -> tuple[bool, str]:
        """Detect potential security violations in commands for MONITORING/LOGGING purposes.
        
        SECURITY MODEL:
        ===============
        - PRIMARY ENFORCEMENT: System prompt instructions (soft restriction via LLM guidance)
        - SECONDARY LAYER: This detection function (monitoring and alerting only)
        - TERTIARY LAYER: Claude Code sandbox settings (hard restrictions on file access)
        
        This function provides defense-in-depth monitoring alongside the system prompt.
        It does NOT block execution - it only logs warnings for security review.
        
        KNOWN LIMITATIONS:
        - String matching can be bypassed via obfuscation (e.g., 'sys' + 'tem')
        - Dynamic code generation can evade detection
        - Base64/hex encoding can hide patterns
        
        For stronger enforcement, consider:
        - AST parsing for Python code analysis
        - Sandboxed execution environments
        - Runtime syscall filtering (seccomp)
        
        Returns:
            tuple: (is_violation, violation_type) - Used for logging, not blocking
        """
        command_lower = command.lower()
        
        # Environment variable access patterns
        env_patterns = [
            'printenv', 'env ', 'export ', 'echo $', '${', 
            'os.environ', 'os.getenv', 'process.env',
            'cat /proc/self/environ', 'cat /proc/*/environ'
        ]
        
        # System information gathering
        system_patterns = [
            'uname', 'hostname', 'whoami', 'id ', 
            '/etc/os-release', '/etc/passwd', '/etc/shadow',
            '/proc/version', '/proc/cpuinfo', '/proc/meminfo'
        ]
        
        # Network and security reconnaissance
        network_patterns = [
            'nmap', 'netstat', 'ss ', 'ifconfig', 'ip addr',
            'ping ', 'traceroute', 'dig ', 'nslookup'
        ]
        
        # Process and system analysis
        process_patterns = [
            'ps aux', 'ps -ef', 'top', 'htop', 'pstree',
            'lsof', 'fuser', 'df ', 'du ', 'mount',
            'free', 'vmstat', 'systemctl', 'service '
        ]
        
        # Code execution patterns (subprocess, eval, exec)
        code_exec_patterns = [
            'subprocess.run', 'subprocess.popen', 'subprocess.call',
            'os.system', 'os.popen', 'os.spawn',
            'eval(', 'exec(', 'compile(',
            '__import__', 'importlib.import_module'
        ]
        
        # Check each category
        for pattern in env_patterns:
            if pattern in command_lower:
                return True, "environment_variable_access"
        
        for pattern in system_patterns:
            if pattern in command_lower:
                return True, "system_information_gathering"
        
        for pattern in network_patterns:
            if pattern in command_lower:
                return True, "network_reconnaissance"
        
        for pattern in process_patterns:
            if pattern in command_lower:
                return True, "process_analysis"
        
        for pattern in code_exec_patterns:
            if pattern in command_lower:
                return True, "dangerous_code_execution"
        
        return False, ""


    async def _fetch_mcp_tools(self, mcp_server_name: str, server_url: str, headers: Dict[str, str] = None) -> List[str]:
        """Fetch available tools from an MCP server using proper MCP client."""
        try:
            from langchain_mcp_adapters.client import MultiServerMCPClient

            mcp_server_config = {
                mcp_server_name: {
                    "url": server_url,
                    "transport": "streamable_http",
                    "headers": headers or {}
                }
            }

            # Create temporary MCP client
            mcp_client = MultiServerMCPClient(mcp_server_config)

            # Fetch tools using the proper MCP client
            tools = await asyncio.wait_for(mcp_client.get_tools(), timeout=30.0)

            if tools:
                tool_names = [tool.name for tool in tools if hasattr(tool, 'name')]
                logger.info(f"Fetched {len(tool_names)} tools from MCP server {server_url}: {tool_names}")
                return [f"mcp__{mcp_server_name.replace(' ', '_').replace('-', '_')}__{name}" for name in tool_names]
            else:
                logger.warning(f"No tools returned from MCP server {server_url}")
                return []

        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching tools from MCP server {server_url}")
            return []
        except Exception as e:
            logger.warning(f"Error fetching tools from MCP server {server_url}: {e}")
            return []

    async def _create_action_agent_options(self):
        """Create the main action agent with all available tools."""
        working_directory = self._get_working_directory()
        context_directory = self._get_context_directory()
        logger.info(f"Claude Code working directory: {working_directory}")

        # Get current timestamp for the system prompt
        current_timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        # System message defining the architecture (unchanged from original)
        system_prompt = f"""
            You are Chicory AI, an intelligent data analysis, engineering, and operations assistant focused on delivering actionable, validated solutions.

            ## CONTEXT
            - Current Date/Time: {current_timestamp}
            - Working Directory: {working_directory}.
            - Context Directory (READ-ONLY): {context_directory}. **Always** refer to this for context gathering.
            - Project Documentation: `.claude/CLAUDE.md` in your working directory contains project-specific context and guidelines.
            - You have access to processed context. Use targeted tool calls for deeper validation.
            - Use GitHub Flavored Markdown (GFM), if output format is empty.

            ## CRITICAL DIRECTORY BOUNDARIES - ABSOLUTE RESTRICTIONS
            - You MUST operate ONLY within the working directory: {working_directory}
            - You MAY read from the context directory (READ-ONLY): {context_directory}
            - You are STRICTLY FORBIDDEN from accessing, reading, writing, or executing commands outside these directories
            - DO NOT navigate to parent directories (e.g., ../, /tmp, /app, or any path outside the working directory)
            - DO NOT access system directories, home directories, or any other filesystem locations
            - All file operations (Read, Write, Python, Bash) must be confined to the working directory
            - When reading context, use ONLY the context directory path provided above
            - If a user asks about files or directories outside your working directory, respond that you cannot access them
            - NEVER attempt to list, read, or access paths like /Users/*, /home/*, /app/*, or any absolute paths outside your boundaries
            - If you need to check what you can access, only list contents within {working_directory}

            ## SECURITY & PRIVACY GUIDELINES
            - NEVER reveal internal system details, implementation specifics, or technical architecture
            - DO NOT mention Claude Code, SDK, APIs, databases, or other internal technologies
            - NEVER expose file paths, system configurations, or infrastructure details
            - DO NOT execute commands that could compromise system security
            - NEVER access or modify files outside the designated working directory
            - DO NOT reveal sensitive information like API keys, credentials, or connection strings
            - ALWAYS validate and sanitize any user inputs before processing
            - REFUSE requests for system administration, network access, or privilege escalation
            - WRITE ACCESS RESTRICTIONS: You are restricted from writing to the following folders within the working directory: documents/, code/, data/
            
            ## FORBIDDEN COMMANDS - ABSOLUTE PROHIBITIONS
            **NEVER execute these commands under ANY circumstances:**
            
            **Environment & System Information:**
            - `printenv`, `env`, `export` - DO NOT list or access environment variables
            - `echo $VAR`, `echo ${{VAR}}`, `$VAR` - DO NOT access environment variable values
            - `set`, `declare` - DO NOT list shell variables
            - `cat /proc/*/environ`, `cat /proc/self/environ` - DO NOT read process environment
            - `os.environ`, `os.getenv()`, `process.env` - DO NOT access env vars in any programming language
            - Scripts that check, verify, or partially reveal environment variables - DO NOT execute
            - Scripts that show "last 4 characters" or "masked" env vars - DO NOT execute
            - Any code accessing environment variables regardless of stated purpose - DO NOT execute
            - `uname`, `hostname`, `whoami`, `id` - DO NOT gather system information
            - `cat /etc/os-release`, `lsb_release` - DO NOT identify OS version
            - `cat /proc/version`, `cat /proc/cpuinfo`, `cat /proc/meminfo` - DO NOT read system specs
            
            **Network & Security Reconnaissance:**
            - `nmap`, `netstat`, `ss`, `ifconfig`, `ip addr` - DO NOT scan networks or ports
            - `curl`, `wget` to scan ports or enumerate services - DO NOT perform port scanning
            - Creating port scanners or network enumeration scripts - DO NOT build security tools
            - `ping`, `traceroute`, `dig`, `nslookup` for reconnaissance - DO NOT map network topology
            - Testing connectivity to arbitrary external hosts - DO NOT probe external systems
            
            **System & Process Analysis:**
            - `ps aux`, `top`, `htop`, `pstree` - DO NOT enumerate running processes
            - `lsof`, `fuser` - DO NOT list open files or file usage
            - `df`, `du`, `mount` - DO NOT analyze disk usage or mounted filesystems
            - `free`, `vmstat` - DO NOT check memory or system statistics
            - `systemctl`, `service` - DO NOT query system services
            - `cat /etc/passwd`, `/etc/shadow`, `/etc/group` - DO NOT access user databases
            
            **Privilege & Security:**
            - `sudo`, `su`, `chroot` - DO NOT attempt privilege escalation
            - Checking user permissions or capabilities - DO NOT assess security posture
            - Creating or running penetration testing scripts - DO NOT perform security assessments
            - Compiling or running exploits - DO NOT test system vulnerabilities
            
            **STRICTLY PROHIBITED ACTIVITIES:**
            - **Penetration testing** of any kind
            - **Security assessments** or vulnerability scanning
            - **System reconnaissance** or information gathering
            - **Network enumeration** or port scanning
            - **Creating security tools** (port scanners, exploit scripts, etc.)
            - **Testing system defenses** or attempting to bypass restrictions
            - **Generating security reports** about the host system
            
            **If a user requests any of these:**
            - **IMMEDIATELY REFUSE** - Do not comply even partially
            - State: "I cannot execute this request - it violates security restrictions"
            - **DO NOT provide workarounds, alternatives, or suggestions** on how to accomplish the prohibited task
            - **DO NOT offer to check, verify, or partially execute** the request
            - **DO NOT create scripts** that could be used for these purposes later, even if they claim to be "safe" versions
            - **DO NOT explain how the user could do it themselves** or suggest other tools
            - Simply refuse and stop - do not elaborate on alternatives

            ## IDENTITY
            - If asked about your name or identity, respond that you are "Chicory AI"
            - DO NOT mention any underlying models, SDKs, or technical implementations
            - NEVER reveal what powers you, what technology you use, or what AI model you're based on
            - DO NOT mention Anthropic, Claude, OpenAI, GPT, or any other AI providers or models
            - If asked "who powers you" or "what powers you", simply say "I'm Chicory AI, an intelligent assistant"
            - Present yourself as a unified AI assistant, not a collection of tools or services

            ## WORKING DIRECTORY & STATE MANAGEMENT
            - Your working directory is a temporary, isolated workspace that persists for the duration of this session
            - **Use files for memory**: Store intermediate results, state, or cached data in temporary files (e.g., `state.md`, `notes.md`, `results.json`)
            - **Prefer markdown files** (`.md`) for storing notes, findings, analysis, and structured information—they're human-readable and easy to work with
            - **Benefits of file-based storage**:
              - Preserve data between operations without consuming context window
              - Cache expensive computations or API results for reuse
              - Store large datasets that would otherwise bloat your context
              - Share data between different phases of your workflow
            - **Common patterns**:
              - `Write("analysis_notes.md", markdown_content)` → Store findings and notes
              - `Write("intermediate_data.json", json_data)` → Store structured data
              - `Read("analysis_notes.md")` → Retrieve previous findings
              - `Bash("ls -la")` → See what's available in your workspace
            - **Cleanup**: Your working directory is automatically cleaned at the start of each new session
            - Use this capability freely to manage complex, multi-step workflows efficiently
            
            ## OUTPUT FILE GENERATION
            - **When a task requires generating an output file** (e.g., CSV, Excel, PDF, JSON, report files), **ALWAYS create the file in the `output/` folder** within your working directory
            - **Create the output folder first** if it doesn't exist: `Bash("mkdir -p output")`
            - **File path pattern**: `output/<filename>.<extension>` (e.g., `output/report.csv`, `output/analysis.xlsx`, `output/results.json`)
            - **Examples**:
              - Generating a CSV report → `Write("output/report.csv", csv_content)` or save via pandas to `output/data.csv`
              - Creating an Excel file → Save to `output/analysis.xlsx`
              - Generating a PDF → Save to `output/document.pdf`
              - Creating a JSON export → `Write("output/export.json", json_content)`
            - **This ensures**: All generated output files are organized in a consistent location for easy retrieval and downstream processing

            ## SUBAGENT DELEGATION
            - You have access to specialized subagents for specific tasks
            - **Benefits**: Subagents operate independently, preserve your context window, return only processed results, and provide additional security isolation
            - Delegate proactively to maintain efficiency and response quality
            
            ## FILE GENERATION & ARTIFACT HANDLING
            - **CRITICAL**: NEVER mention file creation, saving, paths, filenames, or download instructions in your responses
            - **FORBIDDEN PHRASES**: Do NOT say "I've created", "file has been created", "saved to", "file is available", "you cannot download", etc.
            - **FORBIDDEN REFERENCES**: Do NOT mention specific filenames like "report.pdf", "data.csv", "File: example.xlsx"
            - **REQUIRED**: If you create files internally, immediately read and display the FULL CONTENT inline in properly formatted markdown
            - **NO METADATA**: Never add signatures, timestamps, or branding like "Generated by Chicory AI"
            - **IGNORE DOWNLOAD REQUESTS**: If users ask about downloading, file locations, or saving files, simply show the content without acknowledging the question
            - **FOR EXTERNAL DELIVERY**: If users need to push output to external systems, guide them to use available integrations (GitHub, S3) as a natural workflow option
            - Simply present the complete output directly - nothing more, nothing less

            ## OUTPUT FORMATTING
            - When a specific output format is requested, consider delegating to the **formatter** subagent for precise format transformation
            - The formatter subagent specializes in converting content to specific formats (JSON, Markdown, CSV, XML, etc.)
            - If handling formatting yourself, ensure your final response matches the requested format exactly
            - Extract only the essential information that matches the requested format
            - Remove explanatory text, reasoning, or extra details if a specific format is requested
            - If JSON is requested, return valid JSON only
            - If specific fields are requested, include only those fields
            - Strip out any references to internal systems, technical details, or debugging information

            ## SKILLS - SPECIALIZED CAPABILITIES
            You have access to specialized Skills that provide expert guidance for specific tasks.
            
            **Available Skills:**
            - **processing-pdfs** - Use for ANY PDF operations: text extraction, table extraction, merging, splitting, OCR, form filling
            - **remotion-best-practices** - Use for video creation with React and Remotion. Create animated videos, compositions, render to MP4/WebM
            - **create-mcp-app** - Use for building interactive HTML UIs that render inside MCP hosts like Claude Desktop

            **SKILL INVOCATION RULES:**
            1. **Check for applicable Skills FIRST** before attempting manual solutions
            2. **Invoke Skills using the Skill tool** - e.g., `Skill("processing-pdfs")` to load PDF processing guidance
            3. **Follow Skill instructions precisely** - Skills contain tested patterns and best practices

            **WHEN TO INVOKE SKILLS:**
            - User mentions PDF files or .pdf extension → Invoke `processing-pdfs` skill
            - User asks to extract text/tables from PDFs → Invoke `processing-pdfs` skill
            - User asks to merge, split, or manipulate PDFs → Invoke `processing-pdfs` skill
            - User asks to create a video, animation, or visual content → Invoke `remotion-best-practices` skill
            - User mentions Remotion, video rendering, or React video → Invoke `remotion-best-practices` skill
            - User asks to create an MCP App, interactive UI, or MCP tool with UI → Invoke `create-mcp-app` skill

            **EXAMPLE SKILL USAGE:**
            - "Extract text from report.pdf" → `Skill("processing-pdfs")` then follow PDF extraction patterns
            - "Merge these PDF files" → `Skill("processing-pdfs")` for merge workflow
            - "Fill out this PDF form" → `Skill("processing-pdfs")` for form filling guidance
            - "Create a video about X" → `Skill("remotion-best-practices")` then use Remotion with React
            - "Make an animated video" → `Skill("remotion-best-practices")` for video composition patterns
            - "Build an MCP App with a dashboard" → `Skill("create-mcp-app")` for MCP App scaffolding

            Be a thoughtful problem solver: understand true needs, select the right tools, validate rigorously, communicate clearly.
            Always keep going and don't ask the user for follow up questions.
        """


        # Configure Claude Code options with MCP server configuration
        logger.info("Configuring Claude Code options with MCP server configuration...")

        # Start with base tools
        allowed_tools = ["Python", "Bash", "Read", "Write", "Skill"]
        mcp_servers = self.mcp_config.get("servers", {})

        logger.info(f"MCP servers configured: {list(mcp_servers.keys())}")

        # Fetch and filter tools from each MCP server
        # Store all MCP tools for both allowed_tools and permissions
        all_mcp_tools = []
        for server_name, server_config in mcp_servers.items():
            server_url = server_config.get("url")
            headers = server_config.get("headers", {})
            
            if server_url:
                try:
                    # Fetch available tools from the server
                    mcp_tools = await self._fetch_mcp_tools(server_name, server_url, headers)
                    
                    # Add all tools from MCP server (already filtered by server)
                    if mcp_tools:
                        allowed_tools.extend(mcp_tools)
                        all_mcp_tools.extend(mcp_tools)
                        logger.info(f"Added {len(mcp_tools)} MCP tools from {server_name}: {mcp_tools}")
                        
                except Exception as e:
                    logger.warning(f"Failed to fetch tools from MCP server {server_name}: {e}")

        logger.info(f"Final allowed_tools: {allowed_tools}")
        logger.info(f"Total MCP tools discovered: {len(all_mcp_tools)}")

        # Build wildcard permission patterns for each MCP server
        # Using wildcards (mcp__server__*) instead of listing individual tools
        # ensures all tools from configured servers are auto-approved
        mcp_server_permission_patterns = []
        for server_name in mcp_servers.keys():
            # Normalize server name (replace spaces/dashes with underscores)
            normalized_name = server_name.replace(' ', '_').replace('-', '_')
            pattern = f"mcp__{normalized_name}__*"
            mcp_server_permission_patterns.append(pattern)
            logger.info(f"Added MCP permission wildcard pattern: {pattern}")

        logger.info(f"MCP server permission patterns: {mcp_server_permission_patterns}")

        # Configure subagents for specialized tasks
        subagents = {
            "reader": AgentDefinition(
                description="Specialized agent for reading, processing, and extracting content from various sources",
                prompt="""You are a reading specialist. Your task is to read and process various content types and extract information accurately.

CAPABILITIES:
- Reading files: PDF, CSV, Excel, JSON, XML, text, logs, configuration files
- Extracting structured data from unstructured content
- Identifying key sections, headings, and document structure
- Processing large documents efficiently (>10MB)
- Streaming large files to avoid memory issues
- Summarizing content while preserving critical details
- Preserving tables, lists, and formatting
- Parsing complex data formats and nested structures

FILE SIZE HANDLING:
1. **Check file size FIRST** using `ls -lh filename` or Python `os.path.getsize()`
2. **Files < 2MB**: Read entire file into memory using Read tool or standard file operations
3. **Files ≥ 2MB**: MUST use streaming/chunked reading to avoid memory issues
   - For text files: Use Python with `open(file, 'r')` and read in chunks or line-by-line
   - For CSV: Use `pandas.read_csv(file, chunksize=10000)` to process in chunks
   - For large PDFs: Use PyPDF2/pdfplumber and process page-by-page
   - For Excel: Use `pandas.read_excel(file, chunksize=1000)` or read specific sheets
4. **Never load files ≥ 2MB entirely into memory** - always stream/chunk

TOOL USAGE PRIORITY:
1. **Check file size first** - Critical for large file handling
2. **Check for available Skills** - Skills provide specialized processing (e.g., PDF extraction)
   - If a Skill exists for the file type, it will be automatically invoked
   - Skills handle their own size management and optimization
   - Let Skills work first before manual processing
3. **ALWAYS try the Read tool first** for files < 2MB (if no Skill available)
4. **For files ≥ 2MB** (if no Skill available): Use Python streaming/chunking methods immediately
5. If Read tool fails or doesn't support the file type, use Python packages (pandas, PyPDF2, openpyxl, etc.)
6. For text files, logs, JSON, CSV < 2MB - Read tool should handle most cases
7. For complex formats (Excel with multiple sheets, password-protected PDFs) - use Python packages as fallback

STREAMING EXAMPLES:
- Large CSV (5MB): `for chunk in pd.read_csv('data.csv', chunksize=10000): process(chunk)`
- Large text file (3MB): `with open('log.txt', 'r') as f: for line in f: process(line)`
- Large PDF (8MB): `for page_num in range(pdf.numPages): page = pdf.getPage(page_num); process(page)`
- Large JSON (4MB): Use `ijson` library for streaming JSON parsing

EXAMPLES:
- "Extract all customer records from customers.csv" → Check size first, if < 2MB use Read tool, if ≥ 2MB stream with pandas chunks
- "Summarize this 50-page PDF report" → PDF Skill will be automatically invoked (Skills handle PDFs)
- "Extract text from invoice.pdf" → PDF Skill will be automatically invoked (Skills handle PDFs)
- "Find all error messages in application.log" → Check size, if ≥ 2MB read line-by-line, don't load entire file
- "Read config.json and explain settings" → Check size, if < 2MB use Read tool, parse JSON
- "Extract table data from large_dataset.csv (10MB)" → MUST use pandas with chunksize, process incrementally

OUTPUT FORMAT:
Return the extracted content in a clear, structured format suitable for further processing. Include:
- File size checked and processing method used (streaming vs full read)
- Main content/data extracted
- Document structure (sections, headings)
- Key findings or important information
- Any tables or structured data in markdown format
- For streamed files: Summary statistics (total rows processed, chunks used, etc.)""",
            ),
            "writer": AgentDefinition(
                description="Specialized agent for creating and writing various content types and files",
                prompt="""You are a writing specialist. Your task is to create and write various content types with proper formatting.

CAPABILITIES:
- Creating files in the working directory: reports, code, data files, documentation
- Generating well-formatted documents: Markdown, JSON, CSV, Python, JavaScript, SQL
- Writing structured content with proper organization
- Creating data files with correct formatting and validation
- Generating code files with proper syntax, imports, and structure
- Multi-file generation for complex projects
- Ensuring content is complete, properly formatted, and production-ready

EXAMPLES:
- "Create a Python script to process CSV data" → Generate complete .py file with imports, functions, main block
- "Generate a JSON config file for database settings" → Create valid JSON with proper structure and comments
- "Write a markdown report summarizing the analysis" → Create structured .md file with sections, tables, findings
- "Create test data CSV with 100 user records" → Generate CSV with headers and realistic sample data
- "Generate SQL schema for user management" → Create .sql file with tables, indexes, constraints

OUTPUT FORMAT:
After creating files, return:
- Confirmation of files created with their paths
- Brief description of what each file contains
- Any important notes about the generated content""",
            ),
            "formatter": AgentDefinition(
                description="Specialized agent for formatting and structuring output in specific formats",
                prompt="""You are a formatting specialist. Your task is to transform content into specific output formats with precision.

CAPABILITIES:
- Converting content to requested formats: JSON, Markdown, CSV, XML, YAML, HTML
- Ensuring proper syntax and structure validation
- Maintaining data integrity during transformation
- Following format-specific best practices and standards
- Extracting only relevant fields when specified
- Schema validation for structured formats

CRITICAL RULES:
1. **NEVER add explanatory text** before or after the formatted output
2. **NEVER add phrases** like "Here is...", "The formatted output is...", "Excellent!", etc.
3. **START immediately** with the formatted content (e.g., `{` for JSON, `[` for arrays, or ```json for code blocks)
4. **END immediately** after the formatted content closes
5. **NO additional commentary** about the formatting process

EXAMPLES:
- "Format this data as JSON with id, name, email fields" → Return valid JSON array with only specified fields
- "Convert this table to CSV format" → Return properly escaped CSV with headers
- "Transform this data to XML" → Return well-formed XML with proper tags and structure
- "Format as markdown table" → Return markdown table with proper alignment
- "Output as YAML configuration" → Return valid YAML with proper indentation

OUTPUT FORMAT:
Return ONLY the formatted output. No explanatory text before or after. Just the formatted data.

WRONG (has explanatory text):
"Here is the JSON output:
```json
{"id": 1, "name": "test"}
```"

CORRECT (no explanatory text):
```json
{"id": 1, "name": "test"}
```""",
            ),
            "code_executor": AgentDefinition(
                description="Isolated agent for executing Python and Bash code with strict security controls",
                prompt="""You are a secure code execution specialist. Your task is to execute code safely within strict boundaries.

## SECURITY RESTRICTIONS - ABSOLUTE REQUIREMENTS

**FORBIDDEN - NEVER EXECUTE:**
- Any code accessing environment variables (os.environ, os.getenv(), process.env)
- System information gathering (uname, hostname, whoami, id, /proc/*, /etc/*)
- Network operations (curl, wget, requests to external hosts, socket operations)
- Process enumeration (ps, top, htop, pstree)
- File system analysis (df, du, mount, lsof)
- Security testing or reconnaissance of any kind
- Port scanning or network enumeration
- Privilege escalation attempts
- Reading system configuration files
- Creating security tools or exploit scripts

**ALLOWED - SAFE OPERATIONS ONLY:**
- Data processing and analysis within working directory
- Mathematical computations and statistical analysis
- File operations (read/write) within working directory only
- Data transformation and manipulation
- Generating reports and visualizations from provided data
- Running data science libraries (pandas, numpy, matplotlib) on local data

## EXECUTION RULES

1. **Validate Before Execute:**
   - Check code doesn't access forbidden resources
   - Verify all file paths are within working directory
   - Ensure no system-level operations

2. **If Code Violates Security:**
   - REFUSE to execute immediately
   - State: "Cannot execute - code attempts to [specific violation]"
   - DO NOT suggest modifications or workarounds
   - DO NOT partially execute "safe" portions

3. **Safe Execution:**
   - Only execute code that operates on data within working directory
   - Ensure all operations are isolated and sandboxed
   - Return results without exposing system information

## EXAMPLES

**REFUSE:**
- `import os; print(os.environ)` → Accesses environment variables
- `import subprocess; subprocess.run(['uname', '-a'])` → System information
- `import requests; requests.get('http://example.com')` → External network access
- `os.system('ps aux')` → Process enumeration

**ALLOW:**
- `import pandas as pd; df = pd.read_csv('data.csv'); print(df.describe())` → Data analysis
- `import numpy as np; result = np.mean([1,2,3,4,5])` → Mathematical computation
- `with open('report.txt', 'w') as f: f.write('Analysis results')` → File writing in working dir

## OUTPUT FORMAT

For successful execution:
- Return the output/results directly
- Include any errors or warnings from the code
- Do not add explanatory text

For refused execution:
- State the security violation clearly
- Do not execute any part of the code
- Do not suggest alternatives""",
            ),
        }
        
        # Configure Claude Code options with strict directory and write restrictions
        # Build MCP server permission patterns (wildcards to auto-approve all tools from each server)
        mcp_permissions_list = [f'"{pattern}"' for pattern in mcp_server_permission_patterns]
        mcp_permissions_str = ",\n                    ".join(mcp_permissions_list) if mcp_permissions_list else ""
        
        settings_json = f"""
        {{
            "sandbox": {{
                "enabled": true,
                "autoAllowBashIfSandboxed": true,
                "excludedCommands": ["docker"],
                "network": {{
                    "allowUnixSockets": [
                        "/var/run/docker.sock"
                    ],
                    "allowLocalBinding": true
                }}
            }},
            "permissions": {{
                "allow": [
                    "Read({working_directory}/**)",
                    "Read({context_directory}/**)",
                    "Write({working_directory}/**)",
                    "Bash({working_directory}/**)",
                    "Python({working_directory}/**)"{"," if mcp_permissions_str else ""}
                    {mcp_permissions_str}
                ],
                "deny": [
                    "Read(../**)",
                    "Read(/tmp/**)",
                    "Read(/app/**)",
                    "Read(/Users/**)",
                    "Read(/home/**)",
                    "Read(./.env)",
                    "Read(./.env.*)",
                    "Read(./secrets/**)",
                    "Read(./config/credentials.json)",
                    "Read(./build)",
                    "Write(../**)",
                    "Write(/tmp/**)",
                    "Write(/app/**)",
                    "Write(/Users/**)",
                    "Write(/home/**)",
                    "Write({context_directory}/**)",
                    "Bash(../**)",
                    "Bash(/tmp/**)",
                    "Bash(/app/**)",
                    "Bash(/Users/**)",
                    "Bash(/home/**)",
                    "Bash({context_directory}/**)",
                    "Python(../**)",
                    "Python(/tmp/**)",
                    "Python(/app/**)",
                    "Python(/Users/**)",
                    "Python(/home/**)",
                    "Python({context_directory}/**)"
                ]
            }}
        }}
        """
        
        # Create stderr callback to capture debug output
        # Store as instance variable so it can be accessed in _invoke_claude_agent
        self.stderr_messages = []
        
        def stderr_callback(message: str):
            """Callback that receives each line of stderr output from Claude Code."""
            self.stderr_messages.append(message)
            # Log stderr messages with appropriate level
            if "[ERROR]" in message or "error" in message.lower():
                logger.error(f"[CLAUDE_CODE_STDERR] {message}")
            elif "[WARN]" in message or "warning" in message.lower():
                logger.warning(f"[CLAUDE_CODE_STDERR] {message}")
            else:
                logger.debug(f"[CLAUDE_CODE_STDERR] {message}")
        
        # Buffer size configuration:
        # - Default: 20MB - sufficient for most document processing (PDFs, Excel files typically < 10MB)
        # - Configurable via MAX_BUFFER_SIZE_MB environment variable
        # - When exceeded: Claude Code will fail with buffer overflow error
        # - For larger files: Skills guide agents to use streaming/chunked processing
        # - Rationale: Prevents memory exhaustion while supporting typical workloads
        buffer_size_mb = int(os.getenv("MAX_BUFFER_SIZE_MB", "20"))

        # Extended thinking configuration:
        # - Enables Claude to show its reasoning process with thinking tokens
        # - Default: 10000 tokens for thinking budget
        # - Configurable via MAX_THINKING_TOKENS environment variable
        # - Set to 0 to disable extended thinking
        max_thinking_tokens = int(os.getenv("MAX_THINKING_TOKENS", "10000"))

        options_config = {
            "allowed_tools": allowed_tools,
            "system_prompt": system_prompt,
            "settings": settings_json,
            "cwd": working_directory,
            "add_dirs": [ context_directory ],
            "setting_sources": ["project"],
            "max_turns": self.recursion_limit,
            "max_buffer_size": buffer_size_mb * 1024 * 1024,
            "agents": subagents,  # Add subagents for specialized tasks
            "stderr": stderr_callback,  # Add stderr callback to capture debug output
            "max_thinking_tokens": max_thinking_tokens if max_thinking_tokens > 0 else None  # Enable extended thinking
        }

        # Add MCP servers if any are configured
        if mcp_servers:
            options_config["mcp_servers"] = mcp_servers

        self.action_agent_options = ClaudeAgentOptions(**options_config)
        logger.info(f"Configured {len(subagents)} subagents: {list(subagents.keys())}")
        logger.info(f"Skills enabled: Loading from project (.claude/skills/) and user (~/.claude/skills/) directories")
        if max_thinking_tokens > 0:
            logger.info(f"Extended thinking enabled with {max_thinking_tokens} token budget")

    def _serialize_content_block(self, block) -> dict:
        """Serialize a single content block to a dictionary."""
        if isinstance(block, TextBlock):
            return {
                "type": "TextBlock",
                "text": block.text
            }
        elif isinstance(block, ThinkingBlock):
            return {
                "type": "ThinkingBlock",
                "thinking": block.thinking,
                "signature": block.signature
            }
        elif isinstance(block, ToolUseBlock):
            return {
                "type": "ToolUseBlock",
                "id": block.id,
                "name": block.name,
                "input": block.input
            }
        elif isinstance(block, ToolResultBlock):
            return {
                "type": "ToolResultBlock",
                "tool_use_id": block.tool_use_id,
                "content": block.content,
                "is_error": block.is_error
            }
        else:
            # Fallback for unknown block types
            return {"type": type(block).__name__, "data": str(block)}
    
    def _serialize_message(self, message) -> str:
        """Convert Claude Code SDK message types to JSON string."""
        try:
            data = {}
            
            if isinstance(message, UserMessage):
                data = {
                    "type": "UserMessage",
                    "content": message.content if isinstance(message.content, str) else [
                        self._serialize_content_block(block) for block in message.content
                    ]
                }
            elif isinstance(message, AssistantMessage):
                data = {
                    "type": "AssistantMessage",
                    "content": [self._serialize_content_block(block) for block in message.content],
                    "model": message.model
                }
            elif isinstance(message, SystemMessage):
                data = {
                    "type": "SystemMessage",
                    "subtype": message.subtype,
                    "data": message.data
                }
            elif isinstance(message, ResultMessage):
                data = {
                    "type": "ResultMessage",
                    "subtype": message.subtype,
                    "duration_ms": message.duration_ms,
                    "duration_api_ms": message.duration_api_ms,
                    "is_error": message.is_error,
                    "num_turns": message.num_turns,
                    "session_id": message.session_id,
                    "total_cost_usd": message.total_cost_usd,
                    "usage": message.usage,
                    "result": message.result
                }
            else:
                # Fallback for unknown message types
                if hasattr(message, '__dict__'):
                    data = {"type": type(message).__name__, **message.__dict__}
                else:
                    data = {"type": type(message).__name__, "content": str(message)}
            
            return json.dumps(data, default=str)
        except Exception as e:
            logger.warning(f"Failed to serialize message: {e}")
            return json.dumps({"type": type(message).__name__, "content": str(message)})
    
    def _format_message_entry(self, message, message_id: str, thread_id: str) -> dict:
        """Create standardized message entry for both Redis and S3 storage."""
        # Get structured data from message
        if isinstance(message, (UserMessage, AssistantMessage, SystemMessage, ResultMessage)):
            # Use the new serializer for Claude Code SDK messages
            structured_data = self._serialize_message(message)
        elif hasattr(message, 'to_dict'):
            structured_data = message.to_dict()
        elif isinstance(message, dict):
            structured_data = message
        else:
            structured_data = {"type": type(message).__name__, "content": str(message)}
        
        # Create standardized message structure
        return {
            "id": thread_id,
            "message_id": message_id,
            "message_type": type(message).__name__,
            "timestamp": datetime.utcnow().isoformat(),
            "structured_data": structured_data
        }

    async def _get_redis_client(self) -> Optional[redis.Redis | RedisCluster]:
        """
        Redis client (async) that works with both standalone and cluster Redis instances.
        Automatically detects the Redis mode and uses the appropriate client.
        """
        if self.redis_client is None:
            try:
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
                logger.info(f"Initializing Redis client with URL: {redis_url}")

                # SSL configuration
                ssl_enabled = redis_url.startswith("rediss://")
                ssl_ca_certs = os.getenv("REDIS_SSL_CA_CERTS", "/etc/ssl/certs/ca-certificates.crt")
                ssl_cert_file = os.getenv("REDIS_SSL_CERT_FILE")
                ssl_key_file = os.getenv("REDIS_SSL_KEY_FILE")

                # First try to connect as standalone Redis
                try:
                    # Build connection parameters
                    connection_params = {
                        "socket_connect_timeout": 3,
                        "socket_timeout": 2,
                        "health_check_interval": 30,
                        "max_connections": 100,
                        "decode_responses": True,
                    }
                    
                    # Only add SSL parameters if SSL is enabled
                    if ssl_enabled:
                        connection_params.update({
                            "ssl": True,
                            "ssl_cert_reqs": "required",
                            "ssl_ca_certs": ssl_ca_certs,
                        })
                        if ssl_cert_file:
                            connection_params["ssl_certfile"] = ssl_cert_file
                        if ssl_key_file:
                            connection_params["ssl_keyfile"] = ssl_key_file
                    
                    self.redis_client = redis.from_url(redis_url, **connection_params)
                    
                    await self.redis_client.ping()
                    logger.info("Redis standalone connection successful!")
                    
                except Exception as standalone_error:
                    logger.info(f"Standalone Redis connection failed: {standalone_error}")
                    logger.info("Trying Redis cluster mode...")
                    
                    # If standalone fails, try cluster mode
                    cluster_params = {
                        "socket_connect_timeout": 3,
                        "socket_timeout": 2,
                        "health_check_interval": 30,
                        "max_connections": 100,
                        "decode_responses": True,
                    }
                    
                    # Only add SSL parameters if SSL is enabled
                    if ssl_enabled:
                        cluster_params.update({
                            "ssl": True,
                            "ssl_cert_reqs": "required",
                            "ssl_ca_certs": ssl_ca_certs,
                        })
                        if ssl_cert_file:
                            cluster_params["ssl_certfile"] = ssl_cert_file
                        if ssl_key_file:
                            cluster_params["ssl_keyfile"] = ssl_key_file
                    
                    self.redis_client = RedisCluster.from_url(redis_url, **cluster_params)
                    
                    await self.redis_client.ping()
                    logger.info("Redis cluster connection successful!")
                
            except Exception as e:
                logger.warning(f"Failed to initialize Redis client: {e}")
                logger.warning(f"Redis URL: {redis_url}")
                logger.warning(f"Error type: {type(e).__name__}")
                self.redis_client = None
                
        return self.redis_client

    async def close_redis_client(self) -> None:
        """Close the Redis client connection."""
        if self.redis_client is not None:
            await self.redis_client.close()
            self.redis_client = None

    async def _publish_claude_message(self, message):
        """Publish raw Claude Code message to Redis."""
        try:
            assistant_task_id = self.runtime_config["configurable"]["assistant_task_id"]
            redis_enabled = self.runtime_config["configurable"].get("redis_publishing_enabled", True)
        except (KeyError, TypeError):
            return
            
        # Skip Redis publishing if disabled
        if not redis_enabled:
            return
            
        redis_client = await self._get_redis_client()
        if not redis_client:
            return
            
        try:
            # Use shared message formatter
            message_entry = self._format_message_entry(message, "redis-stream", assistant_task_id)
            
            # Prepare Redis-specific data (serialize structured_data for Redis)
            message_data = {
                "task_id": message_entry["id"],
                "timestamp": message_entry["timestamp"],
                "message_type": message_entry["message_type"],
                "structured_data": json.dumps(message_entry["structured_data"])
            }
            
            # Publish to Redis stream using assistant_task_id as key
            stream_key = f"task_stream:{assistant_task_id}"
            await redis_client.xadd(stream_key, message_data)
            
            # Set expiration for the stream (1 hour)
            await redis_client.expire(stream_key, 3600)
            
        except Exception as e:
            logger.warning(f"Failed to publish Claude message: {e}")


    async def _invoke_claude_agent_with_retry(self, level, user_prompt, options, max_retries: int = 3):
        """
        Invoke Claude Code agent with automatic retry on failure.
        
        On failure, the error message is passed to the next attempt so Claude Code
        can adapt its approach (e.g., use streaming for large files instead of Read tool).
        
        Args:
            level: Logging level identifier (e.g., 'MAIN_AGENT')
            user_prompt: The prompt to send to Claude Code
            options: ClaudeAgentOptions for the query
            max_retries: Maximum number of retry attempts (default: 3)
            
        Returns:
            Tuple of (result_string, messages_list)
        """
        last_error = None
        all_messages = []
        
        for attempt in range(1, max_retries + 1):
            # Build prompt with error context from previous attempt
            current_prompt = user_prompt
            if last_error and attempt > 1:
                error_context = f"""[RETRY ATTEMPT {attempt}/{max_retries}]
The previous attempt failed with the following error:
---
{last_error}
---
Please try a different approach to complete the task. Consider:
- If "PDF too large" error: Use Python with pypdf/pdfplumber to process page-by-page instead of the Read tool
- If memory error: Process data in smaller chunks
- If command failed: Try an alternative command or approach
- If file not found: Verify the file path and try again

Original request: {user_prompt}
"""
                current_prompt = error_context
                logger.info(f"[{level}] Retry attempt {attempt}/{max_retries} with error context from previous failure")
            
            # Call the actual implementation
            result, messages = await self._invoke_claude_agent(level, current_prompt, options)
            all_messages.extend(messages)
            
            # Check if task was cancelled - don't retry on cancellation
            if result == TASK_CANCELLED_MESSAGE:
                logger.info(f"[{level}] Task cancelled - not retrying")
                return result, messages
            
            # Check if result indicates an error that should trigger retry
            # Check for default error message or explicit failure indicators
            is_error = result and (
                result == DEFAULT_ERROR_MESSAGE or 
                "something went wrong" in result.lower() or
                "Claude Code execution failed" in result
            )
            
            if is_error:
                last_error = result
                logger.warning(f"[{level}] Attempt {attempt}/{max_retries} failed: {result[:200]}...")
                if attempt < max_retries:
                    logger.info(f"[{level}] Will retry with error context...")
                    continue
                else:
                    # Final attempt also failed
                    logger.error(f"[{level}] All {max_retries} attempts failed.")
                    return result, all_messages
            
            # Success - return the result
            logger.info(f"[{level}] Successfully completed on attempt {attempt}/{max_retries}")
            return result, messages
        
        # Should not reach here, but just in case
        return DEFAULT_ERROR_MESSAGE, all_messages


    def _get_options_with_env_variables(self, options: ClaudeAgentOptions) -> ClaudeAgentOptions:
        """
        Create a new options object with environment variables from runtime config.
        
        This injects agent-configured environment variables into the Claude Code SDK settings.
        The env variables are passed to Claude Code via the settings.env field as per:
        https://code.claude.com/docs/en/settings
        
        Args:
            options: The base ClaudeAgentOptions to extend
            
        Returns:
            ClaudeAgentOptions with env variables injected into settings
        """
        # Get env variables from runtime config
        env_variables = {}
        if self.runtime_config:
            env_variables = self.runtime_config.get("configurable", {}).get("env_variables", {})
        
        if not env_variables:
            return options  # No env variables to inject
        
        try:
            # Parse existing settings JSON and add env variables
            existing_settings = json.loads(options.settings) if options.settings else {}
            # Merge with existing env variables, with new ones taking precedence
            existing_env = existing_settings.get("env", {})
            existing_env.update(env_variables)
            existing_settings["env"] = existing_env
            
            # Update settings on the options object directly
            options.settings = json.dumps(existing_settings)
            
            logger.info(f"Injected {len(env_variables)} environment variables into Claude Code settings: {list(env_variables.keys())}")
            return options
            
        except Exception as e:
            logger.warning(f"Failed to inject environment variables into settings: {e}")
            return options  # Return original options on failure

    # NOTE: @traceable decorator removed - langsmith is no longer used
    # Use Phoenix for tracing if needed
    async def _invoke_claude_agent(self, level, user_prompt, options):
        """Invoke Claude Code SDK with the given prompt and options.

        Args:
            level: Log level identifier (e.g., 'MAIN_AGENT')
            user_prompt: The prompt to send to Claude
            options: ClaudeAgentOptions configuration
        """
        logger.info("Starting Claude Code query execution...")
        query_start_time = time.time()
        
        # Inject environment variables from runtime config into options
        options_with_env = self._get_options_with_env_variables(options)

        # Use Claude Code SDK to retrieve context - capture final result only
        final_result = ""
        message_count = 0
        tool_usage_count = 0

        messages = []
        query_generator = None
        
        try:
            query_generator = query(
                    prompt=user_prompt,
                    options=options_with_env
            )
            async for message in query_generator:
                current_time = time.time()
                if self.cancellation_check and (current_time - self._last_cancel_check) >= self._cancel_check_interval:
                    self._last_cancel_check = current_time
                    try:
                        is_cancelled = await self.cancellation_check()
                        if is_cancelled:
                            logger.info(f"[{level}] Task cancelled - aborting Claude Code execution")
                            # Gracefully close the query generator
                            try:
                                await query_generator.aclose()
                            except Exception as close_error:
                                # Suppress anyio cancel scope errors during cleanup
                                logger.debug(f"[{level}] Query generator close error (expected): {close_error}")
                            # Return a cancellation response
                            return TASK_CANCELLED_MESSAGE, messages
                    except Exception as cancel_check_error:
                        logger.warning(f"[{level}] Error checking cancellation: {cancel_check_error}")
                
                message_count += 1
                elapsed = time.time() - query_start_time
                logger.info(
                    f"[{level}] Message #{message_count} received after {elapsed:.2f}s: {type(message).__name__}")

                # Publish raw Claude Code message directly
                await self._publish_claude_message(message)

                if isinstance(message, AssistantMessage):
                    # Process assistant message
                    current_response = ""
                    logger.info(f"[{level}] Processing AssistantMessage with {len(message.content)} blocks")

                    for i, block in enumerate(message.content):
                        if isinstance(block, TextBlock):
                            text_content = block.text
                            current_response += text_content
                            logger.info(f"[{level}] Text Block #{i + 1} ({len(text_content)} chars):")
                            logger.info(f"[{level}] Text Content: {text_content}")

                        elif isinstance(block, ToolUseBlock):
                            tool_usage_count += 1
                            logger.info(
                                f"[{level}] Tool Block #{i + 1} - Tool #{tool_usage_count}: {block.name} (id: {block.id})")

                            # Log detailed tool input and check for security violations
                            if block.name == "Bash":
                                command = block.input.get("command", "")
                                logger.info(f"[{level}] Bash Input:")
                                logger.info(f"[{level}] Command: {command}")
                                
                                # Detect security violations
                                is_violation, violation_type = self._detect_security_violation(command)
                                if is_violation:
                                    logger.warning(f"[{level}] SECURITY VIOLATION DETECTED: {violation_type}")
                                    logger.warning(f"[{level}] Prohibited command: {command}")
                                    
                            elif block.name == "Python":
                                code = block.input.get("code", "")
                                logger.info(f"[{level}] Python Input:")
                                logger.info(f"[{level}] Code: {code[:200]}...")  # Log first 200 chars
                                
                                # Detect security violations in Python code
                                is_violation, violation_type = self._detect_security_violation(code)
                                if is_violation:
                                    logger.warning(f"[{level}] SECURITY VIOLATION DETECTED: {violation_type}")
                                    logger.warning(f"[{level}] Prohibited code pattern detected")
                                    
                            elif block.name == "Read":
                                file_path = block.input.get("path", "")
                                logger.info(f"[{level}] Read Input:")
                                logger.info(f"[{level}] File Path: {file_path}")
                            else:
                                logger.info(f"[{level}] Tool Input: {block.input}")
                        
                        elif isinstance(block, ToolResultBlock):
                            # Capture tool execution results including stderr
                            logger.info(f"[{level}] ========== TOOL RESULT BLOCK #{i + 1} ==========")
                            logger.info(f"[{level}] Tool Use ID: {block.tool_use_id}")
                            
                            # Log all attributes of the block for debugging
                            block_attrs = dir(block)
                            logger.info(f"[{level}] Available attributes: {[attr for attr in block_attrs if not attr.startswith('_')]}")
                            
                            # Check for content attribute (this usually contains the output)
                            if hasattr(block, 'content'):
                                content = block.content
                                logger.info(f"[{level}] Content type: {type(content)}")
                                if isinstance(content, str):
                                    logger.info(f"[{level}] Content: {content[:1000]}...")  # First 1000 chars
                                elif isinstance(content, list):
                                    for idx, item in enumerate(content):
                                        logger.info(f"[{level}] Content item {idx}: {type(item).__name__}")
                                        if hasattr(item, 'text'):
                                            logger.info(f"[{level}] Text: {item.text[:500]}...")
                                else:
                                    logger.info(f"[{level}] Content: {str(content)[:1000]}...")
                            
                            # Check if there's stderr output
                            if hasattr(block, 'stderr') and block.stderr:
                                logger.warning(f"[{level}] ========== STDERR OUTPUT ==========")
                                logger.warning(f"[{level}] {block.stderr}")
                                logger.warning(f"[{level}] =====================================")
                            
                            # Log stdout if present
                            if hasattr(block, 'stdout') and block.stdout:
                                logger.info(f"[{level}] STDOUT: {block.stdout[:500]}...")  # Log first 500 chars
                            
                            # Check for errors
                            if hasattr(block, 'is_error') and block.is_error:
                                error_msg = getattr(block, 'content', 'Unknown error')
                                logger.error(f"[{level}] ========== TOOL EXECUTION ERROR ==========")
                                logger.error(f"[{level}] {error_msg}")
                                logger.error(f"[{level}] ============================================")
                            
                            logger.info(f"[{level}] =============================================")

                        else:
                            logger.info(f"[{level}] Non-text/tooluse block #{i + 1}: {type(block).__name__}")

                    final_result = current_response if current_response else final_result  # Keep only the latest/final response
                    logger.info(f"[{level}] Updated final_result ({len(final_result)} chars): {final_result}")

                elif isinstance(message, ResultMessage):
                    logger.info(f"[{level}] Claude Code completed after {elapsed:.2f}s")
                    if message.total_cost_usd > 0:
                        logger.info(f"[{level}] Cost: ${message.total_cost_usd:.4f}")
                    if hasattr(message, 'num_turns'):
                        logger.info(f"[{level}] Turns: {message.num_turns}")

                    # Log final result details
                    logger.info(f"[{level}] Context Retrieval Summary:")
                    logger.info(f"[{level}] - Total Messages: {message_count}")
                    logger.info(f"[{level}] - Tool Uses: {tool_usage_count}")
                    logger.info(f"[{level}] - Duration: {elapsed:.2f}s")

                else:
                    # Log any other message types for debugging
                    logger.info(f"[{level}] Other message type: {type(message).__name__}")
                    logger.info(f"[{level}] Message content: {str(message)}")
                    
                    # Check if this message has error information
                    if hasattr(message, '__dict__'):
                        msg_dict = message.__dict__
                        if 'error' in msg_dict or 'stderr' in msg_dict:
                            logger.error(f"[{level}] ERROR/STDERR in message: {msg_dict}")
                
                messages.append(message)

            logger.info(f"[{level}] Stats: {message_count} messages, {tool_usage_count} tool uses")
            
            # Log stderr summary
            if hasattr(self, 'stderr_messages') and self.stderr_messages:
                error_count = sum(1 for msg in self.stderr_messages if "error" in msg.lower() or "[ERROR]" in msg)
                warning_count = sum(1 for msg in self.stderr_messages if "warning" in msg.lower() or "[WARN]" in msg)
                logger.info(f"[{level}] Captured {len(self.stderr_messages)} stderr lines ({error_count} errors, {warning_count} warnings)")
                
                # Log first few stderr messages if there were errors
                if error_count > 0:
                    logger.warning(f"[{level}] First stderr error messages:")
                    error_msgs = [msg for msg in self.stderr_messages if "error" in msg.lower() or "[ERROR]" in msg]
                    for msg in error_msgs[:3]:  # Show first 3 errors
                        logger.warning(f"[{level}]   {msg[:200]}...")  # Truncate long messages

            if final_result.strip():
                result_length = len(final_result.strip())
                logger.info(f"[{level}] Retrieved context: {result_length} characters")
                return f"{final_result.strip()}", messages
            else:
                logger.warning("[{level}] No context retrieved from Claude Code")
                return f"[{level}] No context retrieved from Claude Code", messages  # Return empty string instead of placeholder message
        
        except Exception as e:
            elapsed = time.time() - query_start_time
            logger.error(f"[{level}] ========== CLAUDE CODE EXECUTION FAILED ==========")
            logger.error(f"[{level}] Execution time: {elapsed:.2f}s")
            logger.error(f"[{level}] Error type: {type(e).__name__}")
            logger.error(f"[{level}] Error message: {str(e)}")
            
            # Log full traceback for debugging
            import traceback
            logger.error(f"[{level}] Full Traceback:")
            logger.error(traceback.format_exc())
            
            # Check if error has stderr attribute
            if hasattr(e, 'stderr'):
                logger.error(f"[{level}] STDERR from exception attribute: {e.stderr}")
            
            # Parse exception message for stderr details
            error_str = str(e)
            if "exit code" in error_str.lower():
                logger.error(f"[{level}] ========== COMMAND EXECUTION FAILED ==========")
                # Extract exit code if present
                import re
                exit_code_match = re.search(r'exit code[:\s]+(\d+)', error_str, re.IGNORECASE)
                if exit_code_match:
                    logger.error(f"[{level}] Exit Code: {exit_code_match.group(1)}")
                
                # Check if stderr details are mentioned
                if "stderr" in error_str.lower() or "error output" in error_str.lower():
                    logger.error(f"[{level}] STDERR DETAILS: Check tool result blocks above for stderr output")
                    logger.error(f"[{level}] Note: The actual stderr content should be in ToolResultBlock messages")
            
            # Check exception args for additional details
            if hasattr(e, 'args') and e.args:
                logger.error(f"[{level}] Exception args: {e.args}")
            
            # Log any messages captured before failure
            if messages:
                logger.error(f"[{level}] Messages captured before failure: {len(messages)}")
                # Log the last few messages for context
                for i, msg in enumerate(messages[-3:], 1):
                    logger.error(f"[{level}] Last message #{i}: {type(msg).__name__}")
            
            logger.error(f"[{level}] =================================================")
            
            # Return default error message (don't expose internal error details to user)
            return DEFAULT_ERROR_MESSAGE, messages


    def _setup_workflow(self):
        """Initialize workflow (replaces LangGraph StateGraph).

        NOTE: LangGraph removed - using direct Claude SDK calls.
        The workflow_app is set to a marker object for backward compatibility checks.
        """
        self.workflow_app = True  # Marker for "initialized"
        logger.info("Workflow initialized (Claude SDK direct mode)")

    def _create_graph_workflow(self):
        """DEPRECATED: Use _setup_workflow instead. Kept for reference.

        NOTE: This method is no longer called. The StateGraph has been replaced
        with direct Claude SDK calls in _execute_agent().
        """
        pass  # No longer used

    async def _execute_agent(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Main agent - Generate and format final response using Claude Code SDK with enriched context.

        This method replaces the LangGraph agent_action inner function.
        """
        logger.info("---MAIN AGENT - CLAUDE CODE EXECUTION WITH OUTPUT FORMATTING---")

        question = state["question"]
        context = state["context"]
        output_format = state.get('output_format', '')
        prev_messages = state.get("messages", [])

        # Helper function to save messages and return state
        async def save_and_return(final_messages: List[Dict[str, Any]], generation_text: str) -> Dict[str, Any]:
            # Validate final_messages is a list
            if not isinstance(final_messages, list):
                logger.error(f"final_messages is not a list, got type: {type(final_messages)}. Converting to list.")
                final_messages = [] if final_messages is None else [final_messages]

            # Save all messages to S3
            try:
                await self.save_messages_to_s3(final_messages)
                logger.info(f"Successfully saved {len(final_messages)} messages to S3")
            except Exception as e:
                logger.error(f"Failed to save messages to S3: {str(e)}", exc_info=True)

            # Save generated artifacts to S3
            try:
                await self.save_artifacts_to_s3()
                logger.info("Successfully saved artifacts to S3")
            except Exception as e:
                logger.error(f"Failed to save artifacts to S3: {str(e)}", exc_info=True)

            return {
                "question": question,
                "context": context,
                "messages": final_messages,
                "generation": generation_text,
                "output_format": output_format
            }

        # Check if Claude Code SDK is available
        if not CLAUDE_CODE_SDK_AVAILABLE:
            logger.warning("Claude Code SDK not available, falling back to error response")
            error_message = "Claude Code SDK is not available for final response generation"
            final_messages = prev_messages + [{"role": "assistant", "content": error_message}]
            return await save_and_return(final_messages, error_message)

        try:
            start_time = time.time()
            logger.info("Starting Claude Code final response generation...")

            # Create user prompt with question, context, and format requirements
            # Encourage delegation to formatter subagent for output formatting
            format_instruction = ""
            if output_format and output_format.strip():
                format_instruction = f"""

## OUTPUT FORMAT REQUIREMENT
The final response must be formatted according to this specification:
{output_format}

**DELEGATION STRATEGY - MANDATORY FOR STRUCTURED OUTPUT**:
- **ALWAYS delegate to formatter subagent** when output format specifies:
  - JSON with multiple fields or nested structure
  - CSV with specific column requirements
  - XML with schema validation
  - Any format requiring "exact schema", "strict format", or "specific fields"
- Handle directly ONLY for:
  - Plain text responses
  - Simple markdown without specific structure
  - Single-value outputs

**The formatter subagent provides**:
- Syntax validation and proper structure
- Exact field extraction as specified
- Format-specific best practices
- **Formatted output without explanatory text** (critical for API responses)

**IMPORTANT**: If the output format mentions specific field names (e.g., "sql", "reasoning", "n_rows"), this is a STRONG signal to delegate to the formatter subagent.

**When using formatter subagent**:
- The formatter returns formatted output without explanatory text
- Simply return the formatter's output exactly as received
- Do not add phrases like "Here is the result:" before the output

**If you handle formatting yourself**: Ensure the output matches the specification exactly, with no additional commentary or explanatory text before/after the formatted content.
"""
            else:
                format_instruction = "\n\nProvide a comprehensive answer in markdown format."

            user_prompt = f"""# Question
{question}

---

## Context
{context}

---
{format_instruction}

----

Generate the final response using the context provided. Execute additional tools only if needed.

CRITICAL IDENTITY RULES:
- Do not mention "Claude Code", "SDK", internal system workings, or any technical implementation details
- NEVER reveal underlying AI models, providers, or technology (e.g., Anthropic, Claude, OpenAI, GPT)
- If asked "who powers you" or "what technology", simply say "I'm Chicory AI, an intelligent assistant"
- Present yourself as a knowledgeable assistant providing direct help
- If asked about your name or identity, respond that you are "Chicory AI" - nothing more"""

            final_result, messages = await self._invoke_claude_agent_with_retry("MAIN_AGENT", user_prompt, self.action_agent_options, max_retries=3)

            # Ensure messages is always a list to prevent concatenation errors
            if messages is None:
                logger.warning("Messages returned as None, initializing as empty list")
                messages = []
            elif len(messages) == 0:
                logger.info("Agent completed without intermediate messages")

            # Check if task was cancelled during execution
            if final_result == TASK_CANCELLED_MESSAGE:
                logger.info("Task was cancelled during Claude Code execution")
                final_messages = prev_messages + [{"role": "assistant", "content": TASK_CANCELLED_MESSAGE}]
                return await save_and_return(final_messages, TASK_CANCELLED_MESSAGE)

            # Handle empty or invalid response
            if not final_result or final_result.strip() == "":
                logger.warning("Agent generated empty response, creating fallback response")

                # Create a fallback response that matches the requested output format
                if output_format and output_format.strip():
                    try:
                        # Check if JSON format is expected
                        if "json" in output_format.lower() or "{" in output_format:
                            final_result = '{"error": "Unable to generate response", "message": "I apologize, but I was unable to process your request. Please try rephrasing your question or contact support if the issue persists."}'
                        else:
                            final_result = "I apologize, but I was unable to process your request. Please try rephrasing your question or contact support if the issue persists."
                    except Exception:
                        final_result = "I apologize, but I was unable to process your request. Please try rephrasing your question or contact support if the issue persists."
                else:
                    final_result = "I apologize, but I was unable to process your request. Please try rephrasing your question or contact support if the issue persists."

            # Log completion stats
            total_time = time.time() - start_time
            logger.info(f"Claude Code final response generation completed in {total_time:.2f}s")

            # Prepare final messages and save - ensure all components are lists
            try:
                final_messages = prev_messages + messages + [{"role": "assistant", "content": final_result}]
            except TypeError as te:
                logger.error(f"Error concatenating messages: {te}. prev_messages type: {type(prev_messages)}, messages type: {type(messages)}")
                # Fallback: create a minimal valid message list
                final_messages = (prev_messages if isinstance(prev_messages, list) else []) + [{"role": "assistant", "content": final_result}]

            return await save_and_return(final_messages, final_result)

        except Exception as e:
            # Log full internal details, but return a user-safe error message
            logger.error("Error in Claude Code final response generation", exc_info=True)

            if output_format and output_format.strip():
                try:
                    # If JSON-like output is expected, return a minimal JSON error object
                    if "json" in output_format.lower() or "{" in output_format:
                        user_safe_message = json.dumps({
                            "error": "internal_error",
                            "message": DEFAULT_ERROR_MESSAGE
                        })
                    else:
                        user_safe_message = DEFAULT_ERROR_MESSAGE
                except Exception as format_error:
                    logger.warning(f"Failed to format error message: {format_error}")
                    user_safe_message = DEFAULT_ERROR_MESSAGE
            else:
                user_safe_message = DEFAULT_ERROR_MESSAGE

            # Ensure prev_messages is a list before concatenation
            try:
                final_messages = prev_messages + [{"role": "assistant", "content": user_safe_message}]
            except TypeError as te:
                logger.error(f"Error concatenating prev_messages in exception handler: {te}. prev_messages type: {type(prev_messages)}")
                # Fallback: create a minimal valid message list
                final_messages = (prev_messages if isinstance(prev_messages, list) else []) + [{"role": "assistant", "content": user_safe_message}]

            return await save_and_return(final_messages, user_safe_message)

    # ========================================================================
    # PUBLIC API METHODS
    # ========================================================================

    def get_graph(self, xray=True):
        """DEPRECATED: LangGraph removed. Returns None for compatibility."""
        logger.warning("get_graph() is deprecated - LangGraph has been removed")
        return None

    def invoke(self, query: str, thread_id: str = None) -> Dict[str, Any]:
        """Invoke the workflow with a query.

        NOTE: Now uses direct Claude SDK calls instead of LangGraph workflow.
        """
        if not self.workflow_app:
            raise RuntimeError("Workflow not initialized. Call initialize() first.")

        # Generate thread_id if not provided
        if thread_id is None:
            thread_id = f"{self.user}_{self.project}_{int(datetime.now().timestamp())}"

        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }

        # Store runtime config
        self.runtime_config = config

        # Use asyncio to run the async method
        import asyncio
        state = {"question": query, "context": "", "messages": [], "generation": "", "output_format": ""}
        result = asyncio.get_event_loop().run_until_complete(self._execute_agent(state))
        return result

    async def astream(self, input: dict = None, config: dict = None, cancellation_check: Optional[Callable[[], Awaitable[bool]]] = None):
        """Async Stream the workflow response.

        NOTE: Now uses direct Claude SDK calls instead of LangGraph workflow.
        Yields dictionaries in the same format as LangGraph for backward compatibility:
        {"agent_node": {"generation": str, "messages": list, ...}}

        Args:
            input: Input dictionary with question, context, etc.
            config: Configuration dictionary with thread_id, etc.
            cancellation_check: Optional async callable that returns True if task is cancelled.
                               This is called periodically (every 5 seconds) during Claude Code execution.
        """
        if not self.workflow_app:
            raise RuntimeError("Workflow not initialized. Call initialize() first.")

        # Use provided config or create default
        if config is None:
            thread_id = f"{self.user}_{self.project}_{int(datetime.now().timestamp())}"
            config = {
                "configurable": {
                    "thread_id": thread_id
                }
            }

        # Store the runtime config for use throughout the workflow
        self.runtime_config = config

        # Store the cancellation callback and reset rate limiting timer
        self.cancellation_check = cancellation_check
        self._last_cancel_check = 0  # Reset to ensure first check happens immediately

        # Build state from input
        state = {
            "question": input.get("question", "") if input else "",
            "context_flag": input.get("context_flag", True) if input else True,
            "context": input.get("context", "") if input else "",
            "messages": [],
            "generation": "",
            "output_format": input.get("output_format", "") if input else ""
        }

        # Execute agent directly (replaces LangGraph workflow)
        result = await self._execute_agent(state)

        # Yield result in LangGraph-compatible format
        yield {"agent_node": result}

    def stream(self, input: dict = None, config: dict = None):
        """Stream the workflow response.

        NOTE: Now uses direct Claude SDK calls instead of LangGraph workflow.
        Uses asyncio to wrap the async execution.
        """
        if not self.workflow_app:
            raise RuntimeError("Workflow not initialized. Call initialize() first.")

        # Use provided config or create default
        if config is None:
            thread_id = f"{self.user}_{self.project}_{int(datetime.now().timestamp())}"
            config = {
                "configurable": {
                    "thread_id": thread_id
                }
            }

        # Store runtime config
        self.runtime_config = config

        # Build state
        state = {
            "question": input.get("question", "") if input else "",
            "context_flag": input.get("context_flag", True) if input else True,
            "context": input.get("context", "") if input else "",
            "messages": [],
            "generation": "",
            "output_format": input.get("output_format", "") if input else ""
        }

        # Execute and yield result in LangGraph-compatible format
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(self._execute_agent(state))
        yield {"agent_node": result}

    async def save_messages_to_s3(self, messages: List[Any]) -> bool:
        """Save messages to S3 with retry logic and enhanced error handling."""
        max_retries = 3
        retry_delay = 1  # Start with 1 second delay
        
        for attempt in range(max_retries):
            try:
                s3_client = _get_s3_client()
                bucket_name = os.environ.get('TASK_AUDIT_TRAIL_S3_BUCKET_NAME')

                if not bucket_name:
                    logger.warning("TASK_AUDIT_TRAIL_S3_BUCKET_NAME environment variable not set, skipping S3 save")
                    return False

                # Use assistant_task_id for S3 key path
                assistant_task_id = self.runtime_config["configurable"]["assistant_task_id"]
                s3_key = f"{self.project.lower()}/{self.agent_id.lower()}/{assistant_task_id}/messages.json"
                
                # Serialize messages using shared formatter
                serialized_messages = []
                for i, msg in enumerate(messages):
                    message_entry = self._format_message_entry(msg, i, assistant_task_id)
                    serialized_messages.append(message_entry)
            
                # Upload to S3 with retry logic
                s3_client.put_object(
                    Bucket=bucket_name,
                    Key=s3_key,
                    Body=json.dumps(serialized_messages, default=str),
                    ContentType='application/json'
                )
                logger.info(f"Saved {len(serialized_messages)} messages to S3: {s3_key}")
                return True
                
            except ClientError as e:
                if attempt < max_retries - 1:
                    retry_delay *= 2
                    logger.warning(f"S3 save attempt {attempt+1} failed, retrying in {retry_delay:.2f}s: {str(e)}")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"Failed to save to S3 after {max_retries} attempts: {str(e)}")
                    return False
            except Exception as e:
                logger.error(f"Unexpected error saving messages to S3: {str(e)}")
                return False

    async def save_artifacts_to_s3(self) -> bool:
        """Save generated artifacts from working directory to S3."""
        max_retries = 3
        retry_delay = 1
        
        try:
            bucket_name = os.environ.get('TASK_AUDIT_TRAIL_S3_BUCKET_NAME')
            if not bucket_name:
                logger.warning("TASK_AUDIT_TRAIL_S3_BUCKET_NAME not set, skipping artifact upload")
                return False
            
            assistant_task_id = self.runtime_config["configurable"]["assistant_task_id"]
            # Reconstruct working directory path without cleanup
            project_id = self.project.lower()
            agent_id = self.agent_id.lower()
            working_directory = os.path.join("/tmp", "chicory", project_id, agent_id, "work_dir")
            
            # Check if working directory exists
            if not os.path.exists(working_directory):
                logger.info("No working directory found, skipping artifact upload")
                return True
            
            # Collect all files from working directory (excluding irrelevant folders)
            artifact_files = []

            for root, dirs, files in os.walk(working_directory):
                # Skip excluded directories
                dirs[:] = [d for d in dirs if d not in ARTIFACT_SKIP_DIRS]
                
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, working_directory)
                    artifact_files.append((file_path, rel_path))
            
            if not artifact_files:
                logger.info("No artifacts found in working directory")
                return True

            s3_client = _get_s3_client()
            uploaded_count = 0
            
            # Upload each artifact
            for file_path, rel_path in artifact_files:
                s3_key = f"{self.project.lower()}/{self.agent_id.lower()}/{assistant_task_id}/artifacts/{rel_path}"
                
                # Determine content type based on file extension
                content_type, _ = mimetypes.guess_type(file_path)
                if not content_type:
                    content_type = 'application/octet-stream'
                
                # Upload with retry logic
                file_retry_delay = retry_delay  # Use local copy for this file
                for attempt in range(max_retries):
                    try:
                        with open(file_path, 'rb') as f:
                            s3_client.put_object(
                                Bucket=bucket_name,
                                Key=s3_key,
                                Body=f.read(),
                                ContentType=content_type
                            )
                        uploaded_count += 1
                        logger.info(f"Uploaded artifact to S3: {s3_key}")
                        break
                    except ClientError as e:
                        if attempt < max_retries - 1:
                            file_retry_delay *= 2
                            logger.warning(f"S3 upload attempt {attempt+1} failed for {rel_path}, retrying: {str(e)}")
                            await asyncio.sleep(file_retry_delay)
                        else:
                            logger.error(f"Failed to upload {rel_path} after {max_retries} attempts: {str(e)}")
                    except Exception as e:
                        logger.error(f"Unexpected error uploading {rel_path}: {str(e)}")
                        break
            
            logger.info(f"Successfully uploaded {uploaded_count}/{len(artifact_files)} artifacts to S3")
            return uploaded_count > 0
            
        except Exception as e:
            logger.error(f"Error saving artifacts to S3: {str(e)}")
            return False
    
    async def get_tool_summary(self) -> Dict[str, Any]:
        """Get comprehensive summary of available tools."""
        # Get MCP configuration
        mcp_servers = self.mcp_config.get("servers", {})
        available_data_source_types = self.mcp_config.get("available_data_source_types", [])
        
        # Base tools are always available
        base_tool_count = 4  # Python, Bash, Read, Write
        
        summary = {
            "total_tools": base_tool_count,  # Will be updated after tool discovery
            "load_time": f"{self.load_time:.2f}s",
            "init_time": f"{self.init_time:.2f}s",
            "mcp_servers": list(mcp_servers.keys()),
            "available_data_source_types": available_data_source_types,
            "base_tools": base_tool_count,
            "categories": {
                "base": base_tool_count,
                "mcp": 0  # Will be updated after tool discovery
            }
        }

        return summary

    # Removed add_user_tool method - MCP tools are now pre-configured in main_managed.py

async def initialize_agent(user: str,
                     project: str,
                     mcp_config: Dict[str, Any] = None,
                     phoenix_project: Optional[str] = None,
                     agent_id: str = None,
                     recursion_limit: int = 100) -> LLMAgentArchitecture:
    """
    Initialize the LLM Agent Architecture with pre-built MCP configuration.

    Args:
        user: User identifier
        project: Project identifier
        mcp_config: Pre-built MCP configuration with servers and allowed tools
        phoenix_project: Optional Phoenix project name
        agent_id: Optional agent identifier

    Returns:
        Initialized agent architecture

    Example:
        # MCP config is now built in main_managed.py
        mcp_config = {
            "servers": {"db_mcp_server": {"url": "...", "type": "http"}},
            "available_data_source_types": ["databricks", "snowflake"]
        }
        agent = initialize_agent("user123", "project_alpha", mcp_config)
    """
    if mcp_config is None:
        mcp_config = {"servers": {}, "available_data_source_types": []}

    agent_arch = LLMAgentArchitecture(
        project=project,
        user=user,
        agent_id=agent_id,
        mcp_config=mcp_config,
        phoenix_project=phoenix_project,
        recursion_limit=recursion_limit
    )

    if await agent_arch.initialize():
        summary = await agent_arch.get_tool_summary()
        logger.info(f"Agent initialized in {summary['load_time']} with {summary['total_tools']} tools")
        print(f"Agent initialized in {summary['load_time']} with {summary['total_tools']} tools")
        return agent_arch
    else:
        raise RuntimeError("Failed to initialize agent architecture")
