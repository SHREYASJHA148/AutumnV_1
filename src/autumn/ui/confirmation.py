"""A non-activating exact preview; no focus change when shown or clicked."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget


class ConfirmationOverlay(QWidget):
    def __init__(self, advanced):
        super().__init__(None, Qt.Tool | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setWindowTitle("Autumn — confirm exact action")
        self.setFixedSize(520, 280)
        layout = QVBoxLayout(self)
        self.destination = QLabel()
        self.destination.setTextFormat(Qt.PlainText)
        self.destination.setWordWrap(True)
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setAccessibleName("Exact action preview")
        self.preview.setFocusPolicy(Qt.NoFocus)
        layout.addWidget(self.destination)
        layout.addWidget(self.preview)
        layout.addWidget(
            QLabel(
                "Return to the chosen edit field. Confirm: Ctrl+Alt+Y · Cancel: Ctrl+Alt+N\nExpires after 30 seconds. No Enter or clipboard paste."
            )
        )
        buttons = QHBoxLayout()
        for label, callback in (
            ("Confirm exact action", advanced.confirm),
            ("Cancel", advanced.cancelApproval),
        ):
            button = QPushButton(label)
            button.setFocusPolicy(Qt.NoFocus)
            button.setAccessibleName(label)
            button.clicked.connect(callback)
            buttons.addWidget(button)
        layout.addLayout(buttons)
        advanced.showApproval.connect(self.present)
        advanced.hideApproval.connect(self.dismiss)
        self.advanced = advanced

    def present(self, target, text):
        self.destination.setText("Destination: " + target)
        self.preview.setPlainText(text)
        # Explicit native NOACTIVATE, including mouse clicks on child buttons.
        import win32con
        import win32gui

        hwnd = int(self.winId())
        win32gui.SetWindowLong(
            hwnd,
            win32con.GWL_EXSTYLE,
            win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) | 0x08000000,
        )
        self.show()
        screen = self.screen().availableGeometry()
        self.move(screen.right() - self.width() - 24, screen.bottom() - self.height() - 24)

    def dismiss(self):
        self.hide()
        self.preview.clear()
        self.destination.clear()

    def nativeEvent(self, event_type, message):
        from ctypes import wintypes

        if wintypes.MSG.from_address(int(message)).message == 0x21:
            return True, 3  # MA_NOACTIVATE
        return super().nativeEvent(event_type, message)

    def closeEvent(self, event):
        self.advanced.cancelApproval()
        event.accept()
