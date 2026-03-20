"""Tests for tools/code_editor.py."""

import pytest
from pathlib import Path
from unittest.mock import patch

from mcp.server.fastmcp import FastMCP


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_allowed(tmp_path):
    """Patch FilesystemTools to allow tmp_path."""
    with patch("tools.code_editor.FilesystemTools") as MockFS:
        fs_instance = MockFS.return_value
        # Make _validate_path return the resolved absolute path (within tmp_path)
        def validate(p):
            resolved = Path(p).resolve()
            # Allow anything under tmp_path for testing
            try:
                resolved.relative_to(tmp_path.resolve())
                return resolved
            except ValueError:
                raise ValueError(f"Path {p} is outside allowed directories")

        fs_instance._validate_path.side_effect = validate
        yield tmp_path


@pytest.fixture
def tool(tmp_allowed):
    """Return a bound str_replace_editor callable registered on a test MCP."""
    from tools.code_editor import init_tools

    mcp = FastMCP("test")
    init_tools(mcp)

    # Extract the registered function by calling it directly through the module
    # Re-import to get a fresh closure (own undo stack)
    import importlib
    import tools.code_editor as ce_mod
    importlib.reload(ce_mod)

    registered = {}

    class CaptureMCP:
        def tool(self):
            def decorator(fn):
                registered["fn"] = fn
                return fn
            return decorator

    with patch("tools.code_editor.FilesystemTools") as MockFS:
        fs_instance = MockFS.return_value
        def validate(p):
            resolved = Path(p).resolve()
            try:
                resolved.relative_to(tmp_allowed.resolve())
                return resolved
            except ValueError:
                raise ValueError(f"Path {p} is outside allowed directories")
        fs_instance._validate_path.side_effect = validate

        cmcp = CaptureMCP()
        ce_mod.init_tools(cmcp)

    return registered["fn"]


# ---------------------------------------------------------------------------
# view — file
# ---------------------------------------------------------------------------

def test_view_file(tool, tmp_allowed):
    f = tmp_allowed / "hello.py"
    f.write_text("line one\nline two\nline three\n")
    result = tool(command="view", path=str(f))
    assert "error" not in result
    assert "line one" in result["output"]
    assert "1\t" in result["output"] or "     1\t" in result["output"]


def test_view_file_with_range(tool, tmp_allowed):
    f = tmp_allowed / "range.py"
    f.write_text("a\nb\nc\nd\ne\n")
    result = tool(command="view", path=str(f), view_range=[2, 4])
    assert "error" not in result
    assert "b" in result["output"]
    assert "a" not in result["output"]


def test_view_file_invalid_range(tool, tmp_allowed):
    f = tmp_allowed / "small.py"
    f.write_text("only one line\n")
    result = tool(command="view", path=str(f), view_range=[1, 99])
    assert "error" in result


def test_view_missing_file(tool, tmp_allowed):
    result = tool(command="view", path=str(tmp_allowed / "nope.py"))
    assert "error" in result


# ---------------------------------------------------------------------------
# view — directory
# ---------------------------------------------------------------------------

def test_view_directory(tool, tmp_allowed):
    (tmp_allowed / "subdir").mkdir()
    (tmp_allowed / "subdir" / "a.py").write_text("x")
    (tmp_allowed / "b.js").write_text("y")
    result = tool(command="view", path=str(tmp_allowed))
    assert "error" not in result
    assert "subdir" in result["output"]
    assert "b.js" in result["output"]


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------

def test_create_new_file(tool, tmp_allowed):
    f = tmp_allowed / "new.py"
    result = tool(command="create", path=str(f), file_text="print('hi')\n")
    assert "error" not in result
    assert f.exists()
    assert f.read_text() == "print('hi')\n"


def test_create_existing_file_fails(tool, tmp_allowed):
    f = tmp_allowed / "exists.py"
    f.write_text("old content")
    result = tool(command="create", path=str(f), file_text="new content")
    assert "error" in result
    assert f.read_text() == "old content"  # unchanged


def test_create_missing_file_text(tool, tmp_allowed):
    result = tool(command="create", path=str(tmp_allowed / "x.py"))
    assert "error" in result


# ---------------------------------------------------------------------------
# str_replace
# ---------------------------------------------------------------------------

def test_str_replace_basic(tool, tmp_allowed):
    f = tmp_allowed / "edit.py"
    f.write_text("def foo():\n    pass\n")
    result = tool(command="str_replace", path=str(f), old_str="    pass", new_str="    return 42")
    assert "error" not in result
    assert "return 42" in f.read_text()


def test_str_replace_no_match(tool, tmp_allowed):
    f = tmp_allowed / "nomatch.py"
    f.write_text("hello world\n")
    result = tool(command="str_replace", path=str(f), old_str="goodbye", new_str="hi")
    assert "error" in result
    assert "hello world" in f.read_text()  # unchanged


def test_str_replace_multiple_matches(tool, tmp_allowed):
    f = tmp_allowed / "multi.py"
    f.write_text("x = 1\nx = 1\n")
    result = tool(command="str_replace", path=str(f), old_str="x = 1", new_str="x = 2")
    assert "error" in result
    assert f.read_text() == "x = 1\nx = 1\n"  # unchanged


def test_str_replace_missing_params(tool, tmp_allowed):
    f = tmp_allowed / "f.py"
    f.write_text("x\n")
    assert "error" in tool(command="str_replace", path=str(f), old_str="x")
    assert "error" in tool(command="str_replace", path=str(f), new_str="y")


# ---------------------------------------------------------------------------
# insert
# ---------------------------------------------------------------------------

def test_insert_after_line(tool, tmp_allowed):
    f = tmp_allowed / "insert.py"
    f.write_text("line1\nline2\nline3\n")
    result = tool(command="insert", path=str(f), insert_line=1, new_str="inserted")
    assert "error" not in result
    lines = f.read_text().splitlines()
    assert lines[1] == "inserted"
    assert lines[0] == "line1"


def test_insert_out_of_range(tool, tmp_allowed):
    f = tmp_allowed / "ins2.py"
    f.write_text("a\nb\n")
    result = tool(command="insert", path=str(f), insert_line=99, new_str="x")
    assert "error" in result


# ---------------------------------------------------------------------------
# undo_edit
# ---------------------------------------------------------------------------

def test_undo_str_replace(tool, tmp_allowed):
    f = tmp_allowed / "undo.py"
    f.write_text("original content\n")
    tool(command="str_replace", path=str(f), old_str="original content", new_str="changed content")
    assert "changed content" in f.read_text()
    result = tool(command="undo_edit", path=str(f))
    assert "error" not in result
    assert "original content" in f.read_text()


def test_undo_create(tool, tmp_allowed):
    f = tmp_allowed / "created.py"
    tool(command="create", path=str(f), file_text="new file\n")
    assert f.exists()
    result = tool(command="undo_edit", path=str(f))
    assert "error" not in result
    assert not f.exists()


def test_undo_nothing_to_undo(tool, tmp_allowed):
    f = tmp_allowed / "noundo.py"
    f.write_text("x\n")
    result = tool(command="undo_edit", path=str(f))
    assert "error" in result


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------

def test_path_outside_allowed_dirs_rejected(tool, tmp_allowed):
    result = tool(command="view", path="/etc/passwd")
    assert "error" in result


# ---------------------------------------------------------------------------
# Unknown command
# ---------------------------------------------------------------------------

def test_unknown_command(tool, tmp_allowed):
    f = tmp_allowed / "f.py"
    f.write_text("x\n")
    result = tool(command="delete", path=str(f))
    assert "error" in result
