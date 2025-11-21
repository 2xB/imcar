# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

# Collect all PyQt5 and imcar modules
pyqt5_datas, pyqt5_binaries, pyqt5_hiddenimports = collect_all('PyQt5')
imcar_datas, imcar_binaries, imcar_hiddenimports = collect_all('imcar')

# Additional libraries needed for Qt xcb plugin on Linux
# These are required for the xcb platform plugin to work correctly
added_binaries = []
if sys.platform.startswith('linux'):
    try:
        # Try to add xcb libraries if they exist
        xcb_libs = [
            '/lib/x86_64-linux-gnu/libxcb-icccm.so.4',
            '/lib/x86_64-linux-gnu/libxcb-image.so.0',
            '/lib/x86_64-linux-gnu/libxcb-keysyms.so.1',
            '/lib/x86_64-linux-gnu/libxcb-render-util.so.0',
            '/lib/x86_64-linux-gnu/libxcb-xinerama.so.0',
            '/lib/x86_64-linux-gnu/libxcb-xkb.so.1',
            '/lib/x86_64-linux-gnu/libxcb-util.so.1',
            '/lib/x86_64-linux-gnu/libxcb-shape.so.0',
            '/lib/x86_64-linux-gnu/libxkbcommon-x11.so.0',
            '/lib/x86_64-linux-gnu/libxkbcommon.so.0',
        ]
        for lib in xcb_libs:
            if os.path.exists(lib):
                added_binaries.append((lib, '.'))
    except Exception as e:
        print(f"Warning: Could not add some xcb libraries: {e}")

a = Analysis(
    ['start.py'],
    pathex=[],
    binaries=pyqt5_binaries + imcar_binaries + added_binaries,
    datas=pyqt5_datas + imcar_datas,
    hiddenimports=pyqt5_hiddenimports + imcar_hiddenimports + [
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'PyQt5.QtWebEngineWidgets',
        'faultguard',
        'faulthandler',
        'multiprocessing',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='imcar',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='imcar',
)
