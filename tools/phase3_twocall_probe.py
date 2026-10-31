"""Development-only comparison: select a skill, then fill its frozen arguments; no dispatch."""
import asyncio
import copy
import json
import statistics
import time
from pathlib import Path

import autumn.brain.planner as module
from autumn.actions.schemas import Plan
from autumn.brain.contracts import BrainError
from autumn.brain.planner import MODEL, Planner
from autumn.brain.schema import build_schema, enum, obj
from autumn.controller.contracts import Request
from phase3_evaluate import development, settings_for


def main():
    settings=settings_for(development()["catalog"])
    cases=[("Please silence my speakers.","audio.set_mute"),
           ("I want sound back on.","audio.set_mute"),
           ("Make the sound level sixty percent.","audio.set_volume"),
           ("Please capture my primary screen.","screen.capture")]
    rows=[]
    original=module.build_schema
    for index,(text,expected) in enumerate(cases,1):
        planner=Planner()
        live=original(settings,text)
        deadline=time.monotonic()+15
        row={"case":index,"expected_skill":expected}
        started=time.monotonic()
        try:
            asyncio.run(planner.verify(deadline,lambda:True))
            body={"model":MODEL,"think":False,"stream":True,"keep_alive":"5m",
                "format":obj({"skill":enum(sorted(live.ids["skills"]))}),
                "options":{"num_gpu":0,"num_ctx":4096,"num_predict":64,"num_thread":4,"temperature":0,"seed":0},
                "messages":[{"role":"system","content":"Select the single skill requested. Output JSON only. "+str({s:s for s in sorted(live.ids["skills"])})},
                            {"role":"user","content":text}]}
            packets=asyncio.run(planner.transport.request("/api/chat",body,deadline,lambda:True,streaming=True))
            selected=json.loads("".join(p.get("message",{}).get("content","") for p in packets))["skill"]
            if selected not in live.ids["skills"]:
                raise BrainError("INVALID_PLAN")
            narrowed=copy.deepcopy(live)
            items=narrowed.schema["oneOf"][0]["properties"]["steps"]["items"]["oneOf"]
            narrowed.schema["oneOf"][0]["properties"]["steps"]["items"]["oneOf"]=[item for item in items if item["properties"]["skill"]["const"]==selected]
            narrowed.ids["skills"]={selected}
            module.build_schema=lambda *args,**kwargs:narrowed
            reply=planner.plan(text,settings,Request(generation=0),lambda:time.monotonic()<deadline)
            row.update(selected_skill=selected,correct=isinstance(reply,Plan) and reply.steps[0].skill==expected)
        except (BrainError,ValueError,KeyError) as error:
            row.update(correct=False,error=error.code if isinstance(error,BrainError) else "INVALID_SELECTION")
        finally:
            module.build_schema=original
        row["elapsed_seconds"]=round(time.monotonic()-started,4)
        rows.append(row)
        print(f"Two-call development case {index}: {'correct' if row['correct'] else 'incorrect'}, {row['elapsed_seconds']}s",flush=True)
    report={"actions_dispatched":0,"dataset":"four development requests, not held-out","profile":"cpu","correct":sum(r["correct"] for r in rows),"total":len(rows),
            "p50_seconds":statistics.median(r["elapsed_seconds"] for r in rows),"rows":rows,
            "selection_rule":"retain one-call unless the two-call approach improves development accuracy without unacceptable latency"}
    (Path(__file__).resolve().parents[1]/"docs/reports/phase3_two_call_development.json").write_text(json.dumps(report,indent=2),encoding="utf-8")


if __name__=="__main__":
    main()
