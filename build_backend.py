#!/usr/bin/env python3
"""
PyInstaller build script for the Script-to-Speech GUI backend.

This script creates a standalone executable that can be bundled with the Tauri app
for self-contained distribution without requiring Python/uv to be installed.

The executable is renamed with a platform-specific target triple suffix (e.g.,
sts-gui-backend-x86_64-apple-darwin) to comply with Tauri's sidecar naming convention.
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path


def get_target_triple():
    """
    Detect the platform target triple for Tauri sidecar naming.

    Returns:
        str: Target triple (e.g., 'x86_64-apple-darwin', 'x86_64-pc-windows-msvc')

    Raises:
        RuntimeError: If target triple cannot be determined
    """
    try:
        # Try to get target triple from rustc (most reliable)
        result = subprocess.run(
            ["rustc", "-vV"], capture_output=True, text=True, check=True
        )

        # Parse output for "host: <target-triple>"
        match = re.search(r"host:\s+(\S+)", result.stdout)
        if match:
            return match.group(1)

    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback: detect from platform
        print("⚠️  rustc not found, falling back to platform detection...")
        import platform

        system = platform.system().lower()
        machine = platform.machine().lower()

        # Map to common target triples
        if system == "darwin":
            if machine == "arm64" or machine == "aarch64":
                return "aarch64-apple-darwin"
            else:
                return "x86_64-apple-darwin"
        elif system == "windows":
            return "x86_64-pc-windows-msvc"
        elif system == "linux":
            return "x86_64-unknown-linux-gnu"

    raise RuntimeError("Could not determine platform target triple")


def main():
    """Build the GUI backend executable using PyInstaller."""
    print("🔨 Building Script-to-Speech GUI Backend executable...")

    # Ensure we're in the project root
    project_root = Path(__file__).parent
    src_dir = project_root / "src"

    if not src_dir.exists():
        print(
            "❌ Error: src directory not found. Make sure you're running from project root."
        )
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
        "--name",
        "sts-gui-backend",  # Executable name
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(build_dir),
        "--specpath",
        str(project_root),
        "--add-data",
        f"{src_dir / 'script_to_speech' / 'voice_library' / 'voice_library_data'}:script_to_speech/voice_library/voice_library_data",
        "--add-data",
        f"{src_dir / 'script_to_speech' / 'text_processors' / 'configs'}:script_to_speech/text_processors/configs",
        "--add-data",
        f"{src_dir / 'script_to_speech' / 'tts_providers'}:script_to_speech/tts_providers",
        "--hidden-import",
        "script_to_speech.gui_backend",
        "--hidden-import",
        "script_to_speech.tts_providers",
        "--hidden-import",
        "script_to_speech.tts_providers.base",
        "--hidden-import",
        "script_to_speech.tts_providers.openai",
        "--hidden-import",
        "script_to_speech.tts_providers.elevenlabs",
        "--hidden-import",
        "script_to_speech.tts_providers.cartesia",
        "--hidden-import",
        "script_to_speech.tts_providers.minimax",
        "--hidden-import",
        "script_to_speech.tts_providers.zonos",
        "--hidden-import",
        "script_to_speech.tts_providers.dummy_common",
        "--hidden-import",
        "script_to_speech.tts_providers.dummy_stateful",
        "--hidden-import",
        "script_to_speech.tts_providers.dummy_stateless",
        "--hidden-import",
        "script_to_speech.voice_library",
        "--hidden-import",
        "script_to_speech.text_processors",
        "--hidden-import",
        "script_to_speech.audio_generation",
        "--hidden-import",
        "script_to_speech.parser",
        "--hidden-import",
        "script_to_speech.parser.process",
        "--hidden-import",
        "script_to_speech.parser.screenplay_parser",
        "--hidden-import",
        "script_to_speech.parser.analyze",
        # Python 3.13+ built-in modules that PyInstaller may miss
        "--hidden-import",
        "_contextvars",  # Required for asyncio in Python 3.13
        "--hidden-import",
        "_hashlib",  # Required for hashlib algorithms
        "--hidden-import",
        "_ssl",  # Required for SSL/TLS support
        "--hidden-import",
        "unicodedata",  # Required for tqdm and other text processing
        "--console",  # Console app for debugging
        str(main_script),
    ]

    print(f"🚀 Running PyInstaller...")
    print(f"   Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Build completed successfully!")

        # Get platform target triple for Tauri sidecar naming
        try:
            target_triple = get_target_triple()
            print(f"🎯 Detected target triple: {target_triple}")
        except RuntimeError as e:
            print(f"❌ Error: {e}")
            sys.exit(1)

        # Rename the generated executable with platform target triple
        base_executable = dist_dir / "sts-gui-backend"

        if base_executable.exists():
            # Rename with target triple suffix
            new_executable = dist_dir / f"sts-gui-backend-{target_triple}"

            # Remove existing file if it exists
            if new_executable.exists():
                new_executable.unlink()

            # Rename the executable
            base_executable.rename(new_executable)

            # Get file size
            file_size = new_executable.stat().st_size

            print(f"📦 Executable created: {new_executable}")
            print(f"   Size: {file_size / 1024 / 1024:.1f} MB")

            # Copy to Tauri binaries directory for bundling
            tauri_binaries_dir = (
                project_root / "gui" / "frontend" / "src-tauri" / "binaries"
            )
            tauri_binaries_dir.mkdir(parents=True, exist_ok=True)
            tauri_binary_path = tauri_binaries_dir / f"sts-gui-backend-{target_triple}"

            # Remove existing file or directory if it exists
            if tauri_binary_path.exists():
                if tauri_binary_path.is_dir():
                    shutil.rmtree(tauri_binary_path)
                else:
                    tauri_binary_path.unlink()

            # Copy the single executable file
            shutil.copy2(new_executable, tauri_binary_path)
            print(f"📋 Copied to Tauri binaries: {tauri_binary_path}")
            print(f"✨ Ready for Tauri sidecar bundling!")
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
