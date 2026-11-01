"""Public timeout reproduction/repair checks; no microphone or personal actions."""
import asyncio
import json
import re
import time
from pathlib import Path

from autumn.actions.catalog import AppEntry
from autumn.actions.engine import Engine, Outcome
from autumn.agent.controller import SYSTEM, GeneralAgent
from autumn.agent.routing import native_route
from autumn.agent.shell import PowerShell, ShellResult
from autumn.brain.planner import Planner
from autumn.controller.contracts import Request
from autumn.storage.settings import Settings


def main():
    root=Path(__file__).resolve().parents[1]
    fixture=root/'.cache/timeout-repair é'
    fixture.mkdir(parents=True,exist_ok=True)
    settings=Settings(master_control=True,apps=tuple(AppEntry(id=name.casefold(),name=name,kind='package',
        target='Disposable!'+name,enabled=True,reviewed=True) for name in ('Calculator','Spotify')))
    report={'scope':'public disposable development checks; not owner microphone/room acceptance','native':[],'model':[],'end_to_end':[]}
    class Adapter:
        def __init__(self):
            self.calls=[]
        def perform(self,resolved,permit,checkpoint):
            assert checkpoint() and permit.outcome=='allow'
            self.calls.append(resolved.action.skill)
            return Outcome(status='succeeded',code='OK',message='Disposable adapter verified dispatch.',verification='fake adapter; no app launched')
    for text in ('open Spotify','please open Calculator','Autumn, could you open Spotify for me?'):
        started=time.monotonic()
        routing=native_route(text,settings)
        adapter=Adapter()
        outcomes=Engine(adapter,settings).execute(routing.plan,Request(generation=0),lambda:True,lambda *_:None)
        report['native'].append({'input':text,'seconds':round(time.monotonic()-started,4),'verified_dispatch':adapter.calls==['app.open'] and outcomes[0].code=='OK','model_called':False})
    async def model():
        for text in ('please open calculator','open spotify','tell me the current date and time'):
            agent=GeneralAgent(Planner(),PowerShell(fixture))
            started=time.monotonic()
            try:
                step=await agent.next_step([{'role':'system','content':SYSTEM},{'role':'user','content':text}],lambda:True,settings)
                row={'input':text,'seconds':round(time.monotonic()-started,3),'step':step.model_dump(mode='json')}
            except Exception as error:
                row={'input':text,'seconds':round(time.monotonic()-started,3),'error':getattr(error,'code',type(error).__name__)}
            report['model'].append(row)
            print(json.dumps(row),flush=True)
    asyncio.run(model())
    class FixtureShell:
        cwd=fixture
        def __init__(self):
            self.calls=[]
        def run(self,script,checkpoint,**kwargs):
            stripped=re.sub(r"'(?:[^']|'')*'|\"(?:[^\"`]|`.)*\"","''",script)
            commands=re.findall(r'\b[A-Za-z]+-[A-Za-z]+\b',stripped)
            permitted={'get-date','write-output','new-item','get-content','out-null','set-content','test-path'}
            allowed=bool(commands) and all(c.casefold() in permitted for c in commands)
            allowed &= not bool(re.search(r'(?<!&)&(?!&)|`|\$\(|::|\.\.[/\\]|\b(?:iex|cmd|powershell|start|python|explorer|exit)\b',script,re.I))
            absolute=re.findall(r'[A-Za-z]:[\\/][^\r\n\"\']+',script)
            allowed &= all(p.casefold().replace('\\','/').startswith(str(fixture).casefold().replace('\\','/')) for p in absolute)
            self.calls.append({'script':script,'allowed':allowed})
            return PowerShell(fixture).run(script,checkpoint,**kwargs) if allowed else ShellResult('ERROR','Disposable allowlist rejected the suggestion; nothing executed.')
    for text in ('Use PowerShell to read the current date and time, then tell me the result.',):
        shell=FixtureShell()
        agent=GeneralAgent(Planner(),shell)
        started=time.monotonic()
        outcome=agent.run(text,settings,Request(generation=0),lambda:time.monotonic()-started < 50,lambda _:None,lambda _:False)
        report['end_to_end'].append({'input':text,'seconds':round(time.monotonic()-started,3),'outcome':outcome.model_dump(mode='json'),'tools':shell.calls})
    report['passed']=all(r['verified_dispatch'] for r in report['native']) and all('error' not in r for r in report['model']) and all(r['outcome']['status'] in {'succeeded','unverified'} and r['tools'] for r in report['end_to_end'])
    (root/'docs/reports/timeout_after.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'passed':report['passed'],'end_to_end':report['end_to_end']}),flush=True)


if __name__=='__main__':
    main()
