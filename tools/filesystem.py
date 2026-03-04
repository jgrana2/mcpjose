"""Filesystem tools for MCP server."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional


class FilesystemTools:
    """Filesystem operations with allowed directory validation."""

    def __init__(self, allowed_dirs: Optional[List[str]] = None):
        """Initialize filesystem tools with allowed directories.

        Args:
            allowed_dirs: List of allowed directory paths. If None, uses
                         FILESYSTEM_ALLOWED_DIRS env var or defaults to project root.
        """
        if allowed_dirs:
            self.allowed_dirs = [Path(d).resolve() for d in allowed_dirs]
        else:
            # Get from env var or default to project directory
            env_dirs = os.getenv("FILESYSTEM_ALLOWED_DIRS")
            if env_dirs:
                self.allowed_dirs = [Path(d).resolve() for d in env_dirs.split(",")]
            else:
                # Default to project root
                project_root = Path(__file__).parent.parent.resolve()
                self.allowed_dirs = [project_root]

    def _validate_path(self, path: str) -> Path:
        """Ensure path is within allowed directories.

        Args:
            path: Path to validate

        Returns:
            Resolved Path object

        Raises:
            ValueError: If path is outside allowed directories
        """
        full_path = Path(path).resolve()

        # Check if path is within any allowed directory
        for allowed in self.allowed_dirs:
            try:
                full_path.relative_to(allowed)
                return full_path
            except ValueError:
                continue

        raise ValueError(
            f"Path {path} is outside allowed directories: "
            f"{[str(d) for d in self.allowed_dirs]}"
        )

    def read_text_file(
        self, path: str, head: Optional[int] = None, tail: Optional[int] = None
    ) -> Dict[str, Any]:
        """Read text file contents.

        Args:
            path: Path to file
            head: Read only first N lines
            tail: Read only last N lines

        Returns:
            Dictionary with content and path
        """
        try:
            if head and tail:
                return {"error": "Cannot specify both head and tail simultaneously"}

            file_path = self._validate_path(path)

            if not file_path.exists():
                return {"error": f"File not found: {path}"}

            if not file_path.is_file():
                return {"error": f"Path is not a file: {path}"}

            content = file_path.read_text(encoding="utf-8")
            lines = content.split("\n")

            if head:
                lines = lines[:head]
            elif tail:
                lines = lines[-tail:]

            return {
                "content": "\n".join(lines),
                "path": str(file_path),
                "total_lines": len(content.split("\n")),
                "returned_lines": len(lines),
            }
        except ValueError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"Failed to read file: {str(e)}"}

    def list_directory(self, path: str) -> Dict[str, Any]:
        """List directory contents.

        Args:
            path: Directory path

        Returns:
            Dictionary with entries and path
        """
        try:
            dir_path = self._validate_path(path)

            if not dir_path.exists():
                return {"error": f"Directory not found: {path}"}

            if not dir_path.is_dir():
                return {"error": f"Path is not a directory: {path}"}

            entries = []
            for entry in sorted(
                dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())
            ):
                entry_type = "[DIR]" if entry.is_dir() else "[FILE]"
                entries.append(f"{entry_type} {entry.name}")

            return {"entries": entries, "path": str(dir_path), "count": len(entries)}
        except ValueError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"Failed to list directory: {str(e)}"}

    def write_file(self, path: str, content: str) -> Dict[str, Any]:
        """Write content to file.

        Args:
            path: File path
            content: Content to write

        Returns:
            Dictionary with success status and path
        """
        try:
            file_path = self._validate_path(path)

            # Create parent directories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)

            file_path.write_text(content, encoding="utf-8")

            return {
                "success": True,
                "path": str(file_path),
                "bytes_written": len(content.encode("utf-8")),
            }
        except ValueError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"Failed to write file: {str(e)}"}

    def create_directory(self, path: str) -> Dict[str, Any]:
        """Create a directory.

        Args:
            path: Directory path

        Returns:
            Dictionary with success status and path
        """
        try:
            dir_path = self._validate_path(path)

            dir_path.mkdir(parents=True, exist_ok=True)

            return {
                "success": True,
                "path": str(dir_path),
                "created": not dir_path.exists() or True,
            }
        except ValueError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"Failed to create directory: {str(e)}"}

    def move_file(self, source: str, destination: str) -> Dict[str, Any]:
        """Move or rename a file/directory.

        Args:
            source: Source path
            destination: Destination path

        Returns:
            Dictionary with success status
        """
        try:
            src_path = self._validate_path(source)
            dst_path = self._validate_path(destination)

            if not src_path.exists():
                return {"error": f"Source not found: {source}"}

            if dst_path.exists():
                return {"error": f"Destination already exists: {destination}"}

            # Create parent directories if needed
            dst_path.parent.mkdir(parents=True, exist_ok=True)

            src_path.rename(dst_path)

            return {
                "success": True,
                "source": str(src_path),
                "destination": str(dst_path),
            }
        except ValueError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"Failed to move file: {str(e)}"}

    def get_file_info(self, path: str) -> Dict[str, Any]:
        """Get detailed file/directory metadata.

        Args:
            path: Path to file or directory

        Returns:
            Dictionary with metadata
        """
        try:
            file_path = self._validate_path(path)

            if not file_path.exists():
                return {"error": f"Path not found: {path}"}

            stat = file_path.stat()

            return {
                "path": str(file_path),
                "type": "directory" if file_path.is_dir() else "file",
                "size": stat.st_size,
                "created": stat.st_ctime,
                "modified": stat.st_mtime,
                "accessed": stat.st_atime,
                "permissions": oct(stat.st_mode)[-3:],
                "exists": True,
            }
        except ValueError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"Failed to get file info: {str(e)}"}

    def search_files(
        self, path: str, pattern: str, exclude_patterns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Search for files matching a pattern.

        Args:
            path: Starting directory
            pattern: Search pattern (glob style)
            exclude_patterns: Patterns to exclude

        Returns:
            Dictionary with matches
        """
        try:
            import fnmatch

            search_path = self._validate_path(path)

            if not search_path.exists():
                return {"error": f"Directory not found: {path}"}

            if not search_path.is_dir():
                return {"error": f"Path is not a directory: {path}"}

            exclude_patterns = exclude_patterns or []
            matches = []

            for root, dirs, files in os.walk(search_path):
                # Filter directories to exclude
                dirs[:] = [
                    d
                    for d in dirs
                    if not any(fnmatch.fnmatch(d, ep) for ep in exclude_patterns)
                ]

                for item in dirs + files:
                    if fnmatch.fnmatch(item, pattern):
                        full_path = Path(root) / item
                        try:
                            # Validate path is still in allowed dirs
                            self._validate_path(str(full_path))
                            matches.append(str(full_path))
                        except ValueError:
                            continue

            return {
                "matches": matches,
                "count": len(matches),
                "path": str(search_path),
                "pattern": pattern,
            }
        except ValueError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"Failed to search files: {str(e)}"}

    def list_allowed_directories(self) -> Dict[str, Any]:
        """List all allowed directories.

        Returns:
            Dictionary with allowed directories
        """
        return {
            "allowed_directories": [str(d) for d in self.allowed_dirs],
            "count": len(self.allowed_dirs),
        }
