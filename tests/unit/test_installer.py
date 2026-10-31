import hashlib
import json
import zipfile

import pytest

from autumn.setup.install import PRODUCT, install, member_name, uninstall


def payload(path, files=None, version="0.7.0"):
    files = files or {
        "Autumn.exe": b"fixed fake executable bytes",
        "_internal/fixed.txt": b"public fixture",
    }
    manifest = {
        "product": PRODUCT,
        "version": version,
        "files": {
            name: {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            for name, data in files.items()
        },
    }
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("release-manifest.json", json.dumps(manifest))
        for name, data in files.items():
            archive.writestr(name, data)
    return manifest


def test_per_user_install_upgrade_and_uninstall_preserve_data_and_user_files(tmp_path):
    root = tmp_path / "Autumn test é"
    package = tmp_path / "payload.zip"
    payload(package)
    assert install(package, root)["installed"]
    (root / "config").mkdir()
    (root / "config/settings.json").write_text("owner data")
    (root / "application/my-notes.txt").write_text("keep this user file")
    (root / "application/user-folder").mkdir()
    assert uninstall(root)["application_removed"]
    assert (root / "config/settings.json").read_text() == "owner data"
    assert (root / "application/my-notes.txt").read_text() == "keep this user file"
    assert (root / "application/user-folder").is_dir()


def test_upgrade_uses_validated_stage_and_cleans_only_matching_old_files(tmp_path):
    root = tmp_path / "Autumn"
    package = tmp_path / "payload.zip"
    payload(package)
    install(package, root)
    payload(package, {"Autumn.exe": b"new public bytes"}, "0.7.1")
    result = install(package, root)
    assert (
        result["version"] == "0.7.1"
        and (root / "application/Autumn.exe").read_bytes() == b"new public bytes"
    )
    assert not list(root.glob("application.stage-*")) and not list(
        root.glob("application.previous-*")
    )


def test_unmanaged_existing_application_is_never_replaced(tmp_path):
    root = tmp_path / "Autumn"
    (root / "application").mkdir(parents=True)
    (root / "application/personal.txt").write_text("keep")
    package = tmp_path / "payload.zip"
    payload(package)
    with pytest.raises(ValueError):
        install(package, root)
    assert (root / "application/personal.txt").read_text() == "keep"


@pytest.mark.parametrize(
    "name",
    [
        "../escape",
        "/absolute",
        "C:/evil",
        "a\\evil",
        "CON.exe",
        "CON .exe",
        "a/file:stream",
        "a/file.",
        "a//b",
        "a/./b",
        "a/evil?",
    ],
)
def test_zip_members_cannot_escape_or_alias_windows_paths(name):
    with pytest.raises(ValueError):
        member_name(name)


def test_corrupt_payload_does_not_replace_current_install(tmp_path):
    root = tmp_path / "Autumn"
    package = tmp_path / "payload.zip"
    payload(package)
    install(package, root)
    before = (root / "application/Autumn.exe").read_bytes()
    manifest = payload(tmp_path / "original.zip")
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("release-manifest.json", json.dumps(manifest))
        archive.writestr("Autumn.exe", b"x" * manifest["files"]["Autumn.exe"]["bytes"])
        archive.writestr("_internal/fixed.txt", b"public fixture")
    with pytest.raises(ValueError):
        install(package, root)
    assert (root / "application/Autumn.exe").read_bytes() == before
    assert not list(root.glob("application.stage-*"))


def test_owner_modified_installed_file_is_not_deleted(tmp_path):
    root = tmp_path / "Autumn"
    package = tmp_path / "payload.zip"
    payload(package)
    install(package, root)
    (root / "application/_internal/fixed.txt").write_text("owner modified")
    result = uninstall(root)
    assert result["modified_or_unknown_files_retained"] >= 1
    assert (root / "application/_internal/fixed.txt").read_text() == "owner modified"


def test_disk_full_is_refused_before_extracting_or_replacing(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from autumn.setup import install as service

    monkeypatch.setattr(service.shutil, "disk_usage", lambda root: SimpleNamespace(free=1024))
    package = tmp_path / "payload.zip"
    payload(package)
    root = tmp_path / "Autumn"
    with pytest.raises(OSError):
        install(package, root)
    assert not (root / "application").exists() and not list(root.glob("application.stage-*"))


@pytest.mark.parametrize('owned',[True,False])
def test_uninstall_only_removes_its_exact_startup_command(tmp_path,monkeypatch,owned):
    import subprocess
    import sys
    from types import SimpleNamespace

    from autumn.setup.install import unregister_startup

    class Key:
        def __enter__(self):
            return self
        def __exit__(self,*args):
            pass

    deleted=[]
    command=subprocess.list2cmdline([str(tmp_path/'application/Autumn.exe')]) if owned else 'another application'
    fake=SimpleNamespace(HKEY_CURRENT_USER=1,KEY_QUERY_VALUE=1,KEY_SET_VALUE=2,
                         OpenKey=lambda *args:Key(),QueryValueEx=lambda *args:(command,1),
                         DeleteValue=lambda *args:deleted.append(args[-1]))
    monkeypatch.setitem(sys.modules,'winreg',fake)
    unregister_startup(tmp_path)
    assert deleted==(['AutumnLocal'] if owned else [])
