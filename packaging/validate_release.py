"""Isolated per-user setup/launch/removal with scrubbed environment, no registry writes."""
import argparse
import json
import os
import subprocess
import time
import tomllib
from pathlib import Path
from uuid import uuid4


def main():
    root = Path(__file__).resolve().parents[1]
    parser=argparse.ArgumentParser()
    parser.add_argument('--prefix',default='phase7')
    args=parser.parse_args()
    version=tomllib.loads((root/'pyproject.toml').read_text(encoding='utf-8'))['project']['version']
    release = root / ('dist/Autumn-'+version+'-preview')
    report_root = root / 'docs/reports'
    fixture = root / '.cache' / ('installed preview é-' + uuid4().hex[:8])
    fixture.mkdir()
    env = {k:v for k,v in os.environ.items() if not k.startswith(('PYTHON','QT_','QML_','VIRTUAL_ENV','UV_','CONDA'))}
    for key,folder in {'LOCALAPPDATA':'local','APPDATA':'roaming','TEMP':'temp','TMP':'temp','USERPROFILE':'user'}.items():
        path = fixture / folder
        path.mkdir(exist_ok=True)
        env[key] = str(path)
    env['PATH'] = str(Path(os.environ['SystemRoot']) / 'System32')
    installed = fixture / 'local/Autumn'
    setup = release / 'AutumnSetup.exe'

    def run(arguments, report, scale=None):
        local_env = {**env}
        if scale:
            local_env['QT_SCALE_FACTOR'] = str(scale)
        start = time.perf_counter()
        child = subprocess.Popen(arguments,env=local_env,cwd=fixture,creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            code = child.wait(timeout=60)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=3)
            raise
        elapsed = time.perf_counter()-start
        data = json.loads(report.read_text(encoding='utf-8'))
        if code or not data.get('passed'):
            raise RuntimeError('Release validation failed: ' + report.stem)
        print(json.dumps({'step':report.stem,'passed':True,'wall_seconds':round(elapsed,3)}),flush=True)
        return data,elapsed

    def named(name):
        return report_root/(args.prefix+'_'+name+'.json')
    run([str(setup),'--root',str(installed),'--no-registry','--smoke-report',str(named('installer_install'))],named('installer_install'))
    assert json.loads((installed/'application/_internal/autumn/speech/external_assets.json').read_text())=={}
    readiness=[]
    for name,scale in [('cold',None),('warm',None),('scale2',2)]:
        report = named('installed_'+name)
        data,wall = run([str(installed/'application/Autumn.exe'),'--data-dir',str(installed/'isolated-ui'),'--smoke-report',str(report)],report,scale)
        # Includes process exit overhead, so an upper bound rather than a direct readiness timestamp.
        readiness.append({'run':name,'launch_to_typed_ready_upper_bound_seconds':round(wall-data['elapsed_seconds']+data['ui_ready_after_qml_ms']/1000,3),'direct_readiness_timestamp':False})
    keep = {'config/owner-fixture.json':'public configuration','models/keep-fixture.txt':'public model fixture','data/keep-fixture.txt':'public history fixture','application/owner-note.txt':'public owner file'}
    for name,text in keep.items():
        path = installed/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(text,encoding='utf-8')
    run([str(setup),'--uninstall','--root',str(installed),'--no-registry','--smoke-report',str(named('installer_uninstall'))],named('installer_uninstall'))
    assert all((installed/name).read_text(encoding='utf-8')==text for name,text in keep.items())
    assert not (installed/'application/Autumn.exe').exists()
    named('release_validation').write_text(json.dumps({'passed':True,'scope':'same Windows account, scrubbed environment, disposable per-user install, NO registry writes; not clean-account acceptance','readiness_upper_bounds':readiness,'developer_asset_path_removed':True,'owner_fixtures_retained':True,'models_downloaded':False,'audio_hardware_opened':False,'installed_application_removed':True,'fixture':fixture.name},indent=2),encoding='utf-8')


if __name__ == '__main__':
    main()
