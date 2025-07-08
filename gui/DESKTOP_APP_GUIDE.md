# 🖥️ **Script to Speech Desktop Application Guide**

*Last Updated: July 8, 2025*

## 📋 **Project Overview**

We have successfully built a complete desktop application for the Script to Speech TTS Playground using:
- **Frontend**: React + TypeScript + Vite + Tailwind CSS
- **Backend**: FastAPI with real TTS provider integration  
- **Desktop**: Tauri 2.0 (Rust-based native desktop framework)

## 🎯 **What We've Built**

### **Phase 1: Web Application (✅ Complete)**
- Professional TTS Playground web interface
- Real integration with OpenAI, ElevenLabs, Cartesia, Minimax, Zonos
- Voice library browser with preview functionality
- Dynamic configuration forms based on provider capabilities
- Real-time audio generation and playback

### **Phase 2: Desktop Application (✅ Complete)**
- Native macOS/Windows/Linux desktop application
- Embedded React frontend in native window
- Tauri 2.0 framework with Rust backend
- Professional app with proper icons and window management

### **Phase 3: Self-Contained Architecture (✅ Complete)**
- **Unified Python Package**: Single `script_to_speech` package with optional `[gui]` dependencies
- **Standalone Backend**: 24.9MB PyInstaller executable with all dependencies bundled
- **No External Dependencies**: End users don't need Python, uv, or any technical setup
- **Automatic Backend Startup**: Desktop app automatically starts FastAPI server in production

## 🚀 **Step-by-Step Testing Instructions**

### **Prerequisites**
Before testing, ensure you have:
- ✅ Python 3.13+ with uv package manager
- ✅ Node.js 18+ with npm
- ✅ Rust and Cargo (automatically installed during setup)
- ✅ TTS Provider API keys (optional but recommended)

### **Step 1: Environment Setup**

1. **Navigate to Project Directory**
   ```bash
   cd /Users/tmb/projects/script-to-speech
   ```

2. **Check Environment Variables (Optional)**
   ```bash
   # Copy .env.example to .env and add your API keys for testing
   cp .env.example .env
   # Edit .env with your preferred editor to add:
   # OPENAI_API_KEY=your_key_here
   # ELEVEN_API_KEY=your_key_here
   # etc.
   ```

### **Step 2: Start the FastAPI Backend**

1. **Open Terminal 1 for Backend**
   ```bash
   # From project root (recommended)
   make gui-server
   
   # Alternative: 
   # uv run sts-gui-server
   ```

2. **Verify Backend is Running**
   - You should see: `INFO: Uvicorn running on http://127.0.0.1:8000`
   - Test health check: http://127.0.0.1:8000/health
   - View API docs: http://127.0.0.1:8000/docs

### **Step 3A: Launch Web Interface (Recommended for Development)**

1. **Open Terminal 2 for Web Frontend**
   ```bash
   # From project root (recommended)
   make gui-dev
   
   # Alternative:
   # cd gui/frontend && npm run dev
   ```

2. **Open in Browser**
   - Vite will start on `http://localhost:5173`
   - Open this URL in your browser
   - **Benefits**: Full browser DevTools, React Developer Tools, better debugging

### **Step 3B: Launch Desktop Application (Alternative)**

1. **Open Terminal 2 for Desktop App**
   ```bash
   # From project root (recommended)
   make gui-desktop
   
   # Alternative:
   # cd gui/frontend && . "$HOME/.cargo/env" && npx tauri dev
   ```

2. **Wait for Compilation** (First time only)
   - Rust dependencies will compile (takes 1-2 minutes first time)
   - You'll see: `Building [=======================] 382/382`
   - Then: `Running target/debug/app`
   - Finally: Vite dev server starts

3. **Desktop App Opens**
   - A native desktop window should open
   - Window title: "Script to Speech"
   - Contains your React TTS Playground interface

### **Step 4: Test TTS Playground Functionality**

**💡 Pro Tip**: If using the web interface (Step 3A), open browser DevTools (F12) to:
- Monitor API calls in Network tab
- Check console for any errors
- Use React DevTools extension for component debugging
- Test responsive design with device simulation

#### **4.1 Test Provider Discovery**
1. **Check Provider Dropdown**
   - Look for providers: OpenAI, ElevenLabs, Cartesia, Minimax, Zonos
   - Should NOT show dummy providers
   - Each provider should have description and field information

2. **Select a Provider**
   - Choose "OpenAI" (most reliable for testing)
   - Form should auto-populate with required fields
   - Should see fields like: `voice`, `speed`, `response_format`

#### **4.2 Test Voice Library**
1. **Browse Voice Library**
   - Click on voice library section
   - Should see voices for selected provider
   - OpenAI voices: alloy, echo, fable, nova, onyx, shimmer

2. **Test Voice Selection**
   - Click on a voice entry
   - Should auto-populate configuration fields
   - Preview URLs should be available (if configured)

#### **4.3 Test Audio Generation**
1. **Enter Text**
   - Type in text area: "This is a test of the Script to Speech desktop application"
   - Character count should update

2. **Configure Settings**
   - Select voice: "echo" (or any preferred voice)
   - Set speed: 1.0
   - Set response format: mp3

3. **Generate Audio**
   - Click "Generate Audio" button
   - Should show progress: "Starting audio generation" → "Processing" → "Completed"
   - Audio player should appear with playback controls

4. **Test Playback**
   - Click play button on generated audio
   - Should hear synthesized speech
   - Download button should be available

#### **4.4 Test Multiple Providers**
1. **Switch Providers**
   - Change from OpenAI to ElevenLabs (if API key available)
   - Form fields should update dynamically
   - Different configuration options should appear

2. **Test Provider-Specific Features**
   - ElevenLabs: voice_id, model, voice_settings
   - Cartesia: language, speed settings
   - Each provider should have unique field requirements

### **Step 5: Test Desktop App Features**

#### **5.1 Window Management**
- **Resize Window**: Drag corners to resize - should be responsive
- **Minimize/Maximize**: Standard window controls should work
- **Close App**: Should cleanly shut down both frontend and backend

#### **5.2 Native Integration**
- **Menu Bar**: Native macOS/Windows menu integration
- **App Icons**: Proper app icons in dock/taskbar
- **File Association**: Desktop app behaviors

#### **5.3 Performance Testing**
- **Startup Time**: App should launch within 5-10 seconds
- **Responsiveness**: UI should be smooth and responsive
- **Memory Usage**: Monitor system resources (should be reasonable)

### **Step 6: Test Error Handling**

1. **Backend Connection Issues**
   - Stop backend server (Ctrl+C in Terminal 1)
   - Desktop app should show connection error
   - Restart backend - app should reconnect

2. **Invalid Configurations**
   - Try submitting empty required fields
   - Should show validation errors
   - Error messages should be user-friendly

3. **Network Issues**
   - Test with invalid API keys
   - Should show appropriate error messages
   - App should remain stable

## 🐛 **Troubleshooting**

### **Common Issues**

#### **Desktop App Won't Start**
```bash
# Ensure Rust environment is loaded
source "$HOME/.cargo/env"
cargo --version  # Should show version number

# Clean and rebuild if needed
cd gui/frontend/src-tauri
cargo clean
cd ..
npx tauri dev
```

#### **Backend Connection Failed**
```bash
# Check if backend is running
curl http://127.0.0.1:8000/health

# Restart backend (from project root)
make gui-server
# Alternative: uv run sts-gui-server
```

#### **No Providers Available**
- Check if TTS provider dependencies are installed
- Verify backend logs for import errors
- Ensure dummy providers are filtered out

#### **Audio Generation Fails**
- Check API keys in .env file
- Verify provider-specific configuration
- Check backend logs for detailed error messages

#### **Build Errors**
```bash
# Update dependencies
cd gui/frontend
npm install
npx tauri deps update

# Clear caches
rm -rf node_modules
npm install
```

## 📁 **Project Structure**

```
script-to-speech/
├── src/
│   └── script_to_speech/           # Unified package structure
│       ├── gui_backend/            # FastAPI Backend (integrated)
│       ├── tts_providers/          # TTS provider implementations
│       ├── voice_library/          # Voice library system
│       └── ...                     # Other core modules
├── gui/
│   ├── frontend/                   # React Frontend + Tauri
│   │   ├── src/                    # React components
│   │   ├── src-tauri/              # Tauri Rust backend
│   │   │   ├── src/
│   │   │   ├── Cargo.toml
│   │   │   └── tauri.conf.json
│   │   ├── package.json
│   │   └── vite.config.ts
│   ├── DESKTOP_APP_GUIDE.md        # This file
│   └── start_test.sh               # Quick web app launcher
├── build_backend.py                # PyInstaller build script
├── dist/                           # Built executables
│   └── sts-gui-backend             # Standalone backend (24.9MB)
└── pyproject.toml                  # Unified project configuration
```

## 🎯 **Testing Checklist**

### **Basic Functionality**
- [ ] Desktop app launches successfully
- [ ] Backend connects and shows available providers
- [ ] Can select providers and see dynamic form fields
- [ ] Voice library loads and displays voices
- [ ] Can generate audio with at least one provider
- [ ] Audio playback works in desktop app
- [ ] Can download generated audio files

### **Provider Testing**
- [ ] OpenAI provider works (if API key available)
- [ ] ElevenLabs provider works (if API key available)
- [ ] Cartesia provider works (if API key available)
- [ ] Provider switching updates form fields correctly
- [ ] Validation works for required/optional fields

### **Desktop Integration**
- [ ] Window resizes properly
- [ ] Native menus and controls work
- [ ] App icon appears in dock/taskbar
- [ ] App can be minimized/maximized
- [ ] Clean shutdown when closed

### **Error Handling**
- [ ] Graceful handling of backend disconnection
- [ ] Clear error messages for invalid inputs
- [ ] App remains stable during errors
- [ ] Network error recovery works

## 🏗️ **Building for Distribution**

### **Production Build Process**

#### **Step 1: Clean Build Environment**
```bash
# Navigate to frontend directory
cd gui/frontend

# Clean previous builds
rm -rf dist/ src-tauri/target/

# Update dependencies
npm install
```

#### **Step 2: Build Self-Contained Production App**
```bash
# From project root (recommended)
make gui-build

# Alternative:
# cd gui/frontend && . "$HOME/.cargo/env" && npx tauri build
```

**What this does:**
1. **Builds React frontend** with `npm run build`
2. **Creates standalone backend** with `uv run python build_backend.py` (24.9MB executable)
3. **Bundles everything** into self-contained desktop app
4. **No external dependencies** required for end users

This will create **self-contained** applications with embedded backend:
- **macOS**: `.app` bundle (~25MB) and `.dmg` installer
- **Windows**: `.exe` and `.msi` installer (if on Windows)
- **Linux**: `.AppImage` and `.deb` packages (if on Linux)

**Key Feature**: Backend executable is bundled inside the app - no Python/uv installation required!

#### **Step 3: Locate Build Artifacts**
```bash
# Production builds are located in:
ls src-tauri/target/release/bundle/

# macOS artifacts:
src-tauri/target/release/bundle/macos/Script to Speech.app
src-tauri/target/release/bundle/dmg/Script to Speech_0.1.0_aarch64.dmg

# Windows artifacts (if built on Windows):
src-tauri/target/release/bundle/msi/Script to Speech_0.1.0_x64_en-US.msi

# Linux artifacts (if built on Linux):
src-tauri/target/release/bundle/appimage/script-to-speech_0.1.0_amd64.AppImage
src-tauri/target/release/bundle/deb/script-to-speech_0.1.0_amd64.deb
```

#### **Step 4: Debug vs Release Builds**

**Debug Build (for testing):**
```bash
npx tauri build --debug
# Faster compilation, larger file size, includes debug symbols
```

**Release Build (for distribution):**
```bash
npx tauri build
# Optimized compilation, smaller file size, production ready
```

### **Distribution Preparation**

#### **Code Signing (macOS)**
For distribution outside of testing:
```bash
# Add to tauri.conf.json under bundle.macOS:
"signingIdentity": "Developer ID Application: Your Name",
"entitlements": "path/to/entitlements.plist"
```

#### **Windows Code Signing**
```bash
# Add certificate configuration to tauri.conf.json
"windows": {
  "certificateThumbprint": "YOUR_CERT_THUMBPRINT",
  "digestAlgorithm": "sha256"
}
```

#### **App Store Preparation**
For Mac App Store or Microsoft Store distribution, additional configuration is needed in `tauri.conf.json`.

## 🧪 **Testing the Built Application**

### **Step 1: Test App Bundle Directly**

#### **macOS Testing**
```bash
# Navigate to build directory
cd src-tauri/target/release/bundle/macos/

# Launch app directly
open "Script to Speech.app"

# Or from command line to see output
./Script\ to\ Speech.app/Contents/MacOS/app
```

#### **Test App Installation (macOS)**
```bash
# Mount the DMG
open "src-tauri/target/release/bundle/dmg/Script to Speech_0.1.0_aarch64.dmg"

# Drag app to Applications folder
# Launch from Applications
```

### **Step 2: Comprehensive App Testing**

#### **2.1 Standalone Operation Test**
1. **Close all terminals and development processes**
2. **Launch only the built app** (not dev environment)
3. **Verify backend auto-starts** when app launches
4. **Test complete TTS workflow** without manual backend startup

Expected behavior:
- ✅ App launches immediately
- ✅ Backend status shows "Starting..." then "Running"
- ✅ Providers load automatically
- ✅ Voice library populates
- ✅ Audio generation works end-to-end

#### **2.2 Backend Integration Test**
```bash
# App should automatically start backend process
# Check if backend is running when app is open:
curl http://127.0.0.1:8000/health
# Should return: {"status": "healthy"}

# Check processes:
ps aux | grep "sts_gui_backend"
# Should show running Python backend process
```

#### **2.3 Clean Environment Test**
```bash
# Test on fresh system or clean user account
# This verifies all dependencies are bundled properly

# For thorough testing, create new user account:
# System Preferences > Users & Groups > Add New User
# Install only the .dmg file
# Test complete functionality
```

### **Step 3: Performance Testing**

#### **3.1 Startup Performance**
- **Cold Start**: First launch after system restart
- **Warm Start**: Subsequent launches
- **Memory Usage**: Monitor with Activity Monitor/Task Manager
- **Backend Startup Time**: From app launch to backend ready

Target Performance:
- ✅ App window appears: < 3 seconds
- ✅ Backend ready: < 10 seconds  
- ✅ Memory usage: < 200MB idle
- ✅ No CPU spikes during idle

#### **3.2 Stress Testing**
```bash
# Test multiple rapid audio generations
# Test large text inputs (>1000 characters)
# Test provider switching under load
# Test app stability during network issues
```

### **Step 4: Integration Testing**

#### **4.1 File System Integration**
- **Downloads**: Verify audio files save correctly
- **Permissions**: Check file access permissions
- **Path Resolution**: Test relative/absolute paths work

#### **4.2 System Integration**
- **Notifications**: Test any system notifications
- **Window Management**: Multi-monitor support
- **Keyboard Shortcuts**: Standard app shortcuts (Cmd+Q, etc.)

#### **4.3 Network Integration**
- **Firewall**: Test app works with firewall enabled
- **Proxy**: Test corporate proxy environments
- **Offline**: Graceful handling of network disconnection

### **Step 5: Cross-Platform Testing**

#### **Windows Testing** (if building on Windows)
```powershell
# Install from MSI
Start-Process "Script to Speech_0.1.0_x64_en-US.msi"

# Or run executable directly
.\script-to-speech.exe
```

#### **Linux Testing** (if building on Linux)
```bash
# Install AppImage
chmod +x script-to-speech_0.1.0_amd64.AppImage
./script-to-speech_0.1.0_amd64.AppImage

# Or install DEB package
sudo dpkg -i script-to-speech_0.1.0_amd64.deb
```

## 🚀 **What's Next**

### **Immediate Distribution Steps**
1. ✅ **Backend Auto-Start**: Now automatically starts FastAPI server
2. ✅ **Production Build**: Test `npx tauri build` for distribution
3. 🔄 **App Packaging**: Test installers for macOS/Windows/Linux
4. 📝 **Code Signing**: Set up certificates for trusted distribution

### **Distribution Checklist**
- [ ] Production build successful on target platforms
- [ ] App bundle launches independently  
- [ ] Backend auto-start works reliably
- [ ] All TTS providers function correctly
- [ ] Audio generation and playback work
- [ ] File downloads work properly
- [ ] App performs well under normal usage
- [ ] Clean installation/uninstallation process
- [ ] Code signing configured (for public distribution)

### **Future Enhancements**
1. **Full Script Processing**: Integrate screenplay parsing
2. **Batch Operations**: Multi-file processing
3. **Advanced Voice Casting**: Character-based voice assignment
4. **Export Workflows**: Complete audiobook production

## 🏆 **Success Metrics**

The desktop application successfully provides:
- ✅ **Native Desktop Experience**: Professional desktop app feel
- ✅ **Complete TTS Functionality**: All web app features in desktop
- ✅ **Real Provider Integration**: Actual audio generation capabilities
- ✅ **Modern Architecture**: Scalable, maintainable codebase
- ✅ **Cross-Platform**: Ready for Windows/Linux distribution

## 📞 **Quick Start Commands**

### **Development Mode**

#### **Web Interface (Recommended for Development)**
**Terminal 1 (Backend):**
```bash
# From project root
make gui-server
```

**Terminal 2 (Web Frontend):**
```bash
# From project root  
make gui-dev
# Then open http://localhost:5173 in browser
```

**Why Web Development is Recommended:**
- 🔍 **Better Debugging**: Full browser DevTools, console, network inspection
- ⚛️ **React DevTools**: Component inspection, props, state debugging  
- 🔄 **Fast Refresh**: Instant updates without Rust compilation
- 📱 **Responsive Testing**: Easy device simulation and responsive design testing
- 🌐 **CORS Testing**: Validate API calls and cross-origin requests

#### **Desktop App (For Testing Native Features)**
**Terminal 1 (Backend):**
```bash
# From project root
make gui-server
```

**Terminal 2 (Desktop App):**
```bash
# From project root
make gui-desktop
```

#### **Alternative Commands (Legacy)**
If you prefer working directly in subdirectories:
```bash
# Backend
uv run sts-gui-server

# Web frontend
cd gui/frontend && npm run dev

# Desktop app  
cd gui/frontend && . "$HOME/.cargo/env" && npx tauri dev

# Web version quick test
./gui/start_test.sh
```

### **Testing Current Build**
**Test the debug build we just created:**
```bash
# Launch the built app (with automatic backend startup)
open "src-tauri/target/debug/bundle/macos/Script to Speech.app"

# Or from command line to see debug output:
cd src-tauri/target/debug/bundle/macos/
./Script\ to\ Speech.app/Contents/MacOS/app
```

**Verify backend auto-startup:**
```bash
# After launching the app, check if backend is running:
curl http://127.0.0.1:8000/health
# Should return: {"status": "healthy"}

# Check the backend process:
ps aux | grep "sts_gui_backend" | grep -v grep
# Should show the Python backend process started by the app
```

### **Production Build Commands**
```bash
# From project root (recommended)
make gui-build

# Alternative: Clean build for distribution
cd gui/frontend
rm -rf dist/ src-tauri/target/
. "$HOME/.cargo/env"
npx tauri build

# Test production build (self-contained, no backend needed)
open "gui/frontend/src-tauri/target/release/bundle/macos/Script to Speech.app"

# Manual backend build (if needed)
make gui-build-backend
# Creates: dist/sts-gui-backend (24.9MB standalone executable)
```

---

🎉 **Congratulations!** You now have a fully functional desktop TTS application!