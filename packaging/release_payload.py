"""Create a self-contained personal-preview payload, notices and source snapshot."""
import importlib.metadata as metadata
import json
import shutil
import sys
import zipfile
from pathlib import Path
from uuid import uuid4

from autumn import __version__
from autumn.setup.assets import URLS
from autumn.setup.install import PRODUCT, sha256
from autumn.speech.assets import ARTIFACTS


def build(root):
    output = root / 'dist' / f'Autumn-{__version__}-preview'
    output.mkdir(parents=True, exist_ok=True)
    stage = root / '.cache' / ('release-' + uuid4().hex)
    shutil.copytree(root / 'dist/Autumn preview é/Autumn', stage)
    (stage / '_internal/autumn/speech/external_assets.json').write_text('{}',encoding='utf-8')
    for name in ('README.md','THIRD_PARTY_NOTICES.md','requirements-phase7.lock'):
        shutil.copy2(root / name, stage / name)
    docs = stage / 'guide'
    docs.mkdir()
    for name in ('USER_GUIDE.md','TROUBLESHOOTING.md','KNOWN_ISSUES.md'):
        shutil.copy2(root / 'docs' / name, docs / name)
    notices = stage / 'licenses'
    notices.mkdir()
    inventory = []
    for dist in sorted(metadata.distributions(),key=lambda d:d.metadata['Name'].casefold()):
        name = dist.metadata['Name']
        entry = {'name':name,'version':dist.version,'license':dist.metadata.get('License-Expression') or dist.metadata.get('License',''),'urls':dist.metadata.get_all('Project-URL') or [],'notices':[]}
        for file in dist.files or []:
            parts = Path(str(file)).parts
            if not any(p.endswith('.dist-info') for p in parts):
                continue
            if not any(any(word in p.casefold() for word in ('license','notice','copying','copyright')) for p in parts):
                continue
            source = Path(dist.locate_file(file))
            if not source.is_file():
                continue
            relative = Path(name) / Path(*parts[1:])
            target = notices / relative
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,target)
            entry['notices'].append(relative.as_posix())
        inventory.append(entry)
    python_license = Path(sys.base_prefix) / 'LICENSE.txt'
    if python_license.is_file():
        shutil.copy2(python_license,notices / 'Python-LICENSE.txt')
    provenance = {'version':__version__,'python':sys.version.split()[0],'dependencies':inventory,'model_weights_bundled':False,'models':{key:{'file':v[0],'bytes':v[1],'sha256':v[2],'url':URLS[key]} for key,v in ARTIFACTS.items()},'brain':{'tag':'qwen3:1.7b','digest':'8f68893c685c3ddff2aa3fffce2aa60a30bb2da65ca488b61fff134a4d1730e7'},'public_distribution_review_complete':False}
    (stage / 'provenance.json').write_text(json.dumps(provenance,indent=2),encoding='utf-8')
    with zipfile.ZipFile(stage / 'autumn-source.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
        for folder in ('src','packaging','tests'):
            for path in sorted((root / folder).rglob('*')):
                if path.is_file() and '__pycache__' not in path.parts and path.suffix in {'.py','.qml','.ps1'}:
                    archive.write(path,path.relative_to(root).as_posix())
        for name in ('pyproject.toml','README.md','THIRD_PARTY_NOTICES.md','requirements-phase7.lock','requirements-phase7.in'):
            archive.write(root / name,name)
        for name in ('USER_GUIDE.md','TROUBLESHOOTING.md','KNOWN_ISSUES.md'):
            archive.write(root / 'docs' / name,'docs/' + name)
    files = {p.relative_to(stage).as_posix():{'bytes':p.stat().st_size,'sha256':sha256(p)} for p in sorted(stage.rglob('*')) if p.is_file()}
    manifest = {'product':PRODUCT,'version':__version__,'files':files}
    manifest_path = output / 'release-manifest.json'
    manifest_path.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    payload = output / 'payload.zip'
    with zipfile.ZipFile(payload,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for name in files:
            archive.write(stage / name,name)
        archive.write(manifest_path,'release-manifest.json')
    (output / 'installer-metadata.json').write_text(json.dumps({'version':__version__,'payload_sha256':sha256(payload)},indent=2),encoding='utf-8')
    shutil.copy2(stage / 'provenance.json',output / 'provenance.json')
    print(json.dumps({'payload_mb':round(payload.stat().st_size/1024**2,1),'files':len(files),'dependency_distributions':len(inventory),'license_files':sum(len(e['notices']) for e in inventory),'stage':str(stage)}))


if __name__ == '__main__':
    build(Path(__file__).resolve().parents[1])
