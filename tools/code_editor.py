"""Code editor tool for MCP server — implements Anthropic's str_replace_editor pattern.

Single tool with commands: view, create, str_replace, insert, undo_edit.
Based on: https://www.anthropic.com/engineering/swe-bench-sonnet
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from tools.filesystem import FilesystemTools


def init_tools(mcp: FastMCP) -> None:
    """Register the str_replace_editor tool with MCP."""

    fs = FilesystemTools()
    # In-memory undo stack: resolved_path -> list of prior contents (newest last)
    _undo_stack: Dict[str, List[str]] = {}

    @mcp.tool()
    def str_replace_editor(
        command: str,
        path: str,
        file_text: Optional[str] = None,
        old_str: Optional[str] = None,
        new_str: Optional[str] = None,
        insert_line: Optional[int] = None,
        view_range: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """Custom editing tool for viewing, creating and editing files.

        State is persistent across command calls and discussions with the user.
        If `path` is a file, `view` displays the file with line numbers.
        If `path` is a directory, `view` lists non-hidden files up to 2 levels deep.
        The `create` command cannot be used if `path` already exists as a file.

        Notes for `str_replace`:
        * `old_str` must match EXACTLY one or more consecutive lines. Be mindful of whitespace!
        * If `old_str` is not unique in the file, the replacement will not be performed.
        * Include enough context in `old_str` to make it unique.
        * `new_str` contains the replacement text.

        Args:
            command: One of: view, create, str_replace, insert, undo_edit.
            path: Absolute path to file or directory.
            file_text: Content for the `create` command.
            old_str: String to replace (required for `str_replace`).
            new_str: Replacement string (required for `str_replace`; content for `insert`).
            insert_line: Line number after which to insert `new_str` (required for `insert`).
            view_range: Optional [start, end] line range for `view` on a file.

        Returns:
            Dict with output or error key.
        """
        try:
            resolved = fs._validate_path(path)
        except ValueError as e:
            return {"error": str(e)}

        if command == "view":
            return _cmd_view(resolved, view_range)

        if command == "create":
            return _cmd_create(resolved, file_text, _undo_stack)

        if command == "str_replace":
            return _cmd_str_replace(resolved, old_str, new_str, _undo_stack)

        if command == "insert":
            return _cmd_insert(resolved, insert_line, new_str, _undo_stack)

        if command == "undo_edit":
            return _cmd_undo(resolved, _undo_stack)

        return {"error": f"Unknown command '{command}'. Use: view, create, str_replace, insert, undo_edit."}


# ---------------------------------------------------------------------------
# Command implementations
# ---------------------------------------------------------------------------

def _cmd_view(path: Path, view_range: Optional[List[int]]) -> Dict[str, Any]:
    if path.is_dir():
        lines = []
        for entry in sorted(path.iterdir(), key=lambda e: (not e.is_dir(), e.name)):
            if entry.name.startswith("."):
                continue
            prefix = "📁" if entry.is_dir() else "📄"
            lines.append(f"{prefix} {entry.name}")
            if entry.is_dir():
                for sub in sorted(entry.iterdir(), key=lambda e: (not e.is_dir(), e.name)):
                    if not sub.name.startswith("."):
                        sub_prefix = "📁" if sub.is_dir() else "📄"
                        lines.append(f"  {sub_prefix} {sub.name}")
        return {"output": f"{path}\n" + "\n".join(lines)}

    if not path.exists():
        return {"error": f"File not found: {path}"}
    if not path.is_file():
        return {"error": f"Not a file: {path}"}

    content = path.read_text(encoding="utf-8")
    all_lines = content.splitlines()
    total = len(all_lines)

    start, end = 1, total
    if view_range:
        if len(view_range) != 2:
            return {"error": "view_range must be [start_line, end_line]."}
        start, end = view_range
        if start < 1 or end < start or end > total:
            return {"error": f"view_range [{start}, {end}] is out of bounds for {total}-line file."}

    numbered = "\n".join(
        f"{i:>6}\t{line}" for i, line in enumerate(all_lines[start - 1 : end], start=start)
    )
    return {"output": numbered, "total_lines": total}


def _cmd_create(path: Path, file_text: Optional[str], undo_stack: Dict[str, List[str]]) -> Dict[str, Any]:
    if file_text is None:
        return {"error": "file_text is required for the create command."}
    if path.exists():
        return {"error": f"Cannot create: file already exists at {path}. Use str_replace to edit it."}

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(file_text, encoding="utf-8")
    # Push empty string as "before" so undo_edit can delete the file
    undo_stack.setdefault(str(path), []).append("")
    return {"output": f"File created: {path}"}


def _cmd_str_replace(
    path: Path, old_str: Optional[str], new_str: Optional[str], undo_stack: Dict[str, List[str]]
) -> Dict[str, Any]:
    if old_str is None:
        return {"error": "old_str is required for the str_replace command."}
    if new_str is None:
        return {"error": "new_str is required for the str_replace command."}
    if not path.exists():
        return {"error": f"File not found: {path}"}
    if not path.is_file():
        return {"error": f"Not a file: {path}"}

    content = path.read_text(encoding="utf-8")
    count = content.count(old_str)
    if count == 0:
        return {"error": "No match found for old_str. Verify whitespace and content exactly match the file."}
    if count > 1:
        return {"error": f"old_str matches {count} locations. Add more context to make it unique."}

    _push_undo(undo_stack, str(path), content)
    new_content = content.replace(old_str, new_str, 1)
    path.write_text(new_content, encoding="utf-8")
    return {"output": f"Replacement applied in {path.name}."}


def _cmd_insert(
    path: Path, insert_line: Optional[int], new_str: Optional[str], undo_stack: Dict[str, List[str]]
) -> Dict[str, Any]:
    if insert_line is None:
        return {"error": "insert_line is required for the insert command."}
    if new_str is None:
        return {"error": "new_str is required for the insert command."}
    if not path.exists():
        return {"error": f"File not found: {path}"}
    if not path.is_file():
        return {"error": f"Not a file: {path}"}

    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    if insert_line < 0 or insert_line > len(lines):
        return {"error": f"insert_line {insert_line} is out of range (0–{len(lines)})."}

    _push_undo(undo_stack, str(path), "".join(lines))
    insert_text = new_str if new_str.endswith("\n") else new_str + "\n"
    lines.insert(insert_line, insert_text)
    path.write_text("".join(lines), encoding="utf-8")
    return {"output": f"Inserted after line {insert_line} in {path.name}."}


def _cmd_undo(path: Path, undo_stack: Dict[str, List[str]]) -> Dict[str, Any]:
    key = str(path)
    if not undo_stack.get(key):
        return {"error": f"No edits to undo for {path}."}

    prior = undo_stack[key].pop()
    if prior == "":
        # The file was created by create command — remove it
        path.unlink(missing_ok=True)
        return {"output": f"Undone: deleted {path.name} (creation reversed)."}

    path.write_text(prior, encoding="utf-8")
    return {"output": f"Last edit to {path.name} reverted."}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MAX_UNDO_DEPTH = 10


def _push_undo(stack: Dict[str, List[str]], key: str, content: str) -> None:
    entries = stack.setdefault(key, [])
    entries.append(content)
    if len(entries) > _MAX_UNDO_DEPTH:
        entries.pop(0)
