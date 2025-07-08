use std::process::{Command, Stdio};
use std::sync::Mutex;
use tauri::{AppHandle, Manager, State};
use std::fs;

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
    
    // Get the path to the bundled backend executable
    let backend_executable = if cfg!(debug_assertions) {
        // In development: use the development script
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
        
        return Ok("Backend started successfully (development)".to_string());
    } else {
        // In production: use the bundled executable
        let resource_dir = app_handle
            .path()
            .resource_dir()
            .map_err(|e| format!("Failed to get resource directory: {}", e))?;
        
        let backend_path = resource_dir.join("sts-gui-backend");
        
        // Make sure the executable exists
        if !backend_path.exists() {
            return Err(format!("Backend executable not found at: {:?}", backend_path));
        }
        
        // Make sure it's executable on Unix systems
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let mut perms = fs::metadata(&backend_path)
                .map_err(|e| format!("Failed to get permissions: {}", e))?
                .permissions();
            perms.set_mode(0o755);
            fs::set_permissions(&backend_path, perms)
                .map_err(|e| format!("Failed to set permissions: {}", e))?;
        }
        
        println!("Using bundled backend executable: {:?}", backend_path);
        backend_path
    };
    
    // Start the bundled backend executable
    let child = Command::new(&backend_executable)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("Failed to start backend executable {:?}: {}", backend_executable, e))?;
    
    println!("Backend server started with PID: {}", child.id());
    *process_guard = Some(child);
    
    Ok("Backend started successfully (production)".to_string())
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
