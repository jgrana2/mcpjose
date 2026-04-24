"""Bash command execution tool."""

import shlex
import subprocess
from typing import Any, Dict, Optional

_MAX_OUTPUT_BYTES = 50_000  # 50 KB per stream
_ALLOWED_SHELL_BINARIES = {"bash", "sh", "zsh"}


class BashExecutor:
    """Run bash commands with timeout and output limits."""

    def __init__(self, allowed_dirs: Optional[list[str]] = None):
        from tools.filesystem import FilesystemTools

        self._fs = FilesystemTools(allowed_dirs)

    def _build_command_args(self, command: str) -> list[str]:
        stripped_command = command.strip()
        if not stripped_command:
            raise ValueError("Command cannot be empty")

        cmd_parts = shlex.split(stripped_command)
        if len(cmd_parts) >= 2 and cmd_parts[0] in _ALLOWED_SHELL_BINARIES and cmd_parts[1] == "-lc":
            if len(cmd_parts) != 3:
                raise ValueError("Shell commands must use the form '<shell> -lc <command>'")
            return [cmd_parts[0], "-lc", cmd_parts[2]]

        if cmd_parts and cmd_parts[0] in _ALLOWED_SHELL_BINARIES:
            return [cmd_parts[0], "-lc", stripped_command]

        return ["bash", "-lc", stripped_command]

    def execute(
        self,
        command: str,
        cwd: Optional[str] = None,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        if cwd is not None:
            try:
                resolved_cwd = str(self._fs._validate_path(cwd))
            except ValueError as e:
                return {"ok": False, "error": str(e)}
        else:
            resolved_cwd = str(self._fs.allowed_dirs[0])

        try:
            cmd_parts = self._build_command_args(command)
            result = subprocess.run(
                cmd_parts,
                shell=False,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=resolved_cwd,
            )
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "error": f"Command timed out after {timeout}s",
                "command": command,
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc), "command": command}

        stdout = result.stdout
        stderr = result.stderr
        truncated = False

        if len(stdout.encode()) > _MAX_OUTPUT_BYTES:
            stdout = stdout.encode()[:_MAX_OUTPUT_BYTES].decode(errors="replace")
            truncated = True
        if len(stderr.encode()) > _MAX_OUTPUT_BYTES:
            stderr = stderr.encode()[:_MAX_OUTPUT_BYTES].decode(errors="replace")
            truncated = True

        return {
            "ok": result.returncode == 0,
            "stdout": stdout,
            "stderr": stderr,
            "returncode": result.returncode,
            "command": command,
            **({"truncated": True} if truncated else {}),
        }
