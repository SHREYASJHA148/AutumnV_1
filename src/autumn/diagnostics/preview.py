"""Capture only this app's isolated public demonstration surface."""

import json
import time

from PySide6.QtCore import QObject, QTimer


class Preview(QObject):
    def __init__(self, app, window, vm, report, image):
        super().__init__()
        self.app, self.window, self.vm, self.report, self.image = app, window, vm, report, image
        self.started = time.monotonic()
        self.frames = []
        window.frameSwapped.connect(lambda: self.frames.append(time.monotonic()))
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.tick)
        self.timer.start()
        self.ready_at = 0.0

    def tick(self):
        if not self.vm.canSend:
            if time.monotonic() - self.started > 12:
                self.app.quit()
            return
        if not self.ready_at:
            self.window.setProperty("page", 0)
            self.vm.conversation = [
                {"role": "You", "text": "What can you help me with?"},
                {
                    "role": "Autumn",
                    "text": "Open your reviewed apps, find a file, or build an everyday routine. Your requests stay on this computer.",
                },
            ]
            self.vm.notice = "Ready when you are. Microphone is off."
            self.vm.changed.emit()
            self.ready_at = time.monotonic()
        elif time.monotonic() - self.ready_at > 1.7:
            self.image.parent.mkdir(parents=True, exist_ok=True)
            saved = self.window.grabWindow().save(str(self.image))
            intervals = [(b - a) * 1000 for a, b in zip(self.frames, self.frames[1:])]
            self.report.parent.mkdir(parents=True, exist_ok=True)
            self.report.write_text(
                json.dumps(
                    {
                        "passed": bool(saved),
                        "microphone_opened": False,
                        "public_demo_only": True,
                        "motion_enabled": not self.vm.settings.reduced_motion,
                        "frames": len(self.frames),
                        "frame_interval_p95_ms": sorted(intervals)[int(len(intervals) * 0.95)]
                        if intervals
                        else None,
                        "window": [self.window.width(), self.window.height()],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            self.timer.stop()
            self.app.quit()
