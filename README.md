# LaunchPad

A comprehensive desktop application for managing Django/React development stacks with real-time monitoring, service presets, and intelligent system analysis.

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.12+-green.svg)
![Platform](https://img.shields.io/badge/platform-linux%20%7C%20macOS%20%7C%20windows-lightgrey.svg)

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage Guide](#usage-guide)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [System Requirements](#system-requirements)
- [Architecture](#architecture)
- [Troubleshooting](#troubleshooting)
- [Development](#development)

---

## 🎯 Overview

LaunchPad is a powerful GUI application designed to simplify the management of complex development environments. It provides a unified interface to start, stop, and monitor multiple services including Django (via Daphne/ASGI), Celery workers, Redis, and React frontend servers.

### Why LaunchPad?

- **Unified Control**: Manage all your development services from one window
- **Real-time Monitoring**: Track CPU and memory usage for each service
- **Intelligent Auto-restart**: Automatically restarts failed services (up to 3 attempts)
- **Service Presets**: Quick-switch between different development scenarios
- **System Analysis**: Get hardware-based recommendations for optimal configuration
- **Persistent Configuration**: SQLite database ensures settings survive restarts

### 🍎 Enhanced macOS Support (New!)

LaunchPad now includes first-class macOS support with native integrations:

- **🔍 Auto-Detection**: Automatically finds Docker, npm, and Redis on macOS (Intel & Apple Silicon)
- **🍺 Homebrew Integration**: Native support for Homebrew-installed tools and services
- **🚀 Apple Silicon Ready**: Full support for M1/M2/M3 Macs with proper `/opt/homebrew` paths
- **📱 Native Notifications**: Uses macOS notification system instead of third-party tools
- **💻 Terminal Integration**: Opens Django shell in Terminal.app or iTerm2
- **⚡ Efficient Redis**: Prefers Homebrew Redis over Docker for better performance

See [MAC_COMPATIBILITY_CHANGES.md](MAC_COMPATIBILITY_CHANGES.md) for detailed information about macOS-specific features.

---

## ✨ Features

### Core Service Management

- **Django Backend (Daphne/ASGI)**
  - Runs Django application via Daphne ASGI server
  - Configurable host and port
  - Optional OpenAPI schema fetching
  - Automatic browser opening

- **Celery Workers**
  - Celery Beat (scheduler)
  - Celery Worker with configurable pool types (solo/threads/eventlet)
  - Adjustable concurrency levels
  - Custom queue support

- **Redis (Docker/Homebrew)**
  - Runs Redis in Docker container (all platforms)
  - Native Homebrew Redis support (macOS)
  - Configurable memory and CPU limits
  - Automatic container lifecycle management

- **React Frontend**
  - Vite/NPM development server
  - Production build support
  - Configurable host and port

### Advanced Features

#### 🎨 Service Presets
Pre-configured service combinations for different workflows:
- **Backend Only**: Daphne + Celery + Redis
- **Frontend Only**: Just the React dev server
- **Full Stack**: All services running
- **Minimal**: Daphne + Redis only

#### 📊 System Analysis
Intelligent resource analysis and recommendations:
- CPU analysis with core count and usage
- Memory analysis with RAM/swap statistics
- Disk space monitoring
- Network port availability checking
- Docker environment inspection
- Active process monitoring
- **Smart Recommendations**: Automatically calculates optimal Celery worker count, Docker resource limits, and pool type based on your hardware

#### 🔍 Real-time Monitoring
- Color-coded status indicators (gray/yellow/green/red)
- Live CPU and memory usage per service
- Process status tracking
- Desktop notifications (Linux notify-send)
- Auto-restart on failure detection

#### 📝 Log Management
- Tabbed log view for each service
- "All" tab with consolidated logs
- Search functionality with highlighting
- Export logs to file
- Color-coded log levels (error/warning)

#### 🔧 Developer Tools
- **Build Frontend**: One-click production builds
- **Django Shell**: Launch Django management shell
- **Git Integration**: View branch status, pull, push
- **Database Migration**: Manual or automatic migration policies
- **View DB Config**: Inspect and export configuration

#### 🪟 User Interface
- System tray icon with quick actions (Linux/Windows only)
- Minimize to tray support (Linux/Windows)
- Modern ttk-themed interface
- Responsive design (1200x800)
- Persistent window state

> **Note for macOS users**: System tray functionality is disabled on macOS due to compatibility issues between `pystray` and tkinter. Use the standard Dock icon instead.

---

## 💾 Installation

### Prerequisites

#### Linux (Ubuntu/Debian)

```bash
# System packages
sudo apt-get install python3-tk python3-dev

# For notifications
sudo apt-get install libnotify-bin

# Docker (for Redis)
# Follow: https://docs.docker.com/engine/install/
```

#### macOS

```bash
# Install Homebrew (if not already installed)
# Visit: https://brew.sh/

# Python 3.12+ (includes tkinter)
brew install python@3.12

# Docker Desktop for Mac
# Download from: https://www.docker.com/products/docker-desktop/

# Node.js (for frontend)
brew install node
```

#### Windows

```powershell
# Python 3.12+ from python.org (includes tkinter)
# Download from: https://www.python.org/downloads/

# Docker Desktop for Windows
# Download from: https://www.docker.com/products/docker-desktop/

# Node.js (for frontend)
# Download from: https://nodejs.org/
```

### Building from Source

#### Linux

1. **Clone or download** the LaunchPad files

2. **Set up Python virtual environment**:
```bash
cd "launch pad"
python3 -m venv venv
source venv/bin/activate
```

3. **Install dependencies**:
```bash
pip install psutil pystray pillow pyinstaller
```

4. **Build the executable**:
```bash
pyinstaller --onefile --windowed --name LaunchPad launchpad.py --clean
```

5. **The executable will be in**: `dist/LaunchPad`

#### macOS

1. **Clone or download** the LaunchPad files

2. **Set up Python virtual environment**:
```bash
cd "launch-pad"
python3 -m venv venv
source venv/bin/activate
```

3. **Install dependencies**:
```bash
pip install psutil pystray pillow pyinstaller
```

4. **Build the executable**:
```bash
pyinstaller --onefile --windowed --name LaunchPad launchpad.py --clean
```

5. **The executable will be in**: `dist/LaunchPad`

#### Windows

1. **Clone or download** the LaunchPad files

2. **Set up Python virtual environment**:
```powershell
cd "launch pad"
python -m venv venv
venv\Scripts\activate
```

3. **Install dependencies**:
```powershell
pip install psutil pystray pillow pyinstaller
```

4. **Build the executable**:
```powershell
pyinstaller --onefile --windowed --name LaunchPad launchpad.py --clean
```

5. **The executable will be in**: `dist\LaunchPad.exe`

### Desktop Integration

#### Linux

Create a desktop launcher at `~/.local/share/applications/launchpad.desktop`:

```ini
[Desktop Entry]
Version=1.0
Type=Application
Name=LaunchPad
Comment=Django/React Stack Manager
Exec=/home/YOUR_USERNAME/VisualStudio/launch pad/dist/LaunchPad
Icon=applications-system
Terminal=false
Categories=Development;Utility;
```

#### macOS

Create an application bundle or add to Dock:

**Option 1: Run from Terminal**
```bash
open /Users/YOUR_USERNAME/VisualStudioProjects/launch-pad/dist/LaunchPad
```

**Option 2: Create Alias**
```bash
# Drag dist/LaunchPad to Applications folder while holding Cmd+Option
# Or create symbolic link:
ln -s /Users/YOUR_USERNAME/VisualStudioProjects/launch-pad/dist/LaunchPad /Applications/LaunchPad
```

**Option 3: Add to Dock**
1. Open Finder and navigate to `dist/LaunchPad`
2. Drag the executable to your Dock
3. Right-click and select "Options" → "Keep in Dock"

#### Windows

Create a shortcut:
1. Right-click `dist\LaunchPad.exe`
2. Select "Create shortcut"
3. Move shortcut to Desktop or Start Menu
4. Optional: Pin to taskbar

---

## 🚀 Quick Start

### First Run

1. **Launch LaunchPad**:
```bash
./dist/LaunchPad
```

2. **Configure Settings** (Click "Configure..." button):
   - Set your Django project root directory
   - Set your React frontend directory
   - Verify NPM and Docker executable paths
   - Configure ports if defaults conflict

3. **Start Services**:
   - Click **"Start Backend"** to launch Daphne + Celery + Redis
   - Click **"Start Frontend"** to launch React dev server
   - Or click **"Start All"** for everything at once

### Typical Workflow

```
1. Open LaunchPad
2. Select preset: "Full Stack" (from dropdown)
3. Click "Start All"
4. Monitor services in status panel
5. View logs in tabbed interface
6. Stop when done with "Stop All"
```

---

## ⚙️ Configuration

### Configuration Storage

All settings are stored in SQLite database at:
- **Linux**: `~/.config/launchpad/launchpad.db`
- **macOS**: `~/Library/Application Support/LaunchPad/launchpad.db`
- **Windows**: `%APPDATA%\LaunchPad\launchpad.db`

### Configuration Dialog

Access via **"Configure..."** button. Available settings:

#### Paths
| Setting | Description | Example |
|---------|-------------|---------|
| Project Root | Django project directory | `/home/user/projects/backend` |
| Frontend Dir | React/Vite project directory | `/home/user/projects/frontend` |
| NPM Executable | Path to npm | `/usr/bin/npm` |
| Docker Executable | Path to docker | `/usr/bin/docker` |

#### Django/Daphne
| Setting | Description | Default |
|---------|-------------|---------|
| ASGI Application | Django ASGI app path | `myproject.asgi:application` |
| Host | Daphne bind address | `127.0.0.1` |
| Port | Daphne port | `8070` |
| Auto Open Browser | Open browser on start | Yes |

#### Redis
| Setting | Description | Default |
|---------|-------------|---------|
| Host | Redis hostname | `127.0.0.1` |
| Port | Redis port | `6379` |
| Docker Name | Container name | `local-redis-7` |
| Memory Limit | Docker memory limit | `512m` |
| CPU Limit | Docker CPU cores | `1.0` |

#### Celery
| Setting | Description | Options |
|---------|-------------|---------|
| Queue Name | Celery queue | Any string |
| Pool Type | Worker pool | `solo`, `threads`, `eventlet` |
| Concurrency | Worker count | 1-16 |

#### Frontend
| Setting | Description | Default |
|---------|-------------|---------|
| Host | Dev server address | `127.0.0.1` |
| Port | Dev server port | `5178` |

#### Migrations
| Setting | Description | Options |
|---------|-------------|---------|
| Migration Policy | When to run | `manual`, `always` |

### Recommended Configurations

#### Low-End System (< 4GB RAM)
```
Celery Pool: solo
Celery Concurrency: 1
Docker Memory: 256m
Docker CPU: 1.0
```

#### Mid-Range System (8-16GB RAM)
```
Celery Pool: threads
Celery Concurrency: 2-4
Docker Memory: 512m
Docker CPU: 1.5
```

#### High-End System (16GB+ RAM)
```
Celery Pool: threads or eventlet
Celery Concurrency: 4-8
Docker Memory: 1g-2g
Docker CPU: 2.0
```

> 💡 **Tip**: Use the **System Analysis** feature to get personalized recommendations!

---

## 📖 Usage Guide

### Service Control

#### Starting Services

**Individual Services:**
- `Start Backend`: Starts Redis → Daphne → Celery Beat → Celery Worker
- `Start Frontend`: Starts React/Vite dev server
- `Start All`: Starts all services in optimal order

**Using Presets:**
1. Click the **"Presets"** dropdown menu
2. Select desired configuration
3. Services start automatically with 0.5s delay between each

#### Stopping Services

- `Stop All`: Gracefully terminates all running services
- Close button or system tray "Quit": Stops all and exits

### Status Indicators

Services show real-time status with colored circles:

| Color | Status | Meaning |
|-------|--------|---------|
| 🔵 Gray | Stopped | Service not running |
| 🟡 Yellow | Starting | Service launching |
| 🟢 Green | Running | Service operational |
| 🔴 Red | Failed | Service crashed/failed |

Below each indicator: Live CPU% and RAM usage

### Log Management

#### Viewing Logs

Navigate between log tabs:
- **All**: Combined logs from all services
- **Daphne**: Django ASGI server logs
- **Celery Beat**: Scheduler logs
- **Celery Worker**: Task execution logs
- **Frontend**: React/Vite dev server
- **Redis**: Docker container logs
- **Migrations**: Database migration output
- **System**: Stack Controller internal logs

#### Searching Logs

1. Enter search term in "Search logs:" field
2. Press Enter or click "Find"
3. Matching text highlighted in yellow
4. Click "Clear" to remove highlighting

#### Exporting Logs

1. Click "Export Logs" button
2. Choose save location
3. All logs saved with timestamp

### System Analysis

Click **"📊 System Analysis"** to view:

1. **CPU Analysis**: Core count, usage, worker recommendations
2. **Memory Analysis**: RAM/swap stats, Docker limit recommendations
3. **Disk Analysis**: Space usage and warnings
4. **Network Analysis**: Port availability for your services
5. **Active Processes**: Current resource usage by service
6. **Docker Analysis**: Container stats and Docker info
7. **Recommendations**: Optimal settings for your hardware

Click **"Refresh"** to re-analyze.

### Git Integration

Click **"Git Status"** to:
- View current branch
- See uncommitted changes
- Pull latest changes
- Push local commits

### Django Management

**Run Migrations:**
- Click "Run Migrations" button
- View progress in Migrations log tab
- Set to "always" in config for automatic runs

**Django Shell:**
- Click "Django Shell" button
- Opens terminal with Django management shell
- Full access to Django models and ORM

### Building Frontend

Click **"Build Frontend"** to:
1. Run `npm run build` in frontend directory
2. Create production-optimized build
3. View output in logs

### Database Configuration

Click **"View DB Config"** to:
- Inspect all configuration values
- View as formatted JSON
- Export configuration to file

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+B` | Start Backend |
| `Ctrl+F` | Start Frontend |
| `Ctrl+A` | Start All Services |
| `Ctrl+Q` | Stop All Services |
| `Ctrl+M` | Run Migrations |
| `Ctrl+D` | Open Django Shell |
| `Ctrl+G` | Show Git Status |
| `Ctrl+I` | System Analysis |

---

## 💻 System Requirements

### Minimum Requirements
- **OS**: Linux (Ubuntu 20.04+), macOS 11+ (Big Sur or later), or Windows 10/11
- **Python**: 3.12 or higher
- **RAM**: 4GB
- **CPU**: Dual-core processor
- **Disk**: 2GB free space
- **Docker**: 20.10+
- **Node.js**: 16+ (for frontend)

### Recommended Requirements
- **RAM**: 8GB or more
- **CPU**: Quad-core processor
- **Disk**: 10GB free space
- **SSD**: For better performance

### Dependencies

**Python Packages:**
- `tkinter` (Linux: python3-tk, macOS: included with Homebrew Python, Windows: included)
- `psutil` - Process and system monitoring
- `pystray` - System tray icon
- `Pillow` - Image processing
- `pyinstaller` - Executable building

**System Tools:**
- `docker` - Container management
- `npm` - Node package manager
- `git` - Version control (optional)
- `notify-send` - Desktop notifications (Linux only)
- `terminal-notifier` - Desktop notifications (macOS, optional): `brew install terminal-notifier`

---

## 🏗️ Architecture

### Project Structure

```
launch pad/
├── launchpad.py               # Main application (1,857 lines)
├── launchpad.db               # Configuration database (auto-created)
├── dist/
│   └── LaunchPad              # Executable (22MB)
├── venv/                      # Python virtual environment
├── build/                     # PyInstaller build files
└── README.md                  # This file
```

### Configuration Database

**Locations**:
- Linux: `~/.config/launchpad/launchpad.db`
- macOS: `~/Library/Application Support/LaunchPad/launchpad.db`
- Windows: `%APPDATA%\LaunchPad\launchpad.db`

**Schema**: Key-value store
- Key: Configuration parameter name
- Value: JSON-encoded value

**Automatic Migration**: Old JSON configs auto-migrate to SQLite

### Process Management

#### Process Lifecycle

```
STOPPED → STARTING → RUNNING → (failed?) → STOPPED
              ↓           ↓
           (auto-    (monitoring)
           restart)
```

#### Auto-restart Logic
- Monitors process health every 2 seconds
- On failure, attempts restart (max 3 times)
- Resets counter after 60 seconds of stability
- Desktop notification on restart

#### Service Dependencies

```
Backend Startup Order:
1. Redis (Docker) - must be healthy
2. Daphne (Django ASGI)
3. Celery Beat
4. Celery Worker

Frontend:
- Independent, can run alone
```

### Resource Monitoring

Uses `psutil` to track:
- CPU percentage (per-process)
- Memory (RSS in MB)
- Process status (running/zombie/stopped)

Updates every 2 seconds in background thread.

---

## 🔧 Troubleshooting

### Common Issues

#### "Port already in use"

**Problem**: Service can't start because port is occupied

**Solution (Linux/macOS)**:
```bash
# Find process on port 8070
sudo lsof -i :8070
# Kill it
kill -9 <PID>
```

**Solution (Windows)**:
```powershell
# Find process on port 8070
netstat -ano | findstr :8070
# Kill it (use PID from last column)
taskkill /PID <PID> /F
```

Or change port in Settings.

#### "Docker not found"

**Problem**: Redis service fails to start

**Solution (Linux)**:
```bash
# Check Docker installation
docker --version

# Start Docker service
sudo systemctl start docker

# Set correct path in Settings
which docker  # Copy this path
```

**Solution (macOS)**:
```bash
# Check Docker Desktop is running
docker --version

# Start Docker Desktop from Applications
open -a Docker

# Set path in Settings (usually):
which docker  # Typically /usr/local/bin/docker
```

**Solution (Windows)**:
```powershell
# Check Docker Desktop is running
docker --version

# Start Docker Desktop from Start Menu
# Set path in Settings (usually):
# C:\Program Files\Docker\Docker\resources\bin\docker.exe
```

#### "ModuleNotFoundError: tkinter"

**Problem**: Missing tkinter system package

**Solution (Linux)**:
```bash
sudo apt-get install python3-tk
```

**Solution (macOS)**:
```bash
# tkinter is included with Python from Homebrew
# If missing, reinstall Python:
brew reinstall python@3.12
```

#### "NSUpdateCycleInitialize() called off main thread" (macOS)

**Problem**: App crashes on macOS with error about NSUpdateCycleInitialize

**Solution**:
This is a known issue with `pystray` (system tray) and tkinter on macOS. The system tray icon feature is automatically disabled on macOS to prevent this crash. The app will work normally, just without the system tray icon.

**Note**: On macOS, use the Dock icon instead of a system tray icon. You can still minimize the window normally using Cmd+M or the yellow minimize button.

#### Services keep restarting

**Problem**: Auto-restart loop due to configuration error

**Solution**:
1. Check logs for error messages
2. Verify paths in Settings
3. Test services manually:

**Linux/macOS**:
```bash
cd /path/to/django/project
python3 manage.py runserver
```

**Windows**:
```powershell
cd C:\path\to\django\project
python manage.py runserver
```

#### High CPU/Memory usage

**Problem**: Resources maxed out

**Solution**:
1. Run "System Analysis"
2. Reduce Celery concurrency
3. Lower Docker memory limit
4. Use "solo" pool for Celery
5. Run fewer services (use presets)

### Log Files

Application logs available in:
- **System tab**: Internal LaunchPad logs
- **Service tabs**: Output from each service
- Export all logs via "Export Logs" button

### Debug Mode

Run from terminal to see detailed output:

**Linux**:
```bash
./dist/LaunchPad
# Or run source directly:
python launchpad.py
```

**Windows**:
```powershell
.\dist\LaunchPad.exe
# Or run source directly:
python launchpad.py
```

---

## 👨‍💻 Development

### Running from Source

**Linux/macOS**:
```bash
# Activate virtual environment
source venv/bin/activate

# Run directly
python launchpad.py

# Or with debug output
python -u launchpad.py
```

**Windows**:
```powershell
# Activate virtual environment
venv\Scripts\activate

# Run directly
python launchpad.py

# Or with debug output
python -u launchpad.py
```

### Building Executable

**Linux/macOS**:
```bash
# Clean build
pyinstaller --onefile --windowed --name LaunchPad launchpad.py --clean

# Output: dist/LaunchPad
```

**Windows**:
```powershell
# Clean build
pyinstaller --onefile --windowed --name LaunchPad launchpad.py --clean

# Output: dist\LaunchPad.exe
```

### Code Structure

**Main Classes:**

- `Paths` - Configuration dataclass
- `ConfigManager` - SQLite database management
- `ProcessStatus` - Service state enum
- `Proc` - Process wrapper with auto-restart
- `LaunchController` - Core process management logic
- `App` - Main Tkinter GUI
- `ConfigDialog` - Settings dialog

**Key Methods:**

- `start_redis()` - Launch Redis Docker container
- `start_daphne()` - Start Django ASGI server
- `start_celery_beat()` - Start scheduler
- `start_celery_worker()` - Start task worker
- `start_frontend()` - Start React dev server
- `_monitor_loop()` - Background monitoring thread
- `_check_and_restart()` - Auto-restart logic

### Adding Features

To add a new service:

1. Add configuration to `DEFAULTS` dict
2. Add fields to `Paths` dataclass
3. Create `start_service()` method
4. Add to `LaunchController.procs` dict
5. Update UI with status indicator
6. Add to presets if needed

### Testing

```bash
# Test configuration persistence
python -c "from launchpad import ConfigManager, get_config_path; 
           cm = ConfigManager(get_config_path()); 
           print(cm.load())"

# Test process management
# (Run app and check /tmp/ for process info)
```

---

## 📊 Performance Tips

1. **Use Service Presets**: Only run what you need
2. **Optimize Celery**: Match concurrency to CPU cores
3. **Limit Docker Resources**: Prevent Redis from hogging memory
4. **Monitor Regularly**: Check System Analysis for bottlenecks
5. **SSD Recommended**: Faster log writes and builds
6. **Close Unused Apps**: Free up system resources

---

## 🤝 Contributing

This is a personal development tool. For issues or suggestions:
1. Document the problem with logs
2. Include system specs (from System Analysis)
3. Note configuration settings
4. Describe expected vs actual behavior

---

## 📜 License

Personal use project. Modify and distribute as needed.

---

## 🙏 Acknowledgments

Built with:
- **Tkinter** - GUI framework
- **psutil** - System monitoring
- **pystray** - System tray integration
- **PyInstaller** - Executable packaging

---

## 📞 Support

**Common Resources:**
- Django Docs: https://docs.djangoproject.com/
- Celery Docs: https://docs.celeryproject.org/
- Docker Docs: https://docs.docker.com/
- React Docs: https://react.dev/

**Quick Reference:**

```bash
# View LaunchPad logs (macOS/Linux)
tail -f /tmp/launchpad.log  # If logging to file

# Check service health
docker ps  # Redis
curl http://localhost:8070/  # Daphne
curl http://localhost:5178/  # Frontend

# Reset configuration
# Linux:
rm ~/.config/launchpad/launchpad.db
# macOS:
rm ~/Library/Application\ Support/LaunchPad/launchpad.db
# Windows:
del %APPDATA%\LaunchPad\launchpad.db
```

---

**Version**: 1.0.0  
**Last Updated**: November 19, 2025  
**Python**: 3.12.3  
**Executable Size**: 22MB  
**Lines of Code**: 1,857
