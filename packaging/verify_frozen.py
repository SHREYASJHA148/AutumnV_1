"""Check bundled Autumn bytecode and UI against the current source candidate."""
import argparse
import json
import types
from pathlib import Path

from PyInstaller.loader.pyimod01_archive import ZlibArchiveReader


def equal(a,b):
    if isinstance(a,types.CodeType) and isinstance(b,types.CodeType):
        fields=('co_code','co_names','co_varnames','co_freevars','co_cellvars','co_flags','co_argcount','co_kwonlyargcount','co_posonlyargcount')
        return all(getattr(a,f)==getattr(b,f) for f in fields) and len(a.co_consts)==len(b.co_consts) and all(equal(x,y) for x,y in zip(a.co_consts,b.co_consts))
    return type(a) is type(b) and a==b


def main():
    root=Path(__file__).resolve().parents[1]
    parser=argparse.ArgumentParser()
    parser.add_argument('--report',type=Path,default=root/'docs/reports/personal_freeze_integrity.json')
    args=parser.parse_args()
    archive=ZlibArchiveReader(str(root/'build/phase1/Autumn/PYZ-00.pyz'))
    mismatches=[]
    checked=0
    for name in archive.toc:
        if name!='autumn' and not name.startswith('autumn.'):
            continue
        path=root/'src'/Path(*name.split('.'))
        source=path.with_suffix('.py') if path.with_suffix('.py').is_file() else path/'__init__.py'
        if not source.is_file():
            continue
        frozen=archive.extract(name)
        original=compile(source.read_bytes(),str(source),'exec',dont_inherit=True,optimize=0)
        checked+=1
        if not equal(original,frozen):
            mismatches.append(name)
    data_mismatches=[]
    for source in (root/'src/autumn/ui').glob('*'):
        if source.suffix not in {'.qml','.ico'}:
            continue
        bundled=root/'dist/Autumn preview é/Autumn/_internal/autumn/ui'/source.name
        if not bundled.is_file() or source.read_bytes()!=bundled.read_bytes():
            data_mismatches.append(source.name)
    report={'passed':checked>0 and not mismatches and not data_mismatches,'modules_checked':checked,'bytecode_mismatches':mismatches,'ui_mismatches':data_mismatches}
    args.report.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
    return 0 if report['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
