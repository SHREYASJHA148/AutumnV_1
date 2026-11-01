"""Trusted registrations are edited explicitly in the UI, never by planner output."""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Literal
from urllib.parse import unquote, urlsplit, urlunsplit

from pydantic import Field, field_validator

from autumn.actions.schemas import Identifier
from autumn.controller.contracts import Contract

BLOCKED_EXECUTABLES = {"cmd", "powershell", "pwsh", "wscript", "cscript", "mshta", "rundll32", "regsvr32"}


def local_path(value: str) -> Path:
    if value.startswith(("\\\\", "//")) or "\x00" in value:
        raise ValueError("Network/device paths are not supported")
    path = Path(value)
    if not path.is_absolute() or (os.name == "nt" and ":" in str(path)[3:]):
        raise ValueError("Choose an absolute local path")
    return path


def no_reparse(path: Path) -> Path:
    path = local_path(str(path))
    for item in (path, *path.parents):
        info = item.lstat()
        if item.is_symlink() or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("Reparse targets are not supported")
    return path.resolve(strict=True)


def within(path: Path, root: Path) -> Path:
    resolved_root = no_reparse(root)
    resolved = no_reparse(path)
    if not resolved.is_relative_to(resolved_root):
        raise ValueError("Outside registered root")
    return resolved


def safe_url(value: str) -> str:
    if any(ord(c) <= 32 or ord(c) == 127 for c in value) or any(c in value for c in '\\`|<>";${}'):
        raise ValueError("Unsafe address")
    decoded = unquote(value)
    if any(ord(c) < 32 or ord(c) == 127 for c in decoded) or "\\" in decoded:
        raise ValueError("Unsafe escaped address")
    parsed = urlsplit(value)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Use an HTTP/HTTPS address without credentials")
    host = parsed.hostname.encode("idna").decode("ascii")
    if not re.fullmatch(r"[A-Za-z0-9.:-]+", host):
        raise ValueError("Invalid host")
    _ = parsed.port  # validates invalid/out-of-range ports
    return urlunsplit((parsed.scheme.lower(), parsed.netloc, parsed.path, parsed.query, parsed.fragment))


class AppEntry(Contract):
    id: Identifier
    name: str = Field(min_length=1, max_length=80)
    aliases: tuple[str, ...] = Field(default=(), max_length=12)
    kind: Literal["executable", "shortcut", "package", "file"]
    target: str = Field(min_length=1, max_length=2048)
    fingerprint: str = ""
    enabled: bool = False
    reviewed: bool = False

    @field_validator("aliases")
    @classmethod
    def alias_lengths(cls, values):
        if any(not value.strip() or len(value) > 80 for value in values):
            raise ValueError("Invalid alias")
        return values


class FolderEntry(Contract):
    id: Identifier
    name: str = Field(min_length=1, max_length=80)
    path: str
    search: bool = True


class SiteEntry(Contract):
    id: Identifier
    name: str = Field(min_length=1, max_length=80)
    url: str

    @field_validator("url")
    @classmethod
    def check_url(cls, value):
        return safe_url(value)


def fingerprint(path: Path) -> str:
    if path.suffix.lower() == ".lnk":
        if path.stat().st_size > 1_000_000:
            raise ValueError("Oversized shortcut")
        return hashlib.sha256(path.read_bytes()).hexdigest()
    info = path.stat()
    return f"{info.st_size}:{info.st_mtime_ns}"


def validate_app(entry: AppEntry) -> AppEntry:
    if entry.kind == "package":
        if not re.fullmatch(r"[A-Za-z0-9._-]+![A-Za-z0-9._-]+", entry.target):
            raise ValueError("Invalid packaged app identity")
    else:
        path = no_reparse(local_path(entry.target))
        if entry.kind == 'file':
            from autumn.actions.broad_open import DOCUMENT_EXTENSIONS
            valid_extension = path.suffix.casefold() in DOCUMENT_EXTENSIONS
        else:
            valid_extension = path.suffix.lower() == (".exe" if entry.kind == "executable" else ".lnk")
        if not valid_extension or not path.is_file():
            raise ValueError("Invalid launch target")
        if path.stem.casefold() in BLOCKED_EXECUTABLES:
            raise ValueError("Script and shell launchers are not supported")
        observed = fingerprint(path)
        if entry.fingerprint and observed != entry.fingerprint:
            raise ValueError("Target changed since review")
        entry = entry.model_copy(update={"target": str(path), "fingerprint": observed})
    return entry
