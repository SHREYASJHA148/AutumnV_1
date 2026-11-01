"""Collect verification metadata for the owner's requested launch extension."""
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    root=Path(__file__).resolve().parents[1]
    reports=root/'docs/reports'
    def read(name):
        return json.loads((reports/name).read_text(encoding='utf-8'))
    names=('personal_launch_tests.xml','personal_startup_regressions.xml','personal_final_regressions.xml','personal_shortcut_test.xml')
    suites=[ET.parse(reports/name).getroot() for name in names]
    assert not any(list(s.iter('failure')) or list(s.iter('error')) for s in suites)
    tests={(c.get('classname'),c.get('name')) for suite in suites for c in suite.iter('testcase')}
    profile=read('personal_profile.json')
    startup=read('personal_startup_probe.json')
    frozen=read('personal_standalone_ui.json')
    integrity=read('personal_freeze_integrity.json')
    install=read('personal_release_validation.json')
    assert all(r.get('passed') for r in (startup,frozen,integrity,install))
    release=root/'dist/Autumn-0.7.1-preview'
    checksums={name:digest(release/name) for name in ('AutumnSetup.exe','payload.zip','release-manifest.json')}
    (release/'SHA256SUMS.txt').write_text(''.join(value+'  '+name+'\n' for name,value in checksums.items()),encoding='ascii')
    source=hashlib.sha256()
    for path in sorted((root/'src/autumn').rglob('*')):
        if path.is_file() and path.suffix in {'.py','.qml','.ico'}:
            source.update(path.relative_to(root).as_posix().encode())
            source.update(path.read_bytes())
    report={'version':'0.7.1','date':'2026-11-01','requested_extension':'implemented and configured','release_acceptance':'NOT PASSED; previous accuracy/hardware/performance acceptance remains open','unique_passing_software_tests':len(tests),'full_suite_cases':438,'additional_unique_regressions':len(tests)-438,'startup':startup,'personal_profile':profile,'scope':'normal Windows account permissions; installed apps/common folders and explicit supported local paths, with application validation; no generated command execution','real_microphone_or_speakers_used_in_tests':False,'new_dependencies':False,'brain_model_changed':False,'source_fingerprint_sha256':source.hexdigest(),'freeze_integrity':integrity,'standalone_ui':{'passed':frozen['passed'],'render_timings':frozen['input_to_render']},'isolated_installer':install,'installer_bytes':(release/'AutumnSetup.exe').stat().st_size,'checksums':checksums,'attempts_and_limits':['Initial real-server startup did not report brain readiness; subsequent real startup checks passed. Startup activation budget raised to 40 seconds without changing 15-second command planning. A fresh cold-server repeat is not claimed.','A hidden-window timing attempt did not meet visible-render timing; the sequential visible-window rerun passed at 16 ms p95 input/Stop. Failed attempt retained in personal_standalone_hidden_attempt.json.','The microphone was simulated during startup/tray testing. Owner speech, echo/false activation, real device/power/accessibility/offline/clean-account and two-hour stability acceptance remain pending.','The native workspace launcher exists; isolated installer validation deliberately avoids registry writes. Complete public distribution review and signing remain pending.'],'evidence':[ *names,'personal_startup_probe.json','personal_initial_startup.json','personal_standalone_ui.json','personal_standalone_hidden_attempt.json','personal_freeze_integrity.json','personal_release_validation.json','personal_profile.json']}
    (reports/'personal_launch.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'tests':len(tests),'shortcut':profile['shortcut'],'enabled_apps':startup['enabled_apps'],'installer_mb':round(report['installer_bytes']/1024**2,1),'installer_sha256':checksums['AutumnSetup.exe']}))


if __name__=='__main__':
    main()
