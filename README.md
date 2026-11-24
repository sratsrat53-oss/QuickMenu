
QuickMenu

A lightweight Windows utility that saves time on small daily tasks. Press Alt+Q (customizable), and a menu pops up right next to your cursor: translate text, fix keyboard layout, calculate an expression, or quickly Google something. You don't even need to select text first—just open the menu and type your query.
No administrator rights required, no keylogging, and the source code is completely open. You can read it yourself to see what it does.

How to Run

bash
pip install -r requirements.txt
pythonw main.py
Используйте код с осторожностью.
pythonw runs the app without a console window. If something doesn't work and you want to see the error logs, run it via python main.py.
Upon launch, a notification will show your active hotkey, and a tray icon will appear. From the tray menu, you can open the popup, access settings, or exit. If you launch QuickMenu a second time, the duplicate instance will silently close.

Want to build the .exe yourself?

bash
pip install pyinstaller
pyinstaller QuickMenu.spec
Используйте код с осторожностью.
The compiled QuickMenu.exe will appear in the dist folder.

Features

• Translate. Two modes, selectable next to the button:
	• Text — translates selected text. The source language is auto-detected, and it translates into your chosen target language: EN, RU, ES, DE, FR, JA, ZH, KO, UK, PL, or TR.
	• Image — no text selection needed: click "Translate," the screen freezes, drag your mouse over an area containing text, and the app recognizes it using Windows' built-in OCR and translates it. This allows you to translate text on images and screenshots.
	• The result appears in the same window and can be copied with a single click. If Google blocks requests due to rate limits, the app tries fallback providers—and if nothing works, it will honestly let you know.
• Layout. Typed "ghbdtn" instead of "привет"? Click the button to convert the text to the right layout. Works both ways, and "Replace in text" immediately pastes the fixed version over your selection.
• Calculate. Supports + - * / // % **, parentheses, commas instead of decimal points, and symbols like × ÷ − ^. Evaluates math safely without using eval.
• Google. Opens a web search for the selected text.
• Search bar at the bottom. Press the hotkey, type your query, hit Enter. No need to open a browser beforehand.
• Settings (⚙ button or tray menu). Change the interface language (Russian or English) and customize your hotkey. New hotkeys take effect immediately without restarting.
You can drag the window by its top bar (even to another monitor) and resize its width by dragging the right edge (the width is saved). It closes when you press Esc, click outside, or when it loses focus.

Security & Privacy

I understand that trusting an unknown .exe is hard, so here is the short and honest breakdown:
• No admin rights are required.
• No keylogging. The hotkey is registered via native Windows API (RegisterHotKey), not by hooking or intercepting all keystrokes.
• Selected text is copied only at the exact moment you press the hotkey, and your previous clipboard text is restored afterward.
• Network access is used strictly for translation: only the text you explicitly send for translation goes to Google Translate (or MyMemory as a fallback). Nothing else.
• Image text recognition (Windows.Media.Ocr) runs 100% locally. Screenshots are never uploaded anywhere—only the extracted text is sent for translation.
• All source code is right here. You can inspect it or compile it yourself.
• The .exe is unsigned because code-signing certificates cost money and this is a free project. Because of this, Windows SmartScreen might show a warning. If you don't trust the pre-built .exe, run it from the source or build it yourself.

Project Structure


File	Description
main.py	System tray icon, startup notification, single-instance protection, hotkey registration
actions.py	Clipboard handling, translation, layout switcher, calculator, search, settings
popup_ui.py	UI windows built with customtkinter: popup menu and settings
quickmenu_config.json	Your user settings, generated next to the executable/script
QuickMenu.spec	PyInstaller build configuration


Under the Hood

• The hotkey is bound to the physical key scan code, so it works regardless of your active keyboard layout (including Cyrillic).
• To grab selected text, the app simulates Ctrl+C via SendInput, backs up your previous clipboard text, and restores it afterward.
• For "Replace in text," focus is returned to the original window first, the text is pasted via Ctrl+V, and the clipboard is restored.
• A named Windows mutex prevents multiple instances from running simultaneously.
• Borderless, always-on-top window with rounded corners. Spawns near the cursor on the active monitor while respecting taskbar boundaries.

Good to Know

• Only plain text in the clipboard is backed up and restored. If you had an image or copied files in your clipboard, they will be overwritten.
• Hotkeys won't trigger over windows running as Administrator unless QuickMenu itself is also run as Administrator. Only run it as admin if you genuinely need to.
• If Ctrl+C acts as an interrupt/cancel command in your active window (e.g., inside a terminal/console), pressing the hotkey will send that interrupt signal.
• Google occasionally temporarily blocks IPs that send too many translation requests in a short time. If that happens, just wait a bit.
• Tested on Windows 11 and Python 3.13.
If you'd like me to refine this for a GitHub README, let me know:
• Your GitHub username and repository name (so I can add proper clone/download commands and links)
• Preferred tone (casual indie dev, formal documentation, or concise)
