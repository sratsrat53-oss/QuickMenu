# QuickMenu

A tiny Windows utility that saves time on small everyday tasks. Press **Alt+Q** (configurable), and a compact menu pops up right next to your cursor: translate text, fix keyboard layout, solve math expressions, or quickly Google something. You don't even need to select text first — just open the menu and type your search query.

No admin rights required, no keylogging, fully open-source. You can inspect everything it does.

## How to run

```bash
pip install -r requirements.txt
pythonw main.py
```

`pythonw` runs the app silently without a console window. If something goes wrong and you want to see errors, launch it via `python main.py`.

Once started, you'll see a startup notification showing your hotkey and a new icon in the system tray. From there, you can open the menu, tweak settings, or exit. If you try to launch QuickMenu a second time, the duplicate instance will quietly close itself.

Want to build the `.exe` yourself?

```bash
pip install pyinstaller
pyinstaller QuickMenu.spec
```

The compiled `QuickMenu.exe` will appear inside the `dist` folder.

## Features

- **Translate.** Automatically detects the source language and translates into the target language selected next to the button: EN, RU, ES, DE, FR, JA, ZH, UK, PL, or TR. The result appears right inside the window and can be copied with a single click. If Google rate-limits frequent requests, the app automatically falls back to backup endpoints — or shows a clear error message if offline.
- **Fix Layout.** Typed "ghbdtn" instead of "привет" (or vice versa)? Click the button to convert the text between QWERTY and ЙЦУКЕН. Clicking **Replace in text** pastes the fixed text directly over your selection.
- **Calculate.** Supports `+ - * / // % **`, parentheses, commas as decimal separators, and symbols like `× ÷ − ^`. Evaluated safely using AST parsing (no `eval`).
- **Google Search.** Opens a browser search for your selected text.
- **Bottom search bar.** Press the hotkey, type your query, and hit `Enter`. No need to open your browser beforehand.
- **Settings** (`⚙` button or via the tray menu). Change the interface language (English or Russian), switch between 6 color themes, or set a custom global hotkey. New hotkeys take effect immediately without a restart.

You can drag the window by its top bar anywhere on the screen — even across multiple monitors. It closes when you press `Esc`, click outside, or when it loses focus.

## Security & Privacy

I get why trusting a random `.exe` from the internet feels sketchy, so here is the honest breakdown:

- **No admin rights needed.**
- **No keylogging.** The hotkey is registered via the native Windows API (`RegisterHotKey`), not by hooking or recording your keystrokes.
- **Clipboard safety.** Selected text is copied only at the exact moment you trigger the hotkey, and your previous text clipboard is restored right after.
- **Minimal network usage.** The internet is used strictly for translation: only the text you explicitly send for translation goes to Google Translate (or the MyMemory fallback). Nothing else.
- **Fully open-source.** All code is right here — read it or build it yourself.
- **Unsigned binary.** Code-signing certificates cost money, and this is a free hobby project, so Windows SmartScreen may show a warning. If you don't trust the prebuilt `.exe`, just run it from source or compile it yourself.

## Project Structure

| File | Purpose |
| --- | --- |
| `main.py` | Tray icon, startup notification, single-instance lock, global hotkey listener |
| `actions.py` | Clipboard handling, translation, layout conversion, calculator, search, config |
| `popup_ui.py` | `customtkinter` UI windows: action popup and settings panel |
| `quickmenu_config.json` | Your saved preferences (created automatically next to the app) |
| `QuickMenu.spec` | Build script for PyInstaller |

## Under the Hood

- The global hotkey is bound to a physical virtual-key code, so it works regardless of your active keyboard layout.
- To grab selected text, the app simulates `Ctrl+C` via `SendInput`, backs up your current clipboard text, and restores it afterward.
- When clicking **Replace in text**, focus is returned to your previous window first, the text is pasted via `Ctrl+V`, and the old clipboard is restored.
- A named Windows mutex prevents multiple background instances from running at the same time.
- Frameless, always-on-top window with rounded corners that spawns near your cursor while respecting multi-monitor bounds and taskbar work areas.

## Good to Know

- Only **plain text** in the clipboard is restored. If you had an image or copied files in your clipboard beforehand, they will be overwritten.
- The global hotkey won't trigger on top of windows running **as Administrator** unless QuickMenu is also launched as Administrator. Run it elevated only if you actually need that.
- If `Ctrl+C` means "interrupt" in the active window (such as a terminal), triggering the hotkey there will send an interrupt signal.
- Google occasionally rate-limits frequent translation requests from the same IP — if that happens, just wait a bit and try again.
- Tested on Windows 11 and Python 3.13.

## Support

If you find this tool useful, you can leave a tip on [Boosty](https://boosty.to). Totally optional, always appreciated.
