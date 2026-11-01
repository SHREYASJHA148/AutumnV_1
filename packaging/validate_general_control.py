"""Public development probes; no microphone, personal targets or held-out data."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

from autumn.agent.controller import GeneralAgent
from autumn.agent.shell import PowerShell, ShellResult
from autumn.brain.planner import Planner
from autumn.controller.contracts import Request
from autumn.storage.settings import Settings


def main():
    root = Path(__file__).resolve().parents[1]
    fixture = root/'.cache/general-control-public é'
    fixture.mkdir(parents=True,exist_ok=True)
    # Real model suggestions are reviewed against these fixture-only commands BEFORE dispatch.
    # A rejected script remains a failed test, never executes, and is not repaired for the model.
    class FixtureShell:
        def __init__(self):
            self.executed = []
            self.cwd = fixture
            self.real = PowerShell(fixture)

        def approved(self, script):
            # Quoted filenames such as second-note.txt are data, not command names.
            command_text = re.sub(r"'(?:[^']|'')*'|\"(?:[^\"`]|`.)*\"","''",script)
            commands = re.findall(r'\b[A-Za-z]+-[A-Za-z]+\b',command_text)
            permitted = {'set-content','get-content','write-output','test-path','out-string','new-item','get-date'}
            # No navigation, arbitrary executables, substitutions or non-fixture absolute paths.
            bad = any(c.casefold() not in permitted for c in commands)
            absolute = re.findall(r'[A-Za-z]:[\\/][^\r\n\"\']+',script)
            bad |= any(not p.casefold().startswith(str(fixture).casefold()) for p in absolute)
            bad |= bool(re.search(r'(?<!&)&(?!&)|`|\$\(|::|\.\.[/\\]|\b(?:iex|cmd|powershell|start|python|explorer|exit)\b',script,re.I))
            return not bad

        def run(self, script, checkpoint, **kwargs):
            if not self.approved(script):
                self.executed.append({'approved':False,'script':script})
                return ShellResult('ERROR','Disposable test allowlist rejected the suggestion; nothing executed.')
            self.executed.append({'approved':True,'script':script})
            return self.real.run(script,checkpoint,**kwargs)

    previous = root/'docs/reports/general_control_public.json'
    prior = json.loads(previous.read_text(encoding='utf-8')) if previous.exists() else {}
    report = {'scope':'public disposable development goals; not a broad accuracy or physical-device acceptance result',
        'previous_format_failures':prior.get('previous_format_failures',[])+[{'cases':[{'goal':c['goal'],'status':c['outcome']['status'],'error':c.get('error')} for c in prior.get('cases',[])]}],
        'cases':[]}
    blocked_path_case = next((c for c in prior.get('cases',[]) if 'autumn-note.txt' in c['goal']),prior.get('known_blocked_literal_path_case'))
    report['known_blocked_literal_path_case'] = blocked_path_case
    goals = [
        "Reply with a brief friendly introduction as Autumn. Do not use tools.",
        'Use PowerShell to tell me the current date and time, then answer in English.',
        "In the current working directory, create a new file called second-note.txt containing exactly hello autumn, then read it back. Do not overwrite any existing file. Use PowerShell, not inspect.",
    ]
    for goal in goals:
        shell = FixtureShell()
        planner = Planner()
        original = planner.transport.request
        packets = []
        async def record(*args,**kwargs):
            result = await original(*args,**kwargs)
            if args[0]=='/api/chat':
                packets.append(result)
            return result
        planner.transport.request = record
        agent = GeneralAgent(planner,shell)
        began = time.monotonic()
        progress = []
        outcome = agent.run(goal,Settings(master_control=True),Request(generation=0),lambda:time.monotonic()-began < 100,
            progress.append,lambda step:step.tool=='powershell' and shell.approved(step.script))
        report['cases'].append({'goal':goal,'seconds':round(time.monotonic()-began,3),'outcome':outcome.model_dump(mode='json'),
            'progress':progress,'scripts':shell.executed,'error':agent.last_error,'last_model_reply':getattr(agent,'last_reply',''),
            'model_content':[''.join(p.get('message',{}).get('content','') for p in run) for run in packets]})
        print(json.dumps({'case':len(report['cases']),'status':outcome.status,'seconds':report['cases'][-1]['seconds']},ensure_ascii=False),flush=True)
    note = fixture/'second-note.txt'
    report['fixture_content_verified'] = note.exists() and note.read_text(encoding='utf-8-sig').strip()=='hello autumn'
    # A separately owned UI fixture proves accessibility activation and text entry, not arbitrary app support.
    fixture_code = """import sys,os
from pathlib import Path
from PySide6.QtWidgets import QApplication,QWidget,QVBoxLayout,QLineEdit,QPushButton
from PySide6.QtGui import QAccessible
app=QApplication(sys.argv); w=QWidget();w.setWindowTitle('Autumn disposable automation fixture')
QAccessible.setActive(True)
layout=QVBoxLayout(w); edit=QLineEdit();edit.setAccessibleName('Autumn fixture editor');layout.addWidget(edit)
button=QPushButton('Autumn fixture save');button.setAccessibleName('Autumn fixture save');layout.addWidget(button)
button.clicked.connect(lambda:Path(sys.argv[1]).write_text(edit.text(),encoding='utf-8'))
w.resize(430,160);w.show();Path(sys.argv[2]).write_text(str(os.getpid()));app.exec()
"""
    output = fixture/'uia-result.txt'
    ready = fixture/'ui-ready.pid'
    ready.unlink(missing_ok=True)
    child = subprocess.Popen([sys.executable,'-c',fixture_code,str(output),str(ready)],creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        deadline = time.monotonic()+5
        while not ready.exists() and child.poll() is None and time.monotonic() < deadline:
            time.sleep(.05)
        actual_pid = int(ready.read_text())
        shell = PowerShell(fixture)
        snapshot = shell.run(f'Autumn-Desktop -ProcessId {actual_pid}',lambda:True)
        report['owned_ui_snapshot'] = snapshot.observation()
        controls = [c for w in json.loads(snapshot.output) for c in w['controls']] if snapshot.code=='OK' else []
        edit = next(c for c in controls if c['name']=='Autumn fixture editor')
        button = next(c for c in controls if c['name']=='Autumn fixture save')
        typed = shell.run(f"Autumn-Type -Id '{edit['id']}' -Text 'local automation verified'",lambda:True)
        clicked = shell.run(f"Autumn-Click -Id '{button['id']}'",lambda:True)
        until = time.monotonic()+1
        while not output.exists() and time.monotonic() < until:
            time.sleep(.025)
        report['owned_ui_fixture'] = {'inspect':snapshot.code,'type':typed.code,'click':clicked.code,
            'verified':output.exists() and output.read_text(encoding='utf-8')=='local automation verified'}
    except Exception as error:
        report['owned_ui_fixture'] = {'verified':False,'error':type(error).__name__}
    finally:
        child.terminate()
        child.wait(timeout=3)
    path = root/'docs/reports/general_control_public.json'
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'fixture_content_verified':report['fixture_content_verified'],'owned_ui_fixture':report['owned_ui_fixture']}),flush=True)


if __name__ == '__main__':
    main()
