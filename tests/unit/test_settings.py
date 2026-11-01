import json
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from autumn.storage.settings import Settings, atomic_save, load_settings


def test_first_launch_safe_and_roundtrip(tmp_path):
    path = tmp_path / "space é" / "settings.json"
    settings, code = load_settings(path)
    assert code == "DEFAULTS_CREATED"
    assert not settings.microphone_enabled_at_start
    assert not settings.wake_enabled
    assert not settings.conversation_persistence
    atomic_save(path, Settings(history_days=14))
    assert load_settings(path)[0].history_days == 14


def test_schema5_migration_preserves_explicitly_disabled_phase5_skills(tmp_path):
    path=tmp_path/'settings.json'
    settings=Settings(schema_version=5,enabled_skills=('help.capabilities',))
    atomic_save(path,settings)
    restored,code=load_settings(path)
    assert code=='MIGRATED' and restored.schema_version==10
    assert restored.enabled_skills==('help.capabilities',)
    assert not restored.microphone_enabled_at_start and not restored.wake_enabled


@pytest.mark.parametrize("text", ["{bad", '{"schema_version":99}', '{"microphone_enabled_at_start":true}', '[1]', '"text"'])
def test_corrupt_settings_preserved(tmp_path, text):
    path = tmp_path / "settings.json"
    path.write_text(text, encoding="utf-8")
    settings, code = load_settings(path)
    assert code == "RECOVERED_DEFAULTS"
    assert settings == Settings()
    assert next(tmp_path.glob("settings.recovered-*.json")).read_text(encoding="utf-8") == text


def test_atomic_failure_leaves_last_good_file(tmp_path):
    path = tmp_path / "settings.json"
    atomic_save(path, Settings())
    previous = path.read_bytes()
    with patch("autumn.storage.settings.os.replace", side_effect=OSError("disk full")):
        with pytest.raises(OSError):
            atomic_save(path, Settings(history_days=14))
    assert path.read_bytes() == previous
    assert len(list(tmp_path.iterdir())) == 1


@pytest.mark.parametrize("update", [
    {"model_tag": "cloud-model"}, {"model_digest": "changed"},
    {"history_days": 0}, {"conversation_persistence": True}, {"arbitrary": "value"},
    {"hotkeys": {"stop": "Ctrl+Alt+F9", "voice_toggle": "Ctrl+Alt+F9"}},
])
def test_settings_reject_unsafe_or_unknown_fields(update):
    with pytest.raises(ValidationError):
        Settings.model_validate({**json.loads(Settings().model_dump_json()), **update})
