import QtQuick
import QtQuick.Controls

TextField {
    id: field
    implicitHeight: 42
    leftPadding: 14; rightPadding: 14
    color: "#e1efff"; placeholderTextColor: "#7089a3"
    selectionColor: "#255774"; selectedTextColor: "#ffffff"
    background: Rectangle {
        radius: 10; color: field.activeFocus ? "#10253b" : "#0b1829"
        border.width: field.activeFocus ? 2 : 1; border.color: field.activeFocus ? "#63dceb" : "#273c57"
        Behavior on border.color { ColorAnimation { duration: desktop.reducedMotion ? 0 : 130 } }
    }
}
