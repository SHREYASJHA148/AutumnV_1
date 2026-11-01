"""Draw Autumn's native vector mark into a multi-resolution Windows icon."""
import struct
import sys
from pathlib import Path

from PySide6.QtCore import QBuffer, QIODevice, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter, QPen


def main():
    app=QGuiApplication(sys.argv[:1])
    assert app
    frames=[]
    for size in (16,24,32,48,64,128,256):
        image=QImage(size,size,QImage.Format_ARGB32)
        image.fill(Qt.transparent)
        painter=QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor('#0b192c'))
        painter.setPen(QPen(QColor('#6adeec'),max(1,size*.025)))
        margin=size*.07
        painter.drawEllipse(margin,margin,size-2*margin,size-2*margin)
        painter.setPen(QColor('#ffc27e'))
        font=QFont('Segoe UI')
        font.setPixelSize(round(size*.65))
        font.setWeight(QFont.DemiBold)
        painter.setFont(font)
        painter.drawText(image.rect(),Qt.AlignCenter,'A')
        painter.end()
        buffer=QBuffer()
        buffer.open(QIODevice.WriteOnly)
        assert image.save(buffer,'PNG')
        frames.append((size,bytes(buffer.data())))
    header=struct.pack('<HHH',0,1,len(frames))
    offset=6+16*len(frames)
    directory=b''
    for size,data in frames:
        directory+=struct.pack('<BBBBHHII',size%256,size%256,0,0,1,32,len(data),offset)
        offset+=len(data)
    target=Path(__file__).resolve().parents[1]/'src/autumn/ui/Autumn.ico'
    target.write_bytes(header+directory+b''.join(data for _,data in frames))
    print('Autumn multi-resolution icon generated.')


if __name__=='__main__':
    main()
