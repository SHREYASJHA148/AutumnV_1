import json
import time
from types import SimpleNamespace

import pytest

from autumn.agent.controller import GeneralAgent, Step, needs_review
from autumn.agent.shell import ShellResult
from autumn.brain.contracts import BrainError
from autumn.controller.contracts import Request
from autumn.storage.settings import Settings, atomic_save, load_settings


def step(tool='done', **fields):
    content = fields.pop('script','') if tool=='powershell' else fields.pop('target','') if tool=='open' else fields.pop('message','Complete.')
    return Step(tool=tool,content=content,**{'summary':'Test step','requires_confirmation':False,**fields})


class FakeAgent(GeneralAgent):
    def __init__(self, steps, results=()):
        self.steps = iter(steps)
        self.calls = []
        self.observed = []
        self.results = iter(results)
        self.pending = None
        self.shell = SimpleNamespace(run=self.execute)

    def execute(self, script, checkpoint, **kwargs):
        self.calls.append(script)
        assert checkpoint()
        return next(self.results,ShellResult('OK','Verified test result',0))

    async def next_step(self, messages, checkpoint, settings):
        self.observed.append(messages.copy())
        result = next(self.steps)
        if isinstance(result,Exception):
            raise result
        return result

    def command(self, text='create a note and then read it', *, checkpoint=lambda:True, confirm=lambda step:True, settings=None):
        return self.run(text,settings or Settings(master_control=True),Request(generation=0),checkpoint,lambda _:None,confirm)


def test_general_loop_uses_observations_and_accepts_compound_goal():
    agent = FakeAgent([step('powershell',script="Set-Content -LiteralPath 'test.txt' -Value 'hello'"),
        step('powershell',script="Get-Content -LiteralPath 'test.txt'"),step()])
    result = agent.command()
    assert result.status == 'unverified' and len(agent.calls) == 2
    assert 'create a note and then read it' in agent.observed[-1][1]['content']
    assert 'Verified test result' in agent.observed[-1][-1]['content']


def test_destructive_effect_gets_concrete_review_before_execution():
    planned = step('powershell',script="Remove-Item -LiteralPath 'fixture.txt'")
    agent = FakeAgent([planned])
    reviewed = []
    result = agent.command(confirm=lambda s: reviewed.append(s) or False)
    assert reviewed == [planned] and not agent.calls and result.code == 'CANCELLED'


@pytest.mark.parametrize('result',[ShellResult('ERROR','Partial write'),ShellResult('TIMEOUT'),ShellResult('CANCELLED')])
def test_uncertain_effect_is_not_replayed(result):
    agent = FakeAgent([step('powershell',script='fixture write')],[result])
    outcome = agent.command()
    assert outcome.status == 'partial' and len(agent.calls) == 1


def test_duplicate_mutation_is_stopped():
    write = step('powershell',script='fixture write')
    agent = FakeAgent([write,write])
    assert agent.command().status == 'partial' and len(agent.calls) == 1


def test_followup_retains_unresolved_goal_in_memory():
    agent = FakeAgent([step('ask',message='Which folder?'),step()])
    agent.command('Create a note')
    agent.command('The test folder')
    assert all(part in agent.observed[-1][1]['content'] for part in ('Create a note','Which folder?','The test folder'))
    assert agent.pending is None


def test_model_error_after_effect_reports_partial_truthfully():
    agent = FakeAgent([step('powershell',script='fixture write'),BrainError('TIMEOUT')])
    assert agent.command().status == 'partial'


def test_stop_or_model_disabled_never_dispatches():
    for kwargs in ({'checkpoint':lambda:False},{'settings':Settings(model_enabled=False)}):
        agent = FakeAgent([])
        agent.command(**kwargs)
        assert agent.calls == []


def test_open_target_is_literal_and_not_interpolated():
    agent = FakeAgent([step('open',target="C:\\folder\\it's $(test).txt"),step()])
    agent.command()
    assert "$t='C:\\folder\\it''s $(test).txt'" in agent.calls[0]


def test_schema9_migration_does_not_enable_general_mode(tmp_path):
    path = tmp_path/'settings.json'
    path.write_text(json.dumps({'schema_version':9,'hands_free_on_launch':True}))
    settings, code = load_settings(path)
    assert code == 'MIGRATED' and settings.schema_version == 10 and not settings.master_control
    atomic_save(path,settings.model_copy(update={'master_control':True}))
    assert load_settings(path)[0].master_control


def test_step_payload_validation_and_explicit_effect_review():
    with pytest.raises(ValueError):
        step('powershell')
    assert needs_review(step('open',target='test',requires_confirmation=True))
    assert not needs_review(step('powershell',script='Get-Date'))


def test_shell_unicode_cancellation_timeout_and_no_script_file(tmp_path):
    from autumn.agent.shell import PowerShell
    root = tmp_path/'commands é'
    root.mkdir()
    shell = PowerShell(root)
    result = shell.run("[Console]::Write('Autumn é')",lambda:True)
    assert result.code == 'OK' and result.output == 'Autumn é'
    assert shell.run('this is { not valid',lambda:True).code == 'SYNTAX_ERROR'
    assert shell.run('Start-Sleep -Seconds 10',lambda:True,timeout=.2).code == 'TIMEOUT'
    began = time.monotonic()
    result = shell.run('Start-Sleep -Seconds 10',lambda:time.monotonic()-began < .2)
    assert result.code == 'CANCELLED' and time.monotonic()-began < 2
    assert not list(root.iterdir())


def test_real_body_creates_and_reads_disposable_file_in_unicode_folder(tmp_path):
    from autumn.agent.shell import PowerShell
    root = tmp_path/'body é'
    root.mkdir()
    agent = FakeAgent([step('powershell',script="New-Item -Path 'note.txt' -ItemType File -Value 'hello autumn' | Out-Null"),
        step('powershell',script="Get-Content -LiteralPath 'note.txt'"),step(message='The note contains hello autumn.')])
    agent.shell = PowerShell(root)
    outcome = agent.command()
    assert outcome.status=='unverified'
    assert (root/'note.txt').read_text(encoding='utf-8-sig').strip()=='hello autumn'
    assert 'hello autumn' in agent.observed[-1][-1]['content']


def test_shell_drains_bounded_output_without_hanging(tmp_path):
    from autumn.agent.shell import PowerShell
    result = PowerShell(tmp_path).run("[Console]::Write('x' * 100000)",lambda:True)
    assert result.code=='OK' and 0 < len(result.output) <= 16000


def test_cancel_terminates_owned_descendant(tmp_path):
    import ctypes

    from autumn.agent.shell import PowerShell
    shell = PowerShell(tmp_path)
    pid_file = tmp_path/'child.pid'
    path = str(pid_file).replace("'","''")
    script = f"$p=Start-Process -FilePath ping.exe -ArgumentList @('-t','127.0.0.1') -WindowStyle Hidden -PassThru; $p.Id | Set-Content -LiteralPath '{path}'; Start-Sleep -Seconds 20"
    began = time.monotonic()
    result = shell.run(script,lambda:time.monotonic()-began < 4)
    assert result.code == 'CANCELLED' and pid_file.exists()
    pid = int(pid_file.read_text().strip())
    kernel = ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p,ctypes.c_ulong]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.OpenProcess(0x100000,False,pid)
    try:
        assert not handle or kernel.WaitForSingleObject(handle,1000) == 0
    finally:
        if handle:
            kernel.CloseHandle(handle)
