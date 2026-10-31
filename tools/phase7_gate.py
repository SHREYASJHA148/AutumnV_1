"""Collect existing metadata evidence; never runs or reads the held-out evaluation."""
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    reports = root/'docs/reports'
    def read(name):
        return json.loads((reports/name).read_text(encoding='utf-8-sig'))
    suites = [ET.parse(reports/name).getroot() for name in ('phase7_tests.xml','phase7_setup_regressions.xml')]
    unique = {(c.get('classname'),c.get('name')) for suite in suites for c in suite.iter('testcase')}
    assert not any(list(s.iter('failure')) or list(s.iter('error')) for s in suites)
    release = root/'dist/Autumn-0.7.0-preview'
    payload = json.loads((release/'release-manifest.json').read_text(encoding='utf-8'))
    package = release/'AutumnSetup.exe'
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    frozen = read('phase7_standalone_ui.json')
    installer = read('phase7_release_validation.json')
    speech = read('phase7_speech_frozen.json')
    assert frozen['passed'] and installer['passed'] and speech['pipeline_operational']
    disk = {'installed_application_mb':round(sum(s['bytes'] for s in payload['files'].values())/1024**2,1),'setup_and_retained_maintenance_mb':round(package.stat().st_size/1024**2,1),'development_environment_mb':round(sum(p.stat().st_size for p in (root/'.venv-qt-compat').rglob('*') if p.is_file())/1024**2,1),'model_weights_bundled':False}
    functional = {}
    for line in (root/'docs/PRD.md').read_text(encoding='utf-8').splitlines():
        match = re.match(r'\| (FR-\d+) \| (P\d) \| ([^|]+) \|',line)
        if not match:
            continue
        key,priority,name=match.groups()
        status='implemented; software evidence passed; physical acceptance per pending list'
        if priority=='P2':
            status='deferred, outside version-1 scope'
        if key=='FR-05':
            status='implemented; accuracy acceptance FAILED (NFR-01/NFR-02)'
        if key in {'FR-03','FR-04','FR-11','FR-13','FR-19','FR-20','FR-23','FR-26'}:
            status='implemented; software/synthetic evidence only; hardware/network acceptance pending'
        functional[key]={'priority':priority,'name':name.strip(),'status':status}
    nonfunctional={
        'NFR-01':{'status':'FAILED','evidence':'phase3_gate.json','correct':162,'total':200,'target_percent':95},
        'NFR-02':{'status':'FAILED','evidence':'phase3_gate.json','correct':40,'total':50,'target_percent':95},
        'NFR-03':{'status':'PENDING','evidence':'phase7_speech_frozen.json','note':'10 synthetic public cases, 9 exact; NOT the owner 100-utterance trial'},
        'NFR-04':{'status':'PENDING','note':'CPU disclosed; required GPU profile unverified'},
        'NFR-05':{'status':'PASS in tested software UI load','evidence':'phase7_standalone_ui.json','p95_ms':frozen['input_to_render']},
        'NFR-06':{'status':'PARTIAL','note':'Generation/checkpoint suppression, bounded worker cancellation and stale-result tests pass; full timed hardware pipeline remains pending'},
        'NFR-07':{'status':'PENDING','note':'Short software peak 1096.8 MB excludes incremental Ollama and VRAM; not aggregate memory acceptance'},
        'NFR-08':{'status':'PENDING','note':'Owner wake CPU/mains/battery measurements not performed'},
        'NFR-09':{'status':'measured preview disk budget','evidence':disk,'setup_free_space_required_gb':12},
        'NFR-10':{'status':'PENDING','note':'Wake calibration locked; 50 attempts and 2 household hours not performed'},
        'NFR-11':{'status':'PENDING','evidence':'phase7_software_trial.json','note':'125-second software trial passed; NOT a two-hour mixed-use session'},
        'NFR-12':{'status':'PARTIAL','evidence':'phase7_installed_scale2.json','note':'Qt scale 2 and software focus checks pass; Narrator/real Windows 200%/multi-monitor pending'},
        'NFR-13':{'status':'PARTIAL','note':'Strict loopback/runtime/redirect tests pass; actual network-disabled task trial and ten-minute traffic capture pending'},
        'NFR-14':{'status':'NOT DEMONSTRATED for cold launch','evidence':['phase7_release_validation_initial.json','phase7_release_validation.json'],'note':'Initial indirect upper bound includes exit overhead: first install 6.83s, later ~1.2s; direct cold readiness measurement pending'},
    }
    faults={
        'missing_runtime_model':['tests/unit/test_brain.py','tests/contracts/test_loopback.py','tests/unit/test_setup_assets.py'],
        'device_unplug_privacy_output_failure':['tests/unit/test_voice_capture.py','tests/contracts/test_voice.py','INJECTED only; physical tests pending'],
        'corrupt_settings_permissions':['tests/unit/test_settings.py','tests/contracts/test_worker.py'],
        'worker_crash_hang_and_ui_parent_death':['tests/contracts/test_worker.py','tests/contracts/test_parent_lifetime.py','tests/contracts/test_speech_worker.py'],
        'disk_full_and_corrupt_package':['tests/unit/test_installer.py','tests/unit/test_setup_assets.py'],
        'stop_stale_results_confirmation_routines':['tests/contracts/test_confirmations.py','tests/contracts/test_voice.py','tests/unit/test_phase5.py','tests/unit/test_phase6.py'],
        'second_instance':['phase7_standalone_ui.json','phase7_installed_cold.json'],
    }
    gate={'version':'0.7.0','phase':7,'engineering_implementation':'complete','acceptance':'NOT PASSED','complete_v1_declared':False,'owner_instruction':'Build now; leave hands-on checks pending','unique_software_test_cases':len(unique),'software_failures':0,'source_motion_and_reduced_motion':True,'standalone_and_installed_ui':True,'isolated_install_uninstall':True,'registry_writes_during_validation':False,'actual_clean_windows_account_tested':False,'defender_scope':'Realtime protection enabled while build/install/launch passed; no targeted scan or reputation test claimed','disk':disk,'release':{'installer':'dist/Autumn-0.7.0-preview/AutumnSetup.exe','sha256':digest,'bytes':package.stat().st_size,'signed':False,'models_bundled':False,'license_files':98,'public_redistribution_review_complete':False},'evidence_reports':['phase7_tests.xml','phase7_setup_regressions.xml','phase7_standalone_ui.json','phase7_motion_source.json','phase7_scale2_source.json','phase7_design_preview.json','phase7_reduced_motion.json','phase7_setup_ui.json','phase7_software_trial.json','phase7_speech_frozen.json','phase7_release_validation.json','phase7_defender_status.json'],'fault_matrix':faults,'requirements':{'functional':functional,'nonfunctional':nonfunctional},'pending':['owner speech/microphone/speakers/device loss','dictation foreground/delivery and non-stealing confirmation','wake intentional/household/idle CPU/battery trials','Narrator/real Windows scaling/multi-monitor','physical lock/sleep/Modern Standby/resume','clean Windows account and real uninstall registration/maintenance-copy validation','network-disabled execution and ten-minute network trace','two-hour mixed-use stability','GPU aggregate RAM/VRAM and latency','direct cold readiness timing','public redistribution/license review'],'questions':[]}
    gate['evidence_reports'].append('phase7_release_validation_initial.json')
    (reports/'phase7_gate.json').write_text(json.dumps(gate,indent=2),encoding='utf-8')
    (release/'SHA256SUMS.txt').write_text(digest+'  AutumnSetup.exe\n',encoding='ascii')
    print(json.dumps({'unique_tests':len(unique),'installer_mb':gate['disk']['setup_and_retained_maintenance_mb'],'sha256':digest,'acceptance':gate['acceptance']}))


if __name__=='__main__':
    main()
