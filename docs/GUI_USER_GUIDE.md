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

### 7. Text Processing

The **Text Processing** screen configures how your screenplay's text is transformed before audio generation (e.g. expanding "V.O." to "VOICE OVER", removing page numbers, adjusting capitalization).

When a screenplay is parsed, a text processor config file is created for the project (seeded from sensible defaults). This screen edits that file directly — the same file the CLI uses — so changes made here and via the command line stay in sync.

- **Structure / Text sections**: The pipeline in two ordered lists — steps that reshape the screenplay's structure (merging, splitting, removing chunks) and steps that transform each line's spoken text. Steps run top to bottom (arrows between the cards show the flow); use a card's arrow buttons to reorder it, the trash button to remove it, and **Add** to insert new steps. The Structure section starts collapsed since it rarely needs changes — click the chevron to expand it.
- **Step configuration**: Each step shows a form for its settings, with a **?** next to each field explaining what it does and a help button on the card describing the step and any setup notes. Less common options sit behind an **Advanced options** collapse. Rules support an optional **Notes** field (under Advanced) — a note is kept in the config file and displayed above the rule.
- **Saving changes**: An edited step shows an amber *modified* chip with inline buttons to **save**, **discard**, or **test** just that change; removed steps stay visible as ghost rows until the removal is saved or the step restored, and reordering a section shows an *order changed* chip with its own save/revert. The same works one level down: inside a step, an edited rule (a single substitution or replacement) gets an amber edge and its own test/save/discard buttons, and deleted rules stay visible as ghost lines until the removal is saved or the rule restored. The **Save all** / **Discard all** buttons at the top show how many changes are pending (hover for the list). Navigating away with unsaved changes prompts you to save or discard first.
- **Testing changes**: The flask button on a modified step or rule — and **Preview unsaved changes** on the Preview tab — runs your screenplay through both the saved config and your edited one, and shows only what the edits *add* (e.g. "6 chunks change", with diffs). The full-pipeline preview (everything the config does, with per-step attribution) remains available below it.
- **Defaults menu**:
    - **Save as my default**: Use the current pipeline as the starting configuration for future screenplays you parse.
    - **Load my default into this project**: Replace this project's pipeline with your saved default.
    - **Reset**: Re-seed this project (or your saved default) from the built-in defaults.
- **Update notices**: If a new version of Script to Speech changes the built-in defaults, a banner notes that your config was seeded from an older version and offers to re-seed it. Projects using the older add-on style config are offered a one-click conversion to the editable format (processing behavior is unchanged).

For the underlying configuration format and CLI usage, see the [Text Processing Guide](TEXT_PROCESSORS.md).

### 8. Audio Generation & Exporting

Generate audio for the entire script from the **Generate Audio** tab, then review problem clips and export the final audiobook as an MP3 file.

### 9. Reviewing & Re-recording Audio

The **Review Audio** tab helps you find and fix individual clips:

- **Silent Clips / Missing Clips**: clips that failed generation or came back
  silent, grouped by speaker. Play the existing audio, regenerate with the
  current voice settings, or edit the text sent to the provider (useful for
  pronunciation fixes) and generate variants. Committing a variant replaces
  the clip in the project's audio cache.
- **Find Chunks**: search every chunk in the screenplay — not just problem
  clips — by text, speaker, type, or status, and re-record any of them with
  the same tools.

Things to know when re-recording:

- **Shared audio**: identical text + speaker combinations share one audio
  file (a repeated speaker name may serve dozens of lines). A badge shows
  how many chunks share a clip; re-recording changes all of them.
- **User-modified clips**: committing a variant marks the cached file as
  user-modified (an "edited text" or "custom take" badge). These clips are
  still scanned for silence and surfaced for review, but are never
  automatically regenerated — that decision stays with you; editing the text
  here changes only the audio, never the screenplay itself.

### 10. Screenplay Viewer

The **Screenplay Viewer** tab shows the whole screenplay as a readable,
script-styled list of chunks — scene headings, action, speakers and dialogue —
with each chunk's audio status in the margin (a marker for missing audio, a
dimmed glyph for intentional silence, and an icon for user-modified clips).
The viewer needs a fully cast project: finish **Voice Casting** first, or the
tab shows a reminder instead of the screenplay.

- **Play a chunk**: hover a row (the controls stay visible on the selected
  and currently playing rows) and press play to hear just that chunk through
  the app's audio player (the transport bar at the bottom of the page).
- **Play in sequence**: press **Play all** in the toolbar, or a row's
  "play from here" button, to listen through the screenplay from that point.
  Chunks are chained with the same 500 ms gap the generated audiobook uses;
  missing chunks are skipped. The active row is highlighted and kept in
  view — scrolling away pauses the auto-follow until you press **Jump to
  current**. Pausing in the transport bar pauses the sequence; resuming
  continues it.
- **Inspect and re-record**: click any chunk to open a side panel with its
  details — original vs. processed (spoken) text, the cache filename, and
  how many chunks share the same audio (with links to jump to each) — plus
  the same re-record/edit/commit tools as Review Audio, and play /
  play-from-here buttons in the panel header. Committed changes show up in
  the viewer immediately.
- **PDF view**: if the screenplay was parsed from a PDF, use the **List | PDF**
  toggle in the toolbar to switch to the original rendered screenplay with each
  source region's audio-status highlight drawn directly on the page. Click a
  highlight to select it and open the persistent detail panel; playback and
  editing stay in that panel so reading the page doesn't trigger audio by
  accident — the panel's play-from-here button starts sequential playback
  from any selected region. If preprocessing split one source region into
  several audio chunks, the highlight shows their count and the panel provides
  a short navigator for choosing the segment to inspect or re-record.
  Highlight color reports audio availability (cached, missing, or intentional
  silence), while separate edit and retake markers preserve user-modified
  provenance. Sequential playback highlights the current region and scrolls to
  follow it. A few chunks that can't be confidently located on the page aren't
  drawn (a small "N chunks not shown" note appears); the List view always
  shows every chunk. Text-only screenplays (no source PDF) don't have a PDF
  view. PDFs with cropped or shifted page boxes remain readable in PDF view,
  but audio highlights are disabled with an on-screen explanation until that
  page geometry can be validated against a real example; use List view to
  select and edit chunks in that case.
- **Your place is kept**: the viewer remembers the chunk at the top of your
  viewport. Switching between List and PDF lands on the same spot in the
  other view, and returning to the viewer tab later in the session restores
  it too.
- **Refresh**: the toolbar's **Refresh** button (with its "Last refreshed"
  time) recomputes everything from disk — use it after making changes outside
  the GUI (e.g. CLI runs) so statuses match reality.

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
