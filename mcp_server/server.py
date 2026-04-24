"""Unified MCP server with all tools."""

import logging
import os
import sys
import threading
import time
import schedule
from pathlib import Path
from typing import Dict
from dotenv import load_dotenv

# Load environment variables from .env file
env_file = Path(__file__).parent.parent / "auth" / ".env"
if env_file.exists():
    load_dotenv(env_file)

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Add scrape_play directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scrape_play"))

from mcp.server.fastmcp import FastMCP  # noqa: E402

from langchain_agent.tool_registry import ProjectToolRegistry  # noqa: E402

logger = logging.getLogger(__name__)


def create_server() -> FastMCP:
    """Create and configure the MCP server with all tools.

    Returns:
        Configured FastMCP server instance.
    """
    print("Creating server...")
    mcp = FastMCP("mcpjose")
    print("Server created.")

    ProjectToolRegistry().register_mcp_tools(mcp)

    # Initialize cron tools
    _init_cron_tools(mcp)

    # Start cron worker thread
    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(1)

    threading.Thread(target=run_scheduler, daemon=True).start()

    return mcp


def _init_cron_tools(mcp: FastMCP) -> None:
    """Initialize cron job tools."""

    @mcp.tool()
    def add_cron_job(
        task_name: str, schedule_str: str, task_command: str
    ) -> Dict[str, str]:
        """Add a cron-like task to be executed periodically.
        schedule_str: 'every 1 minute', 'every 1 hour', '10:30' (daily at 10:30).
        """

        def job():
            logger.info(f"Running scheduled task: {task_name}")
            os.system(task_command)

        try:
            if "minute" in schedule_str:
                schedule.every(int(schedule_str.split()[1])).minutes.do(job)
            elif "hour" in schedule_str:
                schedule.every(int(schedule_str.split()[1])).hours.do(job)
            else:
                schedule.every().day.at(schedule_str).do(job)

            return {"status": "success", "message": f"Job '{task_name}' added."}
        except Exception as e:
            return {"status": "error", "message": str(e)}


# Global server instance for backwards compatibility
mcp = create_server()

if __name__ == "__main__":
    mcp.run()

# Import and attach our new subscription-aware logic
try:
    from mcp_server.server_patch import add_guard_to_tools

    # In a full integration, these tools would be added to the ProjectToolRegistry
    # For now, we manually register them on the MCP object
    add_guard_to_tools(mcp)
    
    # We could also register the tools here manually if they aren't in registry:
    # This requires adapting the execute method to FastMCP's @tool decorator logic
    # or adding them to the Custom Tool logic inside tool_registry.py

except ImportError as e:
    logger.warning(f"Could not load payment tools: {e}")

