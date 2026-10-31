import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window
    objectName: "autumnWindow"
    visible: true
    width: 1140; height: 800
    minimumWidth: 940; minimumHeight: 680
    title: "Autumn"
    color: "#10191e"
    font.family: "Segoe UI"
    font.pixelSize: 15
    palette.window: "#10191e"
    palette.windowText: "#e6edea"
    palette.text: "#e6edea"
    palette.base: "#1c2a30"
    palette.button: "#26373e"
    palette.buttonText: "#e6edea"
    palette.highlight: "#9ed7bd"
    palette.highlightedText: "#10191e"
    property int page: 0
    property var shortcuts: ["Ctrl+Alt+Backspace", "Ctrl+Alt+Space", "Ctrl+Alt+F9", "Ctrl+Alt+F10"]

    ColumnLayout {
        anchors.fill: parent; spacing: 0
        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 88
            color: "#162228"
            RowLayout {
                anchors.fill: parent; anchors.margins: 22; spacing: 16
                Rectangle {
                    width: 40; height: 40; radius: 20; color: "#ddb78a"
                    Label { anchors.centerIn: parent; text: "a"; color: "#202c2d"; font.pixelSize: 29; font.bold: true }
                }
                ColumnLayout {
                    spacing: 2
                    Label { text: "Autumn"; font.pixelSize: 24; font.weight: Font.DemiBold }
                    Label { text: "Your local workspace"; color: "#a0b5b6"; font.pixelSize: 12 }
                }
                Item { Layout.fillWidth: true }
                Label { text: "●  Local only"; color: "#a4d8bd"; Accessible.name: "Local only. No network connections." }
                Button { objectName: "voiceButton"; text: vm.voiceReady ? "Voice preview off" : "Voice preview on"; Accessible.name: text; onClicked: vm.toggleVoice() }
                Button { objectName: "stopButton"; text: "Stop"; Accessible.name: "Stop all work"; onClicked: vm.stop(); highlighted: true }
            }
        }
        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 0
            Rectangle {
                Layout.preferredWidth: 205; Layout.fillHeight: true; color: "#142025"
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 18; spacing: 10
                    Label { text: "WORKSPACE"; color: "#9cb0b1"; font.pixelSize: 11; font.letterSpacing: 1.8; Layout.topMargin: 8; Layout.bottomMargin: 12 }
                    Repeater {
                        model: ["Conversation", "Activity", "Settings", "Diagnostics"]
                        Button {
                            required property int index
                            required property string modelData
                            Layout.fillWidth: true; text: modelData; checkable: true
                            checked: window.page === index
                            Accessible.name: modelData + " page"
                            onClicked: window.page = index
                        }
                    }
                    Item { Layout.fillHeight: true }
                    Label { text: "FOUNDATION PREVIEW"; color: "#ddb78a"; font.pixelSize: 10; font.letterSpacing: 1.2 }
                    Label { Layout.fillWidth: true; text: "Commands are simulated.\nMicrophone stays closed."; wrapMode: Text.WordWrap; color: "#a7b9ba"; font.pixelSize: 12 }
                    Label { Layout.fillWidth: true; text: "Stop: " + vm.stopShortcut; wrapMode: Text.Wrap; color: "#cad7d3"; font.pixelSize: 12; Layout.topMargin: 10 }
                    Label { text: "Phase 1 · 0.1.0"; color: "#8fa6a8"; font.pixelSize: 11 }
                }
            }
            ColumnLayout {
                Layout.fillWidth: true; Layout.fillHeight: true; Layout.margins: 28; spacing: 16
                RowLayout {
                    Layout.fillWidth: true
                    Label { text: ["A little help, close by.", "Your recent activity", "Make yourself at home", "Workspace health"][window.page]; font.pixelSize: 26; font.weight: Font.DemiBold; Layout.fillWidth: true }
                    Label { text: vm.taskStatus + (vm.queuedCount ? " · " + vm.queuedCount + " queued" : ""); color: "#a4d8bd"; Accessible.name: "Task status: " + text }
                }
                Label { Layout.fillWidth: true; text: vm.captureStatus; color: "#a0b5b6"; Accessible.name: text }
                StackLayout {
                    Layout.fillWidth: true; Layout.fillHeight: true; currentIndex: window.page
                    ColumnLayout {
                        spacing: 14
                        ListView {
                            id: chat
                            objectName: "conversationList"
                            Layout.fillWidth: true; Layout.fillHeight: true
                            clip: true; spacing: 12; model: vm.messages
                            ScrollBar.vertical: ScrollBar {}
                            onCountChanged: Qt.callLater(positionViewAtEnd)
                            delegate: Rectangle {
                                required property var modelData
                                width: chat.width - 14
                                implicitHeight: bubble.implicitHeight + 30
                                radius: 12; color: modelData.role === "You" ? "#20332f" : "#1b2a31"
                                ColumnLayout {
                                    id: bubble; anchors.fill: parent; anchors.margins: 15; spacing: 6
                                    Label { text: modelData.role; color: modelData.role === "You" ? "#a4d8bd" : "#ddb78a"; font.pixelSize: 12; font.weight: Font.DemiBold }
                                    Label { Layout.fillWidth: true; text: modelData.text; textFormat: Text.PlainText; wrapMode: Text.Wrap; color: "#e0e9e5"; Accessible.name: modelData.role + ": " + modelData.text }
                                }
                            }
                        }
                        Label { text: "TRY A PREVIEW"; color: "#9cb0b1"; font.pixelSize: 10; font.letterSpacing: 1.5 }
                        RowLayout {
                            Button { text: "Open Notepad"; Accessible.name: "Preview Open Notepad"; enabled: vm.canSend; onClicked: vm.submit(text) }
                            Button { text: "Find a file"; Accessible.name: "Preview Find a file"; enabled: vm.canSend; onClicked: vm.submit(text) }
                            Item { Layout.fillWidth: true }
                        }
                        RowLayout {
                            Layout.fillWidth: true; spacing: 10
                            TextField {
                                id: input; objectName: "commandInput"; Layout.fillWidth: true
                                placeholderText: "Type a request…"; maximumLength: 2000
                                enabled: vm.canSend; selectByMouse: true
                                Accessible.name: "Type a request"; Accessible.description: "Phase 1 simulation only. Press Enter or Send."
                                onAccepted: { vm.submit(text); text = "" }
                            }
                            Button { objectName: "sendButton"; text: "Send"; enabled: vm.canSend && input.text.trim().length > 0; Accessible.name: "Send typed request"; onClicked: { vm.submit(input.text); input.text = ""; input.forceActiveFocus() } }
                        }
                    }
                    ColumnLayout {
                        spacing: 12
                        Label { text: "Only action metadata is stored. Your words stay out of history."; color: "#a7b9ba"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        ListView {
                            id: activityList; Layout.fillWidth: true; Layout.fillHeight: true
                            model: vm.activity; clip: true; spacing: 10
                            ScrollBar.vertical: ScrollBar {}
                            delegate: Rectangle {
                                required property var modelData
                                width: activityList.width - 14; height: 82; radius: 10; color: "#1b2a31"
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 14
                                    Label { text: (modelData.code === "SIMULATED" ? "Simulated preview" : "Preview interrupted") + " · " + modelData.status; color: "#e0e9e5" }
                                    Label { text: Qt.formatDateTime(new Date(modelData.created * 1000), "ddd d MMM, hh:mm") + " · " + modelData.origin + " · " + modelData.duration_ms + " ms"; color: "#a7b9ba"; font.pixelSize: 12 }
                                }
                            }
                            Label { visible: activityList.count === 0; text: "No recent activity. Try a preview from Conversation."; color: "#a7b9ba"; anchors.centerIn: parent }
                        }
                        Button { text: "Clear history"; Accessible.name: "Clear Autumn activity history"; enabled: vm.canSend; onClicked: vm.clearHistory() }
                    }
                    ScrollView {
                        clip: true
                        ColumnLayout {
                            width: parent.width - 22; spacing: 16
                            Label { text: "Voice & privacy"; font.pixelSize: 18; color: "#ddb78a" }
                            Label { Layout.fillWidth: true; text: "English · Female voice: Lessac\nBuilt-in microphone preferred · System default speakers\nMicrophone is off at every launch. Wake mode and conversation saving are off."; wrapMode: Text.WordWrap; color: "#c1d0ce" }
                            Label { Layout.fillWidth: true; text: "Device selection and live voice controls arrive with speech integration. No computer actions are enabled in this preview."; wrapMode: Text.WordWrap; color: "#a0b5b6" }
                            Label { text: "Controls"; font.pixelSize: 18; color: "#ddb78a" }
                            Label { text: "Stop shortcut" }
                            ComboBox { id: stopChoice; objectName: "stopChoice"; model: window.shortcuts; currentIndex: window.shortcuts.indexOf(vm.stopShortcut); Accessible.name: "Stop shortcut" }
                            Label { text: "Voice readiness shortcut" }
                            ComboBox { id: voiceChoice; model: window.shortcuts; currentIndex: window.shortcuts.indexOf(vm.voiceShortcut); Accessible.name: "Voice readiness shortcut" }
                            Label { text: "Keep activity for this many days (1–90)" }
                            SpinBox { id: days; from: 1; to: 90; value: vm.retentionDays; editable: true; Accessible.name: "History retention days" }
                            Button { text: "Save settings"; enabled: vm.canSend; Accessible.name: "Save settings"; onClicked: vm.saveSettings(days.value, stopChoice.currentText, voiceChoice.currentText) }
                            Label { text: "Saved locations"; font.pixelSize: 18; color: "#ddb78a" }
                            Label { Layout.fillWidth: true; text: vm.locations; textFormat: Text.PlainText; wrapMode: Text.WrapAnywhere; color: "#a7b9ba" }
                            Label { text: "Location editing and permission controls arrive with the action engine."; wrapMode: Text.WordWrap; Layout.fillWidth: true; color: "#a7b9ba" }
                        }
                    }
                    ColumnLayout {
                        spacing: 12
                        Label { text: "Read-only checks. Refresh never opens a microphone or downloads a model."; wrapMode: Text.WordWrap; Layout.fillWidth: true; color: "#a7b9ba" }
                        ListView {
                            id: healthList; Layout.fillWidth: true; Layout.fillHeight: true
                            model: vm.health; clip: true; spacing: 10
                            ScrollBar.vertical: ScrollBar {}
                            delegate: Rectangle {
                                required property var modelData
                                width: healthList.width - 14; implicitHeight: diagnostic.implicitHeight + 26
                                color: "#1b2a31"; radius: 10
                                ColumnLayout {
                                    id: diagnostic; anchors.fill: parent; anchors.margins: 13; spacing: 5
                                    Label { text: modelData.name; color: "#ddb78a"; font.weight: Font.DemiBold }
                                    Label { Layout.fillWidth: true; text: modelData.detail; wrapMode: Text.WordWrap; color: "#c1d0ce"; Accessible.name: modelData.name + ": " + modelData.detail }
                                }
                            }
                        }
                        Button { text: "Refresh checks"; enabled: vm.canSend; Accessible.name: "Refresh workspace diagnostics"; onClicked: vm.refreshDiagnostics() }
                    }
                }
                Rectangle {
                    Layout.fillWidth: true; implicitHeight: noticeText.implicitHeight + 24; radius: 8; color: "#1d3030"
                    Label { id: noticeText; objectName: "notice"; anchors.fill: parent; anchors.margins: 12; text: vm.statusMessage; textFormat: Text.PlainText; wrapMode: Text.WordWrap; color: "#b8d5c7"; Accessible.name: "Status: " + text }
                }
            }
        }
    }
}
