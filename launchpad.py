import os
import sys
import json
import time
import socket
import threading
import subprocess
from urllib.parse import urlparse
import webbrowser
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog as fd
from http.client import HTTPConnection
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    from pystray import Icon, Menu, MenuItem
    from PIL import Image, ImageDraw
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False

# =========================
# OS detection
# =========================
IS_WINDOWS = os.name == "nt"

# =========================
# DEFAULTS (used if no config file present)
# =========================
DEFAULTS = {
    # Paths (just placeholders; you’ll set real ones in Configure…)
    "PROJECT_ROOT": r"C:\path\to\scanner_backend" if IS_WINDOWS else "/home/user/projects/scanner_backend",
    "FRONTEND_DIR": r"C:\path\to\scanner_frontend" if IS_WINDOWS else "/home/user/projects/scanner_frontend",
    "NPM_EXE": r"C:\Program Files\nodejs\npm.cmd" if IS_WINDOWS else "/usr/bin/npm",
    "DOCKER_EXE": r"C:\Program Files\Docker\Docker\resources\bin\docker.exe" if IS_WINDOWS else "/usr/bin/docker",

    # Backend/ASGI
    "DJANGO_ASGI_APP": "scanner_backend.asgi:application",
    "DAPHNE_HOST": "127.0.0.1",
    "DAPHNE_PORT": 8070,

    # Frontend
    "FRONTEND_HOST": "127.0.0.1",
    "FRONTEND_PORT": 5178,
    "AUTO_OPEN_BROWSER": True,

    # Redis
    "REDIS_HOST": "127.0.0.1",
    "REDIS_PORT": 6379,
    "REDIS_DOCKER_NAME": "local-redis-7",

    # OpenAPI schema fetch
    "FETCH_OPENAPI": False,
    "OPENAPI_REL": "/api/schema/",   # joined to http://{DAPHNE_HOST}:{DAPHNE_PORT}

    # Celery
    "CELERY_QUEUE": "ingestion",
    "CELERY_POOL": "solo",           # "solo" | "threads" | "eventlet"
    "CELERY_CONCURRENCY": 1,

    # Migrations
    # "manual" = user clicks "Run Migrations"
    # "always" = run migrations before every backend start
    "MIGRATION_POLICY": "manual",
    
    # Docker resource limits
    "DOCKER_MEMORY_LIMIT": "512m",  # Memory limit for Docker containers
    "DOCKER_CPU_LIMIT": 1.0,        # CPU limit (1.0 = 1 core)
}

# Determine persistent config directory
def get_config_path():
    """Get persistent config path that works both in development and as PyInstaller executable."""
    if IS_WINDOWS:
        config_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'LaunchPad')
    else:
        config_dir = os.path.join(os.path.expanduser('~'), '.config', 'launchpad')
    
    # Create directory if it doesn't exist
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, 'launchpad.db')

CONFIG_DB_PATH = get_config_path()


# =========================
# Config data model
# =========================
@dataclass
class Paths:
    # Paths
    PROJECT_ROOT: str
    FRONTEND_DIR: str
    NPM_EXE: str
    DOCKER_EXE: str

    # Backend / ASGI
    DJANGO_ASGI_APP: str
    DAPHNE_HOST: str
    DAPHNE_PORT: int

    # Frontend
    FRONTEND_HOST: str
    FRONTEND_PORT: int
    AUTO_OPEN_BROWSER: bool

    # Redis
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DOCKER_NAME: str

    # OpenAPI
    FETCH_OPENAPI: bool
    OPENAPI_REL: str

    # Celery
    CELERY_QUEUE: str
    CELERY_POOL: str
    CELERY_CONCURRENCY: int

    # Migrations
    MIGRATION_POLICY: str  # "manual" | "always"
    
    # Docker
    DOCKER_MEMORY_LIMIT: str
    DOCKER_CPU_LIMIT: float

    # ----- Derived paths & URLs -----
    @property
    def VENV_DIR(self):
        return os.path.join(self.PROJECT_ROOT, "venv")

    @property
    def _venv_bin(self):
        # Windows: venv\Scripts\..., Linux/macOS: venv/bin/...
        if IS_WINDOWS:
            return os.path.join(self.VENV_DIR, "Scripts")
        return os.path.join(self.VENV_DIR, "bin")

    @property
    def PYTHON_EXE(self):
        return os.path.join(self._venv_bin, "python.exe" if IS_WINDOWS else "python")

    @property
    def CELERY_EXE(self):
        return os.path.join(self._venv_bin, "celery.exe" if IS_WINDOWS else "celery")

    @property
    def DAPHNE_EXE(self):
        return os.path.join(self._venv_bin, "daphne.exe" if IS_WINDOWS else "daphne")

    @property
    def OPENAPI_URL(self):
        return f"http://{self.DAPHNE_HOST}:{self.DAPHNE_PORT}{self._normalized_rel(self.OPENAPI_REL)}"

    @property
    def FRONTEND_URL(self):
        return f"http://{self.FRONTEND_HOST}:{self.FRONTEND_PORT}"

    @property
    def CELERY_BEAT_SCHEDULE_PATH(self):
        return os.path.join(self.PROJECT_ROOT, "celerybeat-schedule")

    @staticmethod
    def _normalized_rel(p: str) -> str:
        if not p:
            return "/"
        return p if p.startswith("/") else "/" + p


class ConfigManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.data = None
        self._init_db()

    def _init_db(self):
        """Initialize the database and create the config table if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def _migrate_json_to_db(self):
        """One-time migration from old JSON config to database."""
        old_json_path = os.path.join(os.path.dirname(self.db_path), "launchpad.config.json")
        if os.path.exists(old_json_path):
            try:
                with open(old_json_path, "r", encoding="utf-8") as f:
                    old_data = json.load(f) or {}
                if old_data:
                    # Save to database
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    for k, v in old_data.items():
                        cursor.execute(
                            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
                            (k, json.dumps(v))
                        )
                    conn.commit()
                    conn.close()
                    # Rename old file as backup
                    os.rename(old_json_path, old_json_path + ".backup")
            except Exception:
                pass

    def _migrate(self, data: dict) -> dict:
        """Migrate old config keys to the current schema and drop unknowns."""
        migrated = dict(DEFAULTS)  # start from defaults

        # Copy over only known keys
        for k in DEFAULTS.keys():
            if k in data:
                migrated[k] = data[k]

        # Handle legacy FRONTEND_URL -> FRONTEND_HOST/FRONTEND_PORT
        if "FRONTEND_URL" in data:
            try:
                u = urlparse(data["FRONTEND_URL"])
                if u.hostname:
                    migrated["FRONTEND_HOST"] = u.hostname
                if u.port:
                    migrated["FRONTEND_PORT"] = u.port
            except Exception:
                pass

        # Ensure integer types
        for port_key in ["DAPHNE_PORT", "FRONTEND_PORT", "REDIS_PORT", "CELERY_CONCURRENCY"]:
            try:
                migrated[port_key] = int(migrated[port_key])
            except Exception:
                migrated[port_key] = int(DEFAULTS[port_key])

        # Ensure MIGRATION_POLICY is valid
        if migrated.get("MIGRATION_POLICY") not in ("manual", "always"):
            migrated["MIGRATION_POLICY"] = DEFAULTS["MIGRATION_POLICY"]

        return migrated

    def load(self) -> Paths:
        """Load configuration from database."""
        self._migrate_json_to_db()  # Check for old JSON config
        
        raw = {}
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM config")
            for key, value in cursor.fetchall():
                try:
                    raw[key] = json.loads(value)
                except Exception:
                    raw[key] = value
            conn.close()
        except Exception as e:
            print(f"Error loading config from database: {e}")
        
        data = self._migrate(raw)
        self.data = data
        
        # If database was empty or missing keys, save the migrated defaults
        if not raw or len(raw) < len(DEFAULTS):
            paths = Paths(**data)
            try:
                self.save(paths)
            except Exception as e:
                print(f"Error saving initial config: {e}")
            return paths
        
        return Paths(**data)

    def save(self, p: Paths):
        """Save configuration to database."""
        serializable = {k: getattr(p, k) for k in DEFAULTS.keys()}
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            for k, v in serializable.items():
                cursor.execute(
                    "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
                    (k, json.dumps(v))
                )
            conn.commit()
            conn.close()
            self.data = serializable
            print(f"Configuration saved to database: {self.db_path}")
        except Exception as e:
            print(f"Error saving config to database: {e}")
            raise


# =========================
# PROCESS CONTROL
# =========================
class ProcessStatus(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    FAILED = "failed"

class Proc:
    def __init__(self, name, args, cwd, env=None, auto_restart=False):
        self.name = name
        self.args = args
        self.cwd = cwd
        self.env = env or os.environ.copy()
        self.p = None
        self.status = ProcessStatus.STOPPED
        self.auto_restart = auto_restart
        self.start_time = None
        self.restart_count = 0
        self.last_error = None
    
    def get_resource_usage(self):
        """Get CPU and memory usage for this process."""
        if not HAS_PSUTIL or not self.p or self.p.poll() is not None:
            return None
        try:
            proc = psutil.Process(self.p.pid)
            return {
                'cpu': proc.cpu_percent(interval=0.1),
                'memory': proc.memory_info().rss / 1024 / 1024  # MB
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None


class StackController:
    def __init__(self, ui_log, cfg: Paths, status_callback=None, notify_callback=None):
        self.ui_log = ui_log
        self.cfg = cfg
        self.procs = {}
        self.lock = threading.Lock()
        self._browser_opened = False
        self.status_callback = status_callback  # Callback to update status indicators
        self.notify_callback = notify_callback  # Callback for notifications
        self._monitoring_thread = None
        self._stop_monitoring = False
        self._start_monitoring()

    def _start_monitoring(self):
        """Start background thread to monitor process status."""
        def monitor():
            while not self._stop_monitoring:
                time.sleep(2)
                with self.lock:
                    for key, proc in list(self.procs.items()):
                        if proc.p and proc.p.poll() is not None and proc.status == ProcessStatus.RUNNING:
                            # Process died
                            proc.status = ProcessStatus.FAILED
                            proc.last_error = f"Exited with code {proc.p.returncode}"
                            self.log(f"⚠️ {proc.name} crashed!")
                            if self.notify_callback:
                                self.notify_callback(f"{proc.name} stopped unexpectedly", "error")
                            
                            # Auto-restart if enabled
                            if proc.auto_restart and proc.restart_count < 3:
                                proc.restart_count += 1
                                self.log(f"🔄 Auto-restarting {proc.name} (attempt {proc.restart_count}/3)...")
                                threading.Timer(2.0, lambda: self._restart_proc(key)).start()
                        
                        # Update status callback
                        if self.status_callback:
                            self.status_callback(key, proc.status)
        
        self._monitoring_thread = threading.Thread(target=monitor, daemon=True)
        self._monitoring_thread.start()
    
    def _restart_proc(self, key):
        """Restart a failed process."""
        with self.lock:
            proc = self.procs.get(key)
            if not proc:
                return
        
        # Re-spawn based on key
        if key == "daphne":
            self.start_daphne()
        elif key == "celery_beat":
            self.start_celery_beat()
        elif key == "celery_worker":
            self.start_celery_worker()
        elif key == "frontend":
            self.start_frontend()
    
    def _find_pids_on_port(self, port: int):
        """Return a list of (pid, name, cmdline) listening on the given TCP port on localhost."""
        results = []
        try:
            if HAS_PSUTIL:
                for conn in psutil.net_connections(kind='inet'):
                    if conn.laddr and conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                        pid = conn.pid
                        if pid is None:
                            continue
                        try:
                            p = psutil.Process(pid)
                            name = p.name()
                            cmd = ' '.join(p.cmdline())[:300]
                        except Exception:
                            name, cmd = 'unknown', ''
                        results.append((pid, name, cmd))
            else:
                # Fallback: try lsof if available
                try:
                    out = subprocess.check_output(["bash", "-lc", f"command -v lsof >/dev/null 2>&1 && lsof -nP -iTCP:{port} -sTCP:LISTEN || true"], text=True)
                    for line in out.splitlines()[1:]:
                        parts = [p for p in line.split() if p]
                        if len(parts) >= 2 and parts[1].isdigit():
                            pid = int(parts[1])
                            name = parts[0]
                            results.append((pid, name, ''))
                except Exception:
                    pass
        except Exception:
            pass
        # de-dup
        seen = set()
        uniq = []
        for pid, name, cmd in results:
            if pid not in seen:
                uniq.append((pid, name, cmd))
                seen.add(pid)
        return uniq

    def _prompt_kill_pids(self, port: int, pids: list, service_name: str):
        """Show a dialog listing the conflicting processes and ask user to kill them."""
        if not pids:
            return False
        try:
            root = tk._get_default_root()
        except Exception:
            root = None
        details = "\n".join([f"PID {pid} - {name}  {cmd}".strip() for pid, name, cmd in pids])
        msg = (
            f"Port {port} required by {service_name} is already in use.\n\n"
            f"The following process(es) are listening on this port:\n\n{details}\n\n"
            f"Do you want to terminate them now?"
        )
        if root:
            try:
                answer = messagebox.askyesno("Port In Use", msg)
            except Exception:
                answer = False
        else:
            # No Tk root available; log and do not kill automatically
            self.log(msg)
            answer = False
        if not answer:
            return False
        killed_any = False
        for pid, name, cmd in pids:
            try:
                if HAS_PSUTIL:
                    psutil.Process(pid).terminate()
                    try:
                        psutil.Process(pid).wait(timeout=3)
                    except Exception:
                        psutil.Process(pid).kill()
                else:
                    os.kill(pid, 15)
                    time.sleep(1)
                    # if still alive, force kill
                    try:
                        os.kill(pid, 0)
                        os.kill(pid, 9)
                    except Exception:
                        pass
                killed_any = True
                self.log(f"Terminated PID {pid} ({name}) holding port {port}")
            except Exception as e:
                self.log(f"Failed to terminate PID {pid}: {e}")
        return killed_any

    def check_port_conflict(self, port, service_name):
        """Check if a port is already in use, optionally offer to kill the conflicting process."""
        if self._tcp_open("127.0.0.1", port, timeout=0.2):
            msg = f"⚠️ Port {port} is already in use! {service_name} may fail to start."
            self.log(msg)
            if self.notify_callback:
                self.notify_callback(msg, "warning")
            # Try to identify process and prompt user to kill
            pids = self._find_pids_on_port(port)
            if pids:
                self._prompt_kill_pids(port, pids, service_name)
                # Re-check
                if self._tcp_open("127.0.0.1", port, timeout=0.2):
                    return True
                else:
                    self.log(f"Port {port} has been freed. Continuing…")
                    return False
            return True
        return False

    # ---------- Utility ----------
    def log(self, line, tag="INFO"):
        ts = time.strftime("%H:%M:%S")
        self.ui_log(f"[{ts}] {line}", tag)

    def _spawn(self, key, proc: Proc):
        with self.lock:
            if key in self.procs and self.procs[key].p and self.procs[key].p.poll() is None:
                self.log(f"{proc.name} already running.")
                return
        
        proc.status = ProcessStatus.STARTING
        if self.status_callback:
            self.status_callback(key, proc.status)
        
        self.log(f"Starting {proc.name}…")
        try:
            p = subprocess.Popen(
                proc.args,
                cwd=proc.cwd,
                env=proc.env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            proc.start_time = datetime.now()
        except FileNotFoundError as e:
            self.log(f"ERROR: {proc.name} not found: {e}")
            proc.status = ProcessStatus.FAILED
            proc.last_error = str(e)
            if self.status_callback:
                self.status_callback(key, proc.status)
            if self.notify_callback:
                self.notify_callback(f"{proc.name} failed to start", "error")
            return

        def pump():
            for line in iter(p.stdout.readline, ''):
                if not line:
                    break
                self.ui_log(f"[{proc.name}] {line.rstrip()}", proc.name)
            rc = p.wait()
            self.ui_log(f"[{proc.name}] exited with code {rc}", proc.name)

        threading.Thread(target=pump, daemon=True).start()
        
        with self.lock:
            proc.p = p
            proc.status = ProcessStatus.RUNNING
            self.procs[key] = proc
        
        if self.status_callback:
            self.status_callback(key, proc.status)
        if self.notify_callback:
            self.notify_callback(f"{proc.name} started successfully", "success")

    def _terminate(self, key):
        with self.lock:
            proc = self.procs.get(key)
        if not proc or not proc.p:
            return
        if proc.p.poll() is None:
            self.log(f"Stopping {proc.name}…")
            try:
                proc.p.terminate()
            except Exception:
                pass
            for _ in range(20):
                if proc.p.poll() is not None:
                    break
                time.sleep(0.2)
            if proc.p.poll() is None:
                try:
                    proc.p.kill()
                except Exception:
                    pass
            self.log(f"{proc.name} stopped.")
        with self.lock:
            proc.status = ProcessStatus.STOPPED
            if self.status_callback:
                self.status_callback(key, proc.status)
            self.procs.pop(key, None)

    def _tcp_open(self, host, port, timeout=0.5):
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            return False

    def _http_ok(self, url, timeout=1.0):
        try:
            host_port = url.split("//", 1)[1].split("/", 1)[0]
            host, port = host_port.split(":")
            path = url.split(host_port, 1)[1] or "/"
            conn = HTTPConnection(host, int(port), timeout=timeout)
            conn.request("GET", path)
            resp = conn.getresponse()
            return 200 <= resp.status < 500
        except Exception:
            return False

    # ---------- Preflight ----------
    def migrate_db(self):
        self.log("Running Django migrations…")
        args = [self.cfg.PYTHON_EXE, os.path.join(self.cfg.PROJECT_ROOT, "manage.py"), "migrate", "--noinput"]
        proc = Proc("migrate", args, cwd=self.cfg.PROJECT_ROOT)
        self._spawn("migrate", proc)

    # ---------- Redis ----------
    def ensure_redis(self):
        if self._tcp_open(self.cfg.REDIS_HOST, self.cfg.REDIS_PORT):
            self.log(f"Redis already available at {self.cfg.REDIS_HOST}:{self.cfg.REDIS_PORT}.")
            return
        if not self.cfg.DOCKER_EXE or not os.path.exists(self.cfg.DOCKER_EXE):
            self.log("Redis not detected and DOCKER_EXE not configured/exists. Start Redis manually.")
            return

        self.log("Redis not detected; attempting to launch Docker Redis…")
        args = [
            self.cfg.DOCKER_EXE, "run", "--rm", "-d",
            "--name", self.cfg.REDIS_DOCKER_NAME,
            "-p", f"{self.cfg.REDIS_PORT}:6379",
            "--memory", self.cfg.DOCKER_MEMORY_LIMIT,
            "--cpus", str(self.cfg.DOCKER_CPU_LIMIT),
            "redis:7",
        ]
        proc = Proc("redis(docker)", args, cwd=self.cfg.PROJECT_ROOT)
        self._spawn("redis_docker", proc)
        for _ in range(40):
            if self._tcp_open(self.cfg.REDIS_HOST, self.cfg.REDIS_PORT):
                self.log("Redis is up.")
                return
            time.sleep(0.25)
        self.log("WARNING: Redis still not reachable. Check logs or start your service manually.")

    # ---------- Backend ----------
    def start_daphne(self):
        self.check_port_conflict(self.cfg.DAPHNE_PORT, "Daphne")
        args = [
            self.cfg.DAPHNE_EXE,
            f"{self.cfg.DJANGO_ASGI_APP}",
            "--port", str(self.cfg.DAPHNE_PORT),
            "--bind", self.cfg.DAPHNE_HOST,
        ]
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        proc = Proc("daphne", args, cwd=self.cfg.PROJECT_ROOT, env=env, auto_restart=True)
        self._spawn("daphne", proc)

        def waiter():
            for _ in range(120):
                if self._tcp_open(self.cfg.DAPHNE_HOST, self.cfg.DAPHNE_PORT):
                    self.log(f"Daphne reachable at http://{self.cfg.DAPHNE_HOST}:{self.cfg.DAPHNE_PORT}")
                    if self.cfg.FETCH_OPENAPI and self.cfg.OPENAPI_URL:
                        self.fetch_openapi()
                    return
                time.sleep(0.5)
            self.log("ERROR: Daphne did not become reachable in time.")

        threading.Thread(target=waiter, daemon=True).start()

    def fetch_openapi(self):
        self.log("Fetching OpenAPI schema…")
        try:
            import urllib.request
            with urllib.request.urlopen(self.cfg.OPENAPI_URL, timeout=5) as r:
                data = r.read()
            out = os.path.join(self.cfg.PROJECT_ROOT, "openapi.json")
            with open(out, "wb") as f:
                f.write(data)
            self.log(f"OpenAPI saved → {out}")
        except Exception as e:
            self.log(f"OpenAPI fetch failed: {e}")

    def start_celery_beat(self):
        try:
            if os.path.exists(self.cfg.CELERY_BEAT_SCHEDULE_PATH):
                os.remove(self.cfg.CELERY_BEAT_SCHEDULE_PATH)
        except Exception as e:
            self.log(f"WARNING: could not remove old beat schedule: {e}")
        args = [
            self.cfg.CELERY_EXE, "-A", "scanner_backend.celery:app",
            "beat", "-l", "info", "-s", self.cfg.CELERY_BEAT_SCHEDULE_PATH,
        ]
        proc = Proc("celery-beat", args, cwd=self.cfg.PROJECT_ROOT, auto_restart=True)
        self._spawn("celery_beat", proc)

    def start_celery_worker(self):
        if self.cfg.CELERY_POOL in ("eventlet", "gevent"):
            args = [
                self.cfg.CELERY_EXE, "-A", "scanner_backend.celery:app", "worker",
                "-Q", self.cfg.CELERY_QUEUE, "-l", "info",
                "-P", self.cfg.CELERY_POOL, "-c", str(self.cfg.CELERY_CONCURRENCY),
                "--without-gossip", "--without-mingle", "--without-heartbeat",
            ]
        else:
            args = [
                self.cfg.CELERY_EXE, "-A", "scanner_backend.celery:app", "worker",
                "-Q", self.cfg.CELERY_QUEUE, "-l", "info",
                "-P", self.cfg.CELERY_POOL, "-c", str(self.cfg.CELERY_CONCURRENCY),
            ]
        proc = Proc("celery-worker", args, cwd=self.cfg.PROJECT_ROOT, auto_restart=True)
        self._spawn("celery_worker", proc)

    # ---------- Frontend ----------
    def start_frontend(self):
        # Check if frontend is already running (managed by us)
        with self.lock:
            if "frontend" in self.procs and self.procs["frontend"].p and self.procs["frontend"].p.poll() is None:
                self.log("Frontend is already running (managed).")
                return
        
        # Check if port is in use by another process
        if self._tcp_open("127.0.0.1", self.cfg.FRONTEND_PORT, timeout=0.2):
            self.log(f"⚠️ Frontend port {self.cfg.FRONTEND_PORT} is already in use by another process.")
            if self.notify_callback:
                self.notify_callback(f"Frontend port {self.cfg.FRONTEND_PORT} already in use", "warning")
            # Try to identify and optionally kill the process
            pids = self._find_pids_on_port(self.cfg.FRONTEND_PORT)
            if pids:
                if self._prompt_kill_pids(self.cfg.FRONTEND_PORT, pids, "Frontend"):
                    time.sleep(1)  # Give it a moment to free the port
                    if self._tcp_open("127.0.0.1", self.cfg.FRONTEND_PORT, timeout=0.2):
                        self.log("Port still in use. Aborting frontend start.")
                        return
                else:
                    self.log("Port conflict not resolved. Aborting frontend start.")
                    return
            else:
                self.log("Could not identify process on port. Aborting frontend start.")
                return
        
        args = [
            self.cfg.NPM_EXE, "run", "dev", "--",
            "--port", str(self.cfg.FRONTEND_PORT),
            "--strictPort",
            "--host", self.cfg.FRONTEND_HOST,
        ]
        proc = Proc("frontend", args, cwd=self.cfg.FRONTEND_DIR, auto_restart=True)
        self._spawn("frontend", proc)

        if self.cfg.AUTO_OPEN_BROWSER:
            def opener():
                for _ in range(240):
                    if self._http_ok(self.cfg.FRONTEND_URL, timeout=0.5):
                        if not self._browser_opened:
                            self._browser_opened = True
                            self.log(f"Opening browser → {self.cfg.FRONTEND_URL}")
                            webbrowser.open(self.cfg.FRONTEND_URL)
                        return
                    time.sleep(0.5)
                self.log("WARNING: Frontend URL did not become reachable in time.")
            threading.Thread(target=opener, daemon=True).start()

    # ---------- Orchestration ----------
    def start_backend(self):
        self.ensure_redis()
        if self.cfg.MIGRATION_POLICY == "always":
            self.migrate_db()
            # give migrate some breathing room; it runs in its own proc anyway
            time.sleep(1.0)
        threading.Timer(1.0, self.start_daphne).start()
        threading.Timer(1.5, self.start_celery_beat).start()
        threading.Timer(2.0, self.start_celery_worker).start()

    def start_all(self):
        self.start_backend()
        threading.Timer(3.0, self.start_frontend).start()

    def stop_all(self):
        """Stop all managed processes without blocking the UI thread."""
        def worker():
            order = ["frontend", "celery_worker", "celery_beat", "daphne", "redis_docker", "migrate"]
            self.log("Stopping all services…")
            for key in order:
                try:
                    self._terminate(key)
                    time.sleep(0.5)  # Brief delay between terminations
                except Exception as e:
                    self.log(f"Error stopping {key}: {e}")
            
            # Verify ports are freed
            time.sleep(1)
            if self._tcp_open("127.0.0.1", self.cfg.FRONTEND_PORT, timeout=0.2):
                self.log(f"⚠️ Warning: Frontend port {self.cfg.FRONTEND_PORT} still in use after stop")
            if self._tcp_open("127.0.0.1", self.cfg.DAPHNE_PORT, timeout=0.2):
                self.log(f"⚠️ Warning: Daphne port {self.cfg.DAPHNE_PORT} still in use after stop")
            
            self.log("All services stopped.")
        threading.Thread(target=worker, daemon=True).start()


# --------------- UI: Configure Dialog ---------------
class ConfigDialog(tk.Toplevel):
    def __init__(self, parent, cfg: Paths, on_save):
        super().__init__(parent)
        self.title("Configure LaunchPad")
        self.resizable(False, False)
        self.cfg = cfg
        self.on_save = on_save

        pad = {'padx': 6, 'pady': 4}
        frm = ttk.Frame(self)
        frm.pack(fill="both", expand=True, **pad)

        r = 0
        # Backend root
        ttk.Label(frm, text="Backend PROJECT_ROOT:").grid(row=r, column=0, sticky="w", **pad)
        self.e_backend = ttk.Entry(frm, width=70)
        self.e_backend.grid(row=r, column=1, **pad, sticky="we")
        self.e_backend.insert(0, self.cfg.PROJECT_ROOT)
        ttk.Button(frm, text="Browse…", command=self._browse_backend).grid(row=r, column=2, **pad)
        r += 1

        # Frontend dir
        ttk.Label(frm, text="Frontend FRONTEND_DIR:").grid(row=r, column=0, sticky="w", **pad)
        self.e_frontend = ttk.Entry(frm, width=70)
        self.e_frontend.grid(row=r, column=1, **pad, sticky="we")
        self.e_frontend.insert(0, self.cfg.FRONTEND_DIR)
        ttk.Button(frm, text="Browse…", command=self._browse_frontend).grid(row=r, column=2, **pad)
        r += 1

        # NPM path
        ttk.Label(frm, text="NPM_EXE:").grid(row=r, column=0, sticky="w", **pad)
        self.e_npm = ttk.Entry(frm, width=70)
        self.e_npm.grid(row=r, column=1, **pad, sticky="we")
        self.e_npm.insert(0, self.cfg.NPM_EXE)
        ttk.Button(frm, text="Browse…", command=self._browse_npm).grid(row=r, column=2, **pad)
        r += 1

        # Docker path (optional)
        ttk.Label(frm, text="DOCKER_EXE (optional):").grid(row=r, column=0, sticky="w", **pad)
        self.e_docker = ttk.Entry(frm, width=70)
        self.e_docker.grid(row=r, column=1, **pad, sticky="we")
        self.e_docker.insert(0, self.cfg.DOCKER_EXE)
        ttk.Button(frm, text="Browse…", command=self._browse_docker).grid(row=r, column=2, **pad)
        r += 1

        # ----- Hosts / Ports -----
        ttk.Label(frm, text="Daphne Host:").grid(row=r, column=0, sticky="w", **pad)
        self.e_dhost = ttk.Entry(frm, width=30)
        self.e_dhost.grid(row=r, column=1, sticky="w", **pad)
        self.e_dhost.insert(0, self.cfg.DAPHNE_HOST)
        r += 1

        ttk.Label(frm, text="Daphne Port:").grid(row=r, column=0, sticky="w", **pad)
        self.e_dport = ttk.Entry(frm, width=15)
        self.e_dport.grid(row=r, column=1, sticky="w", **pad)
        self.e_dport.insert(0, str(self.cfg.DAPHNE_PORT))
        r += 1

        ttk.Label(frm, text="Frontend Host:").grid(row=r, column=0, sticky="w", **pad)
        self.e_fhost = ttk.Entry(frm, width=30)
        self.e_fhost.grid(row=r, column=1, sticky="w", **pad)
        self.e_fhost.insert(0, self.cfg.FRONTEND_HOST)
        r += 1

        ttk.Label(frm, text="Frontend Port:").grid(row=r, column=0, sticky="w", **pad)
        self.e_fport = ttk.Entry(frm, width=15)
        self.e_fport.grid(row=r, column=1, sticky="w", **pad)
        self.e_fport.insert(0, str(self.cfg.FRONTEND_PORT))
        r += 1

        # ----- Redis -----
        ttk.Label(frm, text="Redis Host:").grid(row=r, column=0, sticky="w", **pad)
        self.e_rhost = ttk.Entry(frm, width=30)
        self.e_rhost.grid(row=r, column=1, sticky="w", **pad)
        self.e_rhost.insert(0, self.cfg.REDIS_HOST)
        r += 1

        ttk.Label(frm, text="Redis Port:").grid(row=r, column=0, sticky="w", **pad)
        self.e_rport = ttk.Entry(frm, width=15)
        self.e_rport.grid(row=r, column=1, sticky="w", **pad)
        self.e_rport.insert(0, str(self.cfg.REDIS_PORT))
        r += 1

        # ----- Celery -----
        ttk.Label(frm, text="Celery Queue:").grid(row=r, column=0, sticky="w", **pad)
        self.e_cqueue = ttk.Entry(frm, width=30)
        self.e_cqueue.grid(row=r, column=1, sticky="w", **pad)
        self.e_cqueue.insert(0, self.cfg.CELERY_QUEUE)
        r += 1

        ttk.Label(frm, text="Celery Pool:").grid(row=r, column=0, sticky="w", **pad)
        self.cb_cpool = ttk.Combobox(frm, values=["solo", "threads", "eventlet"], state="readonly", width=15)
        self.cb_cpool.grid(row=r, column=1, sticky="w", **pad)
        self.cb_cpool.set(self.cfg.CELERY_POOL)
        r += 1

        ttk.Label(frm, text="Celery Concurrency:").grid(row=r, column=0, sticky="w", **pad)
        self.e_cconc = ttk.Entry(frm, width=10)
        self.e_cconc.grid(row=r, column=1, sticky="w", **pad)
        self.e_cconc.insert(0, str(self.cfg.CELERY_CONCURRENCY))
        r += 1

        # ----- Migration Policy -----
        ttk.Label(frm, text="Migration Policy:").grid(row=r, column=0, sticky="w", **pad)
        self.cb_mig = ttk.Combobox(frm, values=["manual", "always"], state="readonly", width=15)
        self.cb_mig.grid(row=r, column=1, sticky="w", **pad)
        self.cb_mig.set(self.cfg.MIGRATION_POLICY)
        r += 1

        # ----- OpenAPI -----
        self.var_fetch_openapi = tk.BooleanVar(value=self.cfg.FETCH_OPENAPI)
        ttk.Checkbutton(frm, text="Fetch OpenAPI on startup", variable=self.var_fetch_openapi).grid(
            row=r, column=0, columnspan=2, sticky="w", **pad
        )
        r += 1

        ttk.Label(frm, text="OpenAPI Relative Path:").grid(row=r, column=0, sticky="w", **pad)
        self.e_openapi_rel = ttk.Entry(frm, width=40)
        self.e_openapi_rel.grid(row=r, column=1, sticky="w", **pad)
        self.e_openapi_rel.insert(0, self.cfg.OPENAPI_REL)
        r += 1

        # ----- Browser auto-open -----
        self.var_auto_open = tk.BooleanVar(value=self.cfg.AUTO_OPEN_BROWSER)
        ttk.Checkbutton(frm, text="Auto-open browser for frontend", variable=self.var_auto_open).grid(
            row=r, column=0, columnspan=2, sticky="w", **pad
        )
        r += 1
        
        # ----- Docker Settings -----
        ttk.Label(frm, text="Docker Memory Limit:").grid(row=r, column=0, sticky="w", **pad)
        self.e_docker_mem = ttk.Entry(frm, width=15)
        self.e_docker_mem.grid(row=r, column=1, sticky="w", **pad)
        self.e_docker_mem.insert(0, self.cfg.DOCKER_MEMORY_LIMIT)
        ttk.Label(frm, text="(e.g., 512m, 1g)").grid(row=r, column=2, sticky="w")
        r += 1
        
        ttk.Label(frm, text="Docker CPU Limit:").grid(row=r, column=0, sticky="w", **pad)
        self.e_docker_cpu = ttk.Entry(frm, width=15)
        self.e_docker_cpu.grid(row=r, column=1, sticky="w", **pad)
        self.e_docker_cpu.insert(0, str(self.cfg.DOCKER_CPU_LIMIT))
        ttk.Label(frm, text="(e.g., 1.0 = 1 core)").grid(row=r, column=2, sticky="w")
        r += 1

        # Action buttons
        btns = ttk.Frame(frm)
        btns.grid(row=r, column=0, columnspan=3, sticky="e", **pad)
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="right", padx=5)
        ttk.Button(btns, text="Save", command=self._save).pack(side="right")

        self.grab_set()
        self.focus()

    # ---- Browsers ----
    def _browse_backend(self):
        path = fd.askdirectory(title="Select Backend Project Root")
        if path:
            self.e_backend.delete(0, tk.END)
            self.e_backend.insert(0, path)

    def _browse_frontend(self):
        path = fd.askdirectory(title="Select Frontend (folder with package.json)")
        if path:
            self.e_frontend.delete(0, tk.END)
            self.e_frontend.insert(0, path)

    def _browse_npm(self):
        path = fd.askopenfilename(
            title="Select npm (npm.cmd / npm)",
            filetypes=[("Command or binary", "*.*")],
        )
        if path:
            self.e_npm.delete(0, tk.END)
            self.e_npm.insert(0, path)

    def _browse_docker(self):
        path = fd.askopenfilename(
            title="Select docker executable",
            filetypes=[("Executable", "*.*")],
        )
        if path:
            self.e_docker.delete(0, tk.END)
            self.e_docker.insert(0, path)

    # ---- Validation helpers ----
    @staticmethod
    def _parse_port(name: str, value: str, errs: list[str]) -> int:
        try:
            p = int(value)
            if not (1 <= p <= 65535):
                raise ValueError
            return p
        except Exception:
            errs.append(f"{name} must be an integer between 1 and 65535 (got {value!r}).")
            return 0

    @staticmethod
    def _parse_int(name: str, value: str, min_v: int, errs: list[str]) -> int:
        try:
            v = int(value)
            if v < min_v:
                raise ValueError
            return v
        except Exception:
            errs.append(f"{name} must be an integer ≥ {min_v} (got {value!r}).")
            return 0

    def _save(self):
        errs: list[str] = []

        proj = self.e_backend.get().strip()
        fe = self.e_frontend.get().strip()
        npm = self.e_npm.get().strip()
        docker = self.e_docker.get().strip()  # optional

        dhost = self.e_dhost.get().strip() or "127.0.0.1"
        dport = self._parse_port("Daphne Port", self.e_dport.get().strip(), errs)

        fhost = self.e_fhost.get().strip() or "127.0.0.1"
        fport = self._parse_port("Frontend Port", self.e_fport.get().strip(), errs)

        rhost = self.e_rhost.get().strip() or "127.0.0.1"
        rport = self._parse_port("Redis Port", self.e_rport.get().strip(), errs)

        cqueue = self.e_cqueue.get().strip() or "ingestion"
        cpool = self.cb_cpool.get().strip() or "solo"
        cconc = self._parse_int("Celery Concurrency", self.e_cconc.get().strip(), 1, errs)

        mig_policy = self.cb_mig.get().strip() or "manual"
        if mig_policy not in ("manual", "always"):
            errs.append("Migration Policy must be 'manual' or 'always'.")

        fetch_openapi = self.var_fetch_openapi.get()
        openapi_rel = self.e_openapi_rel.get().strip() or "/api/schema/"
        if not openapi_rel.startswith("/"):
            openapi_rel = "/" + openapi_rel

        auto_open = self.var_auto_open.get()
        
        # Docker settings
        docker_mem = self.e_docker_mem.get().strip() or "512m"
        docker_cpu_str = self.e_docker_cpu.get().strip() or "1.0"
        try:
            docker_cpu = float(docker_cpu_str)
            if docker_cpu <= 0:
                raise ValueError
        except:
            errs.append(f"Docker CPU limit must be a positive number (got {docker_cpu_str!r})")
            docker_cpu = 1.0

        # Basic path checks
        if not os.path.exists(proj):
            errs.append(f"PROJECT_ROOT not found: {proj}")
        if not os.path.exists(fe):
            errs.append(f"FRONTEND_DIR not found: {fe}")
        if not os.path.exists(npm):
            errs.append(f"NPM_EXE not found: {npm}")

        # Derived executables from backend venv
        venv_dir = os.path.join(proj, "venv")
        venv_bin = os.path.join(venv_dir, "Scripts" if IS_WINDOWS else "bin")
        py = os.path.join(venv_bin, "python.exe" if IS_WINDOWS else "python")
        cel = os.path.join(venv_bin, "celery.exe" if IS_WINDOWS else "celery")
        dph = os.path.join(venv_bin, "daphne.exe" if IS_WINDOWS else "daphne")

        if not os.path.exists(py):
            errs.append(f"Python venv not found: {py} (expected under PROJECT_ROOT/venv)")
        if not os.path.exists(cel):
            errs.append(f"Celery executable not found: {cel}")
        if not os.path.exists(dph):
            errs.append(f"Daphne executable not found: {dph}")

        pkg_json = os.path.join(fe, "package.json")
        if not os.path.exists(pkg_json):
            errs.append(f"package.json not found in FRONTEND_DIR: {fe}")

        if cpool == "solo" and cconc != 1:
            errs.append("With Celery pool 'solo', concurrency must be 1.")

        if errs:
            messagebox.showerror("Invalid Configuration", "Fix these issues:\n\n" + "\n".join(errs))
            return

        new_cfg = Paths(
            PROJECT_ROOT=proj,
            FRONTEND_DIR=fe,
            NPM_EXE=npm,
            DOCKER_EXE=docker,
            DJANGO_ASGI_APP=DEFAULTS["DJANGO_ASGI_APP"],
            DAPHNE_HOST=dhost,
            DAPHNE_PORT=dport,
            FRONTEND_HOST=fhost,
            FRONTEND_PORT=fport,
            AUTO_OPEN_BROWSER=auto_open,
            REDIS_HOST=rhost,
            REDIS_PORT=rport,
            REDIS_DOCKER_NAME=DEFAULTS["REDIS_DOCKER_NAME"],
            FETCH_OPENAPI=fetch_openapi,
            OPENAPI_REL=openapi_rel,
            CELERY_QUEUE=cqueue,
            CELERY_POOL=cpool,
            CELERY_CONCURRENCY=cconc,
            MIGRATION_POLICY=mig_policy,
            DOCKER_MEMORY_LIMIT=docker_mem,
            DOCKER_CPU_LIMIT=docker_cpu,
        )

        self.on_save(new_cfg)
        self.destroy()


# --------------- Main App UI ---------------
class App(tk.Tk):
    def __init__(self, cfg: Paths, cfg_mgr: ConfigManager):
        super().__init__()
        self.title("LaunchPad")
        self.geometry("1200x800")
        self.cfg = cfg
        self.cfg_mgr = cfg_mgr
        self.status_indicators = {}
        self.resource_labels = {}
        self.log_tabs = {}

        # Top button bar
        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=8)

        self.btn_config = ttk.Button(top, text="Configure…", command=self.open_config)
        self.btn_run_migrate = ttk.Button(top, text="Run Migrations", command=self.run_migrations)
        self.btn_view_config = ttk.Button(top, text="View DB Config", command=self.view_db_config)
        self.btn_django_shell = ttk.Button(top, text="Django Shell", command=self.open_django_shell)
        self.btn_git_status = ttk.Button(top, text="Git Status", command=self.show_git_status)
        
        self.btn_start_backend = ttk.Button(top, text="Start Backend", command=self.start_backend)
        self.btn_start_fe = ttk.Button(top, text="Start Frontend", command=self.start_frontend)
        self.btn_start_all = ttk.Button(top, text="Start All", command=self.start_all)
        self.btn_stop_all = ttk.Button(top, text="Stop All", command=self.stop_all)

        self.btn_config.pack(side="left", padx=5)
        self.btn_run_migrate.pack(side="left", padx=5)
        self.btn_view_config.pack(side="left", padx=5)
        self.btn_django_shell.pack(side="left", padx=5)
        self.btn_git_status.pack(side="left", padx=5)
        self.btn_start_backend.pack(side="left", padx=5)
        self.btn_start_fe.pack(side="left", padx=5)
        self.btn_start_all.pack(side="left", padx=5)
        self.btn_stop_all.pack(side="right", padx=5)
        
        # Second row for custom commands and tools
        tools_row = ttk.Frame(self)
        tools_row.pack(fill="x", padx=10, pady=(0, 8))
        
        ttk.Button(tools_row, text="Build Frontend", command=self.build_frontend).pack(side="left", padx=2)
        ttk.Button(tools_row, text="📊 System Analysis", command=self.analyze_system).pack(side="left", padx=2)
        
        # Separator
        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=10)

        # Status indicators panel with CPU/Memory
        status_frame = ttk.LabelFrame(self, text="Service Status & Resources", padding=10)
        status_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        services = [
            ("redis_docker", "Redis"),
            ("daphne", "Daphne"),
            ("celery_beat", "Celery Beat"),
            ("celery_worker", "Celery Worker"),
            ("frontend", "Frontend"),
        ]
        
        for i, (key, label) in enumerate(services):
            # Status indicator
            indicator = tk.Canvas(status_frame, width=20, height=20, highlightthickness=0)
            indicator.grid(row=0, column=i*3, padx=5, sticky="w")
            circle = indicator.create_oval(2, 2, 18, 18, fill="gray", outline="darkgray")
            indicator.circle_id = circle
            
            # Service name
            lbl = ttk.Label(status_frame, text=label, font=("TkDefaultFont", 9, "bold"))
            lbl.grid(row=0, column=i*3+1, padx=(0, 10), sticky="w")
            
            # Resource usage label
            resource_lbl = ttk.Label(status_frame, text="--", font=("Consolas", 8), foreground="gray")
            resource_lbl.grid(row=1, column=i*3+1, padx=(0, 10), sticky="w")
            
            self.status_indicators[key] = indicator
            self.resource_labels[key] = resource_lbl

        # Tabbed log view with search
        log_container = ttk.Frame(self)
        log_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Search bar
        search_frame = ttk.Frame(log_container)
        search_frame.pack(fill="x", pady=(0, 5))
        
        ttk.Label(search_frame, text="Search logs:").pack(side="left", padx=5)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind('<Return>', lambda e: self.search_logs())
        
        ttk.Button(search_frame, text="Find", command=self.search_logs).pack(side="left", padx=2)
        ttk.Button(search_frame, text="Clear", command=self.clear_search).pack(side="left", padx=2)
        ttk.Button(search_frame, text="Export Logs", command=self.export_logs).pack(side="right", padx=5)
        
        self.notebook = ttk.Notebook(log_container)
        self.notebook.pack(fill="both", expand=True)
        
        # Create tabs for each service + an "All" tab
        log_names = [
            ("All", "All"),
            ("daphne", "Daphne"),
            ("celery-beat", "Celery Beat"),
            ("celery-worker", "Celery Worker"),
            ("frontend", "Frontend"),
            ("redis(docker)", "Redis"),
            ("migrate", "Migrations"),
            ("INFO", "System"),
        ]
        
        for tag, label in log_names:
            log_widget = scrolledtext.ScrolledText(self.notebook, wrap="word", font=("Consolas", 9))
            log_widget.tag_config("highlight", background="yellow", foreground="black")
            log_widget.tag_config("error", foreground="red")
            log_widget.tag_config("warning", foreground="orange")
            self.notebook.add(log_widget, text=label)
            self.log_tabs[tag] = log_widget

        self.controller = StackController(
            self.append_log, 
            self.cfg, 
            status_callback=self.update_status,
            notify_callback=self.show_notification
        )
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Initial sanity check
        self._sanity_check(show_dialog=False)
        
        # Start resource monitoring
        self._start_resource_monitoring()
        
        # Setup keyboard shortcuts
        self._setup_shortcuts()
    
    def _setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        self.bind('<Control-b>', lambda e: self.start_backend())
        self.bind('<Control-f>', lambda e: self.start_frontend())
        self.bind('<Control-a>', lambda e: self.start_all())
        self.bind('<Control-q>', lambda e: self.stop_all())
        self.bind('<Control-m>', lambda e: self.run_migrations())
        self.bind('<Control-d>', lambda e: self.open_django_shell())
        self.bind('<Control-g>', lambda e: self.show_git_status())
        self.bind('<Control-i>', lambda e: self.analyze_system())
        self.bind('<Control-k>', lambda e: self.monitor_celery_queues())
        self.bind('<Control-i>', lambda e: self.analyze_system())
    
    def _start_resource_monitoring(self):
        """Start background thread to update resource usage."""
        def monitor():
            while True:
                time.sleep(2)
                if not HAS_PSUTIL:
                    continue
                
                with self.controller.lock:
                    for key, proc in self.controller.procs.items():
                        if key in self.resource_labels:
                            usage = proc.get_resource_usage()
                            if usage:
                                text = f"CPU: {usage['cpu']:.1f}%  RAM: {usage['memory']:.0f} MB"
                                color = "green" if usage['cpu'] < 50 else "orange" if usage['cpu'] < 80 else "red"
                            else:
                                text = "--"
                                color = "gray"
                            
                            self.after(0, lambda k=key, t=text, c=color: self._update_resource_label(k, t, c))
        
        threading.Thread(target=monitor, daemon=True).start()
    
    def _update_resource_label(self, key, text, color):
        """Update resource label in UI thread."""
        if key in self.resource_labels:
            self.resource_labels[key].config(text=text, foreground=color)
    
    def update_status(self, service_key, status):
        """Update status indicator for a service."""
        if service_key not in self.status_indicators:
            return
        
        indicator = self.status_indicators[service_key]
        color_map = {
            ProcessStatus.STOPPED: "gray",
            ProcessStatus.STARTING: "yellow",
            ProcessStatus.RUNNING: "green",
            ProcessStatus.FAILED: "red",
        }
        color = color_map.get(status, "gray")
        indicator.itemconfig(indicator.circle_id, fill=color)
    
    def show_notification(self, message, msg_type="info"):
        """Show desktop notification (simplified version)."""
        # For Linux with notify-send
        if not IS_WINDOWS:
            try:
                icon = {"success": "dialog-information", "error": "dialog-error", "warning": "dialog-warning"}.get(msg_type, "dialog-information")
                subprocess.Popen(["notify-send", "-i", icon, "LaunchPad", message], 
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except:
                pass

    def open_config(self):
        def on_save(new_cfg: Paths):
            self.cfg_mgr.save(new_cfg)
            self.cfg = new_cfg
            self.controller.cfg = new_cfg
            self.append_log("Configuration saved. Re-running sanity checks …")
            self._sanity_check(show_dialog=True)

        ConfigDialog(self, self.cfg, on_save)
    
    def open_django_shell(self):
        """Open Django shell in a new terminal."""
        try:
            cmd = f"cd '{self.cfg.PROJECT_ROOT}' && '{self.cfg.PYTHON_EXE}' manage.py shell"
            if IS_WINDOWS:
                subprocess.Popen(['cmd', '/c', 'start', 'cmd', '/k', cmd])
            else:
                # Try different terminal emulators
                for term in ['gnome-terminal', 'xterm', 'konsole', 'xfce4-terminal']:
                    try:
                        subprocess.Popen([term, '--', 'bash', '-c', cmd])
                        self.append_log("Django shell opened in new terminal")
                        return
                    except FileNotFoundError:
                        continue
                self.append_log("Could not find terminal emulator")
        except Exception as e:
            self.append_log(f"Error opening Django shell: {e}")
    
    def show_git_status(self):
        """Show Git status in a dialog."""
        dialog = tk.Toplevel(self)
        dialog.title("Git Status")
        dialog.geometry("700x500")
        
        text = scrolledtext.ScrolledText(dialog, wrap="word", font=("Consolas", 10))
        text.pack(fill="both", expand=True, padx=10, pady=10)
        
        def run_git_command(cmd, title):
            try:
                result = subprocess.run(
                    cmd, 
                    cwd=self.cfg.PROJECT_ROOT, 
                    capture_output=True, 
                    text=True, 
                    shell=True
                )
                text.insert("end", f"\n{'='*60}\n{title}\n{'='*60}\n")
                text.insert("end", result.stdout if result.stdout else "(no output)\n")
                if result.stderr:
                    text.insert("end", f"\nErrors:\n{result.stderr}\n")
            except Exception as e:
                text.insert("end", f"Error running {title}: {e}\n")
        
        def refresh():
            text.delete("1.0", "end")
            run_git_command("git branch --show-current", "Current Branch")
            run_git_command("git status --short", "Status")
            run_git_command("git log --oneline -5", "Recent Commits")
            text.config(state="disabled")
        
        def git_pull():
            text.config(state="normal")
            run_git_command("git pull", "Git Pull")
            text.config(state="disabled")
        
        def git_push():
            text.config(state="normal")
            run_git_command("git push", "Git Push")
            text.config(state="disabled")
        
        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        ttk.Button(btn_frame, text="Refresh", command=refresh).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Pull", command=git_pull).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Push", command=git_push).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Close", command=dialog.destroy).pack(side="right", padx=5)
        
        refresh()
        dialog.grab_set()
    
    def view_db_config(self):
        """Display current configuration from database in a dialog."""
        dialog = tk.Toplevel(self)
        dialog.title("Database Configuration")
        dialog.geometry("800x600")
        dialog.resizable(True, True)
        
        # Header
        header = ttk.Frame(dialog)
        header.pack(fill="x", padx=10, pady=10)
        ttk.Label(header, text=f"Configuration Database: {CONFIG_DB_PATH}", 
                 font=("TkDefaultFont", 9, "bold")).pack(anchor="w")
        
        # Create scrolled text widget
        text_frame = ttk.Frame(dialog)
        text_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        text = scrolledtext.ScrolledText(text_frame, wrap="none", font=("Consolas", 10))
        text.pack(fill="both", expand=True)
        
        # Load and display config from database
        try:
            conn = sqlite3.connect(CONFIG_DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM config ORDER BY key")
            rows = cursor.fetchall()
            conn.close()
            
            text.insert("end", f"{'Key':<30} | Value\n")
            text.insert("end", f"{'-'*30}-+-{'-'*60}\n")
            
            for key, value in rows:
                try:
                    parsed_value = json.loads(value)
                    if isinstance(parsed_value, str):
                        display_value = parsed_value
                    else:
                        display_value = json.dumps(parsed_value)
                except:
                    display_value = str(value)
                
                text.insert("end", f"{key:<30} | {display_value}\n")
            
            text.insert("end", f"\n{'='*90}\n")
            text.insert("end", f"Total entries: {len(rows)}\n")
            text.insert("end", f"Database location: {CONFIG_DB_PATH}\n")
            
        except Exception as e:
            text.insert("end", f"Error reading database: {e}\n")
        
        text.config(state="disabled")
        
        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        def export_config():
            """Export config to JSON file."""
            from tkinter import filedialog
            filepath = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                initialfile="launchpad_config.json"
            )
            if filepath:
                try:
                    conn = sqlite3.connect(CONFIG_DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute("SELECT key, value FROM config")
                    data = {key: json.loads(value) for key, value in cursor.fetchall()}
                    conn.close()
                    
                    with open(filepath, 'w') as f:
                        json.dump(data, f, indent=2)
                    messagebox.showinfo("Success", f"Configuration exported to:\n{filepath}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to export config:\n{e}")
        
        ttk.Button(btn_frame, text="Export to JSON", command=export_config).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Close", command=dialog.destroy).pack(side="right", padx=5)
        
        dialog.grab_set()
        dialog.focus()
    
    def search_logs(self):
        """Search for text in current log tab and highlight results."""
        search_text = self.search_var.get()
        if not search_text:
            return
        
        # Get current tab
        current_tab_idx = self.notebook.index(self.notebook.select())
        current_widget = list(self.log_tabs.values())[current_tab_idx]
        
        # Clear previous highlights
        current_widget.tag_remove("highlight", "1.0", "end")
        
        # Search and highlight
        start_pos = "1.0"
        count = 0
        while True:
            start_pos = current_widget.search(search_text, start_pos, stopindex="end", nocase=True)
            if not start_pos:
                break
            end_pos = f"{start_pos}+{len(search_text)}c"
            current_widget.tag_add("highlight", start_pos, end_pos)
            start_pos = end_pos
            count += 1
        
        if count > 0:
            self.append_log(f"Found {count} matches for '{search_text}'")
            # Scroll to first match
            first_match = current_widget.search(search_text, "1.0", stopindex="end", nocase=True)
            if first_match:
                current_widget.see(first_match)
        else:
            self.append_log(f"No matches found for '{search_text}'")
    
    def clear_search(self):
        """Clear search highlights from all tabs."""
        for widget in self.log_tabs.values():
            widget.tag_remove("highlight", "1.0", "end")
        self.search_var.set("")
    
    def export_logs(self):
        """Export current tab's logs to a file."""
        from tkinter import filedialog
        
        current_tab_idx = self.notebook.index(self.notebook.select())
        current_name = list(self.log_tabs.keys())[current_tab_idx]
        current_widget = list(self.log_tabs.values())[current_tab_idx]
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"launchpad_{current_name}_logs.txt"
        )
        
        if filepath:
            try:
                content = current_widget.get("1.0", "end-1c")
                with open(filepath, 'w') as f:
                    f.write(f"LaunchPad Logs - {current_name}\n")
                    f.write(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("=" * 80 + "\n\n")
                    f.write(content)
                messagebox.showinfo("Success", f"Logs exported to:\n{filepath}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export logs:\n{e}")

    def _sanity_check(self, show_dialog=True):
        missing = []
        checks = [
            (self.cfg.PYTHON_EXE, "Python venv"),
            (self.cfg.CELERY_EXE, "Celery"),
            (self.cfg.DAPHNE_EXE, "Daphne"),
            (self.cfg.NPM_EXE, "npm"),
        ]
        for p, label in checks:
            if not os.path.exists(p):
                missing.append(f"{label} executable not found: {p}")

        pkg_json = os.path.join(self.cfg.FRONTEND_DIR, "package.json")
        if not os.path.exists(pkg_json):
            missing.append(f"package.json not found in FRONTEND_DIR: {self.cfg.FRONTEND_DIR}")

        if missing:
            msg = "Config errors:\n" + "\n".join(missing)
            self.append_log(msg)
            if show_dialog:
                try:
                    messagebox.showerror("Config Error", msg)
                except Exception:
                    pass
        else:
            self.append_log("Sanity checks passed ✅")

    def append_log(self, text, tag="All"):
        """Append log entry to the appropriate tab(s)."""
        def _do_append():
            # Always append to "All" tab
            if "All" in self.log_tabs:
                self.log_tabs["All"].insert("end", text + "\n")
                self.log_tabs["All"].see("end")
            
            # Also append to service-specific tab if tag matches
            if tag in self.log_tabs and tag != "All":
                self.log_tabs[tag].insert("end", text + "\n")
                self.log_tabs[tag].see("end")
        
        self.after(0, _do_append)

    def run_migrations(self):
        threading.Thread(target=self.controller.migrate_db, daemon=True).start()

    def start_backend(self):
        threading.Thread(target=self.controller.start_backend, daemon=True).start()

    def start_frontend(self):
        threading.Thread(target=self.controller.start_frontend, daemon=True).start()

    def start_all(self):
        threading.Thread(target=self.controller.start_all, daemon=True).start()

    def stop_all(self):
        threading.Thread(target=self.controller.stop_all, daemon=True).start()
    
    def analyze_system(self):
        """Analyze system resources and recommend optimal configurations."""
        dialog = tk.Toplevel(self)
        dialog.title("System Analysis & Recommendations")
        dialog.geometry("800x700")
        
        text = scrolledtext.ScrolledText(dialog, wrap="word", font=("Consolas", 10), bg="#f5f5f5")
        text.pack(fill="both", expand=True, padx=10, pady=10)
        
        def analyze():
            text.delete(1.0, "end")
            text.insert("end", "="*80 + "\n")
            text.insert("end", "LAUNCHPAD - SYSTEM ANALYSIS\n")
            text.insert("end", "="*80 + "\n\n")
            
            if not HAS_PSUTIL:
                text.insert("end", "⚠️  psutil not available - limited analysis\n\n")
                return
            
            # 1. CPU Analysis
            text.insert("end", "🖥️  CPU ANALYSIS\n")
            text.insert("end", "-" * 80 + "\n")
            cpu_count = psutil.cpu_count(logical=False) or psutil.cpu_count()
            cpu_logical = psutil.cpu_count(logical=True)
            cpu_percent = psutil.cpu_percent(interval=1, percpu=False)
            
            text.insert("end", f"Physical Cores: {cpu_count}\n")
            text.insert("end", f"Logical Cores: {cpu_logical}\n")
            text.insert("end", f"Current Usage: {cpu_percent}%\n")
            
            # CPU Recommendations
            text.insert("end", "\n📊 Recommendations:\n")
            recommended_celery_workers = max(1, cpu_count - 1) if cpu_count > 2 else 1
            recommended_docker_cpu = min(2.0, cpu_count * 0.5)
            
            text.insert("end", f"  • Celery concurrency: {recommended_celery_workers} workers\n")
            text.insert("end", f"  • Docker CPU limit: {recommended_docker_cpu} cores\n")
            if cpu_count >= 4:
                text.insert("end", "  • Consider 'threads' or 'eventlet' pool for better parallelism\n")
            else:
                text.insert("end", "  • Use 'solo' pool for single-core efficiency\n")
            
            # 2. Memory Analysis
            text.insert("end", "\n💾 MEMORY ANALYSIS\n")
            text.insert("end", "-" * 80 + "\n")
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            text.insert("end", f"Total RAM: {mem.total / (1024**3):.2f} GB\n")
            text.insert("end", f"Available: {mem.available / (1024**3):.2f} GB ({mem.percent}% used)\n")
            text.insert("end", f"Swap: {swap.total / (1024**3):.2f} GB ({swap.percent}% used)\n")
            
            # Memory Recommendations
            text.insert("end", "\n📊 Recommendations:\n")
            total_gb = mem.total / (1024**3)
            
            if total_gb < 4:
                docker_mem = "256m"
                text.insert("end", f"  ⚠️  Low memory system (< 4GB)\n")
                text.insert("end", f"  • Docker memory limit: {docker_mem}\n")
                text.insert("end", "  • Use 'solo' Celery pool to minimize memory\n")
                text.insert("end", "  • Consider running only essential services\n")
            elif total_gb < 8:
                docker_mem = "512m"
                text.insert("end", f"  • Docker memory limit: {docker_mem}\n")
                text.insert("end", "  • Keep Celery concurrency <= 2\n")
            elif total_gb < 16:
                docker_mem = "1g"
                text.insert("end", f"  • Docker memory limit: {docker_mem}\n")
                text.insert("end", "  • Can run full stack comfortably\n")
            else:
                docker_mem = "2g"
                text.insert("end", f"  ✅ Excellent memory (>= 16GB)\n")
                text.insert("end", f"  • Docker memory limit: {docker_mem}\n")
                text.insert("end", "  • Can run multiple instances or heavy workloads\n")
            
            # 3. Disk Analysis
            text.insert("end", "\n💿 DISK ANALYSIS\n")
            text.insert("end", "-" * 80 + "\n")
            try:
                disk = psutil.disk_usage('/')
                text.insert("end", f"Total: {disk.total / (1024**3):.2f} GB\n")
                text.insert("end", f"Used: {disk.used / (1024**3):.2f} GB ({disk.percent}%)\n")
                text.insert("end", f"Free: {disk.free / (1024**3):.2f} GB\n")
                
                text.insert("end", "\n📊 Recommendations:\n")
                if disk.percent > 90:
                    text.insert("end", "  ⚠️  Disk almost full - clean up space!\n")
                elif disk.percent > 80:
                    text.insert("end", "  ⚠️  Disk usage high - monitor space\n")
                else:
                    text.insert("end", "  ✅ Adequate disk space\n")
            except Exception as e:
                text.insert("end", f"Could not analyze disk: {e}\n")
            
            # 4. Network Analysis
            text.insert("end", "\n🌐 NETWORK ANALYSIS\n")
            text.insert("end", "-" * 80 + "\n")
            
            # Check port availability
            ports_to_check = [
                (int(self.cfg.DAPHNE_PORT), "Daphne"),
                (int(self.cfg.FRONTEND_PORT), "Frontend"),
                (int(self.cfg.REDIS_PORT), "Redis"),
            ]
            
            port_status = []
            for port, service in ports_to_check:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(0.5)
                    result = sock.connect_ex(('127.0.0.1', port))
                    sock.close()
                    if result == 0:
                        port_status.append((port, service, "IN USE ⚠️"))
                    else:
                        port_status.append((port, service, "AVAILABLE ✅"))
                except:
                    port_status.append((port, service, "UNKNOWN"))
            
            for port, service, status in port_status:
                text.insert("end", f"Port {port} ({service}): {status}\n")
            
            text.insert("end", "\n📊 Recommendations:\n")
            in_use = [p for p, s, st in port_status if "IN USE" in st]
            if in_use:
                text.insert("end", f"  ⚠️  {len(in_use)} port(s) already in use - stop conflicts before starting\n")
            else:
                text.insert("end", "  ✅ All configured ports are available\n")
            
            # 5. Running Processes
            text.insert("end", "\n⚙️  ACTIVE STACK PROCESSES\n")
            text.insert("end", "-" * 80 + "\n")
            
            active_services = {}
            for name, proc in self.controller.procs.items():
                if proc.p and proc.p.poll() is None:
                    try:
                        p = psutil.Process(proc.p.pid)
                        mem_mb = p.memory_info().rss / (1024**2)
                        cpu = p.cpu_percent(interval=0.1)
                        active_services[name] = (p.pid, mem_mb, cpu)
                    except:
                        active_services[name] = (proc.p.pid, 0, 0)
            
            if active_services:
                total_mem = 0
                for name, (pid, mem_mb, cpu) in active_services.items():
                    text.insert("end", f"{name}: PID {pid}, RAM {mem_mb:.1f}MB, CPU {cpu:.1f}%\n")
                    total_mem += mem_mb
                text.insert("end", f"\nTotal Stack Memory: {total_mem:.1f} MB\n")
            else:
                text.insert("end", "No services currently running\n")
            
            # 6. Docker Analysis
            text.insert("end", "\n🐳 DOCKER ANALYSIS\n")
            text.insert("end", "-" * 80 + "\n")
            
            try:
                result = subprocess.run(
                    [self.cfg.DOCKER_EXE, "info", "--format", "{{json .}}"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    docker_info = json.loads(result.stdout)
                    text.insert("end", f"Docker Version: {docker_info.get('ServerVersion', 'Unknown')}\n")
                    text.insert("end", f"Running Containers: {docker_info.get('ContainersRunning', 0)}\n")
                    text.insert("end", f"Total Containers: {docker_info.get('Containers', 0)}\n")
                    text.insert("end", f"Images: {docker_info.get('Images', 0)}\n")
                    
                    mem_limit = docker_info.get('MemTotal', 0)
                    if mem_limit:
                        text.insert("end", f"Docker Memory: {mem_limit / (1024**3):.2f} GB\n")
                else:
                    text.insert("end", "⚠️  Docker not responding or not installed\n")
            except Exception as e:
                text.insert("end", f"⚠️  Could not connect to Docker: {e}\n")
            
            # 7. Overall Recommendation
            text.insert("end", "\n" + "="*80 + "\n")
            text.insert("end", "💡 RECOMMENDED CONFIGURATION\n")
            text.insert("end", "="*80 + "\n")
            
            text.insert("end", f"Celery Pool: {'threads' if cpu_count >= 4 else 'solo'}\n")
            text.insert("end", f"Celery Concurrency: {recommended_celery_workers}\n")
            text.insert("end", f"Docker Memory Limit: {docker_mem}\n")
            text.insert("end", f"Docker CPU Limit: {recommended_docker_cpu}\n")
            
            text.insert("end", "\n📝 To apply these settings, go to Settings and update:\n")
            text.insert("end", "  • Celery Pool and Concurrency\n")
            text.insert("end", "  • Docker Memory and CPU limits\n")
            
            text.insert("end", "\n" + "="*80 + "\n")
        
        # Auto-run analysis on dialog open
        analyze()
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(btn_frame, text="Refresh", command=analyze).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Close", command=dialog.destroy).pack(side="right")
        
        dialog.grab_set()
    
    def manage_presets(self):
        """Dialog to manage service presets."""
        dialog = tk.Toplevel(self)
        dialog.title("Manage Service Presets")
        dialog.geometry("500x400")
        
        try:
            presets = json.loads(self.cfg.SERVICE_PRESETS)
        except:
            presets = {}
        
        ttk.Label(dialog, text="Service Presets", font=("TkDefaultFont", 12, "bold")).pack(pady=10)
        
        listbox = tk.Listbox(dialog, height=10)
        listbox.pack(fill="both", expand=True, padx=10, pady=10)
        
        for name in presets.keys():
            listbox.insert("end", name)
        
        def save_presets():
            self.cfg.SERVICE_PRESETS = json.dumps(presets)
            self.cfg_mgr.save(self.cfg)
            self._build_preset_menu()
            dialog.destroy()
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(btn_frame, text="Save", command=save_presets).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side="right")
        
        dialog.grab_set()
    
    def build_frontend(self):
        """Build frontend for production."""
        self.append_log("Building frontend for production...")
        
        def build():
            try:
                result = subprocess.run(
                    [self.cfg.NPM_EXE, "run", "build"],
                    cwd=self.cfg.FRONTEND_DIR,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    self.append_log("✅ Frontend build completed successfully")
                else:
                    self.append_log(f"❌ Frontend build failed: {result.stderr}")
            except Exception as e:
                self.append_log(f"Error building frontend: {e}")
        
        threading.Thread(target=build, daemon=True).start()
    
    def setup_tray_icon(self):
        """Setup system tray icon."""
        if not HAS_TRAY:
            return None
        
        # Create a simple icon
        def create_icon_image():
            img = Image.new('RGB', (64, 64), color='#2196F3')
            draw = ImageDraw.Draw(img)
            draw.rectangle([10, 10, 54, 54], fill='white')
            draw.text((20, 20), "SC", fill='#2196F3')
            return img
        
        def on_show(icon, item):
            self.after(0, self.deiconify)
        
        def on_quit(icon, item):
            icon.stop()
            self.after(0, self.on_close)
        
        def on_start_all(icon, item):
            self.after(0, self.start_all)
        
        def on_stop_all(icon, item):
            self.after(0, self.stop_all)
        
        menu = Menu(
            MenuItem('Show', on_show, default=True),
            MenuItem('Start All', on_start_all),
            MenuItem('Stop All', on_stop_all),
            MenuItem('Quit', on_quit)
        )
        
        icon = Icon("LaunchPad", create_icon_image(), "LaunchPad", menu)
        
        def run_icon():
            icon.run()
        
        threading.Thread(target=run_icon, daemon=True).start()
        return icon
    
    def on_minimize(self):
        """Minimize to tray instead of taskbar."""
        if HAS_TRAY and hasattr(self, 'tray_icon'):
            self.withdraw()
        else:
            self.iconify()

    def on_close(self):
        try:
            self.controller._stop_monitoring = True
            self.controller.stop_all()
        finally:
            if HAS_TRAY and hasattr(self, 'tray_icon') and self.tray_icon:
                self.tray_icon.stop()
            self.destroy()


if __name__ == "__main__":
    cfg_mgr = ConfigManager(CONFIG_DB_PATH)
    cfg = cfg_mgr.load()

    app = App(cfg, cfg_mgr)
    
    # Setup tray icon if available
    if HAS_TRAY:
        app.tray_icon = app.setup_tray_icon()
    
    app.mainloop()
