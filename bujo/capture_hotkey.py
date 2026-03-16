#!/usr/bin/env python3
"""Global hotkey capture for BuJo.

Registers Win+Shift+B (or Ctrl+Shift+B as fallback) to open a floating
capture window from anywhere.

Usage:
    python -m bujo.capture_hotkey
    bujo-capture
"""

import sys


def main() -> None:
    """Entry point. Blocks until interrupted."""
    if sys.platform == "win32":
        import ctypes

        if not ctypes.windll.shell32.IsUserAnAdmin():
            print("Warning: global hotkeys may require Administrator on Windows.")
            print("Running anyway...\n")

    print("BuJo capture active.")
    print("Press Win+Shift+B (or Ctrl+Shift+B) anywhere to capture.")
    print("Press Ctrl+C to quit.\n")

    try:
        import keyboard
    except ImportError:
        print("Error: 'keyboard' package not installed.")
        print("Install with: pip install keyboard")
        sys.exit(1)

    import tkinter as tk
    from pathlib import Path

    def open_capture():
        """Open a floating capture window."""
        from bujo.app import append_entry, ensure_vault
        from bujo.capture import parse_quick_input

        ensure_vault()

        root = tk.Tk()
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.geometry(
            "300x80+{}+{}".format(
                root.winfo_screenwidth() // 2 - 150,
                root.winfo_screenheight() // 2 - 40,
            )
        )
        root.configure(bg="#1e1e2e")

        frame = tk.Frame(root, bg="#1e1e2e", padx=10, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)

        entry = tk.Entry(
            frame,
            font=("Segoe UI", 11),
            bg="#313244",
            fg="#cdd6f4",
            insertbackground="#cdd6f4",
            relief="flat",
        )
        entry.pack(fill=tk.BOTH, expand=True)
        entry.focus_set()

        def save_and_close(event=None):
            text = entry.get().strip()
            if text:
                symbol, cleaned = parse_quick_input(text)
                append_entry(symbol, cleaned)
                print(f"  Captured: {cleaned}")
            root.destroy()

        def cancel(event=None):
            root.destroy()

        entry.bind("<Return>", save_and_close)
        entry.bind("<Escape>", cancel)

        root.mainloop()

    def hotkey_callback():
        """Called when hotkey is pressed."""
        open_capture()

    # Try Win+Shift+B first, fall back to Ctrl+Shift+B
    try:
        keyboard.add_hotkey("windows+shift+b", hotkey_callback)
    except Exception:
        try:
            keyboard.add_hotkey("ctrl+shift+b", hotkey_callback)
            print("Using Ctrl+Shift+B (Win+Shift+B unavailable)")
        except Exception as e:
            print(f"Error registering hotkey: {e}")
            sys.exit(1)

    try:
        keyboard.wait()
    except KeyboardInterrupt:
        print("\nBujo capture stopped.")


if __name__ == "__main__":
    main()
