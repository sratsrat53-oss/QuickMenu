"""QuickMenu actions: clipboard, Ctrl+C/Ctrl+V, translation, layout, calculator, search."""

from __future__ import annotations

import ast
import ctypes
import json
import operator
import os
import re
import sys
import time
import traceback
import webbrowser
from ctypes import wintypes
from urllib.parse import quote

BOOSTY_URL = "https://boosty.to/stratapak/donate"


TARGET_LANGUAGES: dict[str, str] = {
    "EN": "en",
    "RU": "ru",
    "ES": "es",
    "DE": "de",
    "FR": "fr",
    "JA": "ja",
    "ZH": "zh-CN",
    "KO": "ko",
    "TR": "tr",
    "PL": "pl",
    "UK": "uk",
}

UI_LANGUAGES: dict[str, str] = {"EN": "en", "RU": "ru"}

# How the Translate button gets its text: from the selection or from a screenshot.
TRANSLATE_MODES = ("text", "photo")

DEFAULT_WINDOW_WIDTH = 520
MIN_WINDOW_WIDTH = 380
MAX_WINDOW_WIDTH = 900

DEFAULT_PREVIEW_HEIGHT = 74
MIN_PREVIEW_HEIGHT = 44
MAX_PREVIEW_HEIGHT = 360

DEFAULT_HOTKEY = "Alt+Q"

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

MODIFIER_ORDER = (
    ("Ctrl", MOD_CONTROL),
    ("Alt", MOD_ALT),
    ("Shift", MOD_SHIFT),
    ("Win", MOD_WIN),
)

_MODIFIER_FLAGS = {
    "ctrl": MOD_CONTROL,
    "control": MOD_CONTROL,
    "alt": MOD_ALT,
    "shift": MOD_SHIFT,
    "win": MOD_WIN,
    "super": MOD_WIN,
}

_VK_NAMES = {
    0x08: "Backspace",
    0x09: "Tab",
    0x0D: "Enter",
    0x13: "Pause",
    0x1B: "Esc",
    0x20: "Space",
    0x21: "PageUp",
    0x22: "PageDown",
    0x23: "End",
    0x24: "Home",
    0x25: "Left",
    0x26: "Up",
    0x27: "Right",
    0x28: "Down",
    0x2C: "PrintScreen",
    0x2D: "Insert",
    0x2E: "Delete",
}
for _index in range(24):
    _VK_NAMES[0x70 + _index] = f"F{_index + 1}"
for _index in range(10):
    _VK_NAMES[0x60 + _index] = f"Num{_index}"

_VK_FROM_NAME = {name.lower(): vk for vk, name in _VK_NAMES.items()}
_VK_FROM_NAME["escape"] = 0x1B
_VK_FROM_NAME["return"] = 0x0D

_u32 = ctypes.WinDLL("user32", use_last_error=True)
_k32 = ctypes.WinDLL("kernel32", use_last_error=True)

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
SW_RESTORE = 9
VK_LBUTTON = 0x01
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12
VK_LWIN = 0x5B
VK_RWIN = 0x5C
KEYEVENTF_KEYUP = 0x0002
INPUT_KEYBOARD = 1

MONITOR_DEFAULTTONEAREST = 2


class _MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
    ]


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class _HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("ki", _KEYBDINPUT), ("mi", _MOUSEINPUT), ("hi", _HARDWAREINPUT)]


class _INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("union", _INPUTUNION)]


_u32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(_INPUT), ctypes.c_int)
_u32.MonitorFromPoint.argtypes = (wintypes.POINT, wintypes.DWORD)
_u32.MonitorFromPoint.restype = wintypes.HMONITOR
_u32.GetMonitorInfoW.argtypes = (wintypes.HMONITOR, ctypes.POINTER(_MONITORINFO))
_u32.GetMonitorInfoW.restype = wintypes.BOOL

_u32.GetClipboardData.restype = wintypes.HANDLE
_u32.SetClipboardData.argtypes = (wintypes.UINT, wintypes.HANDLE)
_u32.SetClipboardData.restype = wintypes.HANDLE
_u32.OpenClipboard.argtypes = (wintypes.HWND,)
_u32.GetForegroundWindow.restype = wintypes.HWND
_u32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
_u32.GetWindowThreadProcessId.restype = wintypes.DWORD
_u32.AttachThreadInput.argtypes = (wintypes.DWORD, wintypes.DWORD, wintypes.BOOL)
_u32.SetForegroundWindow.argtypes = (wintypes.HWND,)
_u32.BringWindowToTop.argtypes = (wintypes.HWND,)
_u32.ShowWindow.argtypes = (wintypes.HWND, ctypes.c_int)
_u32.IsIconic.argtypes = (wintypes.HWND,)
_u32.GetCursorPos.argtypes = (ctypes.POINTER(wintypes.POINT),)
_k32.GlobalAlloc.argtypes = (wintypes.UINT, ctypes.c_size_t)
_k32.GlobalAlloc.restype = wintypes.HANDLE
_k32.GlobalLock.argtypes = (wintypes.HANDLE,)
_k32.GlobalLock.restype = ctypes.c_void_p
_k32.GlobalUnlock.argtypes = (wintypes.HANDLE,)
_k32.GlobalFree.argtypes = (wintypes.HANDLE,)
_k32.GetCurrentThreadId.restype = wintypes.DWORD

_PROBE = "\u0002quickmenu-probe\u0002"
_CYRILLIC = re.compile(r"[А-Яа-яЁё]")


# --------------------------------------------------------------------------- config

def _config_path() -> str:
    base = (
        os.path.dirname(sys.executable)
        if getattr(sys, "frozen", False)
        else os.path.dirname(os.path.abspath(__file__))
    )
    return os.path.join(base, "quickmenu_config.json")


def _read_config() -> dict:
    try:
        with open(_config_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_config(data: dict) -> None:
    try:
        with open(_config_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        traceback.print_exc()


def get_target_lang() -> str:
    lang = _read_config().get("target_lang", "EN")
    return lang if lang in TARGET_LANGUAGES else "EN"


def set_target_lang(lang_code: str) -> None:
    if lang_code not in TARGET_LANGUAGES:
        return
    data = _read_config()
    data["target_lang"] = lang_code
    _write_config(data)


def get_translate_mode() -> str:
    mode = _read_config().get("translate_mode", "text")
    return mode if mode in TRANSLATE_MODES else "text"


def set_translate_mode(mode: str) -> None:
    if mode not in TRANSLATE_MODES:
        return
    data = _read_config()
    data["translate_mode"] = mode
    _write_config(data)


def get_ui_lang() -> str:
    lang = _read_config().get("ui_lang", "EN")
    return lang if lang in UI_LANGUAGES else "EN"


def set_ui_lang(lang_code: str) -> None:
    if lang_code not in UI_LANGUAGES:
        return
    data = _read_config()
    data["ui_lang"] = lang_code
    _write_config(data)


def get_window_width() -> int:
    """Popup width saved by dragging its right edge."""
    try:
        width = int(_read_config().get("window_width", DEFAULT_WINDOW_WIDTH))
    except (TypeError, ValueError):
        return DEFAULT_WINDOW_WIDTH
    return max(MIN_WINDOW_WIDTH, min(MAX_WINDOW_WIDTH, width))


def set_window_width(width) -> None:
    try:
        value = int(width)
    except (TypeError, ValueError):
        return
    data = _read_config()
    data["window_width"] = max(MIN_WINDOW_WIDTH, min(MAX_WINDOW_WIDTH, value))
    _write_config(data)


def get_preview_height() -> int:
    """Height of the preview box, changed by dragging the menu's bottom edge."""
    try:
        height = int(_read_config().get("preview_height", DEFAULT_PREVIEW_HEIGHT))
    except (TypeError, ValueError):
        return DEFAULT_PREVIEW_HEIGHT
    return max(MIN_PREVIEW_HEIGHT, min(MAX_PREVIEW_HEIGHT, height))


def set_preview_height(height) -> None:
    try:
        value = int(height)
    except (TypeError, ValueError):
        return
    data = _read_config()
    data["preview_height"] = max(MIN_PREVIEW_HEIGHT, min(MAX_PREVIEW_HEIGHT, value))
    _write_config(data)


def get_theme() -> str:
    theme = _read_config().get("theme", "Night")
    return theme if isinstance(theme, str) else "Night"


def set_theme(name: str) -> None:
    data = _read_config()
    data["theme"] = str(name)
    _write_config(data)


def vk_name(vk: int) -> str:
    if 0x41 <= vk <= 0x5A or 0x30 <= vk <= 0x39:
        return chr(vk)
    return _VK_NAMES.get(vk, f"0x{vk:02X}")


def vk_from_name(name: str) -> int | None:
    key = str(name or "").strip()
    if len(key) == 1:
        char = key.upper()
        if "A" <= char <= "Z" or "0" <= char <= "9":
            return ord(char)
    return _VK_FROM_NAME.get(key.lower())


def format_hotkey(mods: int, vk: int) -> str:
    parts = [name for name, flag in MODIFIER_ORDER if mods & flag]
    parts.append(vk_name(vk))
    return "+".join(parts)


def parse_hotkey(combo: str) -> tuple[int, int] | None:
    """'Ctrl+Shift+Q' -> (modifier flags, virtual-key code); None if unusable."""
    parts = [part.strip() for part in str(combo or "").split("+") if part.strip()]
    if len(parts) < 2:
        return None
    mods = 0
    for part in parts[:-1]:
        flag = _MODIFIER_FLAGS.get(part.lower())
        if flag is None:
            return None
        mods |= flag
    key = vk_from_name(parts[-1])
    if not mods or key is None:
        return None
    return mods, key


def get_hotkey() -> str:
    parsed = parse_hotkey(_read_config().get("hotkey", DEFAULT_HOTKEY))
    return format_hotkey(*parsed) if parsed else DEFAULT_HOTKEY


def set_hotkey(combo: str) -> None:
    parsed = parse_hotkey(combo)
    if not parsed:
        return
    data = _read_config()
    data["hotkey"] = format_hotkey(*parsed)
    _write_config(data)


def held_modifiers() -> int:
    """Modifiers physically held right now (Win included, which Tk does not report)."""
    mods = 0
    if _u32.GetAsyncKeyState(VK_MENU) & 0x8000:
        mods |= MOD_ALT
    if _u32.GetAsyncKeyState(VK_CONTROL) & 0x8000:
        mods |= MOD_CONTROL
    if _u32.GetAsyncKeyState(VK_SHIFT) & 0x8000:
        mods |= MOD_SHIFT
    if (_u32.GetAsyncKeyState(VK_LWIN) | _u32.GetAsyncKeyState(VK_RWIN)) & 0x8000:
        mods |= MOD_WIN
    return mods


# --------------------------------------------------------------------------- input

def _key_event(vk: int, up: bool = False) -> _INPUT:
    event = _INPUT()
    event.type = INPUT_KEYBOARD
    event.union.ki.wVk = vk
    event.union.ki.wScan = _u32.MapVirtualKeyW(vk, 0)
    event.union.ki.dwFlags = KEYEVENTF_KEYUP if up else 0
    return event


def send_ctrl(vk: int) -> None:
    """Ctrl+<vk> via SendInput: works regardless of active keyboard layout."""
    events = (_INPUT * 4)(
        _key_event(VK_CONTROL),
        _key_event(vk),
        _key_event(vk, True),
        _key_event(VK_CONTROL, True),
    )
    _u32.SendInput(4, events, ctypes.sizeof(_INPUT))


# --------------------------------------------------------------------------- clipboard

def _open_clipboard(retries: int = 10) -> bool:
    for _ in range(retries):
        if _u32.OpenClipboard(None):
            return True
        time.sleep(0.02)
    return False


def clip_get_text() -> str | None:
    """Text from clipboard or None if clipboard has no text."""
    if not _open_clipboard():
        return None
    try:
        handle = _u32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return None
        ptr = _k32.GlobalLock(handle)
        if not ptr:
            return None
        try:
            return ctypes.wstring_at(ptr)
        finally:
            _k32.GlobalUnlock(handle)
    finally:
        _u32.CloseClipboard()


def clip_set_text(text: str) -> bool:
    data = (text + "\0").encode("utf-16-le")
    if not _open_clipboard():
        return False
    try:
        _u32.EmptyClipboard()
        handle = _k32.GlobalAlloc(GMEM_MOVEABLE, len(data))
        if not handle:
            return False
        ptr = _k32.GlobalLock(handle)
        if not ptr:
            _k32.GlobalFree(handle)
            return False
        ctypes.memmove(ptr, data, len(data))
        _k32.GlobalUnlock(handle)
        if not _u32.SetClipboardData(CF_UNICODETEXT, handle):
            _k32.GlobalFree(handle)
            return False
        return True
    finally:
        _u32.CloseClipboard()


# --------------------------------------------------------------------------- windows

def get_cursor_pos() -> tuple[int, int]:
    point = wintypes.POINT()
    _u32.GetCursorPos(ctypes.byref(point))
    return int(point.x), int(point.y)


def virtual_screen() -> tuple[int, int, int, int]:
    """Bounds across all monitors: (left, top, width, height)."""
    return (
        _u32.GetSystemMetrics(76),
        _u32.GetSystemMetrics(77),
        _u32.GetSystemMetrics(78),
        _u32.GetSystemMetrics(79),
    )


def monitor_work_area(x: int, y: int) -> tuple[int, int, int, int]:
    """Work area of the monitor containing (x, y): (left, top, right, bottom)."""
    pt = wintypes.POINT(int(x), int(y))
    hmon = _u32.MonitorFromPoint(pt, MONITOR_DEFAULTTONEAREST)
    if hmon:
        info = _MONITORINFO()
        info.cbSize = ctypes.sizeof(_MONITORINFO)
        if _u32.GetMonitorInfoW(hmon, ctypes.byref(info)):
            r = info.rcWork
            return int(r.left), int(r.top), int(r.right), int(r.bottom)
    left, top, w, h = virtual_screen()
    return left, top, left + w, top + h


def get_foreground_window() -> int:
    return int(_u32.GetForegroundWindow() or 0)


def focus_window(hwnd: int) -> bool:
    """Brings window to foreground, bypassing Windows foreground lock."""
    if not hwnd:
        return False
    try:
        if _u32.IsIconic(hwnd):
            _u32.ShowWindow(hwnd, SW_RESTORE)
        if _u32.GetForegroundWindow() == hwnd:
            return True
        current_tid = _k32.GetCurrentThreadId()
        attached: list[int] = []
        for source in (int(_u32.GetForegroundWindow() or 0), hwnd):
            tid = int(_u32.GetWindowThreadProcessId(source, None)) if source else 0
            if tid and tid != current_tid and tid not in attached:
                if _u32.AttachThreadInput(current_tid, tid, True):
                    attached.append(tid)
        try:
            _u32.BringWindowToTop(hwnd)
            return bool(_u32.SetForegroundWindow(hwnd))
        finally:
            for tid in attached:
                _u32.AttachThreadInput(current_tid, tid, False)
    except Exception:
        return False


# --------------------------------------------------------------------------- selection

def alt_pressed() -> bool:
    return bool(_u32.GetAsyncKeyState(0x12) & 0x8000)


def _wait_alt_released(timeout: float = 0.6) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not alt_pressed():
            return True
        time.sleep(0.01)
    return not alt_pressed()


def _wait_for_copy(timeout: float) -> str | None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = clip_get_text()
        if value is not None and value != _PROBE:
            return value
        time.sleep(0.02)
    return None


def capture_selection(timeout: float = 0.5) -> tuple[str, str | None]:
    """Silently copies selection via Ctrl+C. Returns (text, previous_clipboard)."""
    previous = clip_get_text()
    clip_set_text(_PROBE)
    if not _wait_alt_released():
        clip_set_text(previous or "")
        return "", previous
    time.sleep(0.01)
    send_ctrl(ord("C"))
    copied = _wait_for_copy(timeout)
    if copied is not None:
        time.sleep(0.03)
    clip_set_text(previous or "")
    return (copied or ""), previous


def replace_selection(text: str, previous_clipboard: str | None, hwnd: int = 0) -> bool:
    """Pastes text over current selection and restores old clipboard."""
    if not text:
        return False
    if hwnd:
        focus_window(hwnd)
        time.sleep(0.15)
    if not clip_set_text(text):
        return False
    time.sleep(0.05)
    send_ctrl(ord("V"))
    time.sleep(0.25)
    clip_set_text(previous_clipboard or "")
    return True


# --------------------------------------------------------------------------- translation

def has_cyrillic(text: str) -> bool:
    return bool(_CYRILLIC.search(text))


def _translate_mymemory(text: str, target: str) -> str:
    """Secondary free translator fallback when Google rate-limits (HTTP 429)."""
    import requests

    lang_pair = f"Autodetect|{target}"
    response = requests.get(
        "https://api.mymemory.translated.net/get",
        params={"q": text[:500], "langpair": lang_pair},
        timeout=15,
    )
    response.raise_for_status()
    translated = (response.json().get("responseData") or {}).get("translatedText") or ""
    return translated.strip()


def _translate_direct(text: str, target: str) -> str:
    """Fallback path if deep_translator hits a Google rate limit."""
    import requests

    response = requests.get(
        "https://translate.googleapis.com/translate_a/single",
        params={"client": "gtx", "sl": "auto", "tl": target, "dt": "t", "q": text},
        timeout=15,
    )
    response.raise_for_status()
    chunks = response.json()[0] or []
    return "".join(part[0] for part in chunks if part and part[0]).strip()


def translate_text(text: str, target_code: str = "EN") -> str:
    """Translate from any auto-detected language into target_code (default: English)."""
    from deep_translator import GoogleTranslator

    source_text = (text or "").strip()
    if not source_text:
        return ""
    target = TARGET_LANGUAGES.get(target_code, "en")
    source_text = source_text[:4900]
    last_exc: Exception = RuntimeError("Translation failed")
    for engine in (
        lambda: GoogleTranslator(source="auto", target=target).translate(source_text),
        lambda: _translate_direct(source_text, target),
        lambda: _translate_mymemory(source_text, target),
    ):
        try:
            result = (engine() or "").strip()
            if result:
                return result
        except Exception as exc:
            last_exc = exc
    raise last_exc


# --------------------------------------------------------------------------- ocr

_OCR_LANGUAGE_TAGS = (
    "en-US", "ru-RU", "de-DE", "es-ES", "fr-FR", "it-IT", "pl-PL", "uk-UA",
    "tr-TR", "pt-BR", "nl-NL", "zh-Hans", "ja-JP", "ko-KR",
)


def _ocr_engine():
    """Windows OCR engine for one of the installed languages, or None."""
    from winrt.windows.globalization import Language
    from winrt.windows.media.ocr import OcrEngine

    engine = OcrEngine.try_create_from_user_profile_languages()
    if engine is not None:
        return engine
    for tag in _OCR_LANGUAGE_TAGS:
        engine = OcrEngine.try_create_from_language(Language(tag))
        if engine is not None:
            return engine
    return None


def _recognize_file(path: str) -> str:
    import asyncio

    async def run() -> str:
        from winrt.windows.graphics.imaging import BitmapDecoder
        from winrt.windows.storage import FileAccessMode, StorageFile

        engine = _ocr_engine()
        if engine is None:
            raise RuntimeError("Windows OCR is not available")
        file = await StorageFile.get_file_from_path_async(path)
        stream = await file.open_async(FileAccessMode.READ)
        decoder = await BitmapDecoder.create_async(stream)
        bitmap = await decoder.get_software_bitmap_async()
        result = await engine.recognize_async(bitmap)
        return "\n".join(line.text.strip() for line in result.lines if line.text.strip())

    return asyncio.run(run())


def ocr_image(image) -> str:
    """Recognize text on a PIL image with the offline Windows OCR engine."""
    import tempfile
    from PIL import Image, ImageOps

    if image.width < 8 or image.height < 8:
        return ""
    if image.width < 900:
        image = image.resize((image.width * 2, image.height * 2), Image.Resampling.LANCZOS)
    # A white margin: Windows OCR drops lines that touch the image edge.
    image = ImageOps.expand(image.convert("RGB"), border=16, fill="white")
    handle, path = tempfile.mkstemp(suffix=".png", prefix="quickmenu_ocr_")
    os.close(handle)
    try:
        image.save(path)
        return _recognize_file(path)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


# --------------------------------------------------------------------------- keyboard layout

_EN_KEYS = "qwertyuiop[]asdfghjkl;'zxcvbnm,./`" + 'QWERTYUIOP{}ASDFGHJKL:"ZXCVBNM<>?~' + '@#$^&'
_RU_KEYS = "йцукенгшщзхъфывапролджэячсмитьбю.ё" + "ЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ,Ё" + '"№;:?'

_EN_TO_RU = dict(zip(_EN_KEYS, _RU_KEYS))
_RU_TO_EN = dict(zip(_RU_KEYS, _EN_KEYS))


def convert_layout(text: str) -> str:
    """QWERTY <-> ЙЦУКЕН; direction is chosen by whether the text has Cyrillic."""
    table = _RU_TO_EN if has_cyrillic(text) else _EN_TO_RU
    return "".join(table.get(char, char) for char in text)


# --------------------------------------------------------------------------- calculator

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_MAX_POWER = 10_000


def _eval_node(node: ast.AST):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
            and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval_node(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > _MAX_POWER:
            raise ValueError("exponent too large")
        return _BIN_OPS[type(node.op)](left, right)
    raise ValueError("unsupported expression")


def _format_number(value) -> str:
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("bad result")
        if value.is_integer() and abs(value) < 1e15:
            return str(int(value))
        return f"{value:.12g}"
    return str(value)


def calculate(text: str) -> str | None:
    """Safely evaluates an arithmetic expression; None if it is not math."""
    expr = (text or "").strip()
    expr = (
        expr.replace("×", "*")
        .replace("÷", "/")
        .replace("−", "-")
        .replace("–", "-")
        .replace("^", "**")
        .replace(",", ".")
        .replace("\u00a0", " ")
    )
    expr = expr.rstrip("= ").strip()
    if not expr or not re.search(r"\d", expr):
        return None
    if not re.fullmatch(r"[\d\s+\-*/%().]+", expr):
        return None
    try:
        tree = ast.parse(expr, mode="eval")
        return _format_number(_eval_node(tree))
    except (SyntaxError, ValueError, ZeroDivisionError, OverflowError, RecursionError):
        return None


# --------------------------------------------------------------------------- links

def open_url(url: str) -> None:
    try:
        webbrowser.open(url, new=2)
    except Exception:
        pass


def google_search(text: str) -> None:
    query = " ".join((text or "").split())[:300]
    if query:
        open_url("https://www.google.com/search?q=" + quote(query))