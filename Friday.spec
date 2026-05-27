# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — builds Friday.app, a double-clickable macOS app.

Build it with the helper:  ./build.sh
(which runs `pyinstaller --noconfirm Friday.spec` inside the venv).

Friday is only the UI. The brain runs in the separate oMLX server, so nothing
about the model is bundled here — just the window, the bridge, and web assets.
"""

from PyInstaller.utils.hooks import collect_all

# web/index.html + the cat sprites must ship inside the app.
datas = [("web", "web")]
binaries = []
# macOS frameworks pywebview's Cocoa backend talks to (helps PyInstaller's
# analysis find them even when imported lazily).
hiddenimports = ["objc", "Foundation", "AppKit", "WebKit", "Quartz", "Security"]

# pywebview (cocoa backend), the mic lib (ships a PortAudio dylib as data), and
# the global-hotkey lib all have pieces PyInstaller misses without collect_all.
for pkg in ("webview", "sounddevice", "pynput"):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

a = Analysis(
    ["app_main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PySide6", "PyQt5", "PyQt6", "tkinter", "matplotlib"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Friday",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # GUI app — no terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Friday",
)

app = BUNDLE(
    coll,
    name="Friday.app",
    icon="assets/friday.icns",
    bundle_identifier="uk.bochen.friday",
    info_plist={
        "CFBundleName": "周五",
        "CFBundleDisplayName": "周五 Friday",
        "CFBundleShortVersionString": "0.1.0",
        "CFBundleVersion": "0.1.0",
        # Shown when macOS asks for mic permission (口语反馈要用麦克风).
        "NSMicrophoneUsageDescription": (
            "周五用麦克风听你说英语，给口语反馈。"
            "Friday uses the microphone for spoken-English feedback."
        ),
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "11.0",
    },
)
