"""Compact QuickMenu popup window."""

from __future__ import annotations

import ctypes
import queue
import threading
import time
import tkinter as tk

import customtkinter as ctk

import actions

BG_KEY = "#010203"  # transparency key for the rounded corners
PANEL = "#171a21"
FIELD = "#101218"
HOVER = "#242834"
FG = "#e9ebf0"
MUTED = "#8a90a0"
ACCENT = "#6f9bff"
SUCCESS = "#7ddc9a"
BORDER = "#282d39"

WIDTH = 430
PREVIEW_H = 74
RESULT_H = 92

# Target languages offered in the popup; keys must exist in actions.TARGET_LANGUAGES.
LANG_CHOICES = ("EN", "RU", "ES", "DE", "FR", "JA", "ZH", "UK", "PL", "TR")

# Interface language: every user-visible string lives here.
UI_STRINGS: dict[str, dict[str, str]] = {
    "EN": {
        "esc": "Esc to close",
        "no_text": "No text selected — select a fragment and press Alt+Q",
        "translate": "Translate",
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
    },
    "RU": {
        "esc": "Esc — закрыть",
        "no_text": "Текст не выделен — выделите фрагмент и нажмите Alt+Q",
        "translate": "Перевести",
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
    },
}

_u32 = ctypes.WinDLL("user32")


def _error_text(exc: Exception, t: dict[str, str]) -> str:
    name = type(exc).__name__
    message = str(exc).strip()
    lowered = message.lower()
    if any(word in name for word in ("Connection", "Timeout", "Proxy")) or "connect" in lowered:
        return t["no_connection"]
    if "TooMany" in name:
        return t["rate_limit"]
    return message[:180] or name


class PopupMenu:
    """Single-use menu window: lives from show until Esc / outside click."""

    def __init__(self, master, text, old_clipboard, target_hwnd, anchor, on_close):
        self.text = (text or "").strip()
        self.old_clipboard = old_clipboard
        self.target_hwnd = target_hwnd
        self.anchor = anchor
        self.on_close = on_close

        self.results: queue.Queue[tuple[bool, object]] = queue.Queue()
        self._closed = False
        self._pos: tuple[int, int] | None = None
        self._result = ""
        self._action_key = "copy"
        self._action_cb = None
        self._status_key = ""
        self.ui_lang = actions.get_ui_lang()
        self._t = UI_STRINGS[self.ui_lang]
        self._shown_at = 0.0
        self._mouse_was_down = False

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
            self.win, fg_color=PANEL, corner_radius=14, border_width=1, border_color=BORDER
        )
        self.panel.pack(fill="both", expand=True)

        body = ctk.CTkFrame(self.panel, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=14, pady=12)

        head = ctk.CTkFrame(body, fg_color="transparent")
        head.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(
            head, text="QuickMenu", font=ctk.CTkFont("Segoe UI Semibold", 12), text_color=ACCENT
        ).pack(side="left")
        self.esc_label = ctk.CTkLabel(
            head, text=self._t["esc"], font=ctk.CTkFont("Segoe UI", 10), text_color=MUTED
        )
        self.esc_label.pack(side="right")
        self.ui_switch = ctk.CTkSegmentedButton(
            head,
            values=list(UI_STRINGS),
            command=self._on_ui_lang,
            width=84,
            height=22,
            corner_radius=6,
            selected_color="#2a3550",
            selected_hover_color="#34426b",
            unselected_color="#1f232e",
            unselected_hover_color=HOVER,
            text_color=FG,
            font=ctk.CTkFont("Segoe UI", 10),
        )
        self.ui_switch.set(self.ui_lang)
        self.ui_switch.pack(side="right", padx=(0, 10))

        preview = self.text[:700] + ("…" if len(self.text) > 700 else "")
        if not preview:
            preview = self._t["no_text"]
        self.preview = self._textbox(body, PREVIEW_H, MUTED if not self.text else FG)
        self._fill(self.preview, preview)
        self.preview.pack(fill="x")

        grid = ctk.CTkFrame(body, fg_color="transparent")
        grid.pack(fill="x", pady=(10, 0))
        for column in (0, 1):
            grid.grid_columnconfigure(column, weight=1, uniform="btn")

        # Cell (0, 0) holds "Translate" plus a compact target-language picker.
        translate_cell = ctk.CTkFrame(grid, fg_color="transparent")
        translate_cell.grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=3)
        translate_cell.grid_columnconfigure(0, weight=1)

        self.buttons = []
        self.button_keys = ("translate", "layout", "calc", "google")
        for index, (key, command) in enumerate(
            (
                ("translate", self._translate),
                ("layout", self._layout),
                ("calc", self._calc),
                ("google", self._google),
            )
        ):
            first = index == 0
            button = ctk.CTkButton(
                translate_cell if first else grid,
                text=self._t[key],
                command=command,
                height=32,
                corner_radius=8,
                fg_color="#1f232e",
                hover_color=HOVER,
                border_width=1,
                border_color=BORDER,
                text_color=FG,
                font=ctk.CTkFont("Segoe UI", 12),
            )
            if first:
                button.grid(row=0, column=0, sticky="ew")
                self.lang_menu = self._lang_menu(translate_cell)
                self.lang_menu.grid(row=0, column=1, sticky="e", padx=(6, 0))
            else:
                button.grid(
                    row=index // 2,
                    column=index % 2,
                    sticky="ew",
                    padx=(0, 6) if index % 2 == 0 else (6, 0),
                    pady=3,
                )
            self.buttons.append(button)
        if not self.text:
            for button in self.buttons:
                button.configure(state="disabled")

        self.result_box = ctk.CTkFrame(body, fg_color="transparent")
        self.res_text = self._textbox(self.result_box, RESULT_H, FG)
        self.res_text.pack(fill="x", pady=(10, 6))

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
            height=30,
            corner_radius=8,
            fg_color="#2a3550",
            hover_color="#34426b",
            text_color=FG,
            font=ctk.CTkFont("Segoe UI", 12),
        )

        self.boosty = ctk.CTkButton(
            body,
            text=self._t["boosty"],
            command=lambda: actions.open_url(actions.BOOSTY_URL),
            height=22,
            corner_radius=6,
            fg_color="transparent",
            hover_color="#1f232e",
            text_color="#6d7486",
            font=ctk.CTkFont("Segoe UI", 10),
        )
        self.boosty.pack(pady=(8, 0))

    @staticmethod
    def _textbox(parent, height: int, text_color: str) -> ctk.CTkTextbox:
        return ctk.CTkTextbox(
            parent,
            height=height,
            corner_radius=8,
            border_width=0,
            border_spacing=6,
            fg_color=FIELD,
            text_color=text_color,
            font=ctk.CTkFont("Segoe UI", 12),
            wrap="word",
            scrollbar_button_color="#252a36",
            scrollbar_button_hover_color="#323847",
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
            height=32,
            corner_radius=8,
            fg_color="#1f232e",
            button_color="#1f232e",
            button_hover_color=HOVER,
            dropdown_fg_color=PANEL,
            dropdown_hover_color=HOVER,
            text_color=FG,
            command=self._on_lang_change,
            font=ctk.CTkFont("Segoe UI", 12),
            dropdown_font=ctk.CTkFont("Segoe UI", 12),
            dynamic_resizing=False,
        )
        menu.set(actions.get_target_lang())
        return menu

    # ------------------------------------------------------------------ lifecycle

    def show(self) -> None:
        self._shown_at = time.monotonic()
        self.win.update_idletasks()
        self._place(initial=True)
        self.win.deiconify()
        self.win.lift()
        self._take_focus()
        self._mouse_was_down = self._left_button_down()
        self.win.bind("<Escape>", lambda _event: self.close())
        self.win.bind("<FocusOut>", self._on_focus_out)
        self.win.after(60, self._keep_focus)
        self.win.after(40, self._drain)
        self.win.after(150, self._watch_mouse)

    def _take_focus(self) -> None:
        try:
            actions.focus_window(int(self.win.wm_frame(), 16))
        except (tk.TclError, ValueError):
            pass
        try:
            self.win.focus_force()
        except tk.TclError:
            pass

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
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
        width = max(WIDTH, self.panel.winfo_reqwidth() + 2)
        height = self.panel.winfo_reqheight()
        left, top, screen_w, screen_h = actions.virtual_screen()
        if initial or self._pos is None:
            ax, ay = self.anchor
            x = min(max(left + 8, ax + 12), left + screen_w - width - 8)
            y = ay + 20
            if y + height > top + screen_h - 56:
                y = max(top + 8, ay - height - 20)
            self._pos = (x, y)
        x, y = self._pos
        x = max(left + 8, min(x, left + screen_w - width - 8))
        y = max(top + 8, min(y, top + screen_h - height - 56))
        self.win.geometry(f"{width}x{height}+{int(x)}+{int(y)}")

    def _resize(self) -> None:
        if not self._closed:
            self._place()

    # ------------------------------------------------------------------ closing on outside click

    @staticmethod
    def _left_button_down() -> bool:
        return bool(_u32.GetAsyncKeyState(actions.VK_LBUTTON) & 0x8000)

    def _on_focus_out(self, _event=None) -> None:
        self.win.after(90, self._check_focus)

    def _check_focus(self) -> None:
        if self._closed or time.monotonic() - self._shown_at < 0.3:
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

    def _on_ui_lang(self, value: str) -> None:
        if value not in UI_STRINGS or value == self.ui_lang:
            return
        self.ui_lang = value
        actions.set_ui_lang(value)
        self._apply_language()

    def _apply_language(self) -> None:
        self._t = UI_STRINGS[self.ui_lang]
        self.esc_label.configure(text=self._t["esc"])
        self.boosty.configure(text=self._t["boosty"])
        for key, button in zip(self.button_keys, self.buttons):
            button.configure(text=self._t[key])
        if not self.text:
            self._fill(self.preview, self._t["no_text"])
        self.action_btn.configure(text=self._t[self._action_key])
        if self._status_key:
            self.status.configure(text=self._t[self._status_key])
        self._resize()

    def _on_lang_change(self, value: str) -> None:
        actions.set_target_lang(value)

    def _translate(self) -> None:
        if not self.text:
            return
        lang = self.lang_menu.get()
        self._start(
            lambda: actions.translate_text(self.text, lang), "translating", "copy", self._copy
        )

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
            self.result_box.pack(fill="x")
        self._fill(self.res_text, self._t[status_key])
        self.status.configure(text="", text_color=MUTED)
        self.action_btn.pack_forget()
        self._resize()
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
        self._resize()

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
        self.close()
        threading.Thread(
            target=actions.replace_selection, args=(text, previous, hwnd), daemon=True
        ).start()
