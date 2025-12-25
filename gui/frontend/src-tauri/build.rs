// Build script to set compile-time environment variables
// This eliminates fragile runtime path traversal for development builds

fn main() {
    let manifest_dir = std::env::var("CARGO_MANIFEST_DIR")
        .expect("CARGO_MANIFEST_DIR should be set by Cargo");
    let manifest_path = std::path::Path::new(&manifest_dir);

    // Calculate project root at build time
    // src-tauri -> frontend -> gui -> script-to-speech (project root)
    let project_root = manifest_path
        .parent() // src-tauri -> frontend
        .and_then(|p| p.parent()) // frontend -> gui
        .and_then(|p| p.parent()) // gui -> script-to-speech
        .expect("Failed to determine project root from CARGO_MANIFEST_DIR");

    // Set compile-time environment variable for development workspace
    println!(
        "cargo:rustc-env=DEV_WORKSPACE_ROOT={}",
        project_root.display()
    );

    // Rerun if this build script changes
    println!("cargo:rerun-if-changed=build.rs");

    // Run Tauri's build script
    tauri_build::build()
}
