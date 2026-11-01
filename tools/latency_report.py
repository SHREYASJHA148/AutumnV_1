"""Collect measured component timings without claiming microphone end-to-end latency."""
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
    suites=[ET.parse(reports/name).getroot() for name in ('latency_tests.xml','latency_regressions.xml')]
    assert not any(list(s.iter('failure')) or list(s.iter('error')) for s in suites)
    cases={(c.get('classname'),c.get('name')) for suite in suites for c in suite.iter('testcase')}
    sweep=read('latency_thread_sweep.json')
    endpoint=read('latency_endpoint.json')
    warmup=read('latency_warmup.json')
    speech=read('latency_frozen_speech.json')
    integrity=read('latency_freeze_integrity.json')
    installed=read('latency_release_validation.json')
    trim=read('latency_trim_quality.json')
    assert all(r.get('passed') for r in (warmup,integrity,installed,trim)) and speech['pipeline_operational']
    before=sweep['medians']['4']
    after=sweep['medians']['8']
    release=root/'dist/Autumn-0.7.2-preview'
    checksums={name:digest(release/name) for name in ('AutumnSetup.exe','payload.zip','release-manifest.json')}
    (release/'SHA256SUMS.txt').write_text(''.join(sha+'  '+name+'\n' for name,sha in checksums.items()),encoding='ascii')
    result={'date':'2026-11-01','version':'0.7.2','implementation':'complete','unique_passing_tests':len(cases),'full_suite':450,'additional_unique_regressions':len(cases)-450,'scope':'Controlled synthetic component measurements and software verification; NO microphone/speaker end-to-end latency claim','controlled_recognition':{'same_pcm_model_and_confidence_gates':True,'before_threads':4,'after_threads':8,'median_before_seconds':before,'median_after_seconds':after,'reduction_percent':round((1-after/before)*100,1),'all_six_synthetic_decodes_exact':all(c['exact'] for c in sweep['cases'])},'endpoint':endpoint,'priming':warmup,'spoken_handoff_duration':read('latency_reply_duration.json'),'app_open_change':'If Windows returns no launch PID, immediately return the same unverified handoff; remove the futile two-second PID-match poll. Known-PID verification remains tested.','fresh_process_timings_note':'latency_before/after.json are observations with cache/load differences; use the interleaved sweep for the controlled percentage.','source_ui_under_speech_load':read('latency_source_ui.json')['input_to_render'],'frozen_synthetic_speech':{'processed':len(speech['synthetic_cases']),'exact':speech['synthetic_exact_matches'],'pipeline_operational':speech['pipeline_operational'],'warm_recognition_p50_seconds':speech['recognition_warm_p50_seconds'],'microphone_or_speakers_opened':False},'installed_validation':installed,'freeze_integrity':integrity,'new_dependencies':False,'brain_speech_voice_models_changed':False,'confidence_and_policy_gates_changed':False,'gpu_or_windows_power_settings_changed':False,'capture_limit_seconds':20,'response_timing_ui':['Quick replies 450 ms','Natural pauses 800 ms','Longer pauses 1200 ms'],'installer_bytes':(release/'AutumnSetup.exe').stat().st_size,'checksums':checksums,'existing_launcher':'C:\\adu\\Autumn.lnk','existing_preferences_preserved':True,'overall_release_acceptance':'NOT PASSED; existing accuracy/performance/hardware gaps remain','pending':'Owner microphone/speaker/room and false-activation trials, GPU, aggregate resources, clean-account/registry, offline trace, Narrator/power and two-hour stability remain unverified.','questions':[]}
    (reports/'latency_optimization.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'tests':len(cases),'controlled_recognition_reduction_percent':result['controlled_recognition']['reduction_percent'],'endpoint_saved_seconds':endpoint['saved_seconds'],'installer_mb':round(result['installer_bytes']/1024**2,1),'installer_sha256':checksums['AutumnSetup.exe']}))


if __name__=='__main__':
    main()
