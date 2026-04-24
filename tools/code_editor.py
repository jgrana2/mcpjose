"""Code editor tool for MCP server — implements Anthropic's str_replace_editor pattern.

Single tool with commands: view, create, str_replace, insert, undo_edit.
Based on: https://www.anthropic.com/engineering/swe-bench-sonnet
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from tools.filesystem import FilesystemTools


def init_tools(mcp: FastMCP) -> None:
    """Register the str_replace_editor tool with MCP."""
    from langchain_agent.tool_registry import ProjectToolRegistry

    registry = ProjectToolRegistry()
    registry.fs_tools = FilesystemTools()

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
        return registry.str_replace_editor(
            command=command,
            path=path,
            file_text=file_text,
            old_str=old_str,
            new_str=new_str,
            insert_line=insert_line,
            view_range=view_range,
        )


def _cmd_view(path: Path, view_range: Optional[List[int]]) -> Dict[str, Any]:
    if path.is_dir():
        lines = []
        for entry in sorted(path.iterdir(), key=lambda entry: (not entry.is_dir(), entry.name)):
            if entry.name.startswith("."):
                continue
            prefix = "[DIR]" if entry.is_dir() else "[FILE]"
            lines.append(f"{prefix} {entry.name}")
            if entry.is_dir():
                for subentry in sorted(
                    entry.iterdir(),
                    key=lambda item: (not item.is_dir(), item.name),
                ):
                    if not subentry.name.startswith("."):
                        sub_prefix = "[DIR]" if subentry.is_dir() else "[FILE]"
                        lines.append(f"  {sub_prefix} {subentry.name}")
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
        f"{index:>6}\t{line}"
        for index, line in enumerate(all_lines[start - 1 : end], start=start)
    )
    return {"output": numbered, "total_lines": total}


def _cmd_create(path: Path, file_text: Optional[str], undo_stack: Dict[str, List[str]]) -> Dict[str, Any]:
    if file_text is None:
        return {"error": "file_text is required for the create command."}
    if path.exists():
        return {"error": f"Cannot create: file already exists at {path}. Use str_replace to edit it."}

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(file_text, encoding="utf-8")
    undo_stack.setdefault(str(path), []).append("")
    return {"output": f"File created: {path}"}


def _cmd_str_replace(
    path: Path,
    old_str: Optional[str],
    new_str: Optional[str],
    undo_stack: Dict[str, List[str]],
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
    path: Path,
    insert_line: Optional[int],
    new_str: Optional[str],
    undo_stack: Dict[str, List[str]],
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
        path.unlink(missing_ok=True)
        return {"output": f"Undone: deleted {path.name} (creation reversed)."}

    path.write_text(prior, encoding="utf-8")
    return {"output": f"Last edit to {path.name} reverted."}


_MAX_UNDO_DEPTH = 10


def _push_undo(stack: Dict[str, List[str]], key: str, content: str) -> None:
    entries = stack.setdefault(key, [])
    entries.append(content)
    if len(entries) > _MAX_UNDO_DEPTH:
        entries.pop(0)
