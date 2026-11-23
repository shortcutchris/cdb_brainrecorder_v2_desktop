#!/usr/bin/env python3
"""Render the cdbPiOS boot UI from our existing icon (development tool only)."""
import os
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QTransform
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]


def render():
    app = QApplication.instance() or QApplication([])
    output = ROOT / 'deploy/boot-brand/assets'
    output.mkdir(parents=True, exist_ok=True)
    icon = QImage(str(ROOT / 'icon.png'))
    if icon.isNull():
        raise ValueError('Missing original CDB icon')
    for mode, caption in [('startup', 'cdbPiOS startet …'),
                          ('shutdown', 'cdbPiOS wird heruntergefahren …')]:
        canvas = QImage(1280, 720, QImage.Format.Format_RGB32)
        canvas.fill(QColor('#000e22'))
        painter = QPainter(canvas)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawImage(QRectF(420, 12, 440, 440), icon)
        font = QFont('Arial'); font.setPixelSize(48); font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font); painter.setPen(QColor('#ffffff'))
        painter.drawText(QRectF(0, 425, 1280, 70), Qt.AlignmentFlag.AlignCenter, 'cdbPiOS')
        font.setPixelSize(24); font.setWeight(QFont.Weight.Normal)
        painter.setFont(font); painter.setPen(QColor('#b8c6d7'))
        painter.drawText(QRectF(0, 493, 1280, 40), Qt.AlignmentFlag.AlignCenter, caption)
        painter.end()
        canvas.save(str(output / f'{mode}-landscape.png'))
        # Wayland's transform 90 is counter-clockwise; no desktop/KMS changes.
        for rotation in (90, 270):
            canvas.transformed(QTransform().rotate(-rotation)).save(str(output / f'{mode}-portrait{rotation}.png'))
    dot = QImage(14, 14, QImage.Format.Format_ARGB32); dot.fill(Qt.GlobalColor.transparent)
    painter = QPainter(dot); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(QColor('#dda247'))
    painter.drawEllipse(QRectF(1, 1, 12, 12)); painter.end()
    dot.save(str(output / 'dot.png'))
    print(output)


if __name__ == '__main__':
    render()
