# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['backend\\desktop_entry.py'],
    pathex=['backend'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'uvicorn', 'main', 'routers', 'capabilities', 'execution',
        'pandas', 'polars', 'openpyxl', 'pyautogui', 'pyscreeze', 'PIL', 
        'send2trash', 'requests', 'isort', 'difflib'
    ],
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
    name='backend-api',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
