# PyInstaller spec for CmdVault — builds a standalone executable.
# Requires: pip install pyinstaller
# Build (from project root): pyinstaller cmdvault_app.spec

a = Analysis(
    ['cmdvault/__main__.py'],
    pathex=['.'],
    datas=[],
    hiddenimports=['tkinter', 'cmdvault', 'cmdvault.main', 'cmdvault.db', 'cmdvault.ui', 'cmdvault.themes', 'cmdvault.utils'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='CmdVault',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,   # GUI app — no terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
