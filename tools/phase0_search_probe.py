"""Bounded filename-scan experiment over disposable project fixtures only."""
import json
import os
from pathlib import Path
import time

ROOT=Path(__file__).resolve().parents[1]
fixture=ROOT/'.cache/search fixtures é'
fixture.mkdir(parents=True,exist_ok=True)
for group in range(10):
    directory=fixture/f'folder {group}'; directory.mkdir(exist_ok=True)
    for index in range(100):
        name=f'autumn-budget-{index}.xlsx' if index%25==0 else f'fixture-{index}.txt'
        path=directory/name
        if not path.exists(): path.write_text('Disposable Autumn filename-search fixture. Not a real spreadsheet.',encoding='utf-8')
started=time.perf_counter(); matches=[]; visited=0; limited=False
for directory,children,files in os.walk(fixture,followlinks=False):
    children[:]=[c for c in children if not (Path(directory)/c).is_symlink()]
    for name in files:
        visited+=1
        if time.perf_counter()-started>10 or visited>200000:
            limited=True; break
        if 'budget' in name.lower() and name.lower().endswith('.xlsx'): matches.append(Path(directory)/name)
    if limited: break
assert len(matches)==40 and all(p.resolve().is_relative_to(fixture.resolve()) for p in matches)
report={'backend':'bounded scan','fixture_files':1000,'visited':visited,'matches':len(matches),
    'elapsed_seconds':round(time.perf_counter()-started,6),'limited':limited,'personal_files_tested':False,
    'indexed_root_coverage':'not verified; Windows Search service must be checked independently'}
(ROOT/'docs/reports/search_probe.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
