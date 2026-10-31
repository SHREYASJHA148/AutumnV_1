"""Routing-only evaluation. Never imports an action executor or saves input/model text."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import time
from pathlib import Path

from autumn.actions.catalog import AppEntry, FolderEntry, SiteEntry
from autumn.actions.router import route
from autumn.actions.schemas import Plan
from autumn.brain.contracts import Answer, BrainError, Clarification
from autumn.brain.planner import MODEL, Planner
from autumn.controller.contracts import Request
from autumn.storage.settings import MODEL_DIGEST, Settings

ROOT = Path(__file__).resolve().parents[1]


def development():
    catalog = {"apps":[{"id":"editor","name":"Fixture Editor"},{"id":"calculator","name":"Calculator"}],
        "folders":[{"id":"documents","name":"Documents"},{"id":"downloads","name":"Downloads"}],
        "sites":[{"id":"reference","name":"Reference","url":"https://example.com"}]}
    def action(skill,arguments):
        return {"kind":"action_plan","steps":[{"skill":skill,"arguments":arguments}]}
    samples = [
        ("open Fixture Editor",action("app.open",{"app_id":"editor"})),
        ("I need the Calculator app.",action("app.open",{"app_id":"calculator"})),
        ("Please bring up Fixture Editor.",action("app.open",{"app_id":"editor"})),
        ("Could you show the Downloads folder?",action("folder.open",{"folder_id":"downloads"})),
        ("open Documents",action("folder.open",{"folder_id":"documents"})),
        ("Take me to Reference.",action("website.open",{"site_id":"reference"})),
        ("open https://example.com",action("website.open",{"url":"https://example.com"})),
        ("set volume to 35 percent",action("audio.set_volume",{"percent":35})),
        ("Make the sound level sixty percent.",action("audio.set_volume",{"percent":60})),
        ("Turn the volume down to twenty percent.",action("audio.set_volume",{"percent":20})),
        ("mute",action("audio.set_mute",{"muted":True})),
        ("Could you silence the speakers?",action("audio.set_mute",{"muted":True})),
        ("I want sound back on.",action("audio.set_mute",{"muted":False})),
        ("unmute speakers",action("audio.set_mute",{"muted":False})),
        ("next track",action("media.control",{"command":"next"})),
        ("Skip this track.",action("media.control",{"command":"next"})),
        ("Return to the previous song.",action("media.control",{"command":"previous"})),
        ("play pause",action("media.control",{"command":"play_pause"})),
        ("take a screenshot",action("screen.capture",{"monitor":"primary"})),
        ("Please capture my primary screen.",action("screen.capture",{"monitor":"primary"})),
        ("Capture all the monitors in one screenshot.",action("screen.capture",{"monitor":"all"})),
        ("find pdf budget in documents",action("files.search",{"query":"budget","type_hint":"pdf","root_ids":["documents"]})),
        ("Search Downloads for spreadsheets named expenses.",action("files.search",{"query":"expenses","type_hint":"spreadsheet","root_ids":["downloads"]})),
        ("what can you do?",action("help.capabilities",{})),
        ("Tell me which actions you can perform.",action("help.capabilities",{})),
    ]
    negatives = ["don't open Fixture Editor","open unknown-tool","delete my files","run cmd.exe /c anything",
        "open file:///C:/private.exe","set volume to 120 percent","show me that thing",
        "send an email","open Fixture Editor and delete files","play a named playlist",
        "open it","Tell me tomorrow's weather"]
    cases = [{"id":f"dev-{i:02d}","input":text,"expected":expected} for i,(text,expected) in enumerate(samples,1)]
    cases += [{"id":f"dev-neg-{i:02d}","input":text,"expected":{"allowed_kinds":["clarification","unsupported"]}} for i,text in enumerate(negatives,1)]
    return {"catalog":catalog,"cases":cases}


def settings_for(catalog):
    return Settings(apps=tuple(AppEntry(id=a["id"],name=a["name"],aliases=tuple(a.get("aliases",())),
        kind="package",target="EvaluationOnly_pkg!App",enabled=True,reviewed=True) for a in catalog.get("apps",())),
        folders=tuple(FolderEntry(id=f["id"],name=f["name"],path=str(ROOT/".cache/evaluation-no-dispatch")) for f in catalog.get("folders",())),
        sites=tuple(SiteEntry(**s) for s in catalog.get("sites",())))


def prediction(text,settings,planner):
    deterministic = route(text,settings)
    if deterministic.plan is not None:
        planner.clear_context()
        return deterministic.plan,"deterministic"
    if not deterministic.allow_model:
        return Clarification(message=deterministic.message[:180],choices=deterministic.choices),"deterministic"
    reply=planner.plan(text,settings,Request(generation=0),lambda:True)
    return reply,"guard" if planner.last_metrics.get("path")=="intent_guard" else "model"


def correct(reply,expected):
    if "allowed_kinds" in expected:
        return reply.kind in expected["allowed_kinds"]
    expected_plan=Plan.model_validate(expected)
    if isinstance(reply,Answer):
        return len(expected_plan.steps)==1 and expected_plan.steps[0].skill=="help.capabilities"
    return isinstance(reply,Plan) and reply==expected_plan


def summary(rows):
    result={"total":len(rows),"correct":sum(r["correct"] for r in rows)}
    result["accuracy"]=round(result["correct"]/len(rows),4) if rows else None
    durations=sorted(r["elapsed_seconds"] for r in rows)
    if durations:
        result.update(p50_seconds=round(statistics.median(durations),4),p95_seconds=round(durations[math.ceil(len(durations)*.95)-1],4))
        n=len(rows)
        p=result["correct"]/n
        denom=1+1.96**2/n
        center=(p+1.96**2/(2*n))/denom
        radius=1.96*math.sqrt(p*(1-p)/n+1.96**2/(4*n*n))/denom
        result["wilson_95"]= [round(center-radius,4),round(center+radius,4)]
        supported=[r for r in rows if r["supported"]]
        if supported:
            result["skill_accuracy"]=round(sum(r.get("skill_correct",False) for r in supported)/len(supported),4)
            result["skill_and_argument_accuracy"]=round(sum(r["correct"] for r in supported)/len(supported),4)
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--heldout",action="store_true")
    parser.add_argument("--limit",type=int)
    parser.add_argument("--report",default="phase3_development.json")
    args=parser.parse_args()
    if Path(args.report).name!=args.report or not args.report.endswith(".json"):
        raise SystemExit("Report must be a JSON filename")
    if args.heldout:
        if args.limit:
            raise SystemExit("Held-out trials must use the complete locked release dataset")
        lock_path=ROOT/"docs/contracts/phase3-rc-lock.json"
        lock=json.loads(lock_path.read_text())
        from autumn.brain.planner import SYSTEM
        if lock["prompt_sha256"]!=hashlib.sha256(SYSTEM.encode()).hexdigest():
            raise SystemExit("Release prompt changed; held-out trial blocked")
        marker=ROOT/".cache/evaluation-lockbox"/("evaluated-"+lock["rc_id"]+".marker")
        with marker.open("x") as f:
            f.write("Routing-only release trial begun. Never rerun this candidate or tune from this dataset.\n")
        datasets=[]
        for shard in lock["shards"]:
            data=(ROOT/shard["file"]).read_bytes()
            if hashlib.sha256(data).hexdigest()!=shard["sha256"]:
                raise SystemExit("Held-out shard hash mismatch")
            datasets.append(json.loads(data))
    else:
        datasets=[development()]
    rows=[]
    planner=Planner()
    model_seen=False
    for dataset in datasets:
        settings=settings_for(dataset["catalog"])
        for case in dataset["cases"]:
            if args.limit and len(rows)>=args.limit:
                break
            # Each evaluation case has no prior conversational context.
            planner.clear_context()
            started=time.perf_counter()
            deterministic=route(case["input"],settings)
            path="deterministic" if deterministic.plan is not None or not deterministic.allow_model else "model"
            row={"id":case["id"],"supported":"allowed_kinds" not in case["expected"],"path":path}
            try:
                reply,path=prediction(case["input"],settings,planner)
                row["path"]=path
                row.update(correct=correct(reply,case["expected"]),kind=reply.kind,
                    skill=reply.steps[0].skill if isinstance(reply,Plan) else None)
                if row["supported"]:
                    expected_plan=Plan.model_validate(case["expected"])
                    row["skill_correct"]=(isinstance(reply,Plan) and [s.skill for s in reply.steps]==[s.skill for s in expected_plan.steps]) or (isinstance(reply,Answer) and len(expected_plan.steps)==1 and expected_plan.steps[0].skill=="help.capabilities")
                if path=="model":
                    row["thinking_disabled"]=planner.last_metrics.get("thinking_disabled",False)
                    row["repairs"]=planner.last_metrics.get("repairs",0)
            except BrainError as error:
                row.update(correct=False,error=error.code)
            row["elapsed_seconds"]=round(time.perf_counter()-started,4)
            row["cold_model_case"]=path=="model" and not model_seen
            model_seen=model_seen or path=="model"
            rows.append(row)
            print(f"Case {len(rows)}: {path}, {'correct' if row['correct'] else 'incorrect'}, {row['elapsed_seconds']}s",flush=True)
            if planner.failures>=3:
                break
        if planner.failures>=3:
            break
    report={"dataset":"held-out release trial" if args.heldout else "development only", "model":MODEL,"digest":MODEL_DIGEST,
        "profile":"cpu; GPU gate unverified", "actions_dispatched":0,"input_text_logged":False,
        "settings":{"num_ctx":4096,"num_predict":256,"think":False,"temperature":0,"num_gpu":0,"num_thread":4},
        "combined":summary(rows),"supported":summary([r for r in rows if r["supported"]]),
        "ambiguous_unsupported":summary([r for r in rows if not r["supported"]]),
        "deterministic":summary([r for r in rows if r["path"]!="model"]),
        "intent_guard":summary([r for r in rows if r["path"]=="guard"]),
        "deterministic_share":round(sum(r["path"]!="model" for r in rows)/len(rows),4) if rows else None,
        "model_warm":summary([r for r in rows if r["path"]=="model" and not r["cold_model_case"]]),
        "rows":rows,"three_failure_stop":planner.failures>=3}
    (ROOT/"docs/reports"/args.report).write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k in {"combined","supported","ambiguous_unsupported","model_warm"}}))


if __name__=="__main__":
    main()
