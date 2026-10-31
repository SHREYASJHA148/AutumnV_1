import hashlib
import io

import pytest

from autumn.setup import assets


class Response(io.BytesIO):
    def __init__(self, data, status=200, headers=None):
        super().__init__(data)
        self.status = status
        self.headers = headers or {}


class Opener:
    def __init__(self, response):
        self.response = response
        self.requests = []

    def open(self, request, timeout):
        self.requests.append(request)
        return self.response


@pytest.fixture
def artifact(monkeypatch):
    data = b"Autumn fixed public test bytes"
    sha = hashlib.sha256(data).hexdigest()
    monkeypatch.setitem(assets.ARTIFACTS, "test", ("stt/test.bin", len(data), sha))
    monkeypatch.setitem(assets.URLS, "test", "https://huggingface.co/fixed-test")
    return data, sha


def test_download_pin_and_corrupt_target_preserved(tmp_path, artifact):
    data, sha = artifact
    target = tmp_path / "stt/test.bin"
    target.parent.mkdir()
    target.write_bytes(b"old unexpected data")
    assets.download("test", tmp_path, lambda: True, opener=Opener(Response(data)))
    assert target.read_bytes() == data
    assert next(target.parent.glob("test.bin.replaced-*")).read_bytes() == b"old unexpected data"
    assert not list(tmp_path.rglob("*.partial"))


def test_interrupted_download_can_resume_exact_range(tmp_path, artifact):
    data, sha = artifact

    class Interrupted(Response):
        def read(self, size):
            if self.tell():
                raise OSError("Injected disconnect")
            return super().read(7)

    with pytest.raises(OSError):
        assets.download("test", tmp_path, lambda: True, opener=Opener(Interrupted(data)))
    partial = tmp_path / f"stt/test.bin.{sha[:12]}.partial"
    assert partial.read_bytes() == data[:7] and not (tmp_path / "stt/test.bin").exists()
    opener = Opener(
        Response(data[7:], 206, {"Content-Range": f"bytes 7-{len(data) - 1}/{len(data)}"})
    )
    assets.download("test", tmp_path, lambda: True, opener=opener)
    assert opener.requests[0].get_header("Range") == "bytes=7-"
    assert (tmp_path / "stt/test.bin").read_bytes() == data


@pytest.mark.parametrize("bad", ["checksum", "too_long", "cancel"])
def test_invalid_or_cancelled_download_never_loadable(tmp_path, artifact, bad):
    data, sha = artifact
    payload = (
        b"x" * len(data) if bad == "checksum" else data + b"extra" if bad == "too_long" else data
    )
    with pytest.raises((ValueError, InterruptedError)):
        assets.download("test", tmp_path, lambda: bad != "cancel", opener=Opener(Response(payload)))
    assert not (tmp_path / "stt/test.bin").exists()


def test_unowned_partial_and_unexpected_resume_are_refused(tmp_path, artifact):
    data, sha = artifact
    folder = tmp_path / "stt"
    folder.mkdir()
    partial = folder / f"test.bin.{sha[:12]}.partial"
    partial.write_bytes(b"user")
    with pytest.raises(ValueError):
        assets.download("test", tmp_path, lambda: True, opener=Opener(Response(data)))
    assert partial.read_bytes() == b"user"


@pytest.mark.parametrize("path", ["../outside", "/absolute", "foo:stream", "folder\\escape"])
def test_destination_never_escapes_root(tmp_path, path):
    with pytest.raises(ValueError):
        assets.destination(tmp_path, path)


def test_verified_import_and_cancel_cleanup(tmp_path, artifact):
    data, sha = artifact
    source = tmp_path / "source"
    (source / "stt").mkdir(parents=True)
    (source / "stt/test.bin").write_bytes(data)
    dest = tmp_path / "destination"
    with pytest.raises(InterruptedError):
        assets.import_asset("test", source, dest, lambda: False)
    assert not list(dest.rglob("*.partial"))
    assets.import_asset("test", source, dest, lambda: True)
    assert (dest / "stt/test.bin").read_bytes() == data


def test_https_redirect_cannot_downgrade_or_leave_sources():
    import urllib.request

    handler = assets.HTTPSOnlyRedirect()
    for url in (
        "http://huggingface.co/a",
        "https://example.com/a",
        "https://user:secret@huggingface.co/a",
    ):
        with pytest.raises(ValueError):
            handler.redirect_request(
                urllib.request.Request("https://huggingface.co/a"), None, 302, "", {}, url
            )
