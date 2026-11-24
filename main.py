"""QuickMenu — Alt+Q action menu with a tray icon."""
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
from popup_ui import PopupMenu, SettingsWindow, UI_STRINGS

HOTKEY_ID = 1
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
WM_APP = 0x8000
WM_HOTKEY_CHANGE = WM_APP + 1
PM_NOREMOVE = 0x0000

_u32 = ctypes.WinDLL("user32", use_last_error=True)
_u32.RegisterHotKey.argtypes = (wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT)
_u32.RegisterHotKey.restype = wintypes.BOOL
_u32.UnregisterHotKey.argtypes = (wintypes.HWND, ctypes.c_int)
_u32.GetMessageW.argtypes = (ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT)
_u32.GetMessageW.restype = ctypes.c_int
_u32.PeekMessageW.argtypes = (
    ctypes.POINTER(wintypes.MSG),
    wintypes.HWND,
    wintypes.UINT,
    wintypes.UINT,
    wintypes.UINT,
)
_u32.PostThreadMessageW.argtypes = (wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)


class HotkeyListener(threading.Thread):
    """Global hotkey via RegisterHotKey: independent of the active keyboard layout.

    Registration happens on this thread, so ``set_combo`` / ``release`` are
    marshalled to it and the new combination is live without a restart.
    """

    def __init__(self, callback, combo: str) -> None:
        super().__init__(name="QuickMenuHotkey", daemon=True)
        self.callback = callback
        self.combo = combo
        self.thread_id = 0
        self.registered = False
        self.ready = threading.Event()
        self._requests: queue.Queue = queue.Queue()

    def run(self) -> None:
        self.thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        message = wintypes.MSG()
        _u32.PeekMessageW(ctypes.byref(message), None, 0, 0, PM_NOREMOVE)
        parsed = actions.parse_hotkey(self.combo)
        if parsed:
            self.registered = self._register(*parsed)
        self.ready.set()
        while _u32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
            if message.message == WM_HOTKEY and message.wParam == HOTKEY_ID:
                try:
                    self.callback()
                except Exception:
                    traceback.print_exc()
            elif message.message == WM_HOTKEY_CHANGE:
                self._process_requests()
        _u32.UnregisterHotKey(None, HOTKEY_ID)

    @staticmethod
    def _register(mods: int, vk: int) -> bool:
        return bool(_u32.RegisterHotKey(None, HOTKEY_ID, mods | actions.MOD_NOREPEAT, vk))

    def _process_requests(self) -> None:
        while True:
            try:
                mods, vk, event, result = self._requests.get_nowait()
            except queue.Empty:
                return
            _u32.UnregisterHotKey(None, HOTKEY_ID)
            self.registered = bool(mods and vk and self._register(mods, vk))
            result["ok"] = self.registered
            event.set()

    def _request(self, mods: int, vk: int, timeout: float = 2.0) -> bool:
        if not self.thread_id or not self.is_alive():
            return False
        event = threading.Event()
        result: dict[str, bool] = {}
        self._requests.put((mods, vk, event, result))
        if not _u32.PostThreadMessageW(self.thread_id, WM_HOTKEY_CHANGE, 0, 0):
            return False
        event.wait(timeout)
        return bool(result.get("ok"))

    def set_combo(self, combo: str) -> bool:
        parsed = actions.parse_hotkey(combo)
        if not parsed:
            return False
        ok = self._request(*parsed)
        if ok:
            self.combo = combo
        return ok

    def release(self) -> None:
        self._request(0, 0, timeout=1.0)

    def stop(self) -> None:
        if self.thread_id:
            _u32.PostThreadMessageW(self.thread_id, WM_QUIT, 0, 0)


ERROR_ALREADY_EXISTS = 183
_MUTEX_NAME = "Local\\QuickMenu_SingleInstance"
_k32 = ctypes.WinDLL("kernel32", use_last_error=True)
_k32.CreateMutexW.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
_k32.CreateMutexW.restype = wintypes.HANDLE
_instance_mutex = None  # kept alive for the whole process lifetime


def _acquire_single_instance() -> bool:
    """True if this is the only running copy; False if another one already holds the mutex."""
    global _instance_mutex
    ctypes.set_last_error(0)
    handle = _k32.CreateMutexW(None, False, _MUTEX_NAME)
    if not handle:
        return True  # could not create the mutex — do not block startup
    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        _k32.CloseHandle(handle)
        return False
    _instance_mutex = handle
    return True


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
        self.settings: SettingsWindow | None = None
        self.tray: pystray.Icon | None = None
        self._busy = False
        # Last menu session: (text, previous_clipboard, target_hwnd, anchor).
        # Kept so that "Done" in settings can bring exactly the same menu back.
        self._menu_context: tuple | None = None
        self.hotkey = HotkeyListener(self._on_hotkey, actions.get_hotkey())
        self.hotkey.start()
        self.hotkey.ready.wait(2.0)
        if not self.hotkey.registered:
            print(f"Could not register {actions.get_hotkey()} — another program may already use it")
        self._start_tray()
        self.root.after(40, self._pump)

    def _tray_label(self, key: str) -> str:
        strings = UI_STRINGS[actions.get_ui_lang()]
        if key == "open":
            return f'{strings["tray_open"]}  ({actions.get_hotkey()})'
        return strings[key]

    def _start_tray(self) -> None:
        menu = pystray.Menu(
            pystray.MenuItem(lambda _item: self._tray_label("open"), self._on_hotkey, default=True),
            pystray.MenuItem(lambda _item: self._tray_label("tray_settings"), self._open_settings),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(lambda _item: self._tray_label("tray_exit"), self._tray_quit),
        )
        self.tray = pystray.Icon("QuickMenu", _tray_image(), "QuickMenu", menu)
        threading.Thread(target=self.tray.run, kwargs={"setup": self._on_tray_ready}, daemon=True).start()

    def _on_tray_ready(self, icon: pystray.Icon) -> None:
        """Runs in pystray's thread once the icon exists: show it and announce startup."""
        icon.visible = True
        strings = UI_STRINGS[actions.get_ui_lang()]
        try:
            icon.notify(strings["started"].format(hotkey=actions.get_hotkey()), "QuickMenu")
        except Exception:
            pass

    def _refresh_tray(self) -> None:
        if self.tray is None:
            return
        try:
            self.tray.update_menu()
        except Exception:
            pass

    # ------------------------------------------------------------------ hotkey
    def _on_hotkey(self, _icon=None, _item=None) -> None:
        """Called from the hotkey / pystray thread, not from Tk."""
        if self._busy or self.popup is not None or self.settings is not None:
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

    def _show(self, text: str, previous, hwnd: int, anchor, origin_rect=None) -> None:
        if self.popup is not None:
            return
        self._menu_context = (text, previous, hwnd, anchor)
        try:
            self.popup = PopupMenu(
                self.root,
                text,
                previous,
                hwnd,
                anchor,
                self._popup_closed,
                on_settings=self._open_settings,
                origin_rect=origin_rect,
            )
            self.popup.show()
        except Exception:
            traceback.print_exc()
            self.popup = None

    def _popup_closed(self) -> None:
        self.popup = None

    # ------------------------------------------------------------------ settings
    def _open_settings(self, origin_rect=None, _item=None) -> None:
        rect = origin_rect if isinstance(origin_rect, tuple) else None
        if self.popup is None:
            # Opened from the tray: there is no captured selection, so "Done"
            # will bring up an empty menu (the search line still works).
            self._menu_context = (
                "",
                None,
                actions.get_foreground_window(),
                actions.get_cursor_pos(),
            )
        self.queue.put(lambda: self._show_settings(rect))

    def _show_settings(self, origin_rect=None) -> None:
        if self.settings is not None:
            self.settings.focus()
            return
        try:
            self.settings = SettingsWindow(
                self.root,
                self.hotkey,
                on_close=self._settings_closed,
                on_change=self._refresh_tray,
                on_quit=self._shutdown,
                on_done=self._back_to_menu,
                origin_rect=origin_rect,
            )
            self.settings.show()
        except Exception:
            traceback.print_exc()
            self.settings = None

    def _settings_closed(self) -> None:
        self.settings = None
        self._refresh_tray()

    def _back_to_menu(self, origin_rect=None) -> None:
        """'Done' in settings: show the main menu again, where the settings window was."""
        if self.popup is not None or self.settings is not None:
            return
        context = self._menu_context or ("", None, 0, actions.get_cursor_pos())
        text, previous, hwnd, anchor = context
        self._show(text, previous, hwnd, anchor, origin_rect=origin_rect)

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
            self.popup.close(animate=False)
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
    if not _acquire_single_instance():
        print("QuickMenu is already running")
        return 0
    app = QuickMenuApp()
    try:
        app.run()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())