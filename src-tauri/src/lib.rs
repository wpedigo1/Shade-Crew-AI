use std::io::Write;
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Mutex;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use tauri::{AppHandle, Manager, RunEvent};

const SIDECAR_PORT: &str = "8001";
const READY_TIMEOUT: Duration = Duration::from_secs(30);
const POLL_INTERVAL: Duration = Duration::from_millis(250);

struct BackendProcess {
    child: Mutex<Option<Child>>,
    terminated: AtomicBool,
}

fn log_console(line: &str) {
    println!("[modelmix-sidecar] {line}");
    let path = std::env::temp_dir().join("modelmix-sidecar-startup.log");
    if let Ok(mut f) = std::fs::OpenOptions::new().create(true).append(true).open(path) {
        let ts = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs_f64())
            .unwrap_or(0.0);
        let _ = writeln!(f, "[{ts:12.3}] {line}");
    }
}

/// Raw HTTP health probe — no HTTP client dependency needed.
fn health_ok() -> bool {
    use std::io::{Read, Write};
    use std::net::TcpStream;

    let mut stream = match TcpStream::connect(("127.0.0.1", 8001)) {
        Ok(s) => s,
        Err(_) => return false,
    };
    if stream.set_read_timeout(Some(Duration::from_millis(400))).is_err() {
        return false;
    }
    let req = b"GET /api/health HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n";
    if stream.write_all(req).is_err() {
        return false;
    }
    let mut buf = [0u8; 256];
    match stream.read(&mut buf) {
        Ok(n) => String::from_utf8_lossy(&buf[..n]).starts_with("HTTP/1.1 200"),
        Err(_) => false,
    }
}

/// Resolution priority:
///   1. MODELMIX_BACKEND_EXE override (broken-backend / custom setup)
///   2. Packaged resource dir (production: bundle.resources recursive copy)
///   3. Dev fallback: frozen onedir bundle produced by Mission 033.
///
/// The Resource path mirrors the bundler's `_up_` mapping: `..` in the string
/// becomes `_up_` under the resource base (see tauri's resolve_path for
/// BaseDirectory::Resource). The bundle.resources entry "../dist/modelmix-backend/"
/// therefore lands at <resource base>/_up_/dist/modelmix-backend.
fn resolve_backend_exe(app: &tauri::App) -> PathBuf {
    if let Ok(p) = std::env::var("MODELMIX_BACKEND_EXE") {
        let p = PathBuf::from(p);
        log_console(&format!("MODELMIX_BACKEND_EXE override -> {}", p.display()));
        return p;
    }

    match app.path().resolve(
        "../dist/modelmix-backend/modelmix-backend.exe",
        tauri::path::BaseDirectory::Resource,
    ) {
        Ok(p) if p.exists() => {
            log_console(&format!("resource-dir backend -> {}", p.display()));
            return p;
        }
        Ok(p) => log_console(&format!("resource-dir candidate absent: {}", p.display())),
        Err(e) => log_console(&format!("resource-dir lookup error: {e}")),
    }

    let dev = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../dist/modelmix-backend/modelmix-backend.exe");
    log_console(&format!("dev fallback backend -> {}", dev.display()));
    dev
}

#[cfg(target_os = "windows")]
mod win {
    use std::ffi::c_void;
    use windows_sys::Win32::Foundation::{CloseHandle, HANDLE};
    use windows_sys::Win32::System::JobObjects::{
        AssignProcessToJobObject, CreateJobObjectW, JobObjectExtendedLimitInformation,
        JOBOBJECT_EXTENDED_LIMIT_INFORMATION, JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
        SetInformationJobObject,
    };
    use windows_sys::Win32::System::Threading::{OpenProcess, PROCESS_SET_QUOTA, PROCESS_TERMINATE};
    use windows_sys::Win32::UI::WindowsAndMessaging::{MessageBoxW, MB_ICONERROR, MB_OK};

    pub struct JobHandle(pub HANDLE);

    impl Drop for JobHandle {
        fn drop(&mut self) {
            unsafe { CloseHandle(self.0) };
        }
    }

    /// Job with JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE: when the last handle to the
    /// job closes (i.e. this process exits, cleanly or not), every process in the
    /// job tree is terminated. This is the zero-orphan guarantee even on hard kills.
    pub fn create_kill_on_close_job() -> Option<JobHandle> {
        unsafe {
            let job = CreateJobObjectW(std::ptr::null(), std::ptr::null());
            if job.is_null() {
                return None;
            }
            let mut info: JOBOBJECT_EXTENDED_LIMIT_INFORMATION = std::mem::zeroed();
            info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
            let ok = SetInformationJobObject(
                job,
                JobObjectExtendedLimitInformation,
                &info as *const _ as *const c_void,
                std::mem::size_of::<JOBOBJECT_EXTENDED_LIMIT_INFORMATION>() as u32,
            );
            if ok == 0 {
                CloseHandle(job);
                return None;
            }
            Some(JobHandle(job))
        }
    }

    pub fn assign_pid_to_job(job: HANDLE, pid: u32) -> bool {
        unsafe {
            let proc = OpenProcess(PROCESS_SET_QUOTA | PROCESS_TERMINATE, 0, pid);
            if proc.is_null() {
                return false;
            }
            let assigned = AssignProcessToJobObject(job, proc) != 0;
            CloseHandle(proc);
            assigned
        }
    }

    pub fn show_fatal(title: &str, message: &str) {
        let title_wide: Vec<u16> = title.encode_utf16().chain(Some(0)).collect();
        let message_wide: Vec<u16> = message.encode_utf16().chain(Some(0)).collect();
        unsafe {
            MessageBoxW(
                std::ptr::null_mut(),
                message_wide.as_ptr(),
                title_wide.as_ptr(),
                MB_OK | MB_ICONERROR,
            );
        }
    }
}

#[cfg(target_os = "windows")]
use win::show_fatal;

#[cfg(not(target_os = "windows"))]
fn show_fatal(_title: &str, message: &str) {
    eprintln!("[modelmix-sidecar] FATAL: {message}");
}

fn terminate_backend(app_handle: &AppHandle) {
    let state = app_handle.state::<BackendProcess>();
    if state.terminated.swap(true, Ordering::SeqCst) {
        return;
    }
    let mut guard = match state.child.lock() {
        Ok(g) => g,
        Err(_) => return,
    };
    let Some(mut child) = guard.take() else {
        log_console("no child to terminate");
        return;
    };
    let pid = child.id();
    log_console(&format!("terminating backend pid={pid}"));

    #[cfg(not(target_os = "windows"))]
    {
        let _ = child.kill();
        let _ = child.wait();
    }

    #[cfg(target_os = "windows")]
    {
        let _ = child.kill();
        let _ = child.wait();
        // Tree-kill fallback covering any PyInstaller/uvicorn descendants even if
        // the kill-on-close job was not assignable.
        match Command::new("taskkill").args(["/PID", &pid.to_string(), "/T", "/F"]).output() {
            Ok(o) => log_console(&format!(
                "taskkill /PID {pid} /T /F -> exit={} {}",
                o.status.code().unwrap_or(-1),
                String::from_utf8_lossy(&o.stdout).trim()
            )),
            Err(e) => log_console(&format!("taskkill error: {e}")),
        }
    }

    log_console("backend terminated");
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            let exe = resolve_backend_exe(app);

            let mut cmd = Command::new(&exe);
            cmd.env("LLM_COUNCIL_BIND_PORT", SIDECAR_PORT)
                .env("FRONTEND_HOST", "https://tauri.localhost,http://tauri.localhost")
                .stdin(Stdio::null())
                .stdout(Stdio::null())
                .stderr(Stdio::null());
            #[cfg(target_os = "windows")]
            {
                use std::os::windows::process::CommandExt;
                const CREATE_NO_WINDOW: u32 = 0x0800_0000;
                cmd.creation_flags(CREATE_NO_WINDOW);
            }

            let child = match cmd.spawn() {
                Ok(c) => c,
                Err(e) => {
                    log_console(&format!("SPAWN FAILED for {}: {e}", exe.display()));
                    show_fatal(
                        "ModelMix: backend failed to start",
                        &format!(
                            "Could not start the backend process:\n\n{}\n\n{}",
                            exe.display(),
                            e
                        ),
                    );
                    app.handle().exit(1);
                    return Ok(());
                }
            };
            let pid = child.id();
            log_console(&format!("SPAWNED backend pid={pid} exe={}", exe.display()));

            #[cfg(target_os = "windows")]
            {
                let assigned = win::create_kill_on_close_job().map(|job| {
                    let ok = win::assign_pid_to_job(job.0, pid);
                    // Keep the job handle alive for the whole app lifetime; when this
                    // process exits the job handle closes and the job tree is killed.
                    std::mem::forget(job);
                    ok
                });
                log_console(&format!(
                    "kill-on-close job assignment: {:?}",
                    assigned.unwrap_or(false)
                ));
            }

            app.manage(BackendProcess {
                child: Mutex::new(Some(child)),
                terminated: AtomicBool::new(false),
            });

            let handle = app.handle().clone();
            let backend_exe = exe.clone();
            std::thread::spawn(move || {
                let start = Instant::now();
                let outcome = loop {
                    if health_ok() {
                        break Ok(start.elapsed());
                    }
                    if start.elapsed() >= READY_TIMEOUT {
                        break Err(());
                    }
                    std::thread::sleep(POLL_INTERVAL);
                };
                match outcome {
                    Ok(elapsed) => {
                        log_console(&format!("BACKEND READY after {elapsed:.2?}"));
                        if let Some(w) = handle.get_webview_window("main") {
                            let _ = w.show();
                            let _ = w.set_focus();
                            log_console("main window shown");
                        }
                    }
                    Err(()) => {
                        log_console("BACKEND NOT READY within 30s — showing fatal error and exiting");
                        show_fatal(
                            "ModelMix: backend did not become ready",
                            &format!(
                                "The ModelMix backend at http://127.0.0.1:8001 did not answer \
                                 within 30 seconds.\n\nExecutable: {}",
                                backend_exe.display()
                            ),
                        );
                        handle.exit(1);
                    }
                }
            });

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while running tauri application")
        .run(|app_handle, event| {
            if let RunEvent::Exit = event {
                terminate_backend(app_handle);
            }
        });
}