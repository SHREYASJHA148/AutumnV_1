from types import SimpleNamespace

from PySide6.QtCore import QCoreApplication, QObject

from autumn.ui import desktop


def controller(choice="tray"):
    app = QCoreApplication.instance() or QCoreApplication([])
    assert app
    obj = desktop.Desktop.__new__(desktop.Desktop)
    QObject.__init__(obj)
    calls = []
    obj.close_dialog = False
    obj.pending_quit = False
    obj.host = SimpleNamespace(
        settings=SimpleNamespace(close_behavior=choice),
        update_settings=lambda **kw: calls.append(("save", kw)),
        stop=lambda: calls.append("stop"),
    )
    obj.window = SimpleNamespace(hide=lambda: calls.append("hide"))
    obj.app = SimpleNamespace(quit=lambda: calls.append("quit"))
    obj.microphoneOff = lambda: calls.append("microphone off")
    return obj, calls


def test_tray_close_preserves_mic_and_quit_is_explicit(monkeypatch):
    monkeypatch.setattr(desktop.QSystemTrayIcon, "isSystemTrayAvailable", lambda: True)
    obj, calls = controller("tray")
    obj.requestClose()
    assert calls == ["hide"]
    obj.host.settings.close_behavior = "quit"
    obj.requestClose()
    assert calls[-1] == "quit"


def test_minimize_hides_to_available_tray_without_cancelling_audio(monkeypatch):
    obj,calls=controller()
    obj.window.visibility=lambda:desktop.QWindow.Minimized
    monkeypatch.setattr(desktop.QSystemTrayIcon,'isSystemTrayAvailable',lambda:True)
    obj.onMinimized()
    assert calls==['hide']


def test_first_close_quit_waits_for_saved_choice_then_quits(monkeypatch):
    class Dialog:
        AcceptRole = 0
        DestructiveRole = 1

        def __init__(self):
            self.buttons = []

        def setWindowTitle(self, *args):
            pass

        def setText(self, *args):
            pass

        def setInformativeText(self, *args):
            pass

        def addButton(self, *args):
            button = SimpleNamespace(setEnabled=lambda enabled: None)
            self.buttons.append(button)
            return button

        def setDefaultButton(self, *args):
            pass

        def exec(self):
            pass

        def clickedButton(self):
            return self.buttons[1]

    monkeypatch.setattr(desktop, "QMessageBox", Dialog)
    monkeypatch.setattr(desktop.QSystemTrayIcon, "isSystemTrayAvailable", lambda: True)
    monkeypatch.setattr(desktop.QTimer, "singleShot", lambda *args: None)
    obj, calls = controller("ask")
    obj.requestClose()
    assert "quit" not in calls and ("save", {"close_behavior": "quit"}) in calls
    assert "stop" in calls and "microphone off" in calls
    obj.host.settings.close_behavior = "quit"
    obj.settings_saved()
    assert calls[-1] == "quit"
