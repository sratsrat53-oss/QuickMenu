"""QuickMenu — меню действий по Alt+Q с иконкой в трее."""

from __future__ import annotations

import ctypes
import queue
import sys
import threading
import traceback
from ctypes import wintypes

import customtkinter as ctk
import pystray
from PIL import Image, ImageDraw

import actions
from popup_ui import PopupMenu

HOTKEY_ID = 1
MOD_ALT = 0x0001
VK_Q = 0x51
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

_u32 = ctypes.WinDLL("user32", use_last_error=True)
_u32.RegisterHotKey.argtypes = (wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT)
_u32.RegisterHotKey.restype = wintypes.BOOL
_u32.UnregisterHotKey.argtypes = (wintypes.HWND, ctypes.c_int)
_u32.GetMessageW.argtypes = (ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT)
_u32.GetMessageW.restype = ctypes.c_int
_u32.PostThreadMessageW.argtypes = (wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)


class HotkeyListener(threading.Thread):
    """Alt+Q через RegisterHotKey: не зависит от раскладки клавиатуры."""

    def __init__(self, callback) -> None:
        super().__init__(name="QuickMenuHotkey", daemon=True)
        self.callback = callback
        self.thread_id = 0
        self.registered = False
        self.ready = threading.Event()

    def run(self) -> None:
        self.thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        self.registered = bool(_u32.RegisterHotKey(None, HOTKEY_ID, MOD_ALT, VK_Q))
        self.ready.set()
        if not self.registered:
            return
        message = wintypes.MSG()
        while _u32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
            if message.message == WM_HOTKEY and message.wParam == HOTKEY_ID:
                try:
                    self.callback()
                except Exception:
                    traceback.print_exc()
        _u32.UnregisterHotKey(None, HOTKEY_ID)

    def stop(self) -> None:
        if self.thread_id:
            _u32.PostThreadMessageW(self.thread_id, WM_QUIT, 0, 0)


def _tray_image(size: int = 64) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((2, 2, size - 2, size - 2), radius=14, fill=(32, 38, 54, 255))
    draw.polygon(
        [(38, 8), (18, 36), (30, 36), (25, 56), (46, 26), (33, 26)],
        fill=(120, 160, 255, 255),
    )
    return image


class QuickMenuApp:
    def __init__(self) -> None:
        ctk.set_appearance_mode("dark")
        self.root = ctk.CTk()
        self.root.withdraw()
        self.root.title("QuickMenu")
        self.queue: queue.Queue = queue.Queue()
        self.popup: PopupMenu | None = None
        self.tray: pystray.Icon | None = None
        self._busy = False
        self.hotkey = HotkeyListener(self._on_hotkey)
        self.hotkey.start()
        self.hotkey.ready.wait(2.0)
        if not self.hotkey.registered:
            print("Не удалось зарегистрировать Alt+Q — возможно, её заняла другая программа")
        self._start_tray()
        self.root.after(40, self._pump)

    def _start_tray(self) -> None:
        menu = pystray.Menu(
            pystray.MenuItem("Открыть меню  (Alt+Q)", self._on_hotkey, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Выход", self._tray_quit),
        )
        self.tray = pystray.Icon("QuickMenu", _tray_image(), "QuickMenu — Alt+Q", menu)
        threading.Thread(target=self.tray.run, daemon=True).start()

    # ------------------------------------------------------------------ hotkey

    def _on_hotkey(self, _icon=None, _item=None) -> None:
        """Вызывается из потока hotkey / pystray, не из Tk."""
        if self._busy or self.popup is not None:
            return
        self._busy = True
        try:
            hwnd = actions.get_foreground_window()
            text, previous = actions.capture_selection()
            anchor = actions.get_cursor_pos()
            self.queue.put(lambda: self._show(text, previous, hwnd, anchor))
        except Exception:
            traceback.print_exc()
        finally:
            self._busy = False

    def _show(self, text: str, previous, hwnd: int, anchor) -> None:
        if self.popup is not None:
            return
        try:
            self.popup = PopupMenu(self.root, text, previous, hwnd, anchor, self._popup_closed)
            self.popup.show()
        except Exception:
            traceback.print_exc()
            self.popup = None

    def _popup_closed(self) -> None:
        self.popup = None

    # ------------------------------------------------------------------ pump / shutdown

    def _pump(self) -> None:
        while True:
            try:
                task = self.queue.get_nowait()
            except queue.Empty:
                break
            try:
                task()
            except Exception:
                traceback.print_exc()
        self.root.after(30, self._pump)

    def _tray_quit(self, _icon=None, _item=None) -> None:
        self.queue.put(self._shutdown)

    def _shutdown(self) -> None:
        if self.popup is not None:
            self.popup.close()
        self.hotkey.stop()
        if self.tray is not None:
            try:
                self.tray.stop()
            except Exception:
                pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def run(self) -> None:
        self.root.mainloop()


def main() -> int:
    app = QuickMenuApp()
    try:
        app.run()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
