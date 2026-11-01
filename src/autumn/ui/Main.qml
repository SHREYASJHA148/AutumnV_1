import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

ApplicationWindow {
    id: window
    objectName: "autumnWindow"
    property bool setupShown: false
    property bool motionAllowed: !desktop.reducedMotion && visible && Qt.application.state === Qt.ApplicationActive
    onMotionAllowedChanged: { if (!motionAllowed && pageStack) { pageReveal.stop(); pageStack.opacity = 1 } }
    Connections { target: vm; function onSettingsChanged() { if (vm.firstRun && !window.setupShown) { window.page = 9; window.setupShown = true } } }
    visible: true
    width: Math.min(1240, Screen.desktopAvailableWidth || 1140); height: Math.min(800, Screen.desktopAvailableHeight || 800)
    minimumWidth: Math.min(850, Screen.desktopAvailableWidth || 940); minimumHeight: Math.min(680, Screen.desktopAvailableHeight || 680)
    onClosing: function(event) { event.accepted = false; desktop.requestClose() }
    title: "Autumn"
    color: "#070e1b"
    font.family: "Segoe UI"
    font.pixelSize: 13
    palette.window: "#070e1b"
    palette.windowText: "#e6edea"
    palette.text: "#e6edea"
    palette.base: "#0d1d31"
    palette.button: "#13283e"
    palette.buttonText: "#e6edea"
    palette.highlight: "#64ddeb"
    palette.highlightedText: "#070e1b"
    property int page: 0
    onPageChanged: { if (motionAllowed) pageReveal.restart() }
    property var shortcuts: ["Ctrl+Alt+Backspace", "Ctrl+Alt+Space", "Ctrl+Alt+F9", "Ctrl+Alt+F10"]

    SequentialAnimation {
        id: pageReveal
        PropertyAction { target: pageStack; property: "opacity"; value: .35 }
        NumberAnimation { target: pageStack; property: "opacity"; to: 1; duration: 210; easing.type: Easing.OutCubic }
    }

    ColumnLayout {
        anchors.fill: parent; spacing: 0
        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 76
            color: "#0b1527"
            RowLayout {
                anchors.fill: parent; anchors.margins: 22; spacing: 16
                Rectangle {
                    width: 40; height: 40; radius: 20; color: "#ffc27e"
                    Label { anchors.centerIn: parent; text: "a"; color: "#202c2d"; font.pixelSize: 29; font.bold: true }
                }
                ColumnLayout {
                    spacing: 2
                    Label { text: "Autumn"; font.pixelSize: 24; font.weight: Font.DemiBold }
                    Label { text: "PERSONAL OPERATING SPACE"; color: "#839cb8"; font.pixelSize: 12 }
                }
                Item { Layout.fillWidth: true }
                Label { text: "●  ON DEVICE"; color: "#74deeb"; font.pixelSize: 11; font.letterSpacing: 1.3; Accessible.name: "Inference runs on your computer. Websites and explicit setup downloads use the internet."; visible: window.width > 1000 }
                NeonButton { text: desktop.reducedMotion ? "Motion off" : "Motion on"; Accessible.name: "Toggle decorative motion"; onClicked: desktop.saveOptions(desktop.closeBehavior,!desktop.reducedMotion) }
                NeonButton { text: "Hands-free"; visible: window.width > 1100; checkable: true; checked: voice.handsFree; Accessible.name: "Toggle hands-free listening for Autumn"; onClicked: voice.setHandsFree(!voice.handsFree) }
                NeonButton { objectName: "voiceButton"; text: voice.enabledVoice || wake.enabledWake || wake.busy ? "Microphone off" : "Enable voice"; Accessible.name: text; onClicked: vm.toggleVoice() }
                NeonButton { objectName: "stopButton"; text: "Stop"; Accessible.name: "Stop all work"; onClicked: vm.stop(); highlighted: true }
            }
        }
        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 0
            Rectangle {
                Layout.preferredWidth: 192; Layout.fillHeight: true; color: "#091323"
                ScrollView {
                    anchors.fill: parent; anchors.margins: 12; clip: true
                ColumnLayout {
                    width: 162; spacing: 8
                    Label { text: "COMMAND DECK"; color: "#748ca8"; font.pixelSize: 10; font.letterSpacing: 2; Layout.topMargin: 12; Layout.bottomMargin: 14 }
                    Repeater {
                        model: ["Conversation", "Activity", "Settings", "Diagnostics", "Apps and folders", "Voice setup", "Dictation", "Routines", "Wake and desktop", "Setup & release"]
                        NeonButton {
                            required property int index
                            required property string modelData
                            Layout.fillWidth: true; text: modelData; checkable: true
                            checked: window.page === index
                            Accessible.name: modelData + " page"
                            onClicked: window.page = index
                        }
                    }
                    Item { Layout.fillHeight: true }
                    Label { text: "LOCAL WORKSPACE"; color: "#ffc27e"; font.pixelSize: 10; font.letterSpacing: 1.2 }
                    Label { Layout.fillWidth: true; text: vm.broadOpenAccess ? "Installed apps and local paths enabled.\nListening follows your launch preference." : "Commands use reviewed targets.\nVoice follows your launch preference."; wrapMode: Text.WordWrap; color: "#9bb0c9"; font.pixelSize: 12 }
                    Label { Layout.fillWidth: true; text: "Stop: " + vm.stopShortcut; wrapMode: Text.Wrap; color: "#cad7d3"; font.pixelSize: 12; Layout.topMargin: 10 }
                    Label { text: "PREVIEW 0.7.2"; color: "#8fa6a8"; font.pixelSize: 11 }
                }
                }
            }
            ColumnLayout {
                Layout.fillWidth: true; Layout.fillHeight: true; Layout.margins: window.width < 900 ? 16 : 26; spacing: 14
                RowLayout {
                    Layout.fillWidth: true
                    Label { text: ["A little help, close by.", "Your recent activity", "Make yourself at home", "Workspace health", "Choose your targets", "Make Autumn hear you", "Review and confirm", "Your everyday sequences", "Listening on your terms", "Make it yours"][window.page]; font.pixelSize: 26; font.weight: Font.DemiBold; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                    Label { text: vm.taskStatus + (vm.queuedCount ? " · " + vm.queuedCount + " queued" : ""); color: "#74deeb"; Accessible.name: "Task status: " + text }
                }
                Label { Layout.fillWidth: true; text: vm.captureStatus; color: "#839cb8"; Accessible.name: text }
                StackLayout {
                    id: pageStack
                    Layout.fillWidth: true; Layout.fillHeight: true; currentIndex: window.page
                    ColumnLayout {
                        spacing: 14
                        Rectangle {
                            Layout.fillWidth: true; Layout.preferredHeight: window.height > 680 ? 160 : 86
                            color: "#0c1b2e"; radius: 18; border.color: "#203b57"
                            gradient: Gradient { orientation: Gradient.Horizontal; GradientStop { position: 0; color: "#10243b" } GradientStop { position: 1; color: "#0c1729" } }
                            RowLayout {
                                anchors.fill: parent; anchors.margins: window.height > 680 ? 16 : 8
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 7
                                    Label { text: "AUTUMN / PERSONAL CORE"; color: "#74deeb"; font.pixelSize: 10; font.letterSpacing: 2.1; visible: window.height > 680 }
                                    Label { text: "Your intent.\nA little momentum."; font.pixelSize: window.height > 680 ? 25 : 18; font.weight: Font.Light; color: "#e0efff"; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                                    Label { text: "Speak or type. Review the result. Stay in control."; font.pixelSize: 12; color: "#8faac6"; visible: window.height > 680; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                                }
                                PresenceOrb {
                                    Layout.preferredWidth: window.height > 680 ? 124 : 62; Layout.preferredHeight: Layout.preferredWidth
                                    motionAllowed: window.motionAllowed && window.page === 0
                                    engaged: voice.isBusy || vm.taskStatus !== "Idle"
                                    recording: voice.isRecording; level: voice.inputLevel
                                }
                            }
                        }
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
                                radius: 14; color: modelData.role.indexOf("You") === 0 ? "#112b3f" : "#102137"; border.color: modelData.role.indexOf("You") === 0 ? "#28536b" : "#213750"
                                ColumnLayout {
                                    id: bubble; anchors.fill: parent; anchors.margins: 15; spacing: 6
                                    Label { text: modelData.role; color: modelData.role.indexOf("You") === 0 ? "#74deeb" : "#ffc27e"; font.pixelSize: 12; font.weight: Font.DemiBold }
                                    Label { Layout.fillWidth: true; text: modelData.text; textFormat: Text.PlainText; wrapMode: Text.Wrap; color: "#ddeafa"; Accessible.name: modelData.role + ": " + modelData.text }
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
                                Label { Layout.fillWidth: true; text: modelData.name + "\n" + modelData.path; textFormat: Text.PlainText; wrapMode: Text.WrapAnywhere; color: "#bacce1"; font.pixelSize: 12 }
                                NeonButton { text: "Show folder"; visible: modelData.kind === "match"; Accessible.name: "Show containing folder for " + modelData.name; onClicked: vm.showMatchFolder(modelData.id) }
                            }
                        }
                        Label { text: "TRY A COMMAND"; color: "#748ca8"; font.pixelSize: 10; font.letterSpacing: 1.5 }
                        Flow {
                            Layout.fillWidth: true; spacing: 6
                            Repeater {
                                model: vm.clarificationChoices
                                NeonButton { required property string modelData; text: modelData; Accessible.name: "Clarification choice " + modelData; onClicked: vm.chooseClarification(modelData) }
                            }
                        }
                        RowLayout {
                            NeonButton { text: "What can you do?"; Accessible.name: text; enabled: vm.canSend; onClicked: vm.submit(text) }
                            NeonButton { text: "Review apps"; Accessible.name: text; onClicked: window.page = 4 }
                            NeonButton {
                                objectName: "talkButton"
                                text: voice.mode === "hold" ? "Hold to talk" : (voice.isRecording ? "Finish recording" : "Record command")
                                enabled: vm.canSend && voice.enabledVoice && (!voice.isBusy || voice.isRecording)
                                Accessible.name: text
                                onPressed: voice.beginHold()
                                onReleased: voice.endHold()
                                onCanceled: voice.endHold()
                                onClicked: { if (voice.mode === "toggle") voice.toggleRecording() }
                            }
                            Item { Layout.fillWidth: true }
                        }
                        RowLayout {
                            Layout.fillWidth: true; spacing: 10
                            NeonField {
                                id: input; objectName: "commandInput"; Layout.fillWidth: true
                                placeholderText: "Ask Autumn to do something…"; maximumLength: 2000
                                enabled: vm.canSend; selectByMouse: true
                                Accessible.name: "Type a request"; Accessible.description: "Type a supported command. Press Enter or Send."
                                onAccepted: { vm.submit(text); text = "" }
                            }
                            NeonButton { objectName: "sendButton"; text: "Send"; enabled: vm.canSend && input.text.trim().length > 0; Accessible.name: "Send typed request"; onClicked: { vm.submit(input.text); input.text = ""; input.forceActiveFocus() } }
                        }
                    }
                    ColumnLayout {
                        spacing: 12
                        Label { text: "Only action metadata is stored. Your words stay out of history."; color: "#9bb0c9"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        ListView {
                            id: activityList; Layout.fillWidth: true; Layout.fillHeight: true
                            model: vm.activity; clip: true; spacing: 10
                            ScrollBar.vertical: ScrollBar {}
                            delegate: Rectangle {
                                required property var modelData
                                width: activityList.width - 14; height: 82; radius: 10; color: "#102137"
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 14
                                    Label { text: modelData.skill_id + " · " + modelData.status; color: "#ddeafa" }
                                    Label { text: Qt.formatDateTime(new Date(modelData.created * 1000), "ddd d MMM, hh:mm") + " · " + modelData.origin + " · " + modelData.duration_ms + " ms"; color: "#9bb0c9"; font.pixelSize: 12 }
                                }
                            }
                            Label { visible: activityList.count === 0; text: "No recent activity. Try a preview from Conversation."; color: "#9bb0c9"; anchors.centerIn: parent }
                        }
                        NeonButton { text: "Clear history"; Accessible.name: "Clear Autumn activity history"; enabled: vm.canSend; onClicked: vm.clearHistory() }
                    }
                    ScrollView {
                        clip: true; contentWidth: availableWidth
                        enabled: vm.canConfigure
                        ColumnLayout {
                            width: parent.width - 22; spacing: 16
                            Label { text: "Voice & privacy"; font.pixelSize: 18; color: "#ffc27e" }
                            Label { Layout.fillWidth: true; text: "English · Female voice: Lessac\nBuilt-in microphone preferred · System default speakers\nMicrophone is off at every launch. Wake mode and conversation saving are off."; wrapMode: Text.WordWrap; color: "#bacce1" }
                            NeonButton { text: "Open voice setup"; onClicked: window.page = 5 }
                            Label { text: "Controls"; font.pixelSize: 18; color: "#ffc27e" }
                            Label { text: "Local brain · qwen3:1.7b · CPU"; color: "#ffc27e"; font.pixelSize: 18 }
                            Label { Layout.fillWidth: true; text: vm.modelStatus; wrapMode: Text.WordWrap; color: "#9bb0c9"; Accessible.name: text }
                            CheckBox { id: modelEnabled; text: "Flexible English commands"; checked: vm.modelEnabled; Accessible.name: text; onClicked: vm.setModelOptions(checked, memorySaver.checked) }
                            CheckBox { id: memorySaver; text: "Save memory: release the model after each request"; checked: vm.modelMemorySaver; Accessible.name: text; onClicked: vm.setModelOptions(modelEnabled.checked, checked) }
                            NeonButton { text: "Check local brain"; Accessible.name: text; onClicked: vm.checkLocalBrain() }
                            Label { text: "Stop shortcut" }
                            ComboBox { id: stopChoice; objectName: "stopChoice"; Layout.preferredWidth: 280; model: window.shortcuts; currentIndex: window.shortcuts.indexOf(vm.stopShortcut); Accessible.name: "Stop shortcut" }
                            Label { text: "Talk shortcut" }
                            ComboBox { id: voiceChoice; Layout.preferredWidth: 280; model: window.shortcuts; currentIndex: window.shortcuts.indexOf(vm.voiceShortcut); Accessible.name: "Voice readiness shortcut" }
                            Label { text: "Keep activity for this many days (1–90)" }
                            SpinBox { id: days; from: 1; to: 90; value: vm.retentionDays; editable: true; Accessible.name: "History retention days" }
                            NeonButton { text: "Save settings"; enabled: vm.canSend; Accessible.name: "Save settings"; onClicked: vm.saveSettings(days.value, stopChoice.currentText, voiceChoice.currentText) }
                            Label { text: "Saved locations"; font.pixelSize: 18; color: "#ffc27e" }
                            Label { Layout.fillWidth: true; text: vm.locations; textFormat: Text.PlainText; wrapMode: Text.WrapAnywhere; color: "#9bb0c9" }
                            NeonButton { text: "Choose screenshot folder"; Accessible.name: text; onClicked: vm.chooseScreenshotFolder() }
                            Label { text: "Enabled capabilities"; font.pixelSize: 18; color: "#ffc27e" }
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
                        Label { text: "Read-only checks. Refresh never opens a microphone or downloads a model."; wrapMode: Text.WordWrap; Layout.fillWidth: true; color: "#9bb0c9" }
                        ListView {
                            id: healthList; Layout.fillWidth: true; Layout.fillHeight: true
                            model: vm.health; clip: true; spacing: 10
                            ScrollBar.vertical: ScrollBar {}
                            delegate: Rectangle {
                                required property var modelData
                                width: healthList.width - 14; implicitHeight: diagnostic.implicitHeight + 26
                                color: "#102137"; radius: 10
                                ColumnLayout {
                                    id: diagnostic; anchors.fill: parent; anchors.margins: 13; spacing: 5
                                    Label { text: modelData.name; color: "#ffc27e"; font.weight: Font.DemiBold }
                                    Label { Layout.fillWidth: true; text: modelData.detail; wrapMode: Text.WordWrap; color: "#bacce1"; Accessible.name: modelData.name + ": " + modelData.detail }
                                }
                            }
                        }
                        NeonButton { text: "Refresh checks"; enabled: vm.canSend; Accessible.name: "Refresh workspace diagnostics"; onClicked: vm.refreshDiagnostics() }
                    }
                    ColumnLayout {
                        spacing: 10
                        enabled: vm.canConfigure
                        Label { Layout.fillWidth: true; text: "Imported apps stay disabled until you review and save them. Shortcuts with arguments or script launchers are skipped."; wrapMode: Text.WordWrap; color: "#9bb0c9" }
                        RowLayout {
                            NeonButton { text: "Import installed apps"; enabled: vm.canSend; Accessible.name: text; onClicked: vm.importApps() }
                            NeonButton { text: "Add app…"; enabled: vm.canSend; Accessible.name: text; onClicked: vm.addApp() }
                        }
                        ListView {
                            id: apps; Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                            model: vm.appCatalog; spacing: 10; ScrollBar.vertical: ScrollBar {}
                            delegate: Rectangle {
                                required property var modelData
                                width: apps.width - 16; height: 160; radius: 9; color: "#102137"
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 10; spacing: 4
                                    RowLayout {
                                        NeonField { id: appName; text: modelData.name; Layout.fillWidth: true; maximumLength: 80; Accessible.name: "App name" }
                                        CheckBox { id: appEnabled; text: "Enabled"; checked: modelData.enabled; Accessible.name: "Enable " + modelData.name }
                                    }
                                    NeonField { id: appAliases; text: modelData.alias_text; placeholderText: "Aliases separated by commas"; Layout.fillWidth: true; Accessible.name: "App aliases" }
                                    Label { text: modelData.kind + ": " + modelData.target; textFormat: Text.PlainText; Layout.fillWidth: true; elide: Text.ElideMiddle; color: "#9bb0c9"; font.pixelSize: 11 }
                                    RowLayout {
                                        NeonButton { text: "Review & save"; Accessible.name: "Review and save " + modelData.name; onClicked: vm.saveApp(modelData.id, appName.text, appAliases.text, appEnabled.checked) }
                                        NeonButton { text: "Remove"; Accessible.name: "Remove " + modelData.name; onClicked: vm.removeApp(modelData.id) }
                                    }
                                }
                            }
                        }
                        RowLayout {
                            NeonField { id: folderName; placeholderText: "Folder name"; Layout.fillWidth: true; maximumLength: 80; Accessible.name: "Registered folder name" }
                            NeonButton { text: "Choose folder…"; Accessible.name: text; onClicked: vm.addFolder(folderName.text) }
                        }
                        RowLayout {
                            NeonField { id: siteName; placeholderText: "Website name"; Layout.preferredWidth: 150; maximumLength: 80; Accessible.name: "Registered website name" }
                            NeonField { id: siteUrl; placeholderText: "https://example.com"; Layout.fillWidth: true; maximumLength: 2048; Accessible.name: "Website address" }
                            NeonButton { text: "Add site"; Accessible.name: text; onClicked: vm.addSite(siteName.text, siteUrl.text) }
                        }
                        ListView {
                            id: locations; Layout.fillWidth: true; Layout.preferredHeight: 100; clip: true
                            model: vm.registeredLocations; ScrollBar.vertical: ScrollBar {}
                            delegate: RowLayout {
                                required property var modelData
                                width: locations.width - 16
                                Label { text: modelData.name + " · " + modelData.detail; Layout.fillWidth: true; elide: Text.ElideMiddle; color: "#9bb0c9"; textFormat: Text.PlainText }
                                NeonButton { text: "Remove"; Accessible.name: "Remove " + modelData.name; onClicked: vm.removeLocation(modelData.id, modelData.kind) }
                            }
                        }
                    }
                    ScrollView {
                        clip: true; contentWidth: availableWidth
                        ColumnLayout {
                            width: parent.width - 22; spacing: 14
                            Label { Layout.fillWidth: true; text: voice.handsFree && voice.isRecording ? "Listening for ‘Autumn, …’. Pause to finish your command." : voice.statusText; wrapMode: Text.WordWrap; color: "#b3d9ea"; Accessible.name: text }
                            Label { text: "Response timing"; color: "#ffc27e" }
                            ComboBox { id: responsePause; model: ["Quick replies", "Natural pauses", "Longer pauses"]; currentIndex: voice.responsePauseMs <= 500 ? 0 : voice.responsePauseMs <= 1000 ? 1 : 2; enabled: vm.canConfigure; Accessible.name: "Pause before responding" }
                            NeonButton { text: "Save response timing"; enabled: vm.canConfigure; onClicked: voice.saveResponseTiming([450,800,1200][responsePause.currentIndex]) }
                            Label { Layout.fillWidth: true; text: "Quick replies responds sooner after you stop speaking. Choose a longer pause if Autumn ends your sentence too early; pause listening before changing this setting."; wrapMode: Text.WordWrap; color: "#9bb0c9" }
                            ProgressBar { Layout.fillWidth: true; from: 0; to: 1; value: voice.inputLevel; Accessible.name: "Microphone level" }
                            Label { Layout.fillWidth: true; text: "Enable voice, then hold the talk button or shortcut while speaking. Toggle mode ends after a pause. Recordings stop at 20 seconds. Audio stays in memory."; wrapMode: Text.WordWrap; color: "#9bb0c9" }
                            Label { Layout.fillWidth: true; text: "Shortcuts may not reach administrator windows. Use Autumn's on-screen talk and Stop controls; Autumn runs with ordinary user access."; wrapMode: Text.WordWrap; color: "#9bb0c9" }
                            RowLayout {
                                NeonButton { text: "Refresh devices"; enabled: !voice.isBusy; onClicked: voice.refreshDevices() }
                                NeonButton { text: "Check speech files"; enabled: !voice.isBusy; onClicked: voice.checkModels() }
                            }
                            Label { Layout.fillWidth: true; text: voice.assetsStatus; wrapMode: Text.WordWrap; color: "#bacce1" }
                            Label { Layout.fillWidth: true; text: vm.modelStatus; wrapMode: Text.WordWrap; color: "#bacce1" }
                            NeonButton { text: "Check local brain"; enabled: vm.canSend; onClicked: vm.checkLocalBrain() }
                            Label { text: "Microphone" }
                            ComboBox { id: inputDevice; Layout.fillWidth: true; model: voice.inputDevices; textRole: "label"; valueRole: "id"; currentIndex: indexOfValue(voice.inputId); enabled: !voice.isBusy; Accessible.name: "Microphone selection" }
                            Label { text: "Speakers" }
                            ComboBox { id: outputDevice; Layout.fillWidth: true; model: voice.outputDevices; textRole: "label"; valueRole: "id"; currentIndex: indexOfValue(voice.outputId); enabled: !voice.isBusy; Accessible.name: "Speaker selection" }
                            RowLayout {
                                Label { text: "Talk mode" }
                                ComboBox { id: talkMode; model: ["hold", "toggle"]; currentIndex: model.indexOf(voice.mode); enabled: !voice.isBusy; Accessible.name: "Talk mode" }
                                Label { text: "English recognition" }
                                ComboBox { id: speechModel; model: ["small.en", "base.en"]; currentIndex: model.indexOf(voice.recognitionModel); enabled: !voice.isBusy; Accessible.name: "English recognition model" }
                            }
                            CheckBox { id: replies; text: "Speak short replies to voice commands"; checked: voice.spokenReplies; enabled: !voice.isBusy }
                            Label { text: "Female voice volume" }
                            Slider { id: voiceVolume; Layout.fillWidth: true; from: 0; to: 1; value: voice.volume; enabled: !voice.isBusy; Accessible.name: "Female voice volume" }
                            Label { text: "Voice speed" }
                            Slider { id: voiceRate; Layout.fillWidth: true; from: 0.6; to: 1.6; value: voice.rate; enabled: !voice.isBusy; Accessible.name: "Voice speed" }
                            NeonButton { text: "Save voice settings"; enabled: vm.canConfigure; onClicked: voice.saveOptions(inputDevice.currentValue || "", outputDevice.currentValue || "", talkMode.currentText, speechModel.currentText, voiceVolume.value, voiceRate.value, replies.checked) }
                            RowLayout {
                                NeonButton { text: "Test microphone (4 seconds)"; enabled: vm.canSend && !voice.isBusy; onClicked: voice.testMicrophone() }
                                NeonButton { text: "Play my test recording"; enabled: voice.hasTestRecording && !voice.isBusy; onClicked: voice.playTestRecording() }
                                NeonButton { text: "Test female voice"; enabled: vm.canSend && !voice.isBusy; onClicked: voice.testVoice() }
                            }
                            Label { text: "Recognized words — edit if needed" }
                            TextArea { id: transcriptEditor; objectName: "transcriptEditor"; Layout.fillWidth: true; text: voice.lastTranscript; wrapMode: TextEdit.Wrap; selectByMouse: true; Accessible.name: "Recognized words" }
                            NeonButton { text: "Send edited as text"; enabled: vm.canSend && transcriptEditor.text.trim().length > 0; onClicked: vm.submit(transcriptEditor.text) }
                            Label { Layout.fillWidth: true; text: "Sending edited text creates a new typed command. A microphone test never runs a command. Stop or microphone-off discards pending voice work."; wrapMode: Text.WordWrap; color: "#9bb0c9" }
                            NeonButton { text: "Choose local speech models folder…"; enabled: vm.canConfigure; onClicked: voice.chooseModels() }
                            Label { Layout.fillWidth: true; text: "First-run checklist: review your apps and folders; check the local brain in Settings; check speech files; select microphone and speakers; run the recording and female voice tests. If capture is silent, allow desktop microphone access in Windows Settings → Privacy & security → Microphone."; wrapMode: Text.WordWrap; color: "#bacce1" }
                            Label { Layout.fillWidth: true; text: "Your 100-utterance speech test is pending. Bluetooth testing is unavailable without a headset. Current accuracy and GPU acceptance checks remain incomplete."; wrapMode: Text.WordWrap; color: "#ffc27e" }
                            RowLayout {
                                NeonButton { text: "Preview diagnostics export"; onClicked: voice.previewDiagnostics() }
                                NeonButton { text: "Export preview…"; enabled: voice.diagnosticsPreview.length > 0; onClicked: voice.exportDiagnostics() }
                            }
                            TextArea { Layout.fillWidth: true; text: voice.diagnosticsPreview; readOnly: true; wrapMode: TextEdit.Wrap; selectByMouse: true; visible: text.length > 0; Accessible.name: "Diagnostics export preview" }
                        }
                    }
                    ScrollView {
                        clip: true; contentWidth: availableWidth
                        ColumnLayout {
                            width: parent.width - 22; spacing: 14
                            Label { Layout.fillWidth: true; text: advanced.statusText; wrapMode: Text.WordWrap; color: "#b3d9ea" }
                            NeonButton { text: "Refresh supported windows"; enabled: vm.canConfigure; onClicked: advanced.refreshTargets() }
                            ComboBox { id: dictationTarget; objectName: "dictationTarget"; Layout.fillWidth: true; model: advanced.targetRows; textRole: "label"; valueRole: "id"; currentIndex: -1; enabled: vm.canConfigure; Accessible.name: "Dictation destination"; onActivated: advanced.chooseTarget(currentValue) }
                            Label { Layout.fillWidth: true; text: "Single line, up to 1,000 characters. Standard Windows Edit/RichEdit fields only; passwords, read-only controls and administrator windows are refused. Clipboard paste is off."; wrapMode: Text.WordWrap; color: "#9bb0c9" }
                            TextArea { id: dictationText; objectName: "dictationText"; Layout.fillWidth: true; Layout.preferredHeight: 150; placeholderText: "Exact text to type…"; wrapMode: TextEdit.Wrap; selectByMouse: true; Accessible.name: "Exact dictation text" }
                            RowLayout {
                                NeonButton { text: "Use recognized words"; enabled: !advanced.pending; onClicked: dictationText.text = voice.lastTranscript }
                                NeonButton { text: "Preview and request confirmation"; enabled: vm.canConfigure && dictationText.text.length > 0; onClicked: advanced.dictate(dictationText.text) }
                            }
                            CheckBox { text: "Use my next hold-to-talk recording as dictation"; checked: advanced.dictationArmed; enabled: vm.canConfigure; onClicked: advanced.armDictation(checked); Accessible.name: text }
                            Label { Layout.fillWidth: true; text: "After requesting: return to the chosen app and focus its edit field. Confirm the overlay with Ctrl+Alt+Y; cancel with Ctrl+Alt+N. Confirmation expires in 30 seconds. Any target change stops typing. Partial or uncertain input is never retried. Wake input cannot dictate."; wrapMode: Text.WordWrap; color: "#bacce1" }
                        }
                    }
                    ScrollView {
                        clip: true; contentWidth: availableWidth
                    ColumnLayout {
                        width: parent.width - 22; enabled: vm.canConfigure; spacing: 10
                        Label { Layout.fillWidth: true; text: advanced.statusText; wrapMode: Text.WordWrap; color: "#b3d9ea" }
                        ListView {
                            Layout.fillWidth: true; Layout.preferredHeight: 140; clip: true; model: advanced.routineRows
                            ScrollBar.vertical: ScrollBar {}
                            delegate: RowLayout {
                                required property var modelData
                                width: ListView.view.width
                                Label { text: modelData.name + " · " + modelData.steps + " steps"; Layout.fillWidth: true; textFormat: Text.PlainText }
                                NeonButton { text: "Edit"; onClicked: { advanced.editRoutine(modelData.id); routineName.text = modelData.name } }
                                NeonButton { text: "Run"; onClicked: advanced.runRoutine(modelData.id) }
                                NeonButton { text: "Delete"; onClicked: advanced.deleteRoutine(modelData.id) }
                            }
                        }
                        RowLayout {
                            NeonField { id: routineName; objectName: "routineName"; Layout.fillWidth: true; placeholderText: "Unique routine name"; maximumLength: 60; Accessible.name: "Routine name" }
                            NeonButton { text: "New routine"; onClicked: { advanced.newRoutine(); routineName.text = "" } }
                        }
                        RowLayout {
                            NeonField { id: routineStep; Layout.fillWidth: true; maximumLength: 2000; placeholderText: "One command, e.g. open Calculator or set volume to 35 percent"; Accessible.name: "Add routine command" }
                            NeonButton { text: "Add step"; onClicked: { advanced.addStep(routineStep.text); routineStep.text = "" } }
                        }
                        ListView {
                            Layout.fillWidth: true; Layout.preferredHeight: 220; clip: true; model: advanced.draftRows
                            delegate: RowLayout {
                                required property var modelData
                                width: ListView.view.width
                                Label { text: (modelData.index+1) + ". " + modelData.label; Layout.fillWidth: true; textFormat: Text.PlainText }
                                NeonButton { text: "Up"; onClicked: advanced.moveStep(modelData.index,-1) }
                                NeonButton { text: "Down"; onClicked: advanced.moveStep(modelData.index,1) }
                                NeonButton { text: "Remove"; onClicked: advanced.removeStep(modelData.index) }
                            }
                        }
                        Label { Layout.fillWidth: true; text: "Review this preview before saving. Up to five steps, run in order and stop on the first failure. Each step inherits the request's permissions. No nesting, dictation or unregistered websites."; wrapMode: Text.WordWrap; color: "#9bb0c9" }
                        NeonButton { text: "Save reviewed routine"; onClicked: advanced.saveRoutine(routineName.text) }
                    }
                    }
                    ScrollView {
                        clip: true; contentWidth: availableWidth
                        ColumnLayout {
                            width: parent.width - 22; spacing: 14
                            Label { Layout.fillWidth: true; text: wake.statusText; wrapMode: Text.WordWrap; color: "#b3d9ea"; Accessible.name: text }
                            Label { Layout.fillWidth: true; text: wake.progress; wrapMode: Text.WordWrap; color: "#bacce1"; Accessible.name: text }
                            Label { Layout.fillWidth: true; text: "Wake is a separate opt-in and always starts off. The pretrained phrase is hey jarvis; the assistant is Autumn. Say the phrase, pause briefly, then speak a command. Calibration never runs commands or saves audio."; wrapMode: Text.WordWrap; color: "#9bb0c9" }
                            RowLayout {
                                NeonButton { objectName: "wakeCheckButton"; text: "Check files / load calibration"; enabled: !wake.busy; onClicked: wake.checkFiles() }
                                NeonButton { text: "Arm calibrated wake"; enabled: wake.calibrated && !wake.busy && vm.canSend; onClicked: wake.arm() }
                                NeonButton { text: "Wake off"; onClicked: wake.disarm() }
                            }
                            Label { Layout.fillWidth: true; text: "Calibration: press Next attempt, wait for Listening, then say hey jarvis once within five seconds. Repeat 50 times. Then start 120 minutes of normal household audio, including speaker media. Keep the laptop on mains power so a five-minute CPU window can be measured. At least 45/50 detections, at most two false wakes, and under 5% CPU are required to arm."; wrapMode: Text.WordWrap; color: "#bacce1" }
                            Flow {
                                Layout.fillWidth: true; spacing: 8
                                NeonButton { text: "Next intentional attempt"; enabled: !wake.busy && vm.canSend; onClicked: wake.positiveTrial() }
                                NeonButton { text: "Start household-audio trial"; enabled: !wake.busy && vm.canSend; onClicked: wake.negativeTrial() }
                                NeonButton { text: "Stop and save measurements"; onClicked: wake.saveCalibration() }
                                NeonButton { text: "Reset this session"; onClicked: wake.resetCalibration() }
                            }
                            Label { text: "Wake threshold (changing it requires matching calibration)"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                            Slider { id: wakeThreshold; Layout.fillWidth: true; from: .1; to: .95; value: .5; enabled: vm.canConfigure; Accessible.name: "Wake detection threshold" }
                            NeonButton { text: "Save threshold"; enabled: vm.canConfigure; onClicked: wake.saveThreshold(wakeThreshold.value) }
                            Label { Layout.fillWidth: true; text: "Stop, microphone-off, lock, sleep and Quit disarm wake. Playback closes the listener before speaking and waits for its acoustic tail before rearming. Wake cannot dictate or open an unregistered URL. Real wake, room audio, battery, Narrator and power-transition acceptance trials are still pending."; wrapMode: Text.WordWrap; color: "#ffc27e" }
                            Label { text: "Desktop and accessibility"; font.pixelSize: 18; color: "#ffc27e" }
                            NeonButton { text: voice.handsFree ? "Pause hands-free listening" : "Listen hands-free"; onClicked: voice.setHandsFree(!voice.handsFree) }
                            Label { Layout.fillWidth: true; text: "Say ‘Autumn, open Spotify’ in one utterance. English speech is processed locally; unaddressed speech is discarded. Listening continues when minimized. Stop pauses it; lock, sleep and Quit close the microphone. This mode is experimental and has separate acceptance checks from calibrated hey-jarvis wake."; wrapMode: Text.WordWrap; color: "#9bb0c9" }
                            CheckBox { text: "Start the local brain when Autumn opens"; checked: vm.modelAutostart; enabled: vm.canConfigure; onClicked: vm.saveLaunchOptions(checked,vm.broadOpenAccess,vm.handsFreeAutostart); Accessible.name: text }
                            CheckBox { text: "Allow discovered installed apps and explicit local paths"; checked: vm.broadOpenAccess; enabled: vm.canConfigure; onClicked: vm.saveLaunchOptions(vm.modelAutostart,checked,vm.handsFreeAutostart); Accessible.name: text }
                            CheckBox { text: "Start hands-free listening when Autumn opens"; checked: vm.handsFreeAutostart; enabled: vm.canConfigure; onClicked: vm.saveLaunchOptions(vm.modelAutostart,vm.broadOpenAccess,checked); Accessible.name: text }
                            CheckBox { id: reducedMotion; text: "Reduced motion"; checked: desktop.reducedMotion; Accessible.name: text }
                            Label { Layout.fillWidth: true; text: "Reduced motion disables orbit, hover and page animations. Controls support Tab, Shift+Tab, Space and Enter; Stop and confirmation shortcuts remain global."; wrapMode: Text.WordWrap; color: "#9bb0c9" }
                            ComboBox { id: closeBehavior; model: ["ask", "tray", "quit"]; currentIndex: model.indexOf(desktop.closeBehavior); Accessible.name: "Window close behavior" }
                            NeonButton { text: "Save desktop settings"; enabled: vm.canConfigure; onClicked: desktop.saveOptions(closeBehavior.currentText,reducedMotion.checked) }
                            Label { Layout.fillWidth: true; text: desktop.statusText; wrapMode: Text.WordWrap; color: "#bacce1" }
                            CheckBox { text: "Start Autumn when I sign in (microphone stays off)"; checked: desktop.startupEnabled; onClicked: desktop.setStartup(checked); Accessible.name: text }
                            NeonButton { text: "Check login startup setting"; onClicked: desktop.checkStartup() }
                            NeonButton { text: "Quit Autumn"; onClicked: desktop.quit() }
                        }
                    }
                    ScrollView {
                        clip: true; contentWidth: availableWidth
                        ColumnLayout {
                            width: parent.width - 22; spacing: 14
                            Label { text: "LOCAL SETUP / PREVIEW"; font.pixelSize: 11; font.letterSpacing: 2; color: "#74deeb" }
                            Label { Layout.fillWidth: true; text: setup.statusText; wrapMode: Text.WordWrap; color: "#dceaff"; Accessible.name: text }
                            Label { Layout.fillWidth: true; text: setup.spaceText; wrapMode: Text.WordWrap; color: "#9bb0c9" }
                            ProgressBar { Layout.fillWidth: true; value: setup.progress; visible: setup.isBusy; Accessible.name: "Setup progress" }
                            Flow {
                                Layout.fillWidth: true; spacing: 8
                                NeonButton { objectName: "setupCheckButton"; text: "Check local files and space"; enabled: !setup.isBusy; onClicked: setup.inspect() }
                                NeonButton { text: "Check local brain"; enabled: vm.canSend; onClicked: vm.checkLocalBrain() }
                                NeonButton { text: "Choose model folder"; enabled: vm.canConfigure; onClicked: voice.chooseModels() }
                                NeonButton { text: "Stop setup"; onClicked: setup.cancel() }
                            }
                            Label { Layout.fillWidth: true; text: vm.modelStatus; wrapMode: Text.WordWrap; color: "#b3d9ea" }
                            Label { Layout.fillWidth: true; text: "The local brain needs the separately installed Ollama runtime and the pinned qwen3:1.7b model. If missing, install Ollama from its official site, explicitly pull that model, then use Check local brain. A different digest will not be loaded. Exact typed commands remain usable."; wrapMode: Text.WordWrap; color: "#9bb0c9" }
                            CheckBox { id: assetConsent; text: "I reviewed the licenses; allow selected downloads"; enabled: !setup.isBusy; Accessible.name: text }
                            Label { Layout.fillWidth: true; text: "Downloads use the internet only after your click. English recognition: Whisper; female voice: Lessac (separate 2013 Blizzard license); wake model: openWakeWord / CC-BY-NC-SA, personal noncommercial use. Exact sizes and SHA-256 checks are pinned. Interrupted downloads can resume; existing unexpected files are preserved. License notices accompany the installer."; wrapMode: Text.WordWrap; color: "#9bb0c9" }
                            Repeater {
                                model: setup.artifacts
                                Rectangle {
                                    required property var modelData
                                    Layout.fillWidth: true; implicitHeight: assetRow.implicitHeight + 24; radius: 12; color: "#0e2034"; border.color: "#233d57"
                                    ColumnLayout {
                                        id: assetRow; anchors.fill: parent; anchors.margins: 12; spacing: 8
                                        Label { text: modelData.label + " · " + modelData.size_mb + " MB"; color: "#dceaff" }
                                        Label { text: modelData.state; color: modelData.state === "Verified" ? "#74deeb" : "#ffc27e" }
                                        RowLayout {
                                            NeonButton { text: "Import verified file"; enabled: !setup.isBusy; onClicked: setup.importAsset(modelData.id) }
                                            NeonButton { text: "Download / resume"; enabled: !setup.isBusy && setup.spaceReady && assetConsent.checked && modelData.state !== "Verified"; onClicked: setup.download(modelData.id,assetConsent.checked) }
                                        }
                                    }
                                }
                            }
                            Label { Layout.fillWidth: true; text: "Finish setup: review your apps and folders, explicitly test the microphone and female voice, and keep wake off until calibration passes. This engineering preview has unresolved acceptance checks; it is not a completed version 1 release."; wrapMode: Text.WordWrap; color: "#ffc27e" }
                            NeonButton { text: "Continue to workspace"; onClicked: window.page = 0 }
                        }
                    }
                }
                Rectangle {
                    Layout.fillWidth: true; implicitHeight: noticeText.implicitHeight + 24; radius: 8; color: "#0e2235"
                    Label { id: noticeText; objectName: "notice"; anchors.fill: parent; anchors.margins: 12; text: voice.handsFree ? vm.captureStatus + " · Say ‘Autumn, …’" : vm.statusMessage; textFormat: Text.PlainText; wrapMode: Text.WordWrap; color: "#b3d9ea"; Accessible.name: "Status: " + text }
                }
            }
        }
    }
}
