
QuickMenu

An Alt+Q popup action menu for Windows: select any text → press Alt+Q → a compact menu appears right next to your cursor.

Installation & Launch

bash
pip install -r requirements.txt
pythonw main.py
Используйте код с осторожностью.
pythonw runs the app without a console window; use python main.py for debugging.

Features

• Translate — RU ↔ EN (and other supported languages) via deep_translator (Google), displaying the result in the same window + a "Copy" button.
If Google hits a rate limit, a fallback endpoint is used automatically; if there is no connection, a clear error message is shown.
• Fix Layout — converts QWERTY ↔ ЙЦУКЕН in both directions; the "Replace in text" button pastes the result directly over the selected text.
• Calculate — safe arithmetic evaluation (ast) supporting + - * / // % **, parentheses, , as a decimal separator, and × ÷ − ^.
• Google Search — searches the selected text in your default browser.
• Support on Boosty — opens https://boosty.to/stratapak/donate (actions.BOOSTY_URL constant).
The window closes on Esc, clicking outside, or losing focus; after clicking "Copy", it closes automatically after 0.65 s.

Files


File	Description
main.py	tray icon, global hotkey (RegisterHotKey), Tk event queue
actions.py	WinAPI clipboard handling, Ctrl+C/Ctrl+V, translation, layout conversion, calculator, links
popup_ui.py	customtkinter window: preview, buttons, result display, auto-close logic


How It Works

• The hotkey is registered via RegisterHotKey(MOD_ALT, VK_Q) rather than by character, so it works regardless of the active keyboard layout (including Russian).
• Selected text is copied via SendInput using virtual key codes (Ctrl+C), while the previous clipboard text is preserved and restored afterward.
• "Replace in text" brings the source window to the foreground (SetForegroundWindow bypassing the foreground lock), pastes the text via Ctrl+V, and restores the clipboard.
• The borderless, topmost window features rounded corners (-transparentcolor), positions itself near the cursor, and snaps to screen edges.

Limitations

• Only text clipboard content is restored: if an image or files were in the clipboard, they will be lost (a limitation of WinAPI plain-text handling).
• Global hooks/hotkeys do not trigger over windows running as administrator if QuickMenu is launched without admin privileges. Run it as administrator if you need to use it in such windows.
• Google may rate-limit frequent translation requests from a single IP — an error message will be shown in that case.
• Tested on Windows 11, Python 3.13.
 
 
Note:
• SmartScreen warning: Since the .exe is built with PyInstaller and is not code-signed, Windows SmartScreen may show a warning on first launch — just click "More info" → "Run anyway" (the full source code is open in this repository).
• Auto-install & Startup: The app automatically sets itself up on your PC and adds itself to Windows startup. Once launched, simply check your system tray (or select any text and press Alt+Q) to verify that it is up and running.
