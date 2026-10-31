import QtQuick
import QtQuick.Controls

Item {
    id: orb
    property bool motionAllowed: false
    property bool engaged: false
    property bool recording: false
    property real level: 0
    property real phase: 0
    property real hoverX: motionAllowed && pointer.hovered ? (pointer.point.position.x-width/2)*.025 : 0
    property real hoverY: motionAllowed && pointer.hovered ? (pointer.point.position.y-height/2)*.025 : 0
    HoverHandler { id: pointer }
    property color accent: recording ? "#78ecdf" : engaged ? "#6edcf5" : "#779fcd"
    implicitWidth: 168; implicitHeight: 168
    Accessible.role: Accessible.Graphic
    Accessible.name: "Autumn visual presence. Microphone state is shown separately."
    Rectangle { anchors.centerIn: parent; width: parent.width * .96; height: width; radius: width/2; color: orb.accent; opacity: .025 }
    Rectangle { anchors.centerIn: parent; width: parent.width * .79; height: width; radius: width/2; color: orb.accent; opacity: .045 }
    Rectangle { anchors.centerIn: parent; width: parent.width * .60; height: width; radius: width/2; color: "#102b41"; border.color: "#305f7a"; border.width: 1 }
    Rectangle {
        anchors.centerIn: parent; width: parent.width * (.43 + (orb.recording ? Math.min(.12,orb.level*.12) : 0)); height: width; radius: width/2
        gradient: Gradient { GradientStop { position: 0; color: "#21475e" } GradientStop { position: 1; color: "#0b1a2d" } }
        border.color: orb.accent; border.width: 1
        Behavior on width { NumberAnimation { duration: orb.motionAllowed ? 100 : 0 } }
        transform: Translate { x: orb.hoverX; y: orb.hoverY }
        Text { anchors.centerIn: parent; text: "A"; color: "#c7f6fc"; font.family: "Segoe UI"; font.pixelSize: parent.width*.44; font.weight: Font.Light; font.letterSpacing: 2 }
    }
    Canvas {
        id: circuit; anchors.fill: parent
        onPaint: {
            var ctx = getContext("2d"); ctx.clearRect(0,0,width,height)
            var x=width/2, y=height/2, r=Math.min(width,height)*.435
            ctx.lineWidth=1; ctx.strokeStyle="#254258"
            ctx.beginPath(); ctx.arc(x,y,r,0,Math.PI*2); ctx.stroke()
            ctx.strokeStyle=orb.accent; ctx.lineWidth=2
            var a=orb.phase*Math.PI/180
            for(var i=0;i<3;i++) { ctx.beginPath(); ctx.arc(x,y,r,a+i*2.094,a+i*2.094+.68); ctx.stroke() }
            ctx.strokeStyle="#c89357"; ctx.lineWidth=1
            ctx.beginPath(); ctx.arc(x,y,r*.83,-a*.6,-a*.6+1.12); ctx.stroke()
            for(var j=0;j<24;j++) {
                var q=j*Math.PI/12, l=j%3===0?5:2
                ctx.strokeStyle=j%3===0?"#6488a7":"#29465e"; ctx.beginPath()
                ctx.moveTo(x+Math.cos(q)*(r+5),y+Math.sin(q)*(r+5)); ctx.lineTo(x+Math.cos(q)*(r+5+l),y+Math.sin(q)*(r+5+l)); ctx.stroke()
            }
        }
    }
    Timer { interval: 50; repeat: true; running: orb.motionAllowed && orb.visible; onTriggered: { orb.phase=(orb.phase+(orb.engaged?2.2:.55))%360; circuit.requestPaint() } }
    onAccentChanged: { if (circuit) circuit.requestPaint() }
    onWidthChanged: { if (circuit) circuit.requestPaint() }
    onHeightChanged: { if (circuit) circuit.requestPaint() }
    Component.onCompleted: circuit.requestPaint()
}
