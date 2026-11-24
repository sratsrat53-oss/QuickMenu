"""Compact QuickMenu popup window."""
from __future__ import annotations

import ctypes
import queue
import threading
import time
import tkinter as tk

import customtkinter as ctk
from PIL import ImageGrab, ImageTk

import actions

BG_KEY = "#010203"  # transparency key for the rounded corners

# Colour themes. apply_theme() copies the chosen palette into the module-level
# names below (PANEL, FIELD, ...), and every window reads them when it is built.
THEMES: dict[str, dict[str, str]] = {
    "Night": {
        "PANEL": "#171a21", "FIELD": "#101218", "HOVER": "#242834", "FG": "#e9ebf0",
        "MUTED": "#8a90a0", "ACCENT": "#6f9bff", "SUCCESS": "#7ddc9a", "BORDER": "#282d39",
        "BTN": "#1f232e", "ACTION": "#2a3550", "ACTION_HOVER": "#34426b", "DIM": "#6d7486",
        "SCROLL": "#252a36", "SCROLL_HOVER": "#323847", "ERR": "#f0a5a5",
    },
    "Graphite": {
        "PANEL": "#1c1d20", "FIELD": "#141517", "HOVER": "#2a2c31", "FG": "#ececef",
        "MUTED": "#9a9ca5", "ACCENT": "#cfd2dc", "SUCCESS": "#7ddc9a", "BORDER": "#2e3036",
        "BTN": "#24262b", "ACTION": "#3a3d46", "ACTION_HOVER": "#4a4e59", "DIM": "#767985",
        "SCROLL": "#2c2e34", "SCROLL_HOVER": "#3a3d45", "ERR": "#f0a5a5",
    },
    "Violet": {
        "PANEL": "#1b1726", "FIELD": "#130f1c", "HOVER": "#2a2338", "FG": "#ece8f5",
        "MUTED": "#9a90b0", "ACCENT": "#b48cff", "SUCCESS": "#7ddc9a", "BORDER": "#2e2640",
        "BTN": "#231d31", "ACTION": "#41305f", "ACTION_HOVER": "#53407a", "DIM": "#7a7090",
        "SCROLL": "#2c2540", "SCROLL_HOVER": "#382e4a", "ERR": "#f0a5a5",
    },
    "Forest": {
        "PANEL": "#141d19", "FIELD": "#0e1512", "HOVER": "#1f2c26", "FG": "#e8f0ec",
        "MUTED": "#8aa096", "ACCENT": "#5fd39a", "SUCCESS": "#7ddc9a", "BORDER": "#22322a",
        "BTN": "#19241f", "ACTION": "#25503c", "ACTION_HOVER": "#2f6249", "DIM": "#6d8077",
        "SCROLL": "#212e28", "SCROLL_HOVER": "#2a3b33", "ERR": "#f0a5a5",
    },
    "Crimson": {
        "PANEL": "#1f1517", "FIELD": "#160f10", "HOVER": "#2e1f22", "FG": "#f3e9ea",
        "MUTED": "#b09096", "ACCENT": "#ff7a8a", "SUCCESS": "#7ddc9a", "BORDER": "#35232a",
        "BTN": "#271a1d", "ACTION": "#5a2630", "ACTION_HOVER": "#70303c", "DIM": "#90707a",
        "SCROLL": "#301f24", "SCROLL_HOVER": "#3d2a2e", "ERR": "#ffb3b3",
    },
    "Light": {
        "PANEL": "#f4f5f8", "FIELD": "#ffffff", "HOVER": "#e3e6ee", "FG": "#1d2130",
        "MUTED": "#5d6475", "ACCENT": "#2f63e0", "SUCCESS": "#1f9d55", "BORDER": "#d0d4de",
        "BTN": "#e8ebf2", "ACTION": "#cfdcff", "ACTION_HOVER": "#b9ccff", "DIM": "#7a8195",
        "SCROLL": "#d5d9e3", "SCROLL_HOVER": "#c2c7d4", "ERR": "#c0392b",
    },
}
DEFAULT_THEME = "Night"

THEME_LABELS: dict[str, dict[str, str]] = {
    "EN": {"Night": "Night", "Graphite": "Graphite", "Violet": "Violet",
           "Forest": "Forest", "Crimson": "Crimson", "Light": "Light"},
    "RU": {"Night": "Ночь", "Graphite": "Графит", "Violet": "Фиолетовая",
           "Forest": "Лес", "Crimson": "Рубин", "Light": "Светлая"},
}

# Filled in by apply_theme() right below.
PANEL = FIELD = HOVER = FG = MUTED = ACCENT = SUCCESS = BORDER = ""
BTN = ACTION = ACTION_HOVER = DIM = SCROLL = SCROLL_HOVER = ERR = ""


def apply_theme(name: str | None = None) -> str:
    """Load a palette into the module-level colour names; returns the theme actually applied."""
    if name not in THEMES:
        name = DEFAULT_THEME
    globals().update(THEMES[name])
    return name


apply_theme(DEFAULT_THEME)

WIDTH = actions.DEFAULT_WINDOW_WIDTH
MIN_WIDTH = actions.MIN_WINDOW_WIDTH
MAX_WIDTH = actions.MAX_WINDOW_WIDTH
PREVIEW_H = actions.DEFAULT_PREVIEW_HEIGHT
RESULT_H = 92

# Target languages offered in the popup; keys must exist in actions.TARGET_LANGUAGES.
LANG_CHOICES = ("EN", "RU", "ES", "DE", "FR", "JA", "ZH", "UK", "PL", "TR")

# Translate modes -> keys of their labels in UI_STRINGS.
MODE_LABELS = {"text": "mode_text", "photo": "mode_photo"}

# Interface language: every user-visible string lives here.
UI_STRINGS: dict[str, dict[str, str]] = {
    "EN": {
        "esc": "Esc to close",
        "no_text": "No text selected — search Google below or select a fragment and press Alt+Q",
        "search_ph": "Search Google…",
        "translate": "Translate",
        "mode_text": "Text",
        "mode_photo": "Photo",
        "recognizing": "Reading the photo…",
        "no_text_found": "No text found in the photo",
        "ocr_missing": "Windows OCR is not available on this system",
        "select_region": "Drag over the text  ·  Esc — cancel",
        "layout": "Fix Layout",
        "calc": "Calculate",
        "google": "Google Search",
        "copy": "Copy",
        "replace": "Replace in text",
        "boosty": "Support on Boosty",
        "translating": "Translating…",
        "converting": "Converting layout…",
        "calculating": "Calculating…",
        "copied": "Copied",
        "empty": "Empty response",
        "no_connection": "No connection — could not get a response",
        "rate_limit": "Google is rate limiting translations — please try again later",
        "not_math": "This does not look like a math expression",
        "tray_open": "Open menu",
        "tray_settings": "Settings…",
        "tray_exit": "Exit",
        "started": "QuickMenu is running — press {hotkey} to open the menu",
    },
    "RU": {
        "esc": "Esc — закрыть",
        "no_text": "Текст не выделен — ищите в Google ниже или выделите фрагмент и нажмите Alt+Q",
        "search_ph": "Поиск в Google…",
        "translate": "Перевести",
        "mode_text": "Текст",
        "mode_photo": "Фото",
        "recognizing": "Распознаю фото…",
        "no_text_found": "На фото не нашёл текст",
        "ocr_missing": "Распознавание Windows OCR недоступно",
        "select_region": "Обведите текст  ·  Esc — отмена",
        "layout": "Раскладка",
        "calc": "Посчитать",
        "google": "В Google",
        "copy": "Копировать",
        "replace": "Заменить в тексте",
        "boosty": "Поддержать на Boosty",
        "translating": "Перевожу…",
        "converting": "Меняю раскладку…",
        "calculating": "Считаю…",
        "copied": "Скопировано",
        "empty": "Пустой ответ",
        "no_connection": "Нет соединения — не удалось получить ответ",
        "rate_limit": "Google временно ограничил перевод — попробуйте позже",
        "not_math": "Не похоже на математический пример",
        "tray_open": "Открыть меню",
        "tray_settings": "Настройки…",
        "tray_exit": "Выход",
        "started": "QuickMenu запущена — нажмите {hotkey}, чтобы открыть меню",
    },
}

SETTINGS_STRINGS: dict[str, dict[str, str]] = {
    "EN": {
        "title": "Settings",
        "ui_lang": "Interface language",
        "theme": "Color theme",
        "hotkey": "Show menu hotkey",
        "change": "Change",
        "cancel": "Cancel",
        "press": "Press a combination…",
        "hint": "Hold Alt, Ctrl, Shift or Win and press a key",
        "need_mod": "Add a modifier: Alt, Ctrl, Shift or Win",
        "busy": "This combination is taken by another program or Windows — try another one",
        "saved": "Hotkey saved — it works right away",
        "done": "Done",
        "quit_app": "Quit QuickMenu",
    },
    "RU": {
        "title": "Настройки",
        "ui_lang": "Язык интерфейса",
        "theme": "Цветовая тема",
        "hotkey": "Горячая клавиша вызова",
        "change": "Изменить",
        "cancel": "Отмена",
        "press": "Нажмите комбинацию…",
        "hint": "Зажмите Alt, Ctrl, Shift или Win и нажмите клавишу",
        "need_mod": "Добавьте модификатор: Alt, Ctrl, Shift или Win",
        "busy": "Комбинация занята другой программой или Windows — выберите другую",
        "saved": "Клавиша сохранена — уже работает",
        "done": "Готово",
        "quit_app": "Выйти из QuickMenu",
    },
}

MODIFIER_KEYSYMS = frozenset(
    {
        "Alt_L",
        "Alt_R",
        "Control_L",
        "Control_R",
        "Shift_L",
        "Shift_R",
        "Super_L",
        "Super_R",
        "Meta_L",
        "Meta_R",
        "Caps_Lock",
        "Num_Lock",
    }
)

_u32 = ctypes.WinDLL("user32")


# ---------------------------------------------------------------------------- animation
def _ease_out(t: float) -> float:
    """Fast start, long soft landing."""
    return 1 - (1 - t) ** 3


def _ease_in_out(t: float) -> float:
    """Smootherstep: gentle at both ends."""
    return t * t * t * (t * (t * 6 - 15) + 10)


def _animate(win, duration_ms: int, on_frame, on_done=None, ease=_ease_in_out, alive=None) -> None:
    """Call `on_frame(progress)` for `duration_ms`; progress goes 0 -> 1 following `ease`.

    Frames are paced at ~60 Hz and the progress is derived from the clock, so a slow
    frame never makes the animation last longer. If ``on_frame`` raises TclError
    (window destroyed) the animation stops and ``on_done`` is not called. ``alive``
    lets a newer animation on the same widget cancel this one: once it returns False
    the loop ends without calling ``on_done``.
    """
    started = time.monotonic()

    def tick() -> None:
        if alive is not None and not alive():
            return
        t = min(1.0, (time.monotonic() - started) * 1000.0 / duration_ms)
        try:
            on_frame(ease(t))
            if t < 1.0:
                win.after(16, tick)
                return
        except tk.TclError:
            return
        if on_done is not None:
            on_done()

    tick()


def _slide_in(win, duration_ms: int, width: int, height: int, x: float, y: float,
              rise: int, on_done=None, alive=None) -> None:
    """Fade in while gliding `rise` px up into place; shared by both windows.

    Alpha reaches 1 slightly before the glide ends, so the last frames only move the
    window instead of leaving a half-transparent ghost on screen.
    """
    def frame(progress: float) -> None:
        win.attributes("-alpha", min(1.0, progress * 1.15))
        win.geometry(f"{width}x{height}+{int(x)}+{int(y + rise * (1.0 - progress))}")

    _animate(win, duration_ms, frame, on_done=on_done, ease=_ease_out, alive=alive)


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)


def _mix(a: str, b: str, t: float) -> str:
    """Colour between hex colours `a` (t=0) and `b` (t=1)."""
    ra, rb = _hex_to_rgb(a), _hex_to_rgb(b)
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(ra, rb))


def _swatch_ring(palette: dict[str, str], selected: bool) -> str:
    """Border colour of a theme swatch: muted accent, softer when not selected."""
    return _mix(palette["ACCENT"], palette["PANEL"], 0.25 if selected else 0.6)


def _widget_fill(widget) -> str | None:
    try:
        value = widget.cget("fg_color")
    except Exception:  # noqa: BLE001 - not a colour-bearing widget
        return None
    return value if isinstance(value, str) else None


def _smooth_hover(widget, base_key: str, hover_key: str, duration_ms: int = 130) -> None:
    """Fade a button's fill on hover instead of customtkinter's instant colour swap.

    Palette names are resolved at event time, so switching the theme keeps the right
    colours. customtkinter binds its own hover handlers to the inner canvas and label,
    hence the extra ``add="+"`` bindings there.
    """
    try:
        widget.configure(hover_color=globals()[base_key])
    except Exception:  # noqa: BLE001 - widget without hover_color
        return
    token = {"seq": 0}

    def fade(start: str | None, target: str) -> None:
        token["seq"] += 1
        seq = token["seq"]
        begin = start or globals()[base_key]

        def frame(progress: float) -> None:
            widget.configure(fg_color=_mix(begin, target, progress))

        _animate(widget, duration_ms, frame, ease=_ease_out,
                 alive=lambda: token["seq"] == seq)

    def on_enter(_event=None) -> None:
        try:
            if str(widget.cget("state")).lower() == "disabled":
                return
        except Exception:  # noqa: BLE001 - widget without state
            pass
        fade(_widget_fill(widget), globals()[hover_key])

    def on_leave(_event=None) -> None:
        fade(_widget_fill(widget), globals()[base_key])

    for target in (getattr(widget, "_canvas", None), getattr(widget, "_text_label", None)):
        if target is not None:
            target.bind("<Enter>", on_enter, add="+")
            target.bind("<Leave>", on_leave, add="+")


def _walk(widget):
    yield widget
    for child in widget.winfo_children():
        yield from _walk(child)


# customtkinter colour options that may hold a palette colour.
_TWEEN_OPTIONS = (
    "fg_color", "border_color", "text_color", "hover_color", "button_color",
    "button_hover_color", "dropdown_fg_color", "dropdown_hover_color",
    "dropdown_text_color", "selected_color", "selected_hover_color",
    "unselected_color", "unselected_hover_color", "scrollbar_button_color",
    "scrollbar_button_hover_color", "placeholder_text_color",
)


def _error_text(exc: Exception, t: dict[str, str]) -> str:
    name = type(exc).__name__
    message = str(exc).strip()
    lowered = message.lower()
    if "ocr" in lowered:
        return t["ocr_missing"]
    if any(word in name for word in ("Connection", "Timeout", "Proxy")) or "connect" in lowered:
        return t["no_connection"]
    if "TooMany" in name or "429" in message:
        return t["rate_limit"]
    return message[:180] or name


class SelectRegion:
    """Frozen screenshot of the desktop: drag a rectangle to pick the area to read.

    ``on_done(PIL.Image)`` receives the cropped screenshot, ``on_cancel()`` fires on
    Esc or a right click. The overlay closes itself before either callback runs.
    """

    def __init__(self, master, hint: str, on_done, on_cancel):
        self.on_done = on_done
        self.on_cancel = on_cancel
        self.start: tuple[int, int] | None = None
        self.sel_id = None
        self.dim_ids: list[int] = []
        self._closed = False
        self.shot = None
        self.photo = None
        try:
            self.shot = ImageGrab.grab(all_screens=True)
        except Exception:  # noqa: BLE001 - overlay still works, just without the picture
            self.shot = None

        left, top, width, height = actions.virtual_screen()
        self.win = tk.Toplevel(master)
        self.win.withdraw()
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg="black")
        self.win.geometry(f"{width}x{height}+{left}+{top}")
        self.canvas = tk.Canvas(
            self.win, bg="black", highlightthickness=0, bd=0, cursor="crosshair"
        )
        self.canvas.pack(fill="both", expand=True)
        if self.shot is not None:
            self.photo = ImageTk.PhotoImage(self.shot)
            self.canvas.create_image(0, 0, anchor="nw", image=self.photo)
        self.canvas.create_text(
            width // 2, 34, text=f"  {hint}  ", fill=FG,
            font=ctk.CTkFont("Segoe UI", 13), tags="hint",
        )
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.canvas.bind("<ButtonPress-3>", lambda _e: self._cancel())
        self.win.bind("<Escape>", lambda _e: self._cancel())

    def show(self) -> None:
        self.win.deiconify()
        self.win.lift()
        self.win.focus_force()
        self.win.update_idletasks()
        self._dim(None)

    def _canvas_size(self) -> tuple[int, int]:
        return max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())

    def _dim(self, box) -> None:
        """Dim everything outside ``box`` (canvas coordinates); None dims it all."""
        for item in self.dim_ids:
            self.canvas.delete(item)
        width, height = self._canvas_size()
        rects = [(0, 0, width, height)] if box is None else [
            (0, 0, width, box[1]),
            (0, box[3], width, height),
            (0, box[1], box[0], box[3]),
            (box[2], box[1], width, box[3]),
        ]
        self.dim_ids = [
            self.canvas.create_rectangle(*rect, fill="#000000", stipple="gray50", outline="")
            for rect in rects
        ]
        self.canvas.tag_raise("hint")
        if self.sel_id is not None:
            self.canvas.tag_raise(self.sel_id)

    def _press(self, event) -> None:
        self.start = (event.x, event.y)
        if self.sel_id is not None:
            self.canvas.delete(self.sel_id)
            self.sel_id = None

    def _drag(self, event) -> None:
        if self.start is None:
            return
        x1, y1 = self.start
        box = (min(x1, event.x), min(y1, event.y), max(x1, event.x), max(y1, event.y))
        self._dim(box)
        if self.sel_id is None:
            self.sel_id = self.canvas.create_rectangle(
                *box, outline=ACCENT, width=2, tags="sel"
            )
        else:
            self.canvas.coords(self.sel_id, *box)

    def _release(self, event) -> None:
        if self.start is None:
            return
        x1, y1 = self.start
        box = (min(x1, event.x), min(y1, event.y), max(x1, event.x), max(y1, event.y))
        if box[2] - box[0] < 10 or box[3] - box[1] < 10:
            self._cancel()
            return
        width, height = self._canvas_size()
        image = None
        if self.shot is not None:
            # The canvas may be scaled against the real screen; crop in image pixels.
            sx, sy = self.shot.width / width, self.shot.height / height
            image = self.shot.crop(
                (
                    int(box[0] * sx),
                    int(box[1] * sy),
                    int(box[2] * sx),
                    int(box[3] * sy),
                )
            )
        self._close()
        if image is None:
            self.on_cancel()
        else:
            self.on_done(image)

    def _cancel(self) -> None:
        self._close()
        self.on_cancel()

    def _close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self.win.destroy()
        except tk.TclError:
            pass


class PopupMenu:
    """Single-use menu window: lives from show until Esc / outside click.

    ``origin_rect`` (x, y, w, h) is used when the menu is brought back after the
    settings window: the menu then takes the place of that window instead of
    appearing next to the cursor.
    """

    def __init__(self, master, text, old_clipboard, target_hwnd, anchor, on_close,
                 on_settings=None, origin_rect=None):
        apply_theme(actions.get_theme())
        self.text = (text or "").strip()
        self.old_clipboard = old_clipboard
        self.target_hwnd = target_hwnd
        self.anchor = anchor
        self.on_close = on_close
        self.on_settings = on_settings
        self.origin_rect = origin_rect
        self.results: queue.Queue[tuple[bool, object]] = queue.Queue()
        self._closed = False
        self._paused = False
        self._pos: tuple[int, int] | None = None
        self._result = ""
        self._action_key = "copy"
        self._action_cb = None
        self._status_key = ""
        self.ui_lang = actions.get_ui_lang()
        self.mode = actions.get_translate_mode()
        self.width = actions.get_window_width()
        self.preview_h = actions.get_preview_height()
        self._height_drag: tuple[int, int] | None = None
        self._width_drag: tuple[int, int] | None = None
        self._t = UI_STRINGS[self.ui_lang]
        self._shown_at = 0.0
        self._mouse_was_down = False
        self._drag: tuple[int, int] | None = None
        self._moved = False
        self._resize_seq = 0

        self.win = tk.Toplevel(master)
        self.win.withdraw()
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg=BG_KEY)
        try:
            self.win.attributes("-transparentcolor", BG_KEY)
        except tk.TclError:
            pass
        self.win.protocol("WM_DELETE_WINDOW", self.close)
        self._build()

    # ------------------------------------------------------------------ ui
    def _build(self) -> None:
        self.panel = ctk.CTkFrame(
            self.win, fg_color=PANEL, corner_radius=18, border_width=1, border_color=BORDER
        )
        self.panel.pack(fill="both", expand=True)
        body = ctk.CTkFrame(self.panel, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=14)

        head = ctk.CTkFrame(body, fg_color="transparent")
        head.pack(fill="x", pady=(0, 10))
        self.dot = ctk.CTkLabel(
            head, text="", width=8, height=8, corner_radius=4, fg_color=ACCENT
        )
        self.dot.pack(side="left", padx=(1, 8))
        self.title_label = ctk.CTkLabel(
            head, text="QuickMenu", font=ctk.CTkFont("Segoe UI Semibold", 13), text_color=FG
        )
        self.title_label.pack(side="left")
        self.settings_btn = ctk.CTkButton(
            head,
            text="⚙",
            width=26,
            height=24,
            corner_radius=7,
            fg_color="transparent",
            hover_color=HOVER,
            text_color=MUTED,
            font=ctk.CTkFont("Segoe UI Symbol", 14),
            command=self._open_settings,
        )
        self.settings_btn.pack(side="right", padx=(8, 0))
        self.esc_label = ctk.CTkLabel(
            head,
            text=self._esc_text(),
            font=ctk.CTkFont("Segoe UI", 9),
            text_color=DIM,
            fg_color=BTN,
            corner_radius=6,
            height=20,
        )
        self.esc_label.pack(side="right")

        # The whole header strip is a drag handle.
        for widget in (head, self.title_label, self.esc_label, self.dot):
            widget.bind("<Button-1>", self._drag_start)
            widget.bind("<B1-Motion>", self._drag_move)
            widget.bind("<ButtonRelease-1>", self._drag_end)

        preview = self.text[:700] + ("…" if len(self.text) > 700 else "")
        if not preview:
            preview = self._no_text()
        self.preview = self._textbox(body, self.preview_h, MUTED if not self.text else FG)
        self._fill(self.preview, preview)
        self.preview.pack(fill="x")

        grid = ctk.CTkFrame(body, fg_color="transparent")
        grid.pack(fill="x", pady=(12, 0))
        for column in (0, 1):
            grid.grid_columnconfigure(column, weight=1, uniform="btn")

        # Row 0: "Translate" across the full width, with the mode and language pickers.
        translate_cell = ctk.CTkFrame(grid, fg_color="transparent")
        translate_cell.grid(row=0, column=0, columnspan=2, sticky="ew", pady=4)
        translate_cell.grid_columnconfigure(0, weight=1)

        self.buttons = []
        self.button_keys = ("translate", "layout", "calc", "google")
        for key, command in (
            ("translate", self._translate),
            ("layout", self._layout),
            ("calc", self._calc),
            ("google", self._google),
        ):
            primary = key == "translate"
            button = ctk.CTkButton(
                translate_cell if primary else grid,
                text=self._t[key],
                command=command,
                height=34,
                corner_radius=10,
                fg_color=ACTION if primary else BTN,
                hover_color=ACTION_HOVER if primary else HOVER,
                border_width=0 if primary else 1,
                border_color=BORDER,
                text_color=FG,
                font=ctk.CTkFont("Segoe UI", 12),
            )
            _smooth_hover(
                button,
                "ACTION" if primary else "BTN",
                "ACTION_HOVER" if primary else "HOVER",
            )
            if primary:
                button.grid(row=0, column=0, sticky="ew")
                self.mode_menu = self._mode_menu(translate_cell)
                self.mode_menu.grid(row=0, column=1, sticky="e", padx=(6, 0))
                self.lang_menu = self._lang_menu(translate_cell)
                self.lang_menu.grid(row=0, column=2, sticky="e", padx=(6, 0))
            elif key == "google":
                button.grid(row=2, column=0, columnspan=2, sticky="ew", pady=4)
            else:
                column = 0 if key == "layout" else 1
                button.grid(
                    row=1,
                    column=column,
                    sticky="ew",
                    padx=(0, 5) if column == 0 else (5, 0),
                    pady=4,
                )
            self.buttons.append(button)
        if not self.text:
            for button in self.buttons[1:]:
                button.configure(state="disabled")
        self._sync_translate_state()

        self.result_box = ctk.CTkFrame(body, fg_color="transparent")
        self.res_text = self._textbox(self.result_box, RESULT_H, FG)
        self.res_text.pack(fill="x", pady=(12, 6))
        row = ctk.CTkFrame(self.result_box, fg_color="transparent")
        row.pack(fill="x")
        self.status = ctk.CTkLabel(
            row, text="", font=ctk.CTkFont("Segoe UI", 11), text_color=MUTED, anchor="w"
        )
        self.status.pack(side="left", fill="x", expand=True)
        self.action_btn = ctk.CTkButton(
            row,
            text=self._t["copy"],
            command=self._run_action,
            width=150,
            height=32,
            corner_radius=10,
            fg_color=ACTION,
            hover_color=ACTION_HOVER,
            text_color=FG,
            font=ctk.CTkFont("Segoe UI", 12),
        )
        _smooth_hover(self.action_btn, "ACTION", "ACTION_HOVER")

        # Always-available search line: works with or without a text selection.
        self.search_row = ctk.CTkFrame(body, fg_color="transparent")
        self.search_row.pack(fill="x", pady=(12, 0))
        self.search_entry = ctk.CTkEntry(
            self.search_row,
            placeholder_text=self._t["search_ph"],
            height=36,
            corner_radius=10,
            fg_color=FIELD,
            border_width=1,
            border_color=BORDER,
            text_color=FG,
            placeholder_text_color=MUTED,
            font=ctk.CTkFont("Segoe UI", 12),
        )
        self.search_entry.pack(side="left", fill="x", expand=True)
        self.search_entry.bind("<Return>", lambda _event: self._search())
        self.search_btn = ctk.CTkButton(
            self.search_row,
            text="→",
            command=self._search,
            width=42,
            height=36,
            corner_radius=10,
            fg_color=ACTION,
            hover_color=ACTION_HOVER,
            text_color=FG,
            font=ctk.CTkFont("Segoe UI", 14),
        )
        _smooth_hover(self.search_btn, "ACTION", "ACTION_HOVER")
        self.search_btn.pack(side="left", padx=(6, 0))

        ctk.CTkFrame(body, height=1, fg_color=BORDER).pack(fill="x", pady=(12, 0))

        self.boosty = ctk.CTkButton(
            body,
            text=self._t["boosty"],
            command=lambda: actions.open_url(actions.BOOSTY_URL),
            height=22,
            corner_radius=6,
            fg_color="transparent",
            hover_color=BTN,
            text_color=DIM,
            font=ctk.CTkFont("Segoe UI", 10),
        )
        self.boosty.pack(pady=(6, 0))

        # Resize handles, always visible so it is obvious the menu can be resized:
        # a rail on the right edge changes the width, one on the bottom edge grows
        # the preview box. Values are remembered in the config.
        self.width_grip = ctk.CTkFrame(self.panel, fg_color="transparent", width=12, corner_radius=0)
        self.width_grip.place(relx=1.0, rely=0.0, anchor="ne", relheight=1.0)
        self.width_handle = ctk.CTkFrame(
            self.width_grip, fg_color=self._handle_color(), width=3, height=48, corner_radius=2
        )
        self.width_handle.place(relx=0.5, rely=0.5, anchor="center")
        self.height_grip = ctk.CTkFrame(
            self.panel, fg_color="transparent", width=120, height=12, corner_radius=0
        )
        self.height_grip.place(relx=0.5, rely=1.0, anchor="s")
        self.height_handle = ctk.CTkFrame(
            self.height_grip, fg_color=self._handle_color(), width=44, height=3, corner_radius=2
        )
        self.height_handle.place(relx=0.5, rely=0.5, anchor="center")
        self._bind_resize(
            self.width_handle, (self.width_grip, self.width_handle), "sb_h_double_arrow",
            self._width_drag_start, self._width_drag_move, self._width_drag_end,
        )
        self._bind_resize(
            self.height_handle, (self.height_grip, self.height_handle), "sb_v_double_arrow",
            self._height_drag_start, self._height_drag_move, self._height_drag_end,
        )

    @staticmethod
    def _handle_color() -> str:
        return _mix(PANEL, ACCENT, 0.45)

    def _bind_resize(self, handle, zones, cursor: str, start, move, end) -> None:
        def highlight(_event=None):
            handle.configure(fg_color=ACCENT)

        def dim(_event=None):
            handle.configure(fg_color=self._handle_color())

        for zone in zones:
            for target in (zone, getattr(zone, "_canvas", None)):
                if target is None:
                    continue
                try:
                    target.configure(cursor=cursor)
                except Exception:  # noqa: BLE001 - cursor is cosmetic only
                    pass
                target.bind("<ButtonPress-1>", start)
                target.bind("<B1-Motion>", move)
                target.bind("<ButtonRelease-1>", end)
                target.bind("<Enter>", highlight)
                target.bind("<Leave>", dim)

    @staticmethod
    def _textbox(parent, height: int, text_color: str) -> ctk.CTkTextbox:
        return ctk.CTkTextbox(
            parent,
            height=height,
            corner_radius=10,
            border_width=0,
            border_spacing=8,
            fg_color=FIELD,
            text_color=text_color,
            font=ctk.CTkFont("Segoe UI", 12),
            wrap="word",
            scrollbar_button_color=SCROLL,
            scrollbar_button_hover_color=SCROLL_HOVER,
        )

    @staticmethod
    def _fill(box: ctk.CTkTextbox, text: str) -> None:
        box.configure(state="normal")
        box.delete("1.0", "end")
        if text:
            box.insert("1.0", text)
        box.configure(state="disabled")

    def _lang_menu(self, parent) -> ctk.CTkOptionMenu:
        menu = ctk.CTkOptionMenu(
            parent,
            values=list(LANG_CHOICES),
            width=64,
            height=34,
            corner_radius=10,
            fg_color=BTN,
            button_color=BTN,
            button_hover_color=HOVER,
            dropdown_fg_color=PANEL,
            dropdown_hover_color=HOVER,
            text_color=FG,
            dropdown_text_color=FG,
            command=self._on_lang_change,
            font=ctk.CTkFont("Segoe UI", 12),
            dropdown_font=ctk.CTkFont("Segoe UI", 12),
            dynamic_resizing=False,
        )
        menu.set(actions.get_target_lang())
        return menu

    def _mode_menu(self, parent) -> ctk.CTkOptionMenu:
        menu = ctk.CTkOptionMenu(
            parent,
            values=[self._t[MODE_LABELS[mode]] for mode in actions.TRANSLATE_MODES],
            width=70,
            height=34,
            corner_radius=10,
            fg_color=BTN,
            button_color=BTN,
            button_hover_color=HOVER,
            dropdown_fg_color=PANEL,
            dropdown_hover_color=HOVER,
            text_color=FG,
            dropdown_text_color=FG,
            command=self._on_mode_change,
            font=ctk.CTkFont("Segoe UI", 12),
            dropdown_font=ctk.CTkFont("Segoe UI", 12),
            dynamic_resizing=False,
        )
        menu.set(self._t[MODE_LABELS[self.mode]])
        return menu

    def _mode(self) -> str:
        return self.mode

    def _sync_translate_state(self) -> None:
        """Photo mode works without a selection; text mode needs selected text."""
        if self._closed:
            return
        state = "normal" if (self.text or self._mode() == "photo") else "disabled"
        self.buttons[0].configure(state=state)

    # ------------------------------------------------------------------ lifecycle
    def show(self) -> None:
        self._shown_at = time.monotonic()
        self.win.update_idletasks()
        self._place(initial=True)
        try:
            self.win.attributes("-alpha", 0.0)
            fade = True
        except tk.TclError:
            fade = False
        self.win.deiconify()
        self.win.lift()
        self._take_focus()
        self._mouse_was_down = self._left_button_down()
        self.win.bind("<Escape>", lambda _event: self.close())
        self.win.bind("<FocusOut>", self._on_focus_out)
        self.win.after(60, self._keep_focus)
        self.win.after(100, self._focus_search)
        self.win.after(40, self._drain)
        self.win.after(150, self._watch_mouse)
        if fade:
            self._animate_in()

    def _animate_in(self) -> None:
        """Fade in while gliding ~14 px up into place."""
        x, y = self._pos
        width = max(self.width, self.panel.winfo_reqwidth() + 2)
        height = self.panel.winfo_reqheight()
        _slide_in(self.win, 250, width, height, x, y, 14,
                  on_done=self._place, alive=lambda: not self._closed)

    def _take_focus(self) -> None:
        try:
            actions.focus_window(int(self.win.wm_frame(), 16))
        except (tk.TclError, ValueError):
            pass
        try:
            self.win.focus_force()
        except tk.TclError:
            pass

    def close(self, animate: bool = True) -> None:
        if self._closed:
            return
        self._closed = True
        if animate and self._fade_out():
            return
        self._destroy()

    def _fade_out(self) -> bool:
        """Fade the window away if it is on screen; True when the animation took over."""
        try:
            if not self.win.winfo_exists():
                return False
            x, y = self.win.winfo_x(), self.win.winfo_y()
            width, height = self.win.winfo_width(), self.win.winfo_height()
        except tk.TclError:
            return False
        if width < 2:
            return False

        def frame(progress: float) -> None:
            self.win.attributes("-alpha", 1.0 - progress)
            self.win.geometry(f"{width}x{height}+{x}+{int(y + 6 * progress)}")

        _animate(self.win, 120, frame, on_done=self._destroy, ease=_ease_out)
        return True

    def _destroy(self) -> None:
        try:
            self.win.destroy()
        except tk.TclError:
            pass
        try:
            self.on_close()
        except Exception:
            pass

    def _keep_focus(self) -> None:
        if self._closed:
            return
        try:
            if self.win.focus_get() is None:
                self._take_focus()
        except (KeyError, tk.TclError):
            pass

    def _place(self, initial: bool = False) -> None:
        self.win.update_idletasks()
        width = max(self.width, self.panel.winfo_reqwidth() + 2)
        height = self.panel.winfo_reqheight()
        if initial or self._pos is None:
            if self.origin_rect is not None:
                # Returning from settings: take the place of the settings window.
                ox, oy, ow, _oh = self.origin_rect
                left, top, right, bottom = actions.monitor_work_area(ox + ow // 2, oy + 20)
                x = ox + (ow - width) // 2
                y = oy
            else:
                # Place next to the cursor, inside the work area of the monitor it is on.
                ax, ay = self.anchor
                left, top, right, bottom = actions.monitor_work_area(ax, ay)
                x = min(max(left + 8, ax + 12), right - width - 8)
                y = ay + 20
                if y + height > bottom - 8:
                    y = max(top + 8, ay - height - 20)
            self._pos = (x, y)
        x, y = self._pos
        if self._moved:
            # The user dragged the window: allow any monitor, just keep it on the desktop.
            v_left, v_top, v_w, v_h = actions.virtual_screen()
            left, top, right, bottom = v_left, v_top, v_left + v_w, v_top + v_h
        else:
            left, top, right, bottom = actions.monitor_work_area(x + width // 2, y + 20)
        x = max(left + 8, min(x, right - width - 8))
        y = max(top + 8, min(y, bottom - height - 8))
        self._pos = (x, y)
        self.win.geometry(f"{width}x{height}+{int(x)}+{int(y)}")

    def _drag_start(self, event) -> None:
        self._drag = (event.x_root - self.win.winfo_x(), event.y_root - self.win.winfo_y())

    def _drag_move(self, event) -> None:
        if self._drag is None or self._closed:
            return
        x = event.x_root - self._drag[0]
        y = event.y_root - self._drag[1]
        self._pos = (x, y)
        self._moved = True
        self.win.geometry(f"+{int(x)}+{int(y)}")

    def _drag_end(self, _event=None) -> None:
        self._drag = None

    def _width_drag_start(self, event) -> None:
        self._width_drag = (event.x_root, self.width)
        self._resize_seq += 1  # drop an in-flight height/width tween

    def _width_drag_move(self, event) -> None:
        if self._width_drag is None or self._closed:
            return
        start_x, start_width = self._width_drag
        self.width = max(MIN_WIDTH, min(MAX_WIDTH, start_width + int(event.x_root - start_x)))
        self._place()

    def _width_drag_end(self, _event=None) -> None:
        if self._width_drag is None:
            return
        self._width_drag = None
        actions.set_window_width(self.width)
        self._place()

    def _height_drag_start(self, event) -> None:
        self._height_drag = (event.y_root, self.preview_h)
        self._resize_seq += 1  # drop an in-flight height/width tween

    def _height_drag_move(self, event) -> None:
        if self._height_drag is None or self._closed:
            return
        start_y, start_height = self._height_drag
        height = start_height + int(event.y_root - start_y)
        self.preview_h = max(
            actions.MIN_PREVIEW_HEIGHT, min(actions.MAX_PREVIEW_HEIGHT, height)
        )
        self.preview.configure(height=self.preview_h)
        self._place()

    def _height_drag_end(self, _event=None) -> None:
        if self._height_drag is None:
            return
        self._height_drag = None
        actions.set_preview_height(self.preview_h)
        self._place()

    def _resize(self, animate: bool = False) -> None:
        if self._closed:
            return
        if not animate:
            self._place()
            return
        try:
            old_w, old_h = self.win.winfo_width(), self.win.winfo_height()
            old_x, old_y = self.win.winfo_x(), self.win.winfo_y()
        except tk.TclError:
            return
        self._place()
        new_x, new_y = self._pos
        new_w = max(self.width, self.panel.winfo_reqwidth() + 2)
        new_h = self.panel.winfo_reqheight()
        if (new_w, new_h, new_x, new_y) == (old_w, old_h, old_x, old_y):
            return
        self._resize_seq += 1
        seq = self._resize_seq
        # Restore the old geometry before Tk paints, then glide to the new one.
        self.win.geometry(f"{old_w}x{old_h}+{old_x}+{old_y}")

        def frame(progress: float) -> None:
            width = round(old_w + (new_w - old_w) * progress)
            height = round(old_h + (new_h - old_h) * progress)
            x = round(old_x + (new_x - old_x) * progress)
            y = round(old_y + (new_y - old_y) * progress)
            self.win.geometry(f"{width}x{height}+{x}+{y}")

        _animate(
            self.win,
            190,
            frame,
            on_done=self._place,
            ease=_ease_out,
            alive=lambda: self._resize_seq == seq and not self._closed,
        )

    # ------------------------------------------------------------------ closing on outside click
    @staticmethod
    def _left_button_down() -> bool:
        return bool(_u32.GetAsyncKeyState(actions.VK_LBUTTON) & 0x8000)

    def _on_focus_out(self, _event=None) -> None:
        self.win.after(90, self._check_focus)

    def _check_focus(self) -> None:
        if self._closed or self._paused or time.monotonic() - self._shown_at < 0.3:
            return
        try:
            focused = self.win.focus_get()
        except (KeyError, tk.TclError):
            focused = None
        if focused is None:
            self.close()

    def _watch_mouse(self) -> None:
        if self._closed:
            return
        if self._paused:
            self.win.after(90, self._watch_mouse)
            return
        down = self._left_button_down()
        if down and not self._mouse_was_down:
            x, y = self.win.winfo_pointerxy()
            left, top = self.win.winfo_rootx(), self.win.winfo_rooty()
            inside = (
                left <= x <= left + self.win.winfo_width()
                and top <= y <= top + self.win.winfo_height()
            )
            if not inside:
                self.close()
                return
        self._mouse_was_down = down
        self.win.after(90, self._watch_mouse)

    # ------------------------------------------------------------------ actions
    def _no_text(self) -> str:
        return self._t["no_text"].replace("Alt+Q", actions.get_hotkey())

    def _esc_text(self) -> str:
        return f' {self._t["esc"]} '

    def _apply_language(self) -> None:
        self._t = UI_STRINGS[self.ui_lang]
        self.esc_label.configure(text=self._esc_text())
        self.boosty.configure(text=self._t["boosty"])
        self.search_entry.configure(placeholder_text=self._t["search_ph"])
        for key, button in zip(self.button_keys, self.buttons):
            button.configure(text=self._t[key])
        if not self.text:
            self._fill(self.preview, self._no_text())
        self.mode_menu.configure(
            values=[self._t[MODE_LABELS[mode]] for mode in actions.TRANSLATE_MODES]
        )
        self.mode_menu.set(self._t[MODE_LABELS[self._mode()]])
        self._sync_translate_state()
        self.action_btn.configure(text=self._t[self._action_key])
        if self._status_key:
            self.status.configure(text=self._t[self._status_key])
        self._resize()

    def _open_settings(self) -> None:
        if self._closed:
            return
        callback = self.on_settings
        rect = (
            self.win.winfo_x(),
            self.win.winfo_y(),
            self.win.winfo_width(),
            self.win.winfo_height(),
        )
        self.win.unbind("<FocusOut>")
        if callback is not None:
            callback(rect)
        start_x, start_y = rect[0], rect[1]

        def fade_out(progress: float) -> None:
            self.win.attributes("-alpha", 1.0 - progress)
            self.win.geometry(f"+{start_x}+{int(start_y - 10 * progress)}")

        _animate(self.win, 180, fade_out, on_done=lambda: self.close(animate=False),
                 ease=_ease_in_out)

    def _on_lang_change(self, value: str) -> None:
        actions.set_target_lang(value)

    def _on_mode_change(self, value: str) -> None:
        for mode, key in MODE_LABELS.items():
            if self._t[key] == value:
                self.mode = mode
                actions.set_translate_mode(mode)
                break
        self._sync_translate_state()

    def _translate(self) -> None:
        if self._mode() == "photo":
            self._translate_photo()
            return
        if not self.text:
            return
        lang = self.lang_menu.get()
        self._start(
            lambda: actions.translate_text(self.text, lang), "translating", "copy", self._copy
        )

    def _translate_photo(self) -> None:
        """Hide the menu, let the user drag over a screenshot, then OCR and translate it."""
        if self._closed:
            return
        self._paused = True
        try:
            self.win.unbind("<FocusOut>")
            self.win.withdraw()
        except tk.TclError:
            self._paused = False
            return
        self.win.after(80, self._open_selector)

    def _open_selector(self) -> None:
        if self._closed:
            return
        try:
            SelectRegion(
                self.win.master,
                self._t["select_region"],
                self._region_chosen,
                self._region_cancelled,
            ).show()
        except Exception:
            self._restore_after_photo()
            raise

    def _restore_after_photo(self) -> None:
        if self._closed:
            return
        self._paused = False
        try:
            self.win.deiconify()
            self.win.attributes("-alpha", 1.0)
            self.win.lift()
            self._take_focus()
            self.win.bind("<FocusOut>", self._on_focus_out)
            self.win.after(60, self._keep_focus)
        except tk.TclError:
            pass

    def _region_cancelled(self) -> None:
        self._restore_after_photo()

    def _region_chosen(self, image) -> None:
        self._restore_after_photo()
        lang = self.lang_menu.get()
        strings = self._t

        def work():
            recognized = actions.ocr_image(image)
            if not recognized:
                raise ValueError(strings["no_text_found"])
            return recognized, actions.translate_text(recognized, lang)

        self._start(work, "recognizing", "copy", self._copy)

    def _layout(self) -> None:
        if not self.text:
            return
        self._start(
            lambda: actions.convert_layout(self.text), "converting", "replace", self._replace
        )

    def _calc(self) -> None:
        if not self.text:
            return

        def work() -> str:
            value = actions.calculate(self.text)
            if value is None:
                raise ValueError(self._t["not_math"])
            return value

        self._start(work, "calculating", "copy", self._copy)

    def _focus_search(self) -> None:
        if self._closed:
            return
        try:
            self.search_entry.focus_set()
        except tk.TclError:
            pass

    def _search(self) -> None:
        query = self.search_entry.get().strip()
        if not query:
            return
        actions.google_search(query)
        self.close()

    def _google(self) -> None:
        if not self.text:
            return
        actions.google_search(self.text)
        self.close()

    def _start(self, worker, status_key: str, action_key: str, action_cb) -> None:
        self._result = ""
        self._action_key = action_key
        self._status_key = ""
        self._action_cb = action_cb
        if not self.result_box.winfo_manager():
            self.result_box.pack(fill="x", before=self.search_row)
        self._fill(self.res_text, self._t[status_key])
        self.status.configure(text="", text_color=MUTED)
        self.action_btn.pack_forget()
        self._resize(animate=True)
        threading.Thread(target=self._worker, args=(worker,), daemon=True).start()

    def _worker(self, fn) -> None:
        try:
            self.results.put((True, fn()))
        except Exception as exc:  # noqa: BLE001 - the error is shown in the popup
            self.results.put((False, _error_text(exc, self._t)))

    def _drain(self) -> None:
        if self._closed:
            return
        try:
            while True:
                ok, payload = self.results.get_nowait()
                self._finish(ok, payload)
        except queue.Empty:
            pass
        self.win.after(60, self._drain)

    def _finish(self, ok: bool, payload) -> None:
        if self._closed:
            return
        if ok and isinstance(payload, tuple) and len(payload) == 2:
            recognized, payload = payload
            if recognized:
                # Photo mode: the preview shows what was read off the screenshot.
                self._fill(self.preview, recognized)
        text = str(payload).strip() if payload is not None else ""
        if ok and text:
            self._result = text
            self._fill(self.res_text, text)
            self.action_btn.configure(text=self._t[self._action_key])
            self.action_btn.pack(side="right")
        else:
            self._result = ""
            self._fill(self.res_text, text or self._t["empty"])
            self.action_btn.pack_forget()
        self._resize(animate=True)

    def _run_action(self) -> None:
        callback = self._action_cb
        if callback is not None:
            callback()

    def _copy(self) -> None:
        if not self._result:
            return
        actions.clip_set_text(self._result)
        self._status_key = "copied"
        self.status.configure(text=self._t["copied"], text_color=SUCCESS)
        self.action_btn.configure(text=self._t["copied"])
        self.win.after(650, self.close)

    def _replace(self) -> None:
        text = self._result
        if not text:
            return
        previous = self.old_clipboard
        hwnd = self.target_hwnd
        self.close(animate=False)
        threading.Thread(
            target=actions.replace_selection, args=(text, previous, hwnd), daemon=True
        ).start()


class SettingsWindow:
    """Frameless settings panel: interface language, theme and the global hotkey.

    ``on_done(rect)`` is called when the user presses "Done": the application
    uses it to bring the main menu back in place of this window.
    """

    def __init__(self, master, hotkey, on_close=None, on_change=None, on_quit=None,
                 on_done=None, origin_rect=None):
        self.hotkey = hotkey
        self.on_close = on_close
        self.on_change = on_change
        self.on_quit = on_quit
        self.on_done = on_done
        self.origin_rect = origin_rect
        self.theme = apply_theme(actions.get_theme())
        self.ui_lang = actions.get_ui_lang()
        self._t = SETTINGS_STRINGS[self.ui_lang]
        self._combo = actions.get_hotkey()
        self._capturing = False
        self._closed = False
        self._held = 0
        self._status_key = "hint"
        self._animating = False
        self._drag: tuple[int, int] | None = None

        self.win = tk.Toplevel(master)
        self.win.withdraw()
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg=BG_KEY)
        try:
            self.win.attributes("-transparentcolor", BG_KEY)
        except tk.TclError:
            pass
        self.win.protocol("WM_DELETE_WINDOW", self.close)
        self._build()
        self.win.bind("<Escape>", self._on_escape)
        self.win.bind("<KeyPress>", self._on_key_press)
        self.win.bind("<KeyRelease>", self._on_key_release)
        self._release_hotkey()

    # ------------------------------------------------------------------ ui
    def _build(self) -> None:
        self.panel = ctk.CTkFrame(
            self.win, fg_color=PANEL, corner_radius=18, border_width=1, border_color=BORDER
        )
        self.panel.pack(fill="both", expand=True)
        body = ctk.CTkFrame(self.panel, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=16)

        head = ctk.CTkFrame(body, fg_color="transparent")
        head.pack(fill="x", pady=(0, 12))
        self.title_label = ctk.CTkLabel(
            head,
            text=self._t["title"],
            font=ctk.CTkFont("Segoe UI Semibold", 12),
            text_color=ACCENT,
        )
        self.title_label.pack(side="left")
        self.close_btn = ctk.CTkButton(
            head,
            text="✕",
            width=24,
            height=22,
            corner_radius=6,
            fg_color="transparent",
            hover_color=HOVER,
            text_color=MUTED,
            font=ctk.CTkFont("Segoe UI", 11),
            command=self.close,
        )
        self.close_btn.pack(side="right")
        for widget in (head, self.title_label):
            widget.bind("<Button-1>", self._drag_start)
            widget.bind("<B1-Motion>", self._drag_move)

        self.lang_caption = ctk.CTkLabel(
            body,
            text=self._t["ui_lang"],
            font=ctk.CTkFont("Segoe UI", 10),
            text_color=MUTED,
            anchor="w",
        )
        self.lang_caption.pack(fill="x")
        self.lang_switch = ctk.CTkSegmentedButton(
            body,
            values=list(UI_STRINGS),
            command=self._on_ui_lang,
            height=26,
            corner_radius=7,
            fg_color=FIELD,
            selected_color=ACTION,
            selected_hover_color=ACTION_HOVER,
            unselected_color=BTN,
            unselected_hover_color=HOVER,
            text_color=FG,
            font=ctk.CTkFont("Segoe UI", 11),
        )
        self.lang_switch.set(self.ui_lang)
        self.lang_switch.pack(fill="x", pady=(4, 14))

        self.theme_caption = ctk.CTkLabel(
            body,
            text=self._theme_caption(),
            font=ctk.CTkFont("Segoe UI", 10),
            text_color=MUTED,
            anchor="w",
        )
        self.theme_caption.pack(fill="x")
        self.theme_row = ctk.CTkFrame(body, fg_color="transparent")
        self.theme_row.pack(fill="x", pady=(4, 14))
        self._swatches: dict[str, ctk.CTkButton] = {}
        for name, palette in THEMES.items():
            selected = name == self.theme
            swatch = ctk.CTkButton(
                self.theme_row,
                text="✓" if selected else "",
                width=30,
                height=30,
                corner_radius=15,
                fg_color=_mix(palette["PANEL"], palette["ACCENT"], 0.18),
                hover_color=_mix(palette["HOVER"], palette["ACCENT"], 0.26),
                border_width=2 if selected else 1,
                border_color=_swatch_ring(palette, selected),
                text_color=_mix(palette["ACCENT"], palette["FG"], 0.3),
                font=ctk.CTkFont("Segoe UI", 11),
                command=lambda n=name: self._on_theme(n),
            )
            swatch.pack(side="left", padx=(0, 8))
            self._swatches[name] = swatch

        self.hotkey_caption = ctk.CTkLabel(
            body,
            text=self._t["hotkey"],
            font=ctk.CTkFont("Segoe UI", 10),
            text_color=MUTED,
            anchor="w",
        )
        self.hotkey_caption.pack(fill="x")
        row = ctk.CTkFrame(body, fg_color="transparent")
        row.pack(fill="x", pady=(4, 0))
        self.hotkey_box = ctk.CTkFrame(
            row, fg_color=FIELD, corner_radius=8, border_width=1, border_color=BORDER, height=34
        )
        self.hotkey_box.pack(side="left", fill="x", expand=True)
        self.hotkey_box.pack_propagate(False)
        self.hotkey_label = ctk.CTkLabel(
            self.hotkey_box,
            text=self._combo,
            font=ctk.CTkFont("Segoe UI Semibold", 12),
            text_color=FG,
            anchor="w",
        )
        self.hotkey_label.pack(fill="both", expand=True, padx=10)
        self.change_btn = ctk.CTkButton(
            row,
            text=self._t["change"],
            command=self._toggle_capture,
            width=96,
            height=34,
            corner_radius=10,
            fg_color=BTN,
            hover_color=HOVER,
            border_width=1,
            border_color=BORDER,
            text_color=FG,
            font=ctk.CTkFont("Segoe UI", 12),
        )
        _smooth_hover(self.change_btn, "BTN", "HOVER")
        self.change_btn.pack(side="right", padx=(8, 0))

        self.status = ctk.CTkLabel(
            body,
            text=self._t[self._status_key],
            font=ctk.CTkFont("Segoe UI", 10),
            text_color=DIM,
            anchor="w",
            justify="left",
            wraplength=316,
        )
        self.status.pack(fill="x", pady=(6, 12))

        self.done_btn = ctk.CTkButton(
            body,
            text=self._t["done"],
            command=self._done,
            height=34,
            corner_radius=10,
            fg_color=ACTION,
            hover_color=ACTION_HOVER,
            text_color=FG,
            font=ctk.CTkFont("Segoe UI", 12),
        )
        _smooth_hover(self.done_btn, "ACTION", "ACTION_HOVER")
        self.done_btn.pack(fill="x")

        self.quit_btn = ctk.CTkButton(
            body,
            text=self._t["quit_app"],
            command=self._quit_app,
            height=28,
            corner_radius=8,
            fg_color="transparent",
            hover_color=HOVER,
            text_color=ERR,
            font=ctk.CTkFont("Segoe UI", 11),
        )
        self.quit_btn.pack(fill="x", pady=(6, 0))

    # ------------------------------------------------------------------ lifecycle
    def show(self) -> None:
        self.win.update_idletasks()
        target_w = max(336, self.panel.winfo_reqwidth() + 2)
        target_h = self.panel.winfo_reqheight()
        left, top, screen_w, screen_h = actions.virtual_screen()
        if self.origin_rect is not None:
            ox, oy, ow, _oh = self.origin_rect
            x = ox + (ow - target_w) // 2
            y = oy
        else:
            ax, ay = actions.get_cursor_pos()
            x = ax - target_w // 2
            y = ay + 18
            if y + target_h > top + screen_h - 48:
                y = ay - target_h - 18
        x = min(max(left + 8, x), left + screen_w - target_w - 8)
        y = min(max(top + 8, y), top + screen_h - target_h - 48)
        try:
            self.win.attributes("-alpha", 0.0)
        except tk.TclError:
            pass
        self.win.geometry(f"{target_w}x{target_h}+{int(x)}+{int(y) + 12}")
        self.win.deiconify()
        self.focus()
        self._animate_in(target_w, target_h, x, y)

    def _animate_in(self, width: int, height: int, x: float, y: float) -> None:
        """Same fade-and-glide entrance as the main menu."""
        _slide_in(self.win, 250, width, height, x, y, 12,
                  alive=lambda: not self._closed)

    def focus(self) -> None:
        if self._closed:
            return
        self.win.lift()
        try:
            actions.focus_window(int(self.win.wm_frame(), 16))
        except (tk.TclError, ValueError):
            pass
        try:
            self.win.focus_force()
        except tk.TclError:
            pass

    def close(self, animate: bool = True, after=None) -> None:
        """Close with the same fade-and-slide as the menu; ``after`` runs once gone."""
        if self._closed:
            return
        self._closed = True
        self._capturing = False
        try:
            self.hotkey.set_combo(actions.get_hotkey())
        except Exception:
            pass
        if animate and self._fade_out(after):
            return
        self._destroy()
        if after is not None:
            after()

    def _fade_out(self, after=None) -> bool:
        """Fade the window away if it is on screen; True when the animation took over."""
        try:
            if not self.win.winfo_exists():
                return False
            x, y = self.win.winfo_x(), self.win.winfo_y()
            width, height = self.win.winfo_width(), self.win.winfo_height()
        except tk.TclError:
            return False
        if width < 2 or height < 2:
            return False

        def frame(progress: float) -> None:
            self.win.attributes("-alpha", 1.0 - progress)
            self.win.geometry(f"{width}x{height}+{x}+{int(y + 8 * progress)}")

        def done() -> None:
            self._destroy()
            if after is not None:
                after()

        _animate(self.win, 160, frame, on_done=done, ease=_ease_out)
        return True

    def _destroy(self) -> None:
        try:
            self.win.destroy()
        except tk.TclError:
            pass
        if self.on_close is not None:
            try:
                self.on_close()
            except Exception:
                pass

    def _release_hotkey(self) -> None:
        try:
            self.hotkey.release()
        except Exception:
            pass

    def _resize(self) -> None:
        if self._closed:
            return
        self.win.update_idletasks()
        width = max(336, self.panel.winfo_reqwidth() + 2)
        height = self.panel.winfo_reqheight()
        self.win.geometry(f"{width}x{height}+{self.win.winfo_x()}+{self.win.winfo_y()}")

    def _drag_start(self, event) -> None:
        if self._capturing:
            return
        self._drag = (event.x_root - self.win.winfo_x(), event.y_root - self.win.winfo_y())

    def _drag_move(self, event) -> None:
        if self._drag is None or self._capturing:
            return
        self.win.geometry(f"+{event.x_root - self._drag[0]}+{event.y_root - self._drag[1]}")

    # ------------------------------------------------------------------ settings
    def _theme_caption(self) -> str:
        return f'{self._t["theme"]}: {THEME_LABELS[self.ui_lang][self.theme]}'

    def _on_theme(self, name: str) -> None:
        if self._animating or name == self.theme or name not in THEMES:
            return
        self._animating = True
        old, new = THEMES[self.theme], THEMES[name]
        self.theme = name
        actions.set_theme(name)
        # The swatches keep their own fixed colours; only their "selected" mark moves.
        for key, button in self._swatches.items():
            chosen = key == name
            button.configure(
                text="✓" if chosen else "",
                border_width=2 if chosen else 1,
                border_color=_swatch_ring(THEMES[key], chosen),
            )
        self.theme_caption.configure(text=self._theme_caption())

        # Work out which widget option currently holds which palette colour.
        by_value = {value.lower(): key for key, value in old.items()}
        skip = {id(button) for button in self._swatches.values()}
        plan = []
        for widget in _walk(self.panel):
            if id(widget) in skip or not type(widget).__name__.startswith("CTk"):
                continue
            used = []
            for option in _TWEEN_OPTIONS:
                try:
                    value = widget.cget(option)
                except Exception:  # noqa: BLE001 - option not supported by this widget
                    continue
                key = by_value.get(value.lower()) if isinstance(value, str) else None
                if key:
                    used.append((option, key))
            if used:
                plan.append((widget, used))

        def frame(progress: float) -> None:
            colors = {key: _mix(old[key], new[key], progress) for key in old}
            for widget, used in plan:
                try:
                    widget.configure(**{option: colors[key] for option, key in used})
                except Exception:  # noqa: BLE001 - never break the animation on one widget
                    pass

        def finish() -> None:
            self.theme = apply_theme(name)
            self._animating = False

        # Every colour glides from the old palette to the new one.
        _animate(self.win, 380, frame, on_done=finish)

    def _on_ui_lang(self, value: str) -> None:
        if value not in UI_STRINGS or value == self.ui_lang:
            return
        self.ui_lang = value
        actions.set_ui_lang(value)
        self._t = SETTINGS_STRINGS[value]
        self._apply_language()
        self._changed()

    def _apply_language(self) -> None:
        self.title_label.configure(text=self._t["title"])
        self.lang_caption.configure(text=self._t["ui_lang"])
        self.theme_caption.configure(text=self._theme_caption())
        self.hotkey_caption.configure(text=self._t["hotkey"])
        self.status.configure(text=self._t[self._status_key])
        self.done_btn.configure(text=self._t["done"])
        self.quit_btn.configure(text=self._t["quit_app"])
        self.change_btn.configure(text=self._t["cancel"] if self._capturing else self._t["change"])
        if self._capturing:
            self.hotkey_label.configure(text=self._pending(self._held))
        self._resize()

    def _done(self) -> None:
        """'Done': fade out, then hand the screen back to the main menu."""
        if self._closed:
            return
        try:
            rect = (
                self.win.winfo_x(),
                self.win.winfo_y(),
                self.win.winfo_width(),
                self.win.winfo_height(),
            )
        except tk.TclError:
            rect = None
        callback = self.on_done

        def hand_over() -> None:
            if callback is not None:
                try:
                    callback(rect)
                except Exception:
                    pass

        self.close(after=hand_over)

    def _quit_app(self) -> None:
        self.close(animate=False)
        if self.on_quit is not None:
            try:
                self.on_quit()
            except Exception:
                pass

    def _changed(self) -> None:
        if self.on_change is not None:
            try:
                self.on_change()
            except Exception:
                pass

    def _set_status(self, key: str, color: str) -> None:
        self._status_key = key
        self.status.configure(text=self._t[key], text_color=color)

    def _pending(self, mods: int) -> str:
        names = [name for name, flag in actions.MODIFIER_ORDER if mods & flag]
        return " + ".join(names) + " + …" if names else self._t["press"]

    # ------------------------------------------------------------------ hotkey capture
    def _toggle_capture(self) -> None:
        if self._capturing:
            self._stop_capture()
            return
        self._capturing = True
        self._held = actions.held_modifiers()
        self.change_btn.configure(text=self._t["cancel"])
        self.hotkey_label.configure(text=self._pending(self._held), text_color=ACCENT)
        self._set_status("hint", DIM)
        self.focus()

    def _stop_capture(self) -> None:
        self._capturing = False
        self._held = 0
        self.change_btn.configure(text=self._t["change"])
        self.hotkey_label.configure(text=self._combo, text_color=FG)
        self._set_status("hint", DIM)

    def _on_escape(self, _event=None) -> None:
        if self._capturing:
            self._stop_capture()
        else:
            self.close()

    def _on_key_press(self, event):
        if self._closed or not self._capturing:
            return None
        keysym = str(event.keysym)
        if keysym in MODIFIER_KEYSYMS:
            self._held = actions.held_modifiers()
            self.hotkey_label.configure(text=self._pending(self._held), text_color=ACCENT)
            return "break"
        vk = int(getattr(event, "keycode", 0) or 0)
        mods = actions.held_modifiers() | self._held
        self._held = 0
        if vk < 1 or vk in (actions.VK_SHIFT, actions.VK_CONTROL, actions.VK_MENU,
                            actions.VK_LWIN, actions.VK_RWIN):
            return "break"
        if not mods:
            self.hotkey_label.configure(text=self._t["press"], text_color=ACCENT)
            self._set_status("need_mod", ERR)
            return "break"
        self._commit(actions.format_hotkey(mods, vk))
        return "break"

    def _on_key_release(self, event):
        if self._closed or not self._capturing:
            return None
        if str(event.keysym) in MODIFIER_KEYSYMS:
            self._held = actions.held_modifiers()
            self.hotkey_label.configure(text=self._pending(self._held), text_color=ACCENT)
        return None

    def _commit(self, combo: str) -> None:
        self._capturing = False
        self._held = 0
        self.change_btn.configure(text=self._t["change"])
        try:
            ok = bool(self.hotkey.set_combo(combo))
        except Exception:
            ok = False
        if ok:
            self._combo = combo
            actions.set_hotkey(combo)
            self.hotkey_label.configure(text=combo, text_color=FG)
            self._set_status("saved", SUCCESS)
            self._changed()
            return
        self.hotkey_label.configure(text=self._combo, text_color=FG)
        self._set_status("busy", ERR)
        try:
            self.hotkey.set_combo(self._combo)
        except Exception:
            pass