"""User-authored routines and dictation previews; sensitive text stays volatile."""

import time
from uuid import uuid4

from PySide6.QtCore import Property, QObject, Signal, Slot

from autumn.actions.router import route
from autumn.actions.routines import Routine
from autumn.actions.schemas import Plan, RunRoutine, TypeText
from autumn.controller.contracts import TaskState


class Advanced(QObject):
    changed = Signal()
    showApproval = Signal(str, str)
    hideApproval = Signal()

    def __init__(self, host):
        super().__init__(host)
        self.host = host
        self.targets = []
        self.target_id = ""
        self.token = None
        self.draft = []
        self.editing = ""
        self.arm_dictation = False
        self.status = "Choose a supported Windows Edit/RichEdit control. Browsers and custom editors are not supported."
        host.settingsChanged.connect(self.changed)

    @Property(str, notify=changed)
    def statusText(self):
        return self.status

    @Property("QVariantList", notify=changed)
    def targetRows(self):
        return self.targets

    @Property(bool, notify=changed)
    def pending(self):
        return self.token is not None

    @Property(bool, notify=changed)
    def dictationArmed(self):
        return self.arm_dictation

    @Property("QVariantList", notify=changed)
    def routineRows(self):
        return [
            {"id": r.id, "name": r.name, "steps": len(r.steps)} for r in self.host.settings.routines
        ]

    @Property("QVariantList", notify=changed)
    def draftRows(self):
        return [{"index": i, "label": self.describe(a)} for i, a in enumerate(self.draft)]

    def describe(self, action):
        args = action.arguments
        registries = {
            "app.open": (self.host.settings.apps, "app_id"),
            "folder.open": (self.host.settings.folders, "folder_id"),
            "website.open": (self.host.settings.sites, "site_id"),
        }
        if action.skill in registries:
            rows, key = registries[action.skill]
            name = next((r.name for r in rows if r.id == getattr(args, key)), "Unavailable target")
            return "Open " + name
        if action.skill == "audio.set_volume":
            return f"Volume {args.percent}%"
        if action.skill == "audio.set_mute":
            return "Mute" if args.muted else "Unmute"
        if action.skill == "media.control":
            return args.command.replace("_", " ").title()
        return {
            "help.capabilities": "Show capabilities",
            "screen.capture": "Take screenshot",
            "files.search": "Search filenames",
        }.get(action.skill, "Unavailable action")

    @Slot()
    def refreshTargets(self):
        if self.host.canConfigure:
            self.host.schedule("dictation_targets")

    @Slot(str)
    def chooseTarget(self, token):
        if any(row["id"] == token for row in self.targets):
            self.target_id = token

    @Slot(bool)
    def armDictation(self, armed):
        self.arm_dictation = bool(armed)
        self.changed.emit()

    @Slot(str)
    def dictate(self, text):
        self.submit_dictation(text, "button")

    def submit_dictation(self, text, origin):
        try:
            if not self.target_id or origin == "wake_voice":
                raise ValueError()
            action = TypeText(arguments={"text": text, "target_id": self.target_id})
            self.submit(Plan(steps=(action,)), origin)
            self.status = "Return to the chosen target, focus its edit field, then confirm with Ctrl+Alt+Y. Cancel: Ctrl+Alt+N."
        except ValueError:
            self.status = "Choose a supported target and a single line (1–1000 characters). Passwords, administrator windows and control characters are refused."
        self.changed.emit()

    def submit(self, plan, origin="button"):
        if not self.host.canSend or self.host.session.active is not None or self.host.voice.isBusy:
            self.status = "Wait for the current work or use Stop."
            return
        counter = getattr(self.host.supervisor, "voice_generation", None)
        request = self.host.session.enqueue(
            origin=origin, voice_generation=counter.value if counter is not None else 0
        )
        self.host.pending_inputs[str(request.request_id)] = plan
        self.host.started_requests[str(request.request_id)] = time.monotonic()
        self.host.dispatch_request(request)
        self.host.changed.emit()

    def route_voice(self, request, text):
        self.arm_dictation = False
        try:
            if request.origin != "ptt_voice":
                raise ValueError()
            action = TypeText(arguments={"text": text, "target_id": self.target_id})
            self.host.session.set_task(TaskState.ROUTING)
            self.host.pending_inputs[str(request.request_id)] = Plan(steps=(action,))
            self.host.dispatch_request(request)
        except ValueError:
            self.host.voice.cancel_voice_requests()
            self.status = "Voice dictation needs a chosen target and a supported single line. Wake dictation is unavailable."
        self.changed.emit()

    def event(self, event):
        kind = event["kind"]
        if kind == "dictation_targets":
            self.targets = event["rows"]
            self.target_id = ""
            self.status = "Choose a target, preview the text, then return to that app to confirm. Targets expire after two minutes."
        elif kind == "confirmation":
            active = self.host.session.active
            if (
                active is None
                or str(active.request_id) != event["request_id"]
                or active.generation != event["generation"]
            ):
                return
            self.token = event["token"]
            self.showApproval.emit(event["destination"], event["text"])
        elif kind == "confirmation_closed" and event["token"] == self.token:
            self.dismiss()
        self.changed.emit()

    @Slot()
    def confirm(self):
        self.answer(True)

    @Slot()
    def cancelApproval(self):
        self.answer(False)

    def answer(self, approved):
        if self.token:
            self.host.schedule("confirm", confirmation_id=self.token, approved=approved)
            self.dismiss()

    def dismiss(self):
        self.token = None
        self.hideApproval.emit()
        self.changed.emit()

    @Slot()
    def newRoutine(self):
        self.draft = []
        self.editing = ""
        self.changed.emit()

    @Slot(str)
    def editRoutine(self, identifier):
        routine = next((r for r in self.host.settings.routines if r.id == identifier), None)
        if routine:
            self.draft = list(routine.steps)
            self.editing = identifier
            self.changed.emit()

    @Slot(str)
    def addStep(self, command):
        try:
            plan = route(command, self.host.settings).plan
            if plan is None or len(plan.steps) != 1 or len(self.draft) >= 5:
                raise ValueError()
            Routine(id="preview", name="Preview", steps=tuple([*self.draft, *plan.steps]))
            self.draft.extend(plan.steps)
            self.status = "Step added. Review the complete preview before saving."
        except ValueError:
            self.status = "Use one supported reviewed action. Maximum five steps; no dictation, nested routines, search matches or unregistered URLs."
        self.changed.emit()

    @Slot(int, int)
    def moveStep(self, index, offset):
        other = index + offset
        if 0 <= index < len(self.draft) and 0 <= other < len(self.draft):
            self.draft[index], self.draft[other] = self.draft[other], self.draft[index]
            self.changed.emit()

    @Slot(int)
    def removeStep(self, index):
        if 0 <= index < len(self.draft):
            self.draft.pop(index)
            self.changed.emit()

    @Slot(str)
    def saveRoutine(self, name):
        if not self.host.canConfigure:
            return
        try:
            routine = Routine(id=self.editing or uuid4().hex, name=name, steps=tuple(self.draft))
            rows = [
                r.model_dump(mode="json") for r in self.host.settings.routines if r.id != routine.id
            ]
            self.host.update_settings(routines=[*rows, routine.model_dump(mode="json")])
            self.status = "Routine submitted for saving."
        except ValueError:
            self.status = "Give the routine a unique name and one to five valid steps."
        self.changed.emit()

    @Slot(str)
    def deleteRoutine(self, identifier):
        if self.host.canConfigure:
            self.host.update_settings(
                routines=[
                    r.model_dump(mode="json")
                    for r in self.host.settings.routines
                    if r.id != identifier
                ]
            )

    @Slot(str)
    def runRoutine(self, identifier):
        self.submit(Plan(steps=(RunRoutine(arguments={"routine_id": identifier}),)))
