import os
import subprocess
import traceback
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.core.config import settings

app = FastAPI(
    title="Agent Service",
    description="Claude Agent SDK service for conversation management",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)


def _run_startup_diagnostics():
    """Run diagnostics to help debug Claude CLI issues."""
    print("[STARTUP] ========== DIAGNOSTICS ==========")

    try:
        # Check ANTHROPIC_API_KEY
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if api_key:
            print(f"[STARTUP] ANTHROPIC_API_KEY: {api_key[:8]}...{api_key[-4:]} ({len(api_key)} chars)")
        else:
            print("[STARTUP] WARNING: ANTHROPIC_API_KEY not set!")

        # Check home directory
        home = Path.home()
        print(f"[STARTUP] HOME directory: {home}")
        print(f"[STARTUP] HOME exists: {home.exists()}")

        # Check .claude directory
        claude_dir = home / ".claude"
        print(f"[STARTUP] .claude directory: {claude_dir}")
        print(f"[STARTUP] .claude exists: {claude_dir.exists()}")
        if claude_dir.exists():
            print(f"[STARTUP] .claude is_dir: {claude_dir.is_dir()}")
            print(f"[STARTUP] .claude writable: {os.access(claude_dir, os.W_OK)}")
            try:
                contents = list(claude_dir.iterdir())
                print(f"[STARTUP] .claude contents: {[c.name for c in contents[:10]]}")
            except Exception as e:
                print(f"[STARTUP] .claude list error: {e}")
        else:
            # Try to create it
            print("[STARTUP] .claude does not exist, attempting to create...")
            try:
                claude_dir.mkdir(parents=True, exist_ok=True)
                print(f"[STARTUP] .claude created successfully")
            except Exception as e:
                print(f"[STARTUP] ERROR: Failed to create .claude: {e}")

        # Check workspace directory
        workspace = Path(settings.WORKSPACE_BASE_PATH)
        print(f"[STARTUP] Workspace: {workspace}")
        print(f"[STARTUP] Workspace exists: {workspace.exists()}")
        if workspace.exists():
            print(f"[STARTUP] Workspace writable: {os.access(workspace, os.W_OK)}")

        # Check Claude CLI
        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            print(f"[STARTUP] Claude CLI version: {result.stdout.strip()}")
            if result.stderr:
                print(f"[STARTUP] Claude CLI stderr: {result.stderr.strip()}")
        except FileNotFoundError:
            print("[STARTUP] ERROR: Claude CLI not found in PATH!")
        except subprocess.TimeoutExpired:
            print("[STARTUP] ERROR: Claude CLI --version timed out!")
        except Exception as e:
            print(f"[STARTUP] ERROR: Claude CLI check failed: {e}")

        # Check current user
        print(f"[STARTUP] Current user UID:GID: {os.getuid()}:{os.getgid()}")
        print(f"[STARTUP] Current working directory: {os.getcwd()}")

        # Check default model
        print(f"[STARTUP] Default model: {settings.DEFAULT_MODEL}")

    except Exception as e:
        print(f"[STARTUP] EXCEPTION during diagnostics: {type(e).__name__}: {e}")
        print(f"[STARTUP] Traceback:\n{traceback.format_exc()}")

    print("[STARTUP] ========== END DIAGNOSTICS ==========")


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    _run_startup_diagnostics()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    pass
