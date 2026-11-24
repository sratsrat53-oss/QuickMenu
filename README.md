# QuickMenu

A small Windows utility for everyday text tasks. Press **Alt+Q** (the hotkey is configurable) and a menu pops up next to your cursor: translate text, fix a wrong keyboard layout, calculate an expression, or search Google. Selecting text first is optional: you can open the menu and just type a query.

## How to run

```bash
pip install -r requirements.txt
pythonw main.py
```

`pythonw` runs the app without a console window. If something doesn't work and you want to see the errors, run `python main.py` instead.

After launch you'll get a notification with the hotkey and a tray icon. From the tray you can open the menu, go to settings, or exit.

## What it does

- **Translate** — two modes, switchable next to the button:
  - **Text** translates the selected text. The source language is detected automatically; pick the target: EN, RU, ES, DE, FR, JA, ZH, UK, PL or TR.
  - **Photo** needs no selection: click "Translate", the screen freezes, drag a rectangle over any text (an image, a screenshot, a video), and the app recognizes it with the built-in Windows OCR and translates it.

  The result appears in the same window and can be copied with one click.
- **Fix Layout** — typed "ghbdtn" instead of "привет"? One click converts the text to the right layout, in both directions. "Replace in text" puts the fixed version straight over your selection.
- **Calculate** — supports `+ - * / // % **`, parentheses, a comma as the decimal separator, and the symbols `× ÷ − ^`.
- **Google Search** — searches for the selected text.
- **Search bar** — press the hotkey, type a query, hit Enter. No need to open a browser first.
- **Settings** (the ⚙ button or the tray menu) — change the interface language (English or Russian) and the hotkey. The new hotkey works immediately, no restart needed.

The window can be dragged by its top strip, and closes with `Esc`, a click outside, or when it loses focus.
