"""Apply the owner's requested preferences and create the single workspace icon."""
import json
import shutil
import subprocess
import winreg
from pathlib import Path
from uuid import uuid4

from autumn.actions.registry import DEFAULT_ENABLED
from autumn.setup.shortcut import create_shortcut
from autumn.speech.assets import Assets
from autumn.storage.settings import app_directory, atomic_save, load_settings


def main():
    root=Path(__file__).resolve().parents[1]
    executable=root/'dist/Autumn preview é/Autumn/Autumn.exe'
    if not executable.is_file():
        raise FileNotFoundError('Build Autumn first')
    path=app_directory()/'config/settings.json'
    if path.exists():
        shutil.copy2(path,path.with_name('settings.before-personal-'+uuid4().hex[:8]+'.json'))
    settings,_=load_settings(path)
    assets=Assets()
    for key in ('small.en','voice','voice_config'):
        assets.get(key,str(root/'models'))
    settings=settings.model_copy(update={'start_brain_on_launch':True,'broad_open_access':True,'hands_free_on_launch':True,'model_enabled':True,'model_memory_saver':False,'enabled_skills':DEFAULT_ENABLED,'speech_assets_dir':str(root/'models')})
    atomic_save(path,settings)
    migrated_login=False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Run',0,winreg.KEY_QUERY_VALUE|winreg.KEY_SET_VALUE) as key:
            if winreg.QueryValueEx(key,'AutumnLocal')[0]==subprocess.list2cmdline([str(executable)]):
                winreg.SetValueEx(key,'AutumnLocal',0,winreg.REG_SZ,subprocess.list2cmdline([str(executable),'--login']))
                migrated_login=True
    except FileNotFoundError:
        pass
    destination=root.parent/'Autumn.lnk'
    try:
        create_shortcut(executable,destination,root/'src/autumn/ui/Autumn.ico')
    except ValueError:
        destination=root.parent/'Autumn Local.lnk'
        create_shortcut(executable,destination,root/'src/autumn/ui/Autumn.ico')
    record={'configured':True,'brain_starts_on_open':True,'broad_app_and_local_path_access':True,'hands_free_on_open':True,'activation_prefix':'Autumn','shortcut':str(destination),'real_microphone_opened_by_configuration':False,'login_startup_enabled_by_configuration':False,'owned_legacy_login_entry_migrated_to_mic_off':migrated_login}
    (root/'docs/reports/personal_profile.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps(record))


if __name__=='__main__':
    main()
