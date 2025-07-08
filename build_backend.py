#!/usr/bin/env python3
"""
PyInstaller build script for the Script-to-Speech GUI backend.

This script creates a standalone executable that can be bundled with the Tauri app
for self-contained distribution without requiring Python/uv to be installed.
"""

import shutil
import subprocess
import sys
from pathlib import Path


def main():
    """Build the GUI backend executable using PyInstaller."""
    print("🔨 Building Script-to-Speech GUI Backend executable...")
    
    # Ensure we're in the project root
    project_root = Path(__file__).parent
    src_dir = project_root / "src"
    
    if not src_dir.exists():
        print("❌ Error: src directory not found. Make sure you're running from project root.")
        sys.exit(1)
    
    # Main script path
    main_script = src_dir / "script_to_speech" / "gui_backend" / "main.py"
    
    if not main_script.exists():
        print(f"❌ Error: Main script not found at {main_script}")
        sys.exit(1)
    
    # Output directory
    dist_dir = project_root / "dist"
    build_dir = project_root / "build"
    
    # Clean previous builds
    if dist_dir.exists():
        print("🧹 Cleaning previous build...")
        shutil.rmtree(dist_dir)
    if build_dir.exists():
        shutil.rmtree(build_dir)
    
    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--onefile",  # Single executable file
        "--name", "sts-gui-backend",  # Executable name
        "--distpath", str(dist_dir),
        "--workpath", str(build_dir),
        "--specpath", str(project_root),
        "--add-data", f"{src_dir / 'script_to_speech' / 'voice_library' / 'voice_library_data'}:script_to_speech/voice_library/voice_library_data",
        "--add-data", f"{src_dir / 'script_to_speech' / 'text_processors' / 'configs'}:script_to_speech/text_processors/configs",
        "--hidden-import", "script_to_speech.gui_backend",
        "--hidden-import", "script_to_speech.tts_providers",
        "--hidden-import", "script_to_speech.voice_library",
        "--hidden-import", "script_to_speech.text_processors",
        "--hidden-import", "script_to_speech.audio_generation",
        "--console",  # Console app for debugging
        str(main_script)
    ]
    
    print(f"🚀 Running PyInstaller...")
    print(f"   Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Build completed successfully!")
        
        # Check if executable was created
        executable = dist_dir / "sts-gui-backend"
        if executable.exists():
            print(f"📦 Executable created: {executable}")
            print(f"   Size: {executable.stat().st_size / 1024 / 1024:.1f} MB")
        else:
            print("⚠️  Warning: Executable not found in expected location")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed with exit code {e.returncode}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()