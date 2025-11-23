# Script to Speech GUI User Guide

The Script to Speech GUI provides a user-friendly interface for generating audiobooks from screenplays. It wraps the powerful CLI tools in a modern, intuitive desktop application.

## Getting Started

### Installation

Currently, the GUI is distributed as a standalone application. 
*(Note: Installation instructions will be updated as distribution methods are finalized)*

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

- **API Errors**: Ensure your API keys are correctly configured in the settings or `.env` file.
