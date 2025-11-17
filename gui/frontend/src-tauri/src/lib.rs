use log::{debug, error, info, warn};
use std::io::{BufRead, BufReader};
use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::sync::Mutex;
use tauri::{AppHandle, Manager, State};
use tauri_plugin_shell::{process::CommandEvent, ShellExt};

// Global state to track the backend process
struct BackendProcess(Mutex<Option<std::process::Child>>);

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
    let mut process_guard = backend_state.0.lock().unwrap();

    // Check if we already have a process running
    if let Some(ref mut child) = *process_guard {
        match child.try_wait() {
            Ok(Some(_)) => {
                // Process has exited, remove it
                *process_guard = None;
            }
            Ok(None) => {
                // Process is still running
                return Ok("Backend is already running".to_string());
            }
            Err(e) => {
                return Err(format!("Failed to check process status: {}", e));
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

            // Spawn sidecar with --production flag
            // Python backend will use this flag to determine production mode
            let (mut rx, sidecar_child) = sidecar_cmd
                .args(["--production"])
                .spawn()
                .map_err(|e| format!("Failed to spawn sidecar: {}", e))?;

            info!("Backend sidecar started with PID: {}", sidecar_child.pid());
            debug!("Arguments: [\"--production\"]");

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

            // Note: We don't store the sidecar child in state as Tauri manages its lifecycle
            // The sidecar will be automatically cleaned up when the app exits
            Ok("Backend started successfully (production)".to_string())
        }
        Err(e) => {
            // Development mode - sidecar doesn't exist
            // This happens during `tauri dev`
            info!("Development mode: expecting backend at localhost:8000");
            debug!("Sidecar not found: {}", e);

            let workspace_dir = get_workspace_dir(&app_handle, false)?;
            debug!("Using workspace directory: {:?}", workspace_dir);

            // Start the FastAPI backend using uv
            // Python will independently determine the same workspace path
            let mut child = Command::new("uv")
                .args(&["run", "sts-gui-server"])
                .current_dir(&workspace_dir)
                .stdout(Stdio::piped())
                .stderr(Stdio::piped())
                .spawn()
                .map_err(|e| format!("Failed to start backend from {:?}: {}", workspace_dir, e))?;

            info!("Backend server started with PID: {}", child.id());

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

            *process_guard = Some(child);

            Ok("Backend started successfully (development)".to_string())
        }
    }
}

#[tauri::command]
async fn stop_backend(app_handle: AppHandle) -> Result<String, String> {
    info!("Stopping FastAPI backend server");

    let backend_state: State<BackendProcess> = app_handle.state();
    let mut process_guard = backend_state.0.lock().unwrap();

    if let Some(mut child) = process_guard.take() {
        child.kill().map_err(|e| format!("Failed to kill process: {}", e))?;
        child.wait().map_err(|e| format!("Failed to wait for process: {}", e))?;
        info!("Backend server stopped successfully");
        Ok("Backend stopped successfully".to_string())
    } else {
        Ok("Backend was not running".to_string())
    }
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
        .on_window_event(|window, event| {
            // Graceful shutdown for development mode
            if let tauri::WindowEvent::Destroyed = event {
                // Check if we have a backend process in state (only exists in dev mode)
                let app_handle = window.app_handle();
                let backend_state: State<BackendProcess> = app_handle.state();
                let mut process_guard = backend_state.0.lock().unwrap();

                if let Some(mut child) = process_guard.take() {
                    info!("Window destroyed - cleaning up backend");
                    debug!("Killing backend process with PID: {}", child.id());
                    let _ = child.kill();
                    let _ = child.wait();
                    info!("Backend server stopped gracefully");
                }
                // Note: In bundled mode, Tauri automatically cleans up sidecar processes
            }
        })
        .invoke_handler(tauri::generate_handler![
            start_backend,
            stop_backend,
            get_workspace_path
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
