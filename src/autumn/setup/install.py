"""Verified per-user installation. Configuration/models/history are never removed."""

import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path, PurePosixPath
from uuid import uuid4

from autumn.setup.assets import checked_root, destination

PRODUCT = "org.autumn.local.preview"
MARKER = "autumn-install.json"


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def member_name(name):
    path = PurePosixPath(name)
    if (
        not name
        or path.is_absolute()
        or any(p in {"..", "."} or ":" in p or "\\" in p for p in path.parts)
    ):
        raise ValueError("Unsafe package member")
    if name != path.as_posix() or re.search(r'[\x00-\x1f<>"|?*]', name):
        raise ValueError("Ambiguous package member")
    if name.endswith((".", " ")) or any(p.endswith((".", " ")) for p in path.parts):
        raise ValueError("Ambiguous Windows package path")
    reserved = {
        "con",
        "prn",
        "aux",
        "nul",
        *[f"com{i}" for i in range(1, 10)],
        *[f"lpt{i}" for i in range(1, 10)],
    }
    if any(p.split(".")[0].rstrip(" ").casefold() in reserved for p in path.parts):
        raise ValueError("Reserved Windows path")
    return path.as_posix()


def read_manifest(archive):
    infos = archive.infolist()
    if len(infos) > 25000 or sum(i.file_size for i in infos) > 2 * 1024**3:
        raise ValueError("Package too large")
    names = [member_name(i.filename) for i in infos]
    if len(names) != len({n.casefold() for n in names}):
        raise ValueError("Duplicate package member")
    if any((i.external_attr >> 16) & 0o170000 == 0o120000 for i in infos):
        raise ValueError("Package links refused")
    item = archive.getinfo("release-manifest.json")
    if item.file_size > 4 * 1024**2:
        raise ValueError("Manifest too large")
    manifest = json.loads(archive.read(item))
    if (
        manifest.get("product") != PRODUCT
        or not isinstance(manifest.get("files"), dict)
        or not re.fullmatch(r"\d+\.\d+\.\d+(?:[a-z0-9.-]+)?", manifest.get("version", ""))
    ):
        raise ValueError("Wrong product or version")
    files = manifest["files"]
    if set(names) != {*files, "release-manifest.json"} or "Autumn.exe" not in files:
        raise ValueError("Incomplete package")
    for name, spec in files.items():
        member_name(name)
        if (
            archive.getinfo(name).file_size != spec["bytes"]
            or not isinstance(spec["sha256"], str)
            or not re.fullmatch("[0-9a-f]{64}", spec["sha256"])
        ):
            raise ValueError("Invalid file specification")
    return manifest


def owned_manifest(directory):
    marker = directory / MARKER
    if not marker.is_file():
        raise ValueError("Existing directory is not an Autumn installation")
    from autumn.actions.catalog import no_reparse

    no_reparse(marker)
    if marker.stat().st_size > 4 * 1024**2:
        raise ValueError("Install marker too large")
    manifest = json.loads(marker.read_text(encoding="utf-8"))
    if manifest.get("product") != PRODUCT or not isinstance(manifest.get("files"), dict):
        raise ValueError("Unowned installation")
    for name in manifest["files"]:
        member_name(name)
    return manifest


def remove_owned(directory):
    """Remove matching installed files only; keep unknown or owner-modified files."""
    manifest = owned_manifest(directory)
    kept = 0
    for name, spec in manifest["files"].items():
        path = destination(directory, name)
        if not path.exists():
            continue
        if not path.is_file() or sha256(path) != spec["sha256"]:
            kept += 1
            continue
        path.unlink()
    remaining = [p for p in directory.rglob("*") if not p.is_dir() and p.name != MARKER]
    if not remaining:
        (directory / MARKER).unlink()
    parents = {
        parent
        for name in manifest["files"]
        for parent in destination(directory, name).parents
        if parent != directory and parent.is_relative_to(directory)
    }
    for path in sorted(parents, key=lambda p: len(p.parts), reverse=True):
        if path.exists():
            from autumn.actions.catalog import no_reparse

            no_reparse(path)
            try:
                path.rmdir()
            except OSError:
                pass
    try:
        directory.rmdir()
    except OSError:
        pass
    return max(kept, len(remaining))


def _active_guard(root):
    from autumn.ui.windows import SingleInstance

    guard = SingleInstance(root)
    if not guard.primary:
        guard.close()
        raise RuntimeError("Close Autumn before maintenance")
    return guard


def install(payload, root, progress=lambda *args: None, maintenance=None, registry=False):
    root = checked_root(root, True)
    if root.parent == root or len(root.parts) < 3:
        raise ValueError("Unsafe install root")
    guard = _active_guard(root)
    stage = root / ("application.stage-" + uuid4().hex)
    target = root / "application"
    backup = None
    committed = False
    try:
        if target.exists():
            owned_manifest(checked_root(target))
        with zipfile.ZipFile(payload) as archive:
            manifest = read_manifest(archive)
            if shutil.disk_usage(root).free < max(
                12 * 1024**3, sum(s["bytes"] for s in manifest["files"].values()) * 2
            ):
                raise OSError("Setup requires 12 GB free space")
            stage.mkdir()
            for index, (name, spec) in enumerate(manifest["files"].items()):
                path = destination(stage, name)
                path.parent.mkdir(parents=True, exist_ok=True)
                digest = hashlib.sha256()
                count = 0
                with archive.open(name) as incoming, path.open("xb") as outgoing:
                    while chunk := incoming.read(1024**2):
                        count += len(chunk)
                        if count > spec["bytes"]:
                            raise ValueError("Oversized extracted file")
                        digest.update(chunk)
                        outgoing.write(chunk)
                if count != spec["bytes"] or digest.hexdigest() != spec["sha256"]:
                    raise ValueError("Package checksum mismatch")
                progress(index + 1, len(manifest["files"]))
            (stage / MARKER).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        if target.exists():
            backup = root / ("application.previous-" + uuid4().hex[:10])
            target.rename(backup)
        try:
            stage.rename(target)
            committed = True
        except Exception:
            if backup is not None:
                backup.rename(target)
            raise
        maintenance_path = None
        if maintenance:
            folder = checked_root(root / "maintenance", True)
            maintenance_path = folder / ("AutumnMaintenance-" + sha256(maintenance)[:12] + ".exe")
            if not maintenance_path.exists():
                shutil.copy2(maintenance, maintenance_path)
            elif sha256(maintenance_path) != sha256(maintenance):
                raise ValueError("Unexpected maintenance file")
        if registry and maintenance_path:
            register_uninstall(root, manifest["version"], maintenance_path)
            from autumn.setup.shortcut import create_shortcut
            marker = root/'autumn-shortcut.json'
            if marker.exists():
                from autumn.actions.catalog import no_reparse
                no_reparse(marker)
                if marker.stat().st_size > 1024 or json.loads(marker.read_text(encoding='utf-8')).get('product')!=PRODUCT:
                    raise ValueError('Unrelated shortcut record')
            link = create_shortcut(target/'Autumn.exe',root/'Autumn.lnk')
            marker.write_text(json.dumps({'product':PRODUCT,'sha256':sha256(link)}),encoding='utf-8')
        previous_kept = remove_owned(backup) if backup else 0
        return {
            "installed": True,
            "version": manifest["version"],
            "files": len(manifest["files"]),
            "previous_files_retained": previous_kept,
            "data_retained": True,
        }
    finally:
        guard.close()
        if not committed and stage.exists():
            # Only this newly created stage, with explicit verified containment, is removed.
            absolute = checked_root(stage)
            if absolute.parent != root or not absolute.name.startswith("application.stage-"):
                raise ValueError("Stage containment failed")
            shutil.rmtree(absolute)


def uninstall(root, registry=False):
    root = checked_root(root)
    guard = _active_guard(root)
    try:
        target = checked_root(root / "application")
        owned_manifest(target)
        retained = remove_owned(target)
        link = root/'Autumn.lnk'
        marker = root/'autumn-shortcut.json'
        if link.is_file() and marker.is_file():
            from autumn.actions.catalog import no_reparse
            no_reparse(link)
            no_reparse(marker)
            try:
                record = json.loads(marker.read_text(encoding='utf-8')) if marker.stat().st_size<=1024 else {}
            except (OSError,ValueError):
                record = {}
            if record.get('product')==PRODUCT and record.get('sha256')==sha256(link):
                link.unlink()
                marker.unlink()
        if registry:
            unregister_uninstall(root)
            unregister_startup(root)
        return {
            "application_removed": not (target / "Autumn.exe").exists(),
            "modified_or_unknown_files_retained": retained,
            "settings_models_history_retained": True,
            "maintenance_tool_retained": True,
        }
    finally:
        guard.close()


UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\AutumnLocal"


def register_uninstall(root, version, maintenance):
    import subprocess
    import winreg

    with winreg.CreateKeyEx(
        winreg.HKEY_CURRENT_USER, UNINSTALL_KEY, 0, winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE
    ) as key:
        try:
            existing = winreg.QueryValueEx(key, "InstallLocation")[0]
        except FileNotFoundError:
            existing = None
        if existing and Path(existing) != root:
            raise ValueError("Another installation owns the uninstall entry")
        for name, value in {
            "DisplayName": "Autumn — engineering preview",
            "DisplayVersion": version,
            "Publisher": "Autumn Local",
            "InstallLocation": str(root),
            "UninstallString": subprocess.list2cmdline(
                [str(maintenance), "--uninstall", "--root", str(root)]
            ),
        }.items():
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
        winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)


def unregister_uninstall(root):
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as key:
            if Path(winreg.QueryValueEx(key, "InstallLocation")[0]) != root:
                return
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY)
    except FileNotFoundError:
        pass


def unregister_startup(root):
    """Only remove the exact command belonging to this installation."""
    import subprocess
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r'Software\Microsoft\Windows\CurrentVersion\Run',
                            0, winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE) as key:
            expected = subprocess.list2cmdline([str(root / 'application' / 'Autumn.exe')])
            if winreg.QueryValueEx(key,'AutumnLocal')[0] in {expected,subprocess.list2cmdline([str(root / 'application' / 'Autumn.exe'),'--login'])}:
                winreg.DeleteValue(key,'AutumnLocal')
    except FileNotFoundError:
        pass
