"""DPI-aware GDI capture to PNG using Windows APIs and standard-library encoding."""
from __future__ import annotations

import ctypes
import struct
import zlib
from ctypes import wintypes
from pathlib import Path
from uuid import uuid4

from autumn.actions.catalog import no_reparse


class BitmapInfoHeader(ctypes.Structure):
    _fields_ = [("size", wintypes.DWORD), ("width", wintypes.LONG), ("height", wintypes.LONG),
                ("planes", wintypes.WORD), ("bits", wintypes.WORD), ("compression", wintypes.DWORD),
                ("image_size", wintypes.DWORD), ("xppm", wintypes.LONG), ("yppm", wintypes.LONG),
                ("used", wintypes.DWORD), ("important", wintypes.DWORD)]


def initialize_dpi() -> bool:
    user = ctypes.WinDLL("user32", use_last_error=True)
    user.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
    user.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    user.GetThreadDpiAwarenessContext.restype = ctypes.c_void_p
    user.GetAwarenessFromDpiAwarenessContext.argtypes = [ctypes.c_void_p]
    return user.GetAwarenessFromDpiAwarenessContext(user.GetThreadDpiAwarenessContext()) == 2


def screenshot(folder: Path, monitor: str, checkpoint, *, bounds=None, source_window=None) -> dict:
    user, gdi = ctypes.WinDLL("user32", use_last_error=True), ctypes.WinDLL("gdi32", use_last_error=True)
    if not initialize_dpi():
        raise OSError("Per-monitor DPI awareness unavailable")
    user.GetDC.argtypes = [wintypes.HWND]
    user.GetDC.restype = wintypes.HDC
    user.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    gdi.CreateCompatibleDC.argtypes = [wintypes.HDC]
    gdi.CreateCompatibleDC.restype = wintypes.HDC
    gdi.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
    gdi.CreateCompatibleBitmap.restype = wintypes.HBITMAP
    gdi.SelectObject.argtypes = [wintypes.HDC, wintypes.HANDLE]
    gdi.SelectObject.restype = wintypes.HANDLE
    gdi.BitBlt.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                          wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.DWORD]
    gdi.GetDIBits.argtypes = [wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT,
                             ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT]
    gdi.DeleteObject.argtypes = [wintypes.HANDLE]
    gdi.DeleteDC.argtypes = [wintypes.HDC]
    if bounds is None:
        bounds = (0, 0, user.GetSystemMetrics(0), user.GetSystemMetrics(1)) if monitor == "primary" else (
            user.GetSystemMetrics(76), user.GetSystemMetrics(77), user.GetSystemMetrics(78), user.GetSystemMetrics(79))
    x, y, width, height = bounds
    if width <= 0 or height <= 0 or width * height > 32_000_000:
        raise ValueError("Unsupported capture size")
    if not checkpoint():
        raise InterruptedError()
    screen = user.GetDC(None)
    memory = gdi.CreateCompatibleDC(screen)
    bitmap = gdi.CreateCompatibleBitmap(screen, width, height)
    if not screen or not memory or not bitmap:
        if bitmap:
            gdi.DeleteObject(bitmap)
        if memory:
            gdi.DeleteDC(memory)
        if screen:
            user.ReleaseDC(None, screen)
        raise OSError("Capture unavailable")
    previous = gdi.SelectObject(memory, bitmap)
    try:
        if source_window is not None:
            user.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
            copied = user.PrintWindow(source_window, memory, 1)
        else:
            copied = gdi.BitBlt(memory, 0, 0, width, height, screen, x, y, 0x40CC0020)
        if not copied:
            raise OSError("Capture failed")
        gdi.SelectObject(memory, previous)
        info = BitmapInfoHeader(ctypes.sizeof(BitmapInfoHeader), width, -height, 1, 32, 0, width * height * 4, 0, 0, 0, 0)
        pixels = ctypes.create_string_buffer(width * height * 4)
        if gdi.GetDIBits(memory, bitmap, 0, height, pixels, ctypes.byref(info), 0) != height:
            raise OSError("Pixel read failed")
    finally:
        gdi.SelectObject(memory, previous)
        gdi.DeleteObject(bitmap)
        gdi.DeleteDC(memory)
        user.ReleaseDC(None, screen)
    compressor = zlib.compressobj(3)
    compressed = bytearray()
    raw = pixels.raw
    for row in range(height):
        if row % 32 == 0 and not checkpoint():
            raise InterruptedError()
        bgra = raw[row * width * 4:(row + 1) * width * 4]
        rgb = bytearray(width * 3)
        rgb[0::3], rgb[1::3], rgb[2::3] = bgra[2::4], bgra[1::4], bgra[0::4]
        compressed.extend(compressor.compress(b"\0" + rgb))
    compressed.extend(compressor.flush())

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", bytes(compressed)) + chunk(b"IEND", b"")
    if not checkpoint():
        raise InterruptedError()
    folder.mkdir(parents=True, exist_ok=True)
    folder = no_reparse(folder)
    path = folder / f"Autumn-{uuid4().hex}.png"
    with path.open("xb") as output:
        output.write(png)
    if not path.is_file() or path.stat().st_size < 33:
        raise OSError("Image save failed")
    return {"id": uuid4().hex, "name": path.name, "path": str(path), "width": width, "height": height, "kind": "screenshot"}
