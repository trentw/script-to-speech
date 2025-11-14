use std::process::{Command, Stdio};
use std::sync::Mutex;
use tauri::{AppHandle, Manager, State};
use tauri_plugin_shell::ShellExt;

// Global state to track the backend process
struct BackendProcess(Mutex<Option<std::process::Child>>);

#[tauri::command]
async fn start_backend(app_handle: AppHandle) -> Result<String, String> {
    println!("Starting FastAPI backend server...");
    
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
    
    // Start backend based on build mode
    if cfg!(debug_assertions) {
        // In development: use the development script via uv
        println!("Development mode: using uv run sts-gui-server");

        // Find the script-to-speech root directory
        let working_dir = std::path::PathBuf::from("../../../");
        println!("Using working directory: {:?}", working_dir);

        // Start the FastAPI backend using uv
        let child = Command::new("uv")
            .args(&["run", "sts-gui-server"])
            .current_dir(&working_dir)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|e| format!("Failed to start backend from {:?}: {}", working_dir, e))?;

        println!("Backend server started with PID: {}", child.id());
        *process_guard = Some(child);

        Ok("Backend started successfully (development)".to_string())
    } else {
        // In production: use Tauri's sidecar API for bundled executable
        println!("Production mode: using Tauri sidecar");

        // Use the sidecar API to spawn the backend
        // Tauri handles path resolution, permissions, platform-specific naming, and lifecycle
        let sidecar_command = app_handle
            .shell()
            .sidecar("sts-gui-backend")
            .map_err(|e| format!("Failed to create sidecar command: {}", e))?;

        let (_rx, sidecar_child) = sidecar_command
            .spawn()
            .map_err(|e| format!("Failed to spawn sidecar: {}", e))?;

        println!("Backend sidecar started with PID: {}", sidecar_child.pid());
        // Note: We don't store the sidecar child in state as Tauri manages its lifecycle
        // The sidecar will be automatically cleaned up when the app exits

        Ok("Backend started successfully (production)".to_string())
    }
}

#[tauri::command]
async fn stop_backend(app_handle: AppHandle) -> Result<String, String> {
    println!("Stopping FastAPI backend server...");
    
    let backend_state: State<BackendProcess> = app_handle.state();
    let mut process_guard = backend_state.0.lock().unwrap();
    
    if let Some(mut child) = process_guard.take() {
        child.kill().map_err(|e| format!("Failed to kill process: {}", e))?;
        child.wait().map_err(|e| format!("Failed to wait for process: {}", e))?;
        println!("Backend server stopped successfully");
        Ok("Backend stopped successfully".to_string())
    } else {
        Ok("Backend was not running".to_string())
    }
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
                    eprintln!("Failed to auto-start backend: {}", e);
                }
            });

            Ok(())
        })
        .on_window_event(|window, event| {
            // Graceful shutdown for development mode
            if let tauri::WindowEvent::Destroyed = event {
                if cfg!(debug_assertions) {
                    println!("Window destroyed - cleaning up backend...");
                    let app_handle = window.app_handle();
                    let backend_state: State<BackendProcess> = app_handle.state();
                    let mut process_guard = backend_state.0.lock().unwrap();

                    if let Some(mut child) = process_guard.take() {
                        println!("Killing backend process with PID: {}", child.id());
                        let _ = child.kill();
                        let _ = child.wait();
                        println!("Backend server stopped gracefully");
                    }
                }
                // Production mode: Tauri automatically cleans up sidecar processes
            }
        })
        .invoke_handler(tauri::generate_handler![start_backend, stop_backend])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
