# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Get project root directory (SPECPATH is provided by PyInstaller)
project_root = Path(SPECPATH)
src_dir = project_root / 'src'

# Dynamically collect all submodules from packages using importlib.import_module()
dynamic_packages = [
    'script_to_speech.gui_backend',
    'script_to_speech.tts_providers',
    'script_to_speech.text_processors',
    'script_to_speech.voice_library',
    'script_to_speech.audio_generation',
    'script_to_speech.parser',
]

# Build hidden imports list automatically
hiddenimports = []
for package in dynamic_packages:
    hiddenimports += collect_submodules(
        package,
        filter=lambda name: 'test' not in name and '__pycache__' not in name
    )

# Add Python 3.13+ standard library modules
hiddenimports += ['_contextvars', '_hashlib', '_ssl', 'unicodedata']

a = Analysis(
    [str(src_dir / 'script_to_speech' / 'gui_backend' / 'main.py')],
    pathex=[],
    binaries=[],
    datas=[
        (str(src_dir / 'script_to_speech' / 'voice_library' / 'voice_library_data'), 'script_to_speech/voice_library/voice_library_data'),
        (str(src_dir / 'script_to_speech' / 'text_processors' / 'configs'), 'script_to_speech/text_processors/configs'),
        (str(src_dir / 'script_to_speech' / 'tts_providers'), 'script_to_speech/tts_providers'),
        (str(src_dir / 'script_to_speech' / 'voice_casting'), 'script_to_speech/voice_casting'),
    ],
    hiddenimports=hiddenimports,
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
    name='sts-gui-backend',
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
