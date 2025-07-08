use std::process::{Command, Stdio};
use std::sync::Mutex;
use std::path::PathBuf;
use tauri::{AppHandle, Manager, State};

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
    
    // Determine the correct working directory
    let working_dir = if cfg!(debug_assertions) {
        // In development: relative to frontend directory
        std::path::PathBuf::from("../../../")
    } else {
        // In production: resolve from app bundle to script-to-speech root
        let app_dir = app_handle
            .path()
            .app_data_dir()
            .map_err(|e| format!("Failed to get app directory: {}", e))?;
        
        // For production, we need to find the script-to-speech root
        // The app bundle is typically in: script-to-speech/gui/frontend/src-tauri/target/release/bundle/macos/
        // So we need to go up several levels to reach script-to-speech root
        let mut current = app_dir.clone();
        
        // Try to find the script-to-speech directory by looking for pyproject.toml
        for _ in 0..10 {  // Prevent infinite loop
            current = match current.parent() {
                Some(parent) => parent.to_path_buf(),
                None => break,
            };
            
            if current.join("pyproject.toml").exists() && 
               current.join("src").exists() && 
               current.join("gui").exists() {
                println!("Found script-to-speech root at: {:?}", current);
                break;
            }
        }
        
        current
    };
    
    println!("Using working directory: {:?}", working_dir);
    
    // Start the FastAPI backend using uv
    let child = Command::new("uv")
        .args(&["run", "python", "-m", "sts_gui_backend.main"])
        .current_dir(&working_dir)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("Failed to start backend from {:?}: {}", working_dir, e))?;
    
    println!("Backend server started with PID: {}", child.id());
    *process_guard = Some(child);
    
    Ok("Backend started successfully".to_string())
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
        .on_window_event(|_window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                // Stop the backend when the app is closing - we can't easily access app_handle here
                // so we'll let the process cleanup happen when the app exits
                println!("Window close requested - backend will cleanup on exit");
            }
        })
        .invoke_handler(tauri::generate_handler![start_backend, stop_backend])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
