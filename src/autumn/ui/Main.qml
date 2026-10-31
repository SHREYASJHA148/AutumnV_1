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
                        model: ["Conversation", "Activity", "Settings", "Diagnostics", "Apps and folders"]
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
                    Label { text: "TYPED WORKSPACE"; color: "#ddb78a"; font.pixelSize: 10; font.letterSpacing: 1.2 }
                    Label { Layout.fillWidth: true; text: "Commands use reviewed targets.\nMicrophone stays closed."; wrapMode: Text.WordWrap; color: "#a7b9ba"; font.pixelSize: 12 }
                    Label { Layout.fillWidth: true; text: "Stop: " + vm.stopShortcut; wrapMode: Text.Wrap; color: "#cad7d3"; font.pixelSize: 12; Layout.topMargin: 10 }
                    Label { text: "Phase 3 · 0.3.0"; color: "#8fa6a8"; font.pixelSize: 11 }
                }
            }
            ColumnLayout {
                Layout.fillWidth: true; Layout.fillHeight: true; Layout.margins: 28; spacing: 16
                RowLayout {
                    Layout.fillWidth: true
                    Label { text: ["A little help, close by.", "Your recent activity", "Make yourself at home", "Workspace health", "Choose your targets"][window.page]; font.pixelSize: 26; font.weight: Font.DemiBold; Layout.fillWidth: true }
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
                        ListView {
                            id: results; Layout.fillWidth: true; Layout.preferredHeight: count ? 136 : 0
                            clip: true; spacing: 6; model: vm.resultCards
                            ScrollBar.vertical: ScrollBar {}
                            delegate: RowLayout {
                                required property var modelData
                                width: results.width - 16
                                Label { Layout.fillWidth: true; text: modelData.name + "\n" + modelData.path; textFormat: Text.PlainText; wrapMode: Text.WrapAnywhere; color: "#c1d0ce"; font.pixelSize: 12 }
                                Button { text: "Show folder"; visible: modelData.kind === "match"; Accessible.name: "Show containing folder for " + modelData.name; onClicked: vm.showMatchFolder(modelData.id) }
                            }
                        }
                        Label { text: "TRY A COMMAND"; color: "#9cb0b1"; font.pixelSize: 10; font.letterSpacing: 1.5 }
                        Flow {
                            Layout.fillWidth: true; spacing: 6
                            Repeater {
                                model: vm.clarificationChoices
                                Button { required property string modelData; text: modelData; Accessible.name: "Clarification choice " + modelData; onClicked: vm.chooseClarification(modelData) }
                            }
                        }
                        RowLayout {
                            Button { text: "What can you do?"; Accessible.name: text; enabled: vm.canSend; onClicked: vm.submit(text) }
                            Button { text: "Review apps"; Accessible.name: text; onClicked: window.page = 4 }
                            Item { Layout.fillWidth: true }
                        }
                        RowLayout {
                            Layout.fillWidth: true; spacing: 10
                            TextField {
                                id: input; objectName: "commandInput"; Layout.fillWidth: true
                                placeholderText: "Type a request…"; maximumLength: 2000
                                enabled: vm.canSend; selectByMouse: true
                                Accessible.name: "Type a request"; Accessible.description: "Type a supported command. Press Enter or Send."
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
                                    Label { text: modelData.skill_id + " · " + modelData.status; color: "#e0e9e5" }
                                    Label { text: Qt.formatDateTime(new Date(modelData.created * 1000), "ddd d MMM, hh:mm") + " · " + modelData.origin + " · " + modelData.duration_ms + " ms"; color: "#a7b9ba"; font.pixelSize: 12 }
                                }
                            }
                            Label { visible: activityList.count === 0; text: "No recent activity. Try a preview from Conversation."; color: "#a7b9ba"; anchors.centerIn: parent }
                        }
                        Button { text: "Clear history"; Accessible.name: "Clear Autumn activity history"; enabled: vm.canSend; onClicked: vm.clearHistory() }
                    }
                    ScrollView {
                        clip: true
                        enabled: vm.canConfigure
                        ColumnLayout {
                            width: parent.width - 22; spacing: 16
                            Label { text: "Voice & privacy"; font.pixelSize: 18; color: "#ddb78a" }
                            Label { Layout.fillWidth: true; text: "English · Female voice: Lessac\nBuilt-in microphone preferred · System default speakers\nMicrophone is off at every launch. Wake mode and conversation saving are off."; wrapMode: Text.WordWrap; color: "#c1d0ce" }
                            Label { Layout.fillWidth: true; text: "Device selection and live voice controls arrive with speech integration. Typed commands use the capabilities enabled below."; wrapMode: Text.WordWrap; color: "#a0b5b6" }
                            Label { text: "Controls"; font.pixelSize: 18; color: "#ddb78a" }
                            Label { text: "Local brain · qwen3:1.7b · CPU"; color: "#ddb78a"; font.pixelSize: 18 }
                            Label { Layout.fillWidth: true; text: vm.modelStatus; wrapMode: Text.WordWrap; color: "#a7b9ba"; Accessible.name: text }
                            CheckBox { id: modelEnabled; text: "Flexible English commands"; checked: vm.modelEnabled; Accessible.name: text; onClicked: vm.setModelOptions(checked, memorySaver.checked) }
                            CheckBox { id: memorySaver; text: "Save memory: release the model after each request"; checked: vm.modelMemorySaver; Accessible.name: text; onClicked: vm.setModelOptions(modelEnabled.checked, checked) }
                            Button { text: "Check local brain"; Accessible.name: text; onClicked: vm.checkLocalBrain() }
                            Label { text: "Stop shortcut" }
                            ComboBox { id: stopChoice; objectName: "stopChoice"; Layout.preferredWidth: 280; model: window.shortcuts; currentIndex: window.shortcuts.indexOf(vm.stopShortcut); Accessible.name: "Stop shortcut" }
                            Label { text: "Voice readiness shortcut" }
                            ComboBox { id: voiceChoice; Layout.preferredWidth: 280; model: window.shortcuts; currentIndex: window.shortcuts.indexOf(vm.voiceShortcut); Accessible.name: "Voice readiness shortcut" }
                            Label { text: "Keep activity for this many days (1–90)" }
                            SpinBox { id: days; from: 1; to: 90; value: vm.retentionDays; editable: true; Accessible.name: "History retention days" }
                            Button { text: "Save settings"; enabled: vm.canSend; Accessible.name: "Save settings"; onClicked: vm.saveSettings(days.value, stopChoice.currentText, voiceChoice.currentText) }
                            Label { text: "Saved locations"; font.pixelSize: 18; color: "#ddb78a" }
                            Label { Layout.fillWidth: true; text: vm.locations; textFormat: Text.PlainText; wrapMode: Text.WrapAnywhere; color: "#a7b9ba" }
                            Button { text: "Choose screenshot folder"; Accessible.name: text; onClicked: vm.chooseScreenshotFolder() }
                            Label { text: "Enabled capabilities"; font.pixelSize: 18; color: "#ddb78a" }
                            Repeater {
                                model: vm.skillSettings
                                CheckBox {
                                    required property var modelData
                                    text: modelData.description; checked: modelData.enabled
                                    Accessible.name: text
                                    onClicked: vm.enableSkill(modelData.id, checked)
                                }
                            }
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
                    ColumnLayout {
                        spacing: 10
                        enabled: vm.canConfigure
                        Label { Layout.fillWidth: true; text: "Imported apps stay disabled until you review and save them. Shortcuts with arguments or script launchers are skipped."; wrapMode: Text.WordWrap; color: "#a7b9ba" }
                        RowLayout {
                            Button { text: "Import installed apps"; enabled: vm.canSend; Accessible.name: text; onClicked: vm.importApps() }
                            Button { text: "Add app…"; enabled: vm.canSend; Accessible.name: text; onClicked: vm.addApp() }
                        }
                        ListView {
                            id: apps; Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                            model: vm.appCatalog; spacing: 10; ScrollBar.vertical: ScrollBar {}
                            delegate: Rectangle {
                                required property var modelData
                                width: apps.width - 16; height: 160; radius: 9; color: "#1b2a31"
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 10; spacing: 4
                                    RowLayout {
                                        TextField { id: appName; text: modelData.name; Layout.fillWidth: true; maximumLength: 80; Accessible.name: "App name" }
                                        CheckBox { id: appEnabled; text: "Enabled"; checked: modelData.enabled; Accessible.name: "Enable " + modelData.name }
                                    }
                                    TextField { id: appAliases; text: modelData.alias_text; placeholderText: "Aliases separated by commas"; Layout.fillWidth: true; Accessible.name: "App aliases" }
                                    Label { text: modelData.kind + ": " + modelData.target; textFormat: Text.PlainText; Layout.fillWidth: true; elide: Text.ElideMiddle; color: "#a7b9ba"; font.pixelSize: 11 }
                                    RowLayout {
                                        Button { text: "Review & save"; Accessible.name: "Review and save " + modelData.name; onClicked: vm.saveApp(modelData.id, appName.text, appAliases.text, appEnabled.checked) }
                                        Button { text: "Remove"; Accessible.name: "Remove " + modelData.name; onClicked: vm.removeApp(modelData.id) }
                                    }
                                }
                            }
                        }
                        RowLayout {
                            TextField { id: folderName; placeholderText: "Folder name"; Layout.fillWidth: true; maximumLength: 80; Accessible.name: "Registered folder name" }
                            Button { text: "Choose folder…"; Accessible.name: text; onClicked: vm.addFolder(folderName.text) }
                        }
                        RowLayout {
                            TextField { id: siteName; placeholderText: "Website name"; Layout.preferredWidth: 150; maximumLength: 80; Accessible.name: "Registered website name" }
                            TextField { id: siteUrl; placeholderText: "https://example.com"; Layout.fillWidth: true; maximumLength: 2048; Accessible.name: "Website address" }
                            Button { text: "Add site"; Accessible.name: text; onClicked: vm.addSite(siteName.text, siteUrl.text) }
                        }
                        ListView {
                            id: locations; Layout.fillWidth: true; Layout.preferredHeight: 100; clip: true
                            model: vm.registeredLocations; ScrollBar.vertical: ScrollBar {}
                            delegate: RowLayout {
                                required property var modelData
                                width: locations.width - 16
                                Label { text: modelData.name + " · " + modelData.detail; Layout.fillWidth: true; elide: Text.ElideMiddle; color: "#a7b9ba"; textFormat: Text.PlainText }
                                Button { text: "Remove"; Accessible.name: "Remove " + modelData.name; onClicked: vm.removeLocation(modelData.id, modelData.kind) }
                            }
                        }
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
