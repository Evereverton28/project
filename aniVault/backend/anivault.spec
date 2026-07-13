# AniVault.spec
#
# Build with:   pyinstaller anivault.spec
# Output:       dist/AniVault.exe   (single file)
#
# Re-run this exact command any time you change the source — no need to
# reconstruct these settings; this file IS the build configuration.

# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['desktop_app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('../frontend', 'frontend'),      # HTML/CSS/JS/favicon -> bundle/frontend/
        ('seed_data.json', '.'),          # -> bundle/seed_data.json (root, see paths.py)
    ],
    hiddenimports=[
        'flask_cors',
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AniVault',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,                        # no console window behind the app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='../frontend/favicon.ico',       # exe icon = your AniVault icon
)
