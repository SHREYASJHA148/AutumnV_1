"""After routing evaluation: one model-planned launch of an owned disposable executable."""
from __future__ import annotations

import ctypes
import json
import time
from ctypes import wintypes
from pathlib import Path

from autumn.actions.catalog import AppEntry, fingerprint
from autumn.controller.contracts import Request
from autumn.controller.worker import Job, Supervisor
from autumn.storage.settings import Settings

ROOT=Path(__file__).resolve().parents[1]


def wait_for(supervisor,kind,timeout=20):
    until=time.monotonic()+timeout
    observed=[]
    while time.monotonic()<until:
        batch=supervisor.poll()
        observed.extend(batch)
        if any(m["kind"]==kind for m in batch):
            return observed
        time.sleep(0.02)
    raise RuntimeError("Required bounded worker response missing")


def main():
    target=ROOT/'dist/phase2 fixture é/AutumnDisposable/AutumnDisposable.exe'
    user=ctypes.WinDLL('user32')
    user.FindWindowW.argtypes=[wintypes.LPCWSTR,wintypes.LPCWSTR]
    user.FindWindowW.restype=wintypes.HWND
    user.PostMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
    if user.FindWindowW('AutumnPhase2DisposableClass',None):
        raise RuntimeError('Unowned disposable target already running')
    settings=Settings(apps=(AppEntry(id='fixture',name='Fixture Editor',kind='executable',
        target=str(target),fingerprint=fingerprint(target),enabled=True,reviewed=True),),
        folders=(),sites=(),enabled_skills=('app.open','help.capabilities'))
    supervisor=Supervisor(ROOT/'.cache/phase3 native model é')
    report={'personal_apps_controlled':False,'actions_dispatched':0,'passed':False}
    hwnd=None
    try:
        wait_for(supervisor,'ready')
        supervisor.submit(Job(kind='save_settings',generation=0,settings=settings))
        wait_for(supervisor,'settings_saved')
        request=Request(generation=0)
        supervisor.submit(Job(kind='execute',generation=0,request=request,text='I need the application called Fixture Editor.'))
        observed=wait_for(supervisor,'action_result')
        result=next(m for m in observed if m['kind']=='action_result')
        metrics=next((m.get('metrics',{}) for m in observed if m['kind']=='model_status'),{})
        report['model_thinking_disabled']=metrics.get('thinking_disabled',False)
        report['model_routed']=metrics.get('path')=='model'
        report['result_status']=result['outcome']['status']
        report['skill']=result.get('skill')
        until=time.monotonic()+3
        while not hwnd and time.monotonic()<until:
            hwnd=user.FindWindowW('AutumnPhase2DisposableClass',None)
            time.sleep(0.03)
        report['disposable_window_observed']=bool(hwnd)
        report['actions_dispatched']=int(bool(hwnd))
        report['passed']=bool(hwnd) and report['model_routed'] and report['model_thinking_disabled'] and report['skill']=='app.open' and report['result_status']=='succeeded'
    finally:
        if hwnd:
            user.PostMessageW(hwnd,0x0010,0,0)
        report['worker_shutdown']=supervisor.shutdown()
        (ROOT/'docs/reports/phase3_native_e2e.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
    return 0 if report['passed'] and report['worker_shutdown'] else 1


if __name__=='__main__':
    raise SystemExit(main())
