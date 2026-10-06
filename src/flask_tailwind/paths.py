"""Stylesheet-relative paths and escaped CSS strings."""

import ntpath
import os
from pathlib import Path, PureWindowsPath

from flask_node import AssetResolutionError


def relative_css_path(target, parent) -> str:
    windows = isinstance(target, PureWindowsPath) or isinstance(parent, PureWindowsPath)
    try:
        relative = (ntpath if windows else os.path).relpath(str(target), str(parent))
    except ValueError as exc:
        raise AssetResolutionError("CSS paths must share a filesystem drive.") from exc
    result = relative.replace("\\", "/")
    return result if result.startswith(".") else "./" + result


def css_string(value: str) -> str:
    # CSS escapes differ from JSON escapes for control characters.
    escaped = ""
    for char in value:
        if char in ('"', "\\"):
            escaped += "\\" + char
        elif ord(char) < 32 or ord(char) == 127:
            escaped += f"\\{ord(char):x} "
        else:
            escaped += char
    return '"' + escaped + '"'


def package_path(manager, package: str, path: str, parent: Path) -> str:
    if (
        not isinstance(path, str)
        or not path
        or "\\" in path
        or "\x00" in path
        or PureWindowsPath(path).drive
        or path.startswith("/")
        or any(part in ("", ".", "..") for part in path.split("/"))
    ):
        raise AssetResolutionError(f"Unsafe Tailwind package path: {path!r}")
    parts = path.split("/")
    wildcard = next(
        (i for i, part in enumerate(parts) if any(c in part for c in "*?[{")), None
    )
    if wildcard is None:
        target = manager.resolve(package, path)
        return relative_css_path(target, parent)
    prefix = "/".join(parts[:wildcard])
    target = manager.resolve(package, prefix or ".")
    if not target.is_dir():
        raise AssetResolutionError("A source glob must start from a package directory.")
    return (
        relative_css_path(target, parent).rstrip("/") + "/" + "/".join(parts[wildcard:])
    )
