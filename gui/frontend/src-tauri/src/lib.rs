use log::{debug, error, info, warn};
use std::io::{BufRead, BufReader};
use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::sync::Mutex;
use tauri::{AppHandle, Manager, State};
use tauri_plugin_shell::{process::CommandChild, ShellExt};

#[cfg(debug_assertions)]
use tauri_plugin_shell::process::CommandEvent;

// Port configuration constants
const DEV_PORT: u16 = 8000;
const PROD_PORT: u16 = 58735;

/// Represents the backend process, which can be either:
/// - Dev: Manually spawned via `uv run` (std::process::Child)
/// - Sidecar: Tauri-managed executable bundled with the app (CommandChild)
enum BackendChild {
    Dev(std::process::Child),
    Sidecar(CommandChild),
}

impl BackendChild {
    /// Attempt to kill the backend process
    ///
    /// Note: For Sidecar variant, this consumes the CommandChild since its kill() method takes ownership.
    /// The caller should ensure they take() the Option<BackendChild> from the Mutex before calling this.
    fn kill(self) -> std::io::Result<()> {
        match self {
            BackendChild::Dev(mut child) => child.kill(),
            BackendChild::Sidecar(child) => {
                // CommandChild::kill() takes ownership and returns Result<(), Error>
                child.kill().map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e))
            }
        }
    }

    /// Check if the process has exited (only works for Dev variant)
    fn try_wait(&mut self) -> std::io::Result<Option<std::process::ExitStatus>> {
        match self {
            BackendChild::Dev(child) => child.try_wait(),
            BackendChild::Sidecar(_) => {
                // For sidecar, we can't easily check exit status synchronously
                // Return Ok(None) to indicate "still running" or "unknown"
                Ok(None)
            }
        }
    }

    /// Get the process ID
    fn pid(&self) -> u32 {
        match self {
            BackendChild::Dev(child) => child.id(),
            BackendChild::Sidecar(child) => child.pid(),
        }
    }
}

// Global state to track the backend process
struct BackendProcess(Mutex<Option<BackendChild>>);

/// Helper function to shutdown backend process
/// Extracts common cleanup logic used in stop_backend and RunEvent::Exit
fn shutdown_backend(app_handle: &AppHandle) {
    let state: State<BackendProcess> = app_handle.state();
    let mut guard = state.0.lock().unwrap();
    if let Some(child) = guard.take() {
        let pid = child.pid();
        info!("Killing backend process (PID: {})...", pid);
        if let Err(e) = child.kill() {
            warn!("Failed to kill backend process: {}", e);
        } else {
            info!("Backend process killed successfully");
        }
    } else {
        debug!("No backend process to clean up");
    }
}

/// Get the workspace directory path for the application.
/// Uses runtime detection: bundled apps use Application Support, dev mode uses project root.
fn get_workspace_dir(app_handle: &AppHandle, is_bundled: bool) -> Result<std::path::PathBuf, String> {
    if is_bundled {
        // Bundled mode (production): use Application Support directory (standard for app-managed data)
        // This directory is automatically accessible within the app sandbox
        // Maps to:
        //   - macOS: ~/Library/Application Support/Script to Speech/
        //   - Windows: %APPDATA%\Script to Speech\
        //   - Linux: ~/.local/share/script-to-speech/
        use tauri::path::BaseDirectory;

        let app_data_dir = app_handle
            .path()
            .resolve("", BaseDirectory::AppLocalData)
            .map_err(|e| format!("Failed to get app data directory: {}", e))?;

        Ok(app_data_dir)
    } else {
        // Development mode: use compile-time constant set by build.rs
        // This eliminates fragile runtime path traversal
        Ok(PathBuf::from(env!("DEV_WORKSPACE_ROOT")))
    }
}

#[tauri::command]
async fn start_backend(app_handle: AppHandle) -> Result<String, String> {
    info!("Starting FastAPI backend server");

    let backend_state: State<BackendProcess> = app_handle.state();

    // Hold lock through check and spawn to prevent race condition
    // If two threads call start_backend simultaneously, only one will spawn
    let mut process = backend_state.0.lock().unwrap();

    // Check if backend is already running
    if let Some(ref mut child) = *process {
        match child.try_wait() {
            Ok(None) => {
                // Process is still running
                info!("Backend process already running (PID: {}), skipping spawn", child.pid());
                return Ok("Backend already running".to_string());
            }
            Ok(Some(status)) => {
                info!("Previous backend exited with status: {:?}", status);
                // Process exited, we'll spawn a new one
            }
            Err(e) => {
                warn!("Error checking backend status: {}", e);
                // Assume process is dead, spawn new one
            }
        }
    }

    // Runtime detection: try to create sidecar command to determine if we're bundled
    match app_handle.shell().sidecar("sts-gui-backend") {
        Ok(sidecar_cmd) => {
            // Bundled mode (production) - sidecar exists
            // This works for both debug and release builds
            info!("Bundled mode: launching sidecar with --production flag");

            let workspace_dir = get_workspace_dir(&app_handle, true)?;
            debug!("Using workspace directory: {:?}", workspace_dir);

            // Spawn sidecar with --production flag and port
            // Python backend will use these flags to determine production mode and port
            // NOTE: Tauri sidecars automatically get stdin piped (can use child.write())
            // This enables stdin EOF monitoring for parent death detection
            let (mut rx, sidecar_child) = sidecar_cmd
                .args(["--production", "--port", &PROD_PORT.to_string()])
                .spawn()
                .map_err(|e| format!("Failed to spawn sidecar: {}", e))?;

            let pid = sidecar_child.pid();
            info!("Backend sidecar started with PID: {}", pid);
            debug!("Arguments: [\"--production\", \"--port\", \"{}\"]", PROD_PORT);

            // Capture sidecar output for debugging - only in debug builds
            #[cfg(debug_assertions)]
            {
                tauri::async_runtime::spawn(async move {
                    while let Some(event) = rx.recv().await {
                        match event {
                            CommandEvent::Stdout(line) => {
                                if let Ok(s) = String::from_utf8(line) {
                                    debug!("[Backend stdout] {}", s);
                                }
                            }
                            CommandEvent::Stderr(line) => {
                                if let Ok(s) = String::from_utf8(line) {
                                    warn!("[Backend stderr] {}", s);
                                }
                            }
                            CommandEvent::Error(err) => {
                                error!("[Backend error] {}", err);
                            }
                            CommandEvent::Terminated(payload) => {
                                info!("[Backend terminated] {:?}", payload);
                            }
                            _ => {}
                        }
                    }
                });
            }

            // In release builds, drop the receiver to avoid memory buildup
            #[cfg(not(debug_assertions))]
            {
                drop(rx);
            }

            // CRITICAL: Store the sidecar process handle for lifecycle management
            // Tauri does NOT automatically clean up sidecar processes on exit
            // Lock is already held from the check above
            *process = Some(BackendChild::Sidecar(sidecar_child));
            info!("Sidecar backend stored in state for manual lifecycle management");

            Ok("Backend started successfully (production)".to_string())
        }
        Err(e) => {
            // Development mode - sidecar doesn't exist
            // This happens during `tauri dev`
            info!("Development mode: expecting backend at localhost:8000");
            debug!("Sidecar not found: {}", e);

            let workspace_dir = get_workspace_dir(&app_handle, false)?;
            debug!("Using workspace directory: {:?}", workspace_dir);

            // Start the FastAPI backend using uv (dev mode uses port 8000)
            // Python will independently determine the same workspace path
            let mut child = Command::new("uv")
                .args(&["run", "sts-gui-server", "--port", &DEV_PORT.to_string()])
                .current_dir(&workspace_dir)
                .stdin(Stdio::piped())  // CRITICAL: Pipe stdin for parent death detection
                .stdout(Stdio::piped())
                .stderr(Stdio::piped())
                .spawn()
                .map_err(|e| format!("Failed to start backend from {:?}: {}", workspace_dir, e))?;

            info!("Backend server started with PID: {} on port {}", child.id(), DEV_PORT);

            // Capture stdout/stderr in background threads - only in debug builds
            #[cfg(debug_assertions)]
            {
                if let Some(stdout) = child.stdout.take() {
                    std::thread::spawn(move || {
                        let reader = BufReader::new(stdout);
                        for line in reader.lines() {
                            if let Ok(line) = line {
                                debug!("[Backend stdout] {}", line);
                            }
                        }
                    });
                }

                if let Some(stderr) = child.stderr.take() {
                    std::thread::spawn(move || {
                        let reader = BufReader::new(stderr);
                        for line in reader.lines() {
                            if let Ok(line) = line {
                                warn!("[Backend stderr] {}", line);
                            }
                        }
                    });
                }
            }

            // In release builds, don't capture output to avoid overhead
            #[cfg(not(debug_assertions))]
            {
                // Take and drop to prevent pipe blocking
                child.stdout.take();
                child.stderr.take();
            }

            let pid = child.id();

            // Store the dev process using the BackendChild enum
            // Lock is already held from the check above
            *process = Some(BackendChild::Dev(child));
            info!("Dev backend stored in state for manual lifecycle management (PID: {})", pid);

            Ok("Backend started successfully (development)".to_string())
        }
    }
}

#[tauri::command]
async fn stop_backend(app_handle: AppHandle) -> Result<String, String> {
    info!("Stopping FastAPI backend server");

    shutdown_backend(&app_handle);

    Ok("Backend stopped successfully".to_string())
}

#[tauri::command]
async fn get_workspace_path(app_handle: AppHandle) -> Result<String, String> {
    // Check if sidecar exists to determine bundled mode
    let is_bundled = app_handle.shell().sidecar("sts-gui-backend").is_ok();

    let workspace_dir = get_workspace_dir(&app_handle, is_bundled)?;
    workspace_dir
        .to_str()
        .ok_or_else(|| "Failed to convert workspace path to string".to_string())
        .map(|s| s.to_string())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(BackendProcess(Mutex::new(None)))
        .plugin(tauri_plugin_log::Builder::new().build())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_upload::init())
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            // Automatically start the backend server
            let app_handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                if let Err(e) = start_backend(app_handle).await {
                    error!("Failed to auto-start backend: {}", e);
                }
            });

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            start_backend,
            stop_backend,
            get_workspace_path
        ])
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app_handle, event| {
            match event {
                tauri::RunEvent::Exit => {
                    info!("App exiting, cleaning up backend process...");
                    shutdown_backend(app_handle);
                }
                _ => {}
            }
        });
}
