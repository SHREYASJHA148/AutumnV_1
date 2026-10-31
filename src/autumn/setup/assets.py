"""Pinned setup downloads/imports. Partial or corrupt assets are never loadable."""

import hashlib
import json
import os
import re
import shutil
import time
import urllib.request
from pathlib import Path, PurePosixPath
from uuid import uuid4

from autumn.actions.catalog import local_path, no_reparse, within
from autumn.speech.assets import ARTIFACTS

VOICE = "https://huggingface.co/rhasspy/piper-voices/resolve/b4e358ffcb232591bf73a540e70f7de528e4174a/en/en_US/lessac/medium/"
STT = (
    "https://huggingface.co/ggerganov/whisper.cpp/resolve/5359861c739e955e79d9a303bcbc70fb988958b1/"
)
WAKE = "https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/"
URLS = {
    key: (STT if key in {"small.en", "base.en"} else WAKE if key.startswith("wake") else VOICE)
    + Path(spec[0]).name
    for key, spec in ARTIFACTS.items()
}


class HTTPSOnlyRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        from urllib.parse import urlsplit

        parsed = urlsplit(newurl)
        host = (parsed.hostname or "").casefold()
        allowed = any(
            host == suffix or host.endswith("." + suffix)
            for suffix in ("huggingface.co", "hf.co", "github.com", "githubusercontent.com")
        )
        if parsed.scheme != "https" or parsed.username or parsed.password or not allowed:
            raise ValueError("Unexpected setup redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def checked_root(root, create=False):
    directory = local_path(str(root))
    parent = directory
    while not parent.exists():
        parent = parent.parent
    no_reparse(parent)
    if create:
        directory.mkdir(parents=True, exist_ok=True)
    if directory.exists():
        no_reparse(directory)
    return directory.resolve(strict=False)


def destination(root, relative):
    path = PurePosixPath(relative)
    if (
        path.is_absolute()
        or not path.parts
        or any(p in {"", "..", "."} or ":" in p or "\\" in p for p in path.parts)
    ):
        raise ValueError("Unsafe artifact path")
    target = root.joinpath(*path.parts)
    parent = target
    while not parent.exists():
        parent = parent.parent
    no_reparse(parent)
    if not target.resolve(strict=False).is_relative_to(root.resolve(strict=False)):
        raise ValueError("Artifact escaped model root")
    return target


def verified(path, size, sha):
    no_reparse(path)
    if not path.is_file() or path.stat().st_size != size:
        return False
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest() == sha


def promote(partial, target):
    # Preserve an existing corrupt/unexpected file instead of silently deleting it.
    if target.exists():
        no_reparse(target)
        if not target.is_file():
            raise ValueError("A directory cannot be replaced by an asset")
        target.rename(target.with_name(target.name + ".replaced-" + uuid4().hex[:10]))
    os.replace(partial, target)


def import_asset(key, source, root, checkpoint, progress=lambda *args: None):
    relative, size, sha = ARTIFACTS[key]
    source = within(checked_root(source) / relative, checked_root(source))
    if not verified(source, size, sha):
        raise ValueError("Import checksum mismatch")
    root = checked_root(root, True)
    target = destination(root, relative)
    if target.exists() and verified(target, size, sha):
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    no_reparse(target.parent)
    partial = target.with_name(target.name + ".import-" + uuid4().hex + ".partial")
    created = False
    try:
        with source.open("rb") as incoming, partial.open("xb") as outgoing:
            created = True
            count = 0
            while chunk := incoming.read(512 * 1024):
                if not checkpoint():
                    raise InterruptedError()
                outgoing.write(chunk)
                count += len(chunk)
                progress(count, size)
            outgoing.flush()
            os.fsync(outgoing.fileno())
        if not verified(partial, size, sha):
            raise ValueError("Imported content changed")
        if not checkpoint():
            raise InterruptedError()
        promote(partial, target)
    finally:
        if created and partial.exists():
            partial.unlink()  # This unique temporary file was created above.


def download(key, root, checkpoint, progress=lambda *args: None, *, opener=None):
    relative, size, sha = ARTIFACTS[key]
    root = checked_root(root, True)
    target = destination(root, relative)
    if target.exists() and verified(target, size, sha):
        return
    if shutil.disk_usage(root).free < max(12 * 1024**3, size + 256 * 1024**2):
        raise OSError("Insufficient free space")
    target.parent.mkdir(parents=True, exist_ok=True)
    no_reparse(target.parent)
    partial = target.with_name(target.name + "." + sha[:12] + ".partial")
    marker = partial.with_name(partial.name + ".json")
    identity = {"product": "AutumnLocalSetup/1", "artifact": key, "sha256": sha, "bytes": size}
    if marker.exists():
        no_reparse(marker)
        if json.loads(marker.read_text(encoding="utf-8")) != identity:
            raise ValueError("Unowned partial marker")
    elif partial.exists():
        raise ValueError("Unowned partial file")
    else:
        with marker.open("x", encoding="utf-8") as meta:
            json.dump(identity, meta)
    if partial.exists():
        no_reparse(partial)
        if partial.stat().st_size > size:
            partial.rename(partial.with_name(partial.name + ".invalid-" + uuid4().hex[:8]))
    offset = partial.stat().st_size if partial.exists() else 0
    if offset == size:
        if verified(partial, size, sha):
            if not checkpoint():
                raise InterruptedError()
            promote(partial, target)
            marker.unlink()
            return
        partial.rename(partial.with_name(partial.name + ".invalid-" + uuid4().hex[:8]))
        offset = 0
    request = urllib.request.Request(
        URLS[key],
        headers={
            "User-Agent": "AutumnLocalSetup/0.7",
            "Accept-Encoding": "identity",
            **({"Range": f"bytes={offset}-"} if offset else {}),
        },
    )
    opener = opener or urllib.request.build_opener(
        urllib.request.ProxyHandler({}), HTTPSOnlyRedirect()
    )
    began = time.monotonic()
    with opener.open(request, timeout=5) as response:
        status = response.status
        if offset:
            header = response.headers.get("Content-Range", "")
            match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", header)
            if status != 206 or match is None or int(match[1]) != offset or int(match[3]) != size:
                raise ValueError("Server did not honor the exact resume range")
        elif status not in {200, 206}:
            raise ValueError("Unexpected setup response")
        if response.headers.get("Content-Encoding", "identity") not in {"identity", ""}:
            raise ValueError("Encoded asset refused")
        with partial.open("ab" if offset else "xb") as outgoing:
            count = offset
            while chunk := response.read(512 * 1024):
                if not checkpoint() or time.monotonic() - began > 3600:
                    raise InterruptedError()
                if count + len(chunk) > size:
                    raise ValueError("Asset exceeds pinned length")
                outgoing.write(chunk)
                count += len(chunk)
                progress(count, size)
            outgoing.flush()
            os.fsync(outgoing.fileno())
    if not checkpoint():
        raise InterruptedError()
    if not verified(partial, size, sha):
        raise ValueError("Downloaded asset checksum mismatch")
    promote(partial, target)
    marker.unlink()


def inventory(root):
    root = checked_root(root)
    rows = []
    for key, (relative, size, sha) in ARTIFACTS.items():
        target = destination(root, relative)
        state = (
            "Verified"
            if target.exists() and verified(target, size, sha)
            else "Missing or needs repair"
        )
        partial = target.with_name(target.name + "." + sha[:12] + ".partial")
        if state != "Verified" and partial.exists():
            no_reparse(partial)
            state = "Interrupted download; resume available"
        rows.append(
            {
                "id": key,
                "label": {
                    "voice": "Female voice",
                    "voice_config": "Voice configuration",
                    "voice_license": "Voice license card",
                    "wake": "Wake phrase",
                    "wake_mel": "Wake audio features",
                    "wake_embedding": "Wake embeddings",
                }.get(key, "English speech " + key),
                "state": state,
                "bytes": size,
                "size_mb": round(size / 1024**2, 1),
            }
        )
    return rows
