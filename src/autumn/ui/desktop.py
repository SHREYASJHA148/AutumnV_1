"""Tray, explicit close choice and opt-in per-user startup; no startup microphone."""

import subprocess
import sys
import winreg

from PySide6.QtCore import Property, QObject, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap, QWindow
from PySide6.QtWidgets import QMenu, QMessageBox, QSystemTrayIcon

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def startup_command():
    if not getattr(sys, "frozen", False):
        raise ValueError("Startup is available in the standalone app only")
    return subprocess.list2cmdline([sys.executable,'--login'])


def set_startup(enabled):
    command = startup_command() if enabled else None
    with winreg.CreateKeyEx(
        winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE
    ) as key:
        if enabled:
            try:
                existing = winreg.QueryValueEx(key, "AutumnLocal")[0]
            except FileNotFoundError:
                existing = None
            if existing is not None and existing not in {command,subprocess.list2cmdline([sys.executable])}:
                raise ValueError("A different startup entry owns this name")
            winreg.SetValueEx(key, "AutumnLocal", 0, winreg.REG_SZ, command)
        else:
            try:
                if winreg.QueryValueEx(key, "AutumnLocal")[0] not in {startup_command(),subprocess.list2cmdline([sys.executable])}:
                    raise ValueError("A different startup entry owns this name")
                winreg.DeleteValue(key, "AutumnLocal")
            except FileNotFoundError:
                pass


def startup_enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            return winreg.QueryValueEx(key, "AutumnLocal")[0] in {startup_command(),subprocess.list2cmdline([sys.executable])}
    except (OSError, ValueError):
        return False


class Desktop(QObject):
    changed = Signal()

    def __init__(self, host, app, window=None):
        super().__init__(host)
        self.host, self.app, self.window = host, app, window
        self.startup = startup_enabled()
        self.status = "Login startup is opt-in. Normal launches use your saved listening preference."
        self.close_dialog = False
        self.pending_quit = False
        self.tray = QSystemTrayIcon(self)
        self.menu = QMenu()
        self.open_action = self.menu.addAction("Open Autumn", self.open)
        self.menu.addAction("Stop all work", host.stop)
        self.menu.addAction("Microphone off", self.microphoneOff)
        self.listen_action = self.menu.addAction('Hands-free listening')
        self.listen_action.setCheckable(True)
        self.listen_action.triggered.connect(host.voice.setHandsFree)
        self.arm_action = self.menu.addAction("Arm calibrated wake", host.wake.arm)
        self.menu.addSeparator()
        self.menu.addAction("Quit Autumn", app.quit)
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(
            lambda reason: self.open() if reason in {QSystemTrayIcon.DoubleClick,QSystemTrayIcon.Trigger} else None
        )
        self.last_state = None
        host.changed.connect(self.refresh)
        host.wake.changed.connect(self.refresh)
        host.voice.changed.connect(self.refresh)
        host.settingsChanged.connect(self.changed)
        host.settingsChanged.connect(self.settings_saved)
        self.refresh()
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

    @Property(str, notify=changed)
    def statusText(self):
        return self.status

    @Property(bool, notify=changed)
    def startupEnabled(self):
        return self.startup

    @Property(bool, notify=changed)
    def reducedMotion(self):
        return self.host.settings.reduced_motion

    @Property(str, notify=changed)
    def closeBehavior(self):
        return self.host.settings.close_behavior

    @Slot()
    def open(self):
        if self.window is None:
            return
        self.window.showNormal()
        self.window.raise_()
        self.window.requestActivate()

    @Slot()
    def microphoneOff(self):
        self.host.voice.cancel_voice_requests()
        self.host.voice.cancel(disable=True)
        self.host.wake.disarm()
        self.host.advanced.armDictation(False)
        self.host.changed.emit()

    def refresh(self):
        state = (self.host.captureStatus, self.host.taskStatus, self.host.wake.calibrated,self.host.voice.hands_free)
        if state == self.last_state:
            return
        self.last_state = state
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        active = self.host.wake.monitoring or self.host.voice.recording
        painter.setBrush(QColor("#6bc79c" if active else "#c9915c"))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(4, 4, 56, 56)
        painter.setPen(QColor("#10191e"))
        painter.setFont(QFont("Segoe UI", 28, QFont.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "A")
        painter.end()
        self.tray.setIcon(QIcon(pixmap))
        self.listen_action.setChecked(self.host.voice.hands_free)
        self.tray.setToolTip("Autumn · " + self.host.captureStatus + " · " + self.host.taskStatus)
        self.arm_action.setEnabled(self.host.wake.calibrated and not self.host.wake.enabled)

    @Slot()
    def onMinimized(self):
        if self.window is not None and self.window.visibility() == QWindow.Minimized and QSystemTrayIcon.isSystemTrayAvailable():
            self.window.hide()
            self.status = 'Autumn is in the tray. Listening keeps its current setting.'
            self.changed.emit()

    @Slot()
    def requestClose(self):
        if self.close_dialog:
            return
        choice = self.host.settings.close_behavior
        if choice == "ask":
            self.close_dialog = True
            dialog = QMessageBox()
            dialog.setWindowTitle("Close Autumn")
            dialog.setText("Keep Autumn running in the tray, or quit?")
            dialog.setInformativeText(
                "Keeping it running preserves the current microphone setting. Quit stops all Autumn work. This choice is remembered in Desktop settings."
            )
            tray = dialog.addButton("Keep running in tray", QMessageBox.AcceptRole)
            quit_button = dialog.addButton("Quit Autumn", QMessageBox.DestructiveRole)
            dialog.setDefaultButton(quit_button)
            if not QSystemTrayIcon.isSystemTrayAvailable():
                tray.setEnabled(False)
            dialog.exec()
            clicked = dialog.clickedButton()
            self.close_dialog = False
            if clicked not in (tray, quit_button):
                return
            choice = "tray" if clicked == tray else "quit"
            if choice == "quit":
                self.pending_quit = True
                self.host.stop()
                self.microphoneOff()
                self.host.update_settings(close_behavior=choice)
                QTimer.singleShot(2000, self.finish_quit)
                return
            self.host.update_settings(close_behavior=choice)
        if choice == "tray" and QSystemTrayIcon.isSystemTrayAvailable():
            self.window.hide()
        else:
            self.app.quit()

    def settings_saved(self):
        if self.pending_quit and self.host.settings.close_behavior == "quit":
            self.finish_quit()

    def finish_quit(self):
        if self.pending_quit:
            self.pending_quit = False
            self.app.quit()

    @Slot(str, bool)
    def saveOptions(self, close_behavior, reduced):
        self.host.update_settings(close_behavior=close_behavior, reduced_motion=reduced)

    @Slot()
    def checkStartup(self):
        self.startup = startup_enabled()
        self.status = (
            "Autumn login startup is enabled; microphone remains off on launch."
            if self.startup
            else "Autumn login startup is off."
        )
        self.changed.emit()

    @Slot()
    def quit(self):
        self.app.quit()

    @Slot(bool)
    def setStartup(self, enabled):
        try:
            set_startup(enabled)
            self.startup = enabled
            self.status = (
                "Login startup enabled. Microphone and wake remain off at launch."
                if enabled
                else "Autumn login startup disabled."
            )
        except (OSError, ValueError):
            self.status = "Startup could not be changed. Use the standalone app; no administrator change was attempted."
        self.changed.emit()

    def shutdown(self):
        self.tray.hide()
        self.menu.close()
