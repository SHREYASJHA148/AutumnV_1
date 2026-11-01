from autumn.actions.catalog import AppEntry
from autumn.winworker import windows


def test_handoff_without_a_pid_does_not_wait_for_an_unverifiable_window(monkeypatch):
    reads=[]
    monkeypatch.setattr(windows,'visible_windows',lambda:reads.append(True) or {})
    monkeypatch.setattr(windows,'activate_package',lambda target:0)
    def no_wait(seconds):
        raise AssertionError('No PID is available to match; do not poll')
    monkeypatch.setattr(windows.time,'sleep',no_wait)
    app=AppEntry(id='fixture',name='Fixture',kind='package',target='Fixture!App',enabled=True,reviewed=True)
    outcome=windows.WindowsAdapter.launch_app(None,app,lambda:True)
    assert outcome.status=='unverified' and outcome.code=='HANDOFF'
    assert len(reads)==1


def test_known_process_keeps_new_window_verification(monkeypatch):
    reads=[]
    def windows_for_pid():
        reads.append(True)
        return {} if len(reads)==1 else {99:1234}
    monkeypatch.setattr(windows,'visible_windows',windows_for_pid)
    monkeypatch.setattr(windows,'activate_package',lambda target:1234)
    app=AppEntry(id='fixture',name='Fixture',kind='package',target='Fixture!App',enabled=True,reviewed=True)
    outcome=windows.WindowsAdapter.launch_app(None,app,lambda:True)
    assert outcome.status=='succeeded' and len(reads)==2
