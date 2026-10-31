import QtQuick
import QtQuick.Controls
import QtQuick.Window

Button {
    id: control
    property bool emergency: objectName === "stopButton"
    property bool motionAllowed: !desktop.reducedMotion && Window.window && Window.window.visible && Qt.application.state === Qt.ApplicationActive
    implicitHeight: 38
    implicitWidth: Math.max(90, contentItem.implicitWidth + 28)
    padding: 12
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    scale: emergency || !motionAllowed ? 1 : (down ? 0.98 : 1)
    Behavior on scale { NumberAnimation { duration: control.motionAllowed ? 90 : 0; easing.type: Easing.OutCubic } }
    opacity: enabled ? 1 : 0.40
    contentItem: Text {
        text: control.text; font: control.font
        color: control.emergency ? "#ffd2cd" : (control.checked || control.highlighted ? "#72e5f2" : "#d4e4f4")
        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    background: Rectangle {
        radius: 9
        color: control.emergency ? (control.hovered ? "#552934" : "#351e2b") : (control.down ? "#203d58" : control.checked ? "#16374b" : control.hovered ? "#192d45" : "#101f32")
        border.width: control.activeFocus ? 2 : 1
        border.color: control.emergency ? "#bc5866" : control.activeFocus ? "#7aeeff" : control.checked || control.hovered ? "#427e9a" : "#263d58"
        Behavior on color { ColorAnimation { duration: control.motionAllowed ? 130 : 0 } }
        Behavior on border.color { ColorAnimation { duration: control.motionAllowed ? 130 : 0 } }
        Rectangle { visible: control.checked; width: 3; height: parent.height - 16; anchors.left: parent.left; anchors.leftMargin: 2; anchors.verticalCenter: parent.verticalCenter; radius: 2; color: "#65e6ed" }
        Rectangle { anchors.fill: parent; anchors.margins: -3; radius: 12; color: "transparent"; border.color: "#52b6d7"; opacity: control.activeFocus ? 0.24 : 0 }
    }
}
