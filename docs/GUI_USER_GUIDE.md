# Script to Speech GUI User Guide

The Script to Speech GUI provides a user-friendly interface for generating audiobooks from screenplays. It wraps the powerful CLI tools in a modern, intuitive desktop application.

## Getting Started

### Installation

The GUI is distributed as a standalone desktop application.

**Building from Source:**

To build the application yourself, see the [Building for Production](GUI_TECHNICAL.md#building-for-production) section in the technical documentation.

**Locating Built Applications:**

After building, you can find the application at:
- **macOS**: `gui/frontend/src-tauri/target/release/bundle/macos/Script to Speech.app`
- **macOS Installer**: `gui/frontend/src-tauri/target/release/bundle/dmg/Script to Speech_0.1.0_aarch64.dmg`

Simply double-click the `.app` file or install via the `.dmg` to launch the application.

### Launching the App

Upon opening the application, you will be greeted by the Project Selection screen. Here you can:
- **Open an existing project**: Select a previous project folder
- **Create a new project**: Start fresh with a new screenplay.

## Workflow

### 1. Creating a Project & Importing a Screenplay

1. Click **"New Project"**.
2. Use the file picker to select your screenplay PDF or text file.
3. The application will automatically parse the screenplay and identify characters.

### 2. Configuring API Keys

Before you can use voice casting or generation features, you must configure your API keys.

1. Click on the **Settings** icon (gear icon).
2. Enter your API keys for the providers you intend to use (e.g., OpenAI, ElevenLabs).
3. Keys are stored securely on your local machine.

### 3. Project Overview

The **Project Overview** tab provides a high-level summary of your current project.

- **Project Status**: Shows the current state (e.g., "Ready to Generate") and input/output paths.
- **Quick Links**: Cards to quickly navigate to key tools like Screenplay Info, Voice Casting, and Voice Testing.

### 4. Screenplay Information

The **Screenplay Info** screen offers a detailed analysis of your parsed script.

- **Statistics**: View total chunks, speakers, and other metrics.
- **Actions**:
    - **Re-parse**: Re-run the parser if you've modified the source file.
    - **Download JSON/Text**: Export the parsed data for inspection or manual editing.

### 5. Voice Casting

The **Voice Casting** interface allows you to assign voices to each character found in your script.

- **Character List**: List of characters, along with information on number of lines and total characters of dialogue. 
- **Voice Selection**: Click on "assign voice" on a character to assign a voice. You can filter voices by provider (OpenAI, ElevenLabs, etc.) using the tabs at the top of the selection screen
- **Audition**: Click the "Play" button next to a voice to hear a sample.
- **Custom Voice**: You can also configure a custom voice if supported by the provider.
- **LLM-Assisted Features**: Use the "Character Analysis" and "Voice Suggestions" buttons to enter flows to populate character analysis, and then suggest voices based on character descriptions.

### 6. Test Voices

The **Test Voices** tab is a playground for experimenting with different TTS providers and voices.

- **Text Input**: Type any text you want to hear.
- **Provider & Voice**: Select any configured provider and voice to test.
- **Parameters**: Adjust specific parameters (if supported by the provider).
- **History**: Play back previously generated test clips.

### 7. Audio Generation & Exporting (Coming Soon)

*Note: Full audio generation and exporting features are currently in development. The "Text Processing" and "Generate Audio" sections in the sidebar are currently placeholders.*

Once implemented, you will be able to:
- Configure text processing rules.
- Generate audio for the entire script.
- Export the final audiobook as an MP3 file.

## Manual Mode

**Manual Mode** allows you to use the GUI's tools independently of a specific project. This is particularly useful for CLI users who want to use specific GUI features (like the Voice Caster or Test Voices playground) to assist their command-line workflow.

**To enable Manual Mode:**
1. Toggle the **Manual Mode** switch in the bottom-left corner of the sidebar.

**Available Tools:**
- **Voice Casting**: Create a voice configuration file from scratch or edit an existing one.
- **Test Voices**: Experiment with TTS providers without affecting any project files.

## Troubleshooting

### API Errors

If you encounter errors when trying to use TTS providers:
1. **Configure API Keys**: Open Settings (gear icon) and enter your API keys for the providers you want to use.
2. **Verify Keys**: Ensure the keys are valid and have sufficient credits/quota.
3. **Check Provider Status**: Verify the provider's service is operational (check their status page).

### Backend Connection Issues

If the app launches but features don't work:
1. **Check Backend Status**: The app should show a connection indicator if the backend is running.
2. **Port Conflicts**: Another application might be using port 58735. Close other applications and restart.
3. **Permissions**: Ensure the app has necessary file system permissions on macOS.

### Audio Playback Issues

If voice samples don't play in the Voice Casting or Test Voices screens:
1. **Check Volume**: Ensure your system volume is not muted.
2. **Audio Codec**: Verify your system supports MP3 playback (should work on all modern systems).
3. **Reload**: Try refreshing the voice library or restarting the app.

### Performance Issues

If the app feels slow or unresponsive:
1. **Large Projects**: Processing very long screenplays may take time. Be patient during parsing operations.
2. **Memory**: Ensure sufficient free RAM is available (recommended: 4GB+).
3. **Close Other Apps**: Free up system resources by closing unnecessary applications.

### Getting More Help

For advanced troubleshooting and technical details, see the [Technical Documentation](GUI_TECHNICAL.md#troubleshooting).

If you encounter bugs or have feature requests, please report them at the [GitHub Issues](https://github.com/tmbdev/script-to-speech/issues) page.
