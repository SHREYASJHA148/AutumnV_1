from autumn.actions.engine import Engine
from autumn.winworker.search import scan


def test_filename_only_type_filter_and_bounded_scan(tmp_path):
    (tmp_path / "budget.xlsx").write_text("private content must not be searched")
    (tmp_path / "budget.pdf").write_text("other")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules/budget.xlsx").write_text("excluded")
    result = scan((tmp_path,), "budget", "spreadsheet", lambda: True)
    assert [p.name for p, _ in result.matches] == ["budget.xlsx"]
    limited = scan((tmp_path,), "budget", "any", lambda: True, max_entries=1)
    assert limited.limited
    cancelled = scan((tmp_path,), "budget", "any", lambda: False)
    assert cancelled.cancelled and not cancelled.matches


def test_inaccessible_root_and_escape(tmp_path):
    def denied(_):
        raise PermissionError()

    assert scan((tmp_path,), "budget", "any", lambda: True, scandir=denied).denied == 1
    import pytest

    from autumn.actions.catalog import within
    outside = tmp_path.parent / "outside"
    outside.mkdir(exist_ok=True)
    with pytest.raises(ValueError):
        within(outside, tmp_path)


def test_match_selection_expiry_and_revalidation(tmp_path):
    import pytest

    from autumn.actions.schemas import FolderArgs, OpenFolder
    from autumn.storage.settings import Settings
    now = [0.0]
    engine = Engine(None, Settings(), clock=lambda: now[0])
    path = tmp_path / "fixture.txt"
    path.write_text("test")
    rows = engine.register_matches([(path, tmp_path)])
    action = OpenFolder(arguments=FolderArgs(candidate_id=rows[0]["id"]))
    assert engine.resolve(action).target == tmp_path
    now[0] = 31
    with pytest.raises(LookupError):
        engine.resolve(action)
