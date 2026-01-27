# LaunchPad Setup & Configuration Guide

**Version:** 1.0.0  
**Platform:** macOS, Linux, Windows  
**Last Updated:** January 27, 2026

---

## 📑 Table of Contents

1. [System Requirements](#system-requirements)
2. [macOS Installation](#macos-installation)
3. [Linux Installation](#linux-installation)
4. [Windows Installation](#windows-installation)
5. [First-Time Configuration](#first-time-configuration)
6. [Service Setup](#service-setup)
7. [Troubleshooting](#troubleshooting)
8. [Advanced Configuration](#advanced-configuration)

---

## 🖥️ System Requirements

### Minimum Requirements
- **CPU:** 2+ cores recommended
- **RAM:** 4GB minimum, 8GB+ recommended
- **Disk:** 2GB free space
- **OS:** 
  - macOS 11.0 (Big Sur) or later
  - Ubuntu 20.04+ / Debian 11+ or equivalent Linux
  - Windows 10/11

### Required Software
- Python 3.12 or later
- Node.js 18+ with npm
- Docker or Redis (for backend services)
- Git (for version control features)

---

## 🍎 macOS Installation

### Step 1: Install Homebrew (if not installed)
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Step 2: Install Python 3.12+
```bash
# Install Python
brew install python@3.12

# Verify installation
python3 --version
```

### Step 3: Install Node.js & npm
```bash
# Option A: Using Homebrew
brew install node

# Option B: Using nvm (recommended for multiple Node versions)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.zshrc  # or ~/.bash_profile
nvm install --lts
nvm use --lts

# Verify installation
node --version
npm --version
```

**Note:** If using nvm, your npm path will be something like:
```
/Users/YOUR_USERNAME/.nvm/versions/node/vX.X.X/bin/npm
```

### Step 4: Install Docker Desktop
```bash
# Download and install from:
# https://www.docker.com/products/docker-desktop/

# Or using Homebrew Cask
brew install --cask docker

# Start Docker Desktop from Applications folder
# Verify installation
docker --version
docker ps  # Should show running containers (if any)
```

### Step 5: Install Redis
```bash
# Option A: Install Redis locally (recommended)
brew install redis

# Start Redis as a service
brew services start redis

# Or run Redis manually
redis-server /opt/homebrew/etc/redis.conf

# Option B: Use Docker (if you prefer containerized Redis)
docker run -d --name redis -p 6379:6379 redis:latest
```

**Verify Redis Installation:**
```bash
# Check if Redis is running
redis-cli ping
# Should return: PONG
```

### Step 6: Build LaunchPad

1. **Download or clone the LaunchPad repository:**
```bash
cd ~/VisualStudioProjects
git clone <repository-url> launch-pad
cd launch-pad
```

2. **Create and activate virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate
```

3. **Install Python dependencies:**
```bash
pip install psutil pystray pillow pyinstaller
```

4. **Build the application:**
```bash
pyinstaller LaunchPad.spec --clean
```

5. **Launch the app:**
```bash
# The .app bundle will be in dist/
open dist/LaunchPad.app

# Or run the executable directly
./dist/LaunchPad.app/Contents/MacOS/LaunchPad
```

### Step 7: Add to Applications (Optional)
```bash
# Copy to Applications folder
cp -r dist/LaunchPad.app /Applications/

# Or create a symbolic link
ln -s "$(pwd)/dist/LaunchPad.app" /Applications/LaunchPad.app
```

---

## 🐧 Linux Installation

### Step 1: Install Python & System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y python3.12 python3-pip python3-tk python3-dev
sudo apt-get install -y libnotify-bin  # For notifications
```

**Fedora/RHEL:**
```bash
sudo dnf install -y python3.12 python3-tkinter python3-devel
sudo dnf install -y libnotify  # For notifications
```

### Step 2: Install Node.js & npm

**Ubuntu/Debian:**
```bash
# Install Node.js 20.x
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Verify
node --version
npm --version
```

**Fedora/RHEL:**
```bash
sudo dnf install -y nodejs npm
```

### Step 3: Install Docker

**Ubuntu/Debian:**
```bash
# Add Docker's official GPG key
sudo apt-get install ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker --version
docker ps
```

### Step 4: Install Redis

**Ubuntu/Debian:**
```bash
sudo apt-get install -y redis-server

# Start Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Verify
redis-cli ping
```

**Fedora/RHEL:**
```bash
sudo dnf install -y redis
sudo systemctl start redis
sudo systemctl enable redis
```

### Step 5: Build LaunchPad

```bash
cd ~/VisualStudio
git clone <repository-url> launch-pad
cd launch-pad

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install psutil pystray pillow pyinstaller

# Build
pyinstaller --onefile --windowed --name LaunchPad launchpad.py --clean

# Run
./dist/LaunchPad
```

### Step 6: Create Desktop Launcher (Optional)

Create `~/.local/share/applications/launchpad.desktop`:
```ini
[Desktop Entry]
Version=1.0
Type=Application
Name=LaunchPad
Comment=Django/React Stack Manager
Exec=/home/YOUR_USERNAME/VisualStudio/launch-pad/dist/LaunchPad
Icon=applications-system
Terminal=false
Categories=Development;Utility;
```

---

## 🪟 Windows Installation

### Step 1: Install Python 3.12+

1. Download from [python.org](https://www.python.org/downloads/)
2. Run installer and **check "Add Python to PATH"**
3. Verify in PowerShell:
```powershell
python --version
```

### Step 2: Install Node.js & npm

1. Download from [nodejs.org](https://nodejs.org/)
2. Run installer (includes npm)
3. Verify in PowerShell:
```powershell
node --version
npm --version
```

### Step 3: Install Docker Desktop

1. Download from [docker.com](https://www.docker.com/products/docker-desktop/)
2. Run installer
3. Start Docker Desktop
4. Verify in PowerShell:
```powershell
docker --version
```

### Step 4: Install Redis (Optional)

**Option A: Windows Subsystem for Linux (WSL)**
```powershell
# Enable WSL
wsl --install

# In WSL:
sudo apt-get update
sudo apt-get install redis-server
redis-server
```

**Option B: Docker**
```powershell
docker run -d --name redis -p 6379:6379 redis:latest
```

### Step 5: Build LaunchPad

```powershell
cd C:\Users\YOUR_USERNAME\VisualStudioProjects
git clone <repository-url> launch-pad
cd launch-pad

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install psutil pystray pillow pyinstaller

# Build
pyinstaller --onefile --windowed --name LaunchPad launchpad.py --clean

# Run
.\dist\LaunchPad.exe
```

### Step 6: Create Desktop Shortcut

1. Right-click `dist\LaunchPad.exe`
2. Select "Create shortcut"
3. Move to Desktop or pin to Start Menu

---

## 🎯 First-Time Configuration

### 1. Launch LaunchPad

Run the application for the first time. You'll see the main window with service status indicators.

### 2. Open Configuration Dialog

Click the **"Configure..."** button to open the settings dialog.

### 3. Set Project Paths

#### **Django Project Root**
```
# Example paths:
macOS:   /Users/jeremy/Projects/scanner_backend
Linux:   /home/user/projects/scanner_backend
Windows: C:\Users\User\Projects\scanner_backend
```

This is your Django project directory containing `manage.py` and `settings.py`.

#### **React Frontend Directory**
```
# Example paths:
macOS:   /Users/jeremy/Projects/scanner_frontend
Linux:   /home/user/projects/scanner_frontend
Windows: C:\Users\User\Projects\scanner_frontend
```

This is your React project directory containing `package.json` and `src/`.

### 4. Configure Executable Paths

#### **NPM Path**
Find your npm path:
```bash
# macOS/Linux
which npm

# Common paths:
# macOS (Homebrew):     /opt/homebrew/bin/npm
# macOS (nvm):          /Users/USERNAME/.nvm/versions/node/vX.X.X/bin/npm
# Linux:                /usr/bin/npm
# Windows:              C:\Program Files\nodejs\npm.cmd
```

#### **Docker Path**
Find your Docker path:
```bash
# macOS/Linux
which docker

# Common paths:
# macOS:                /usr/local/bin/docker
# Linux:                /usr/bin/docker
# Windows:              C:\Program Files\Docker\Docker\resources\bin\docker.exe
```

### 5. Configure Django Settings

- **ASGI Application**: Usually `your_project.asgi:application`
- **Host**: `127.0.0.1` (or `0.0.0.0` for external access)
- **Port**: `8070` (or any available port)

### 6. Configure Celery Settings

- **Worker Pool Type**: 
  - `solo` - Single process (simple)
  - `threads` - Thread-based (recommended for I/O)
  - `eventlet` - Async (requires `pip install eventlet`)
- **Concurrency**: Number of worker threads (use "System Analysis" for recommendations)
- **Queues**: Comma-separated list (e.g., `default,celery,priority`)

### 7. Configure Redis Settings (if using Docker)

- **Memory Limit**: e.g., `512m`, `1g`
- **CPU Limit**: e.g., `1.0`, `2.0`
- **Container Name**: `redis-dev` (default)

### 8. Configure Frontend Settings

- **Host**: `localhost` or `0.0.0.0`
- **Port**: `5173` (Vite default) or `3000` (React default)

### 9. Save Configuration

Click **"Save"** and the settings will be stored in SQLite database:
- **macOS**: `~/Library/Application Support/LaunchPad/launchpad.db`
- **Linux**: `~/.config/launchpad/launchpad.db`
- **Windows**: `%APPDATA%\LaunchPad\launchpad.db`

---

## 🚀 Service Setup

### Testing Individual Services

#### 1. Test Redis Connection
```bash
# If Redis is running locally
redis-cli ping
# Should return: PONG

# If using Docker
docker ps | grep redis
```

#### 2. Test Django Backend
```bash
cd /path/to/your/django/project
source venv/bin/activate  # Activate your Django venv
python manage.py check
python manage.py migrate
```

#### 3. Test React Frontend
```bash
cd /path/to/your/react/project
npm install
npm run dev
```

### Starting Services via LaunchPad

1. **Start Individual Services:**
   - Click "Start Daphne" for Django backend
   - Click "Start Celery Beat/Worker"
   - Click "Start Redis" (if using Docker)
   - Click "Start React Frontend"

2. **Start All Services:**
   - Click "Start All" to launch everything at once

3. **Use Service Presets:**
   - Select preset from dropdown (Backend Only, Full Stack, etc.)
   - Click "Start All"

### Monitoring Services

- **Status Panel**: Shows real-time CPU/Memory usage
- **Logs Tab**: View console output for each service
- **System Tray**: Right-click tray icon for quick actions

---

## 🔧 Troubleshooting

### Common Issues

#### "NPM_EXE not found"
**Solution:**
```bash
# Find npm location
which npm

# Update in LaunchPad Configure dialog
# Example: /Users/username/.nvm/versions/node/v24.13.0/bin/npm
```

#### "DOCKER_EXE not found"
**Solution:**
```bash
# macOS: Make sure Docker Desktop is running
open -a Docker

# Find docker location
which docker

# Update in LaunchPad Configure dialog
```

#### "Cannot connect to Redis"
**Solution:**
```bash
# Check if Redis is running
redis-cli ping

# If not running:
# macOS
brew services start redis

# Linux
sudo systemctl start redis-server

# Docker
docker run -d --name redis -p 6379:6379 redis:latest
```

#### "Port already in use"
**Solution:**
```bash
# Find what's using the port
lsof -i :8070  # macOS/Linux
netstat -ano | findstr :8070  # Windows

# Kill the process or change port in LaunchPad configuration
```

#### "Django migrations not applied"
**Solution:**
```bash
cd /path/to/django/project
source venv/bin/activate
python manage.py migrate
```

#### "Celery worker won't start"
**Solution:**
```bash
# Check if Redis is running (Celery needs message broker)
redis-cli ping

# Try different pool type in configuration:
# solo, threads, or eventlet
```

### Log Files

Check logs in LaunchPad's log viewer:
1. Click on service tabs (Daphne, Celery Beat, etc.)
2. Use search to filter errors
3. Export logs if needed

### Reset Configuration

To reset all settings:
```bash
# macOS
rm -rf ~/Library/Application\ Support/LaunchPad/

# Linux
rm -rf ~/.config/launchpad/

# Windows
rmdir /s %APPDATA%\LaunchPad
```

---

## 🔬 Advanced Configuration

### Using System Analysis

1. Click **"System Analysis"** button
2. Review hardware recommendations:
   - CPU cores and optimal Celery concurrency
   - Memory usage and Docker limits
   - Disk space
   - Port availability
3. Click **"Apply Recommended Settings"** to auto-configure

### Custom Celery Queues

Configure multiple queues for task prioritization:
```
default,celery,priority,background
```

Then route tasks to specific queues in Django:
```python
# celery.py
app.conf.task_routes = {
    'app.tasks.urgent_task': {'queue': 'priority'},
    'app.tasks.slow_task': {'queue': 'background'},
}
```

### Database Migration Policies

- **Manual**: You trigger migrations manually
- **Auto (Check Only)**: LaunchPad checks for migrations
- **Auto (Run)**: LaunchPad runs migrations automatically on startup

### Environment Variables

LaunchPad sets environment variables for services:
- `DJANGO_SETTINGS_MODULE`
- `PYTHONPATH`
- `NODE_ENV`

### Running Multiple Instances

To run multiple isolated development environments:
1. Create separate configuration profiles (manually edit database)
2. Use different ports for each instance
3. Use different Redis databases or containers

### Git Integration

LaunchPad includes basic Git tools:
- View current branch and status
- Pull latest changes
- Push commits
- Manage stashes

Access via **Developer Tools** → **Git Panel**

### Building Production Frontend

1. Click **Developer Tools** → **Build Frontend**
2. Runs `npm run build` in frontend directory
3. Outputs to `dist/` or `build/` folder

### Database Viewer

View and export configuration:
1. Click **Developer Tools** → **View DB Config**
2. See all saved settings
3. Export to JSON if needed

---

## 📚 Additional Resources

### Django + Daphne Setup
- [Daphne Documentation](https://github.com/django/daphne)
- [Django ASGI](https://docs.djangoproject.com/en/stable/howto/deployment/asgi/)

### Celery Configuration
- [Celery Documentation](https://docs.celeryq.dev/)
- [Celery Beat](https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html)

### React + Vite
- [Vite Documentation](https://vitejs.dev/)
- [React Documentation](https://react.dev/)

### Docker & Redis
- [Docker Documentation](https://docs.docker.com/)
- [Redis Documentation](https://redis.io/documentation)

---

## 🆘 Getting Help

If you encounter issues not covered in this guide:

1. **Check logs** in LaunchPad's log viewer
2. **Run System Analysis** for hardware recommendations
3. **Verify all dependencies** are installed correctly
4. **Check ports** are not in use by other applications
5. **Review configuration** in the Configure dialog

---

## 📝 Version History

- **1.0.0** (January 2026) - Initial release
  - Full Django/React stack management
  - Celery worker support
  - Redis integration
  - System analysis and monitoring
  - Cross-platform support (macOS, Linux, Windows)

---

**Last Updated:** January 27, 2026  
**Maintained By:** LaunchPad Development Team
