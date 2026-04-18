# -*- mode: python ; coding: utf-8 -*-
import platform

block_cipher = None
is_macos = platform.system() == 'Darwin'

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src/data', 'data'),
        ('src/config', 'config'),
    ],
    hiddenimports=[
        'selenium',
        'pyautogui',
        'pynput',
        'webdriver_manager',
        'tkinter',
        'pynput.keyboard',
        'pynput.mouse',
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
    name='AutoMouse',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

if is_macos:
    app = BUNDLE(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='AutoMouse',
        bundle_identifier='com.automouse.app',
        info_plist={
            'CFBundleName': 'AutoMouse',
            'CFBundleDisplayName': 'Auto Mouse',
            'CFBundleIdentifier': 'com.automouse.app',
            'CFBundleVersion': '1.0.0',
            'CFBundleShortVersionString': '1.0.0',
            'CFBundlePackageType': 'APPL',
            'CFBundleExecutable': 'AutoMouse',
            'LSMinimumSystemVersion': '10.15',
            'NSHumanReadableCopyright': 'Copyright 2024',
            'LSApplicationCategoryType': 'public.app-category.utilities',
        },
    )
else:
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='AutoMouse',
    )
