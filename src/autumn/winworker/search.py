"""Filename metadata only; bounded fallback and explicit coverage reporting."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

from autumn.actions.catalog import within

TYPES = {"any": set(), "pdf": {".pdf"}, "spreadsheet": {".xlsx", ".xls", ".csv", ".ods"},
         "photo": {".png", ".jpg", ".jpeg", ".webp", ".heic", ".bmp"},
         "document": {".doc", ".docx", ".odt", ".rtf", ".pdf"}, "text": {".txt", ".md"}}
EXCLUDED = {"windows", "appdata", "node_modules", ".git", ".venv", "venv", "__pycache__", "$recycle.bin", "system volume information"}


@dataclass
class SearchResult:
    matches: list[tuple[Path, Path]]
    visited: int = 0
    denied: int = 0
    limited: bool = False
    cancelled: bool = False
    backend: str = "bounded scan (index unavailable or root coverage unverified)"


def scan(roots, query, type_hint, checkpoint, *, max_entries=200_000, seconds=10,
         clock=time.monotonic, scandir=os.scandir) -> SearchResult:
    result = SearchResult([])
    until = clock() + seconds
    stack = [(Path(root), Path(root)) for root in roots]
    needle = query.casefold()
    while stack:
        directory, root = stack.pop()
        if any(part.casefold() in EXCLUDED for part in directory.parts):
            result.denied += 1
            continue
        if not checkpoint():
            result.cancelled = True
            break
        if clock() >= until or result.visited >= max_entries:
            result.limited = True
            break
        try:
            within(directory, root)
            with scandir(directory) as entries:
                for entry in entries:
                    if not checkpoint():
                        result.cancelled = True
                        break
                    if clock() >= until or result.visited >= max_entries:
                        result.limited = True
                        break
                    result.visited += 1
                    try:
                        info = entry.stat(follow_symlinks=False)
                        if entry.is_symlink() or getattr(info, "st_file_attributes", 0) & 0x400:
                            continue
                        path = Path(entry.path)
                        if entry.is_dir(follow_symlinks=False):
                            if entry.name.casefold() not in EXCLUDED and not entry.name.casefold().startswith(".venv"):
                                stack.append((path, root))
                        elif needle in entry.name.casefold() and (not TYPES[type_hint] or path.suffix.casefold() in TYPES[type_hint]):
                            within(path, root)
                            result.matches.append((path, root))
                            if len(result.matches) == 20:
                                result.limited = True
                                break
                    except (OSError, ValueError):
                        result.denied += 1
        except (OSError, ValueError):
            result.denied += 1
        if result.limited or result.cancelled:
            break
    return result


def indexed(roots, query, type_hint, checkpoint) -> SearchResult | None:
    """Use the index only if every root is reported included in its crawl scope."""
    try:
        import win32com.client
        manager = win32com.client.Dispatch("Search.Manager")
        catalog = manager.GetCatalog("SystemIndex")
        scope = catalog.GetCrawlScopeManager()
        if not all(scope.IncludedInCrawlScope(root.as_uri()) for root in roots):
            return None
        connection = win32com.client.Dispatch("ADODB.Connection")
        connection.ConnectionTimeout = 2
        connection.CommandTimeout = 5
        connection.Open("Provider=Search.CollatorDSO;Extended Properties='Application=Windows';")
        result = SearchResult([], backend="Windows Search index; configured scopes included")
        try:
            for root in roots:
                if not checkpoint():
                    result.cancelled = True
                    break
                uri = root.as_uri().replace("'", "''")
                # Only a literal escaped value enters SQL; wildcards are escaped as brackets.
                needle = query.replace("[", "[[]").replace("%", "[%]").replace("_", "[_]").replace("'", "''")
                rows, _ = connection.Execute("SELECT TOP 201 System.ItemPathDisplay FROM SYSTEMINDEX WHERE "
                    f"SCOPE='{uri}' AND System.FileName LIKE '%{needle}%'")
                try:
                    while not rows.EOF:
                        if not checkpoint():
                            result.cancelled = True
                            break
                        path = Path(rows.Fields.Item(0).Value)
                        result.visited += 1
                        try:
                            canonical = within(path, root)
                            if not any(part.casefold() in EXCLUDED for part in canonical.parts) and canonical.is_file() and query.casefold() in canonical.name.casefold() and (not TYPES[type_hint] or canonical.suffix.casefold() in TYPES[type_hint]):
                                result.matches.append((canonical, root))
                        except (OSError, ValueError):
                            result.denied += 1
                        if len(result.matches) >= 20 or result.visited >= 200:
                            result.limited = True
                            break
                        rows.MoveNext()
                finally:
                    rows.Close()
                if result.limited or result.cancelled:
                    break
        finally:
            connection.Close()
        return result
    except Exception:
        # Service stopped, COM unavailable, scopes unknown: never claim an empty complete result.
        return None


def search(roots, args, checkpoint):
    return indexed(roots, args.query, args.type_hint, checkpoint) or scan(roots, args.query, args.type_hint, checkpoint)
