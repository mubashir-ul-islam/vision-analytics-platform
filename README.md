# Vision Analytics Platform

A unified platform combining three independent computer-vision systems under a single Docker Compose setup.

| System | URL | Description |
|--------|-----|-------------|
| Heatmap Counter | http://localhost:8001 | Real-time person detection, tracking, and foot-traffic heatmap |
| Phone Detection | http://localhost:8002 | YOLO-based phone usage detection with configurable zones |
| Smart Attendance | http://localhost:3000 | Face-recognition attendance tracking (entry/exit) |
| Attendance API | http://localhost:8080 | FastAPI backend (Swagger docs at `/docs`) |
| CompreFace UI | http://localhost:8000 | Face recognition engine admin panel |

---

## Client Deployment Guide

> **Target environment:** Windows machine with WSL2 (Ubuntu 24.04), Docker installed, NVIDIA GTX 1650

---

## Step 1 — Open WSL Ubuntu Terminal

All commands in this guide are run inside the **Ubuntu 24.04 WSL terminal**, not PowerShell or CMD.

Press `Win`, search for **Ubuntu**, and open it.

---

## Step 2 — Verify Prerequisites

**Check Docker is running:**
```bash
docker --version
docker compose version
```
Both must return a version number. If Docker is not found, see the Troubleshooting section.

**Check GPU is accessible:**
```bash
nvidia-smi
```
You should see the GTX 1650 listed. If this works, the NVIDIA WSL2 driver is already set up correctly.

**Check NVIDIA Container Toolkit** (allows Docker to use the GPU):
```bash
nvidia-ctk --version
```

If the command is not found, install it:
```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

---

## Step 3 — Enable systemd in WSL2

Systemd must be enabled so that the Docker service and scheduled cron jobs run reliably.

Check if it is already enabled:
```bash
systemctl --version
```

If the command fails or returns an error, enable systemd:
```bash
sudo nano /etc/wsl.conf
```

Add the following content (create the file if it does not exist):
```ini
[boot]
systemd=true
```

Save (`Ctrl+X → Y → Enter`), then restart WSL from PowerShell:
```powershell
wsl --shutdown
```

Reopen the Ubuntu terminal. Docker should start automatically.

---

## Step 4 — Transfer the Project

Copy the `vision-analytics-platform` folder to the client machine using whichever method is available.

**Option A — USB drive / shared folder**

From Windows Explorer, copy the folder into a WSL path. The recommended location inside WSL is:
```
/opt/vision-analytics-platform
```

In the Ubuntu terminal:
```bash
# Example: copying from a USB drive mounted at /mnt/e/
sudo cp -r /mnt/e/vision-analytics-platform /opt/
sudo chown -R $USER:$USER /opt/vision-analytics-platform
```

**Option B — Zip file transfer over network**
```bash
# On the client machine, download or copy the zip, then:
sudo mkdir -p /opt
sudo unzip vision-analytics-platform.zip -d /opt/
sudo chown -R $USER:$USER /opt/vision-analytics-platform
```

Move into the project directory — all remaining commands are run from here:
```bash
cd /opt/vision-analytics-platform
```

---

## Step 5 — Configure `.env`

```bash
nano .env
```

Set the following values:

```dotenv
# ── Demo Expiry ──────────────────────────────────────────────
# The date when all services will automatically stop and all
# project files will be deleted. Format: YYYY-MM-DD
DEMO_EXPIRES_DATE=2026-07-15

# ── Smart Attendance — Camera Sources ────────────────────────
# For USB cameras in WSL2, use usbipd-win to attach the device
# (see Camera Setup section below).
# For IP/RTSP cameras, paste the full URL here — recommended for WSL2.
# Example RTSP: rtsp://admin:password@192.168.1.100:554/stream
ENTRANCE_CAMERA_SOURCE=0
EXIT_CAMERA_SOURCE=2

# ── Smart Attendance — CompreFace key ────────────────────────
# Leave blank for now. You will fill this in during Step 7.
COMPREFACE_API_KEY=

# Leave the rest unchanged
COMPREFACE_URL=http://compreface-fe:80
RECOGNITION_THRESHOLD=0.85
RECOGNITION_INTERVAL_SECONDS=2
COOLDOWN_MINUTES=0.010
DATABASE_URL=sqlite:////data/attendance.db
BACKEND_PORT=8080
BACKEND_CORS_ORIGINS=http://localhost:3000
```

Save and exit (`Ctrl+X → Y → Enter`).

---

## Step 6 — Build and Start All Services

```bash
docker compose up -d --build
```

This will take **5–15 minutes** on the first run as Docker downloads base images and builds the custom ones. Subsequent starts are fast.

Watch the startup progress:
```bash
docker compose logs -f
```

Press `Ctrl+C` to stop watching logs (services keep running).

**Wait for CompreFace to become healthy** — it takes approximately 2 minutes:
```bash
docker compose ps
```

All services should show `running` or `running (healthy)` before continuing. The `attendance-backend` will only start once `compreface-core` is healthy.

---

## Step 7 — Set Up Smart Attendance (CompreFace)

This is a one-time setup for the face recognition system.

**7a.** Open the CompreFace admin panel in a browser on the Windows machine:
```
http://localhost:8000
```

**7b.** Click **Sign Up**, create an admin account, then log in.

**7c.** Click **Create Application** — give it any name (e.g. `Attendance`).

**7d.** Inside the application, click **Add Service** → select **Recognition** → give it any name.

**7e.** Copy the **API Key** displayed for that service.

**7f.** Paste the API key into `.env`:
```bash
nano .env
# Set COMPREFACE_API_KEY=<paste key here>
```

**7g.** Restart the attendance backend to load the new key:
```bash
docker compose restart attendance-backend
```

**7h.** Open the attendance dashboard:
```
http://localhost:3000
```

Go to **Employees → Add Employee**, then click **Enroll Face** to upload or capture a photo for each person.

---

## Step 8 — Configure Cameras

### Heatmap Counter and Phone Detection

Both apps have a full settings panel in the browser — no file editing needed.

- **Heatmap Counter** (`http://localhost:8001`): Select camera source, resolution, and model from the UI.
- **Phone Detection** (`http://localhost:8002`): Select camera source and draw detection zones directly in the browser.

Settings are saved automatically and persist across restarts.

### Camera Sources in WSL2

WSL2 does not expose USB cameras to Linux automatically. There are two options:

**Option A — Use an IP / RTSP camera (recommended)**

This works out of the box. Paste the RTSP URL directly into the camera field in each app's UI, or set it in `.env` for the attendance cameras. Example:
```
rtsp://admin:password@192.168.1.100:554/stream
```

**Option B — Pass through a USB camera using usbipd-win**

Install `usbipd-win` on Windows from: https://github.com/dorssel/usbipd-win/releases

Then in PowerShell (as Administrator) on Windows:
```powershell
# List USB devices
usbipd list

# Attach your camera (replace X-Y with the correct BUSID from the list)
usbipd bind --busid X-Y
usbipd attach --wsl --busid X-Y
```

In the Ubuntu terminal, verify the camera appeared:
```bash
ls /dev/video*
```

You must re-attach the device each time Windows is restarted.

---

## Step 9 — Set Up Auto-Expiry

This installs a scheduled job that destroys the entire platform on the expiry date — even if the PC was off at midnight.

```bash
sudo ./scripts/setup-expiry.sh 2026-07-15    # ← use the same date as .env
```

Verify both triggers are installed:
```bash
crontab -l | grep expiry
```

You should see two lines — one for midnight, one for system boot:
```
0 0 * * * /usr/local/bin/demo-expiry-check.sh
@reboot /usr/local/bin/demo-expiry-check.sh
```

**What happens on expiry:**

| Scenario | Result |
|----------|--------|
| PC is on at midnight on the expiry date | Cron fires at midnight — full destruction |
| PC was off at midnight | Destruction runs on the next WSL session start |
| Client tries `docker compose up` after expiry | Containers detect expiry, exit immediately, Docker does not restart them |
| Client tries `docker compose up` after destruction | Project directory is gone — command fails |

**What gets deleted:**
- All running containers
- All Docker images built by this project
- All Docker volumes (database, attendance records)
- The entire project directory on disk

---

## Step 10 — Verify Everything Is Working

```bash
docker compose ps
```

All 9 services should be running:

```
NAME                       STATUS
heatmap-counter            Up
phone-detection            Up
compreface-postgres-db     Up
compreface-core            Up (healthy)
compreface-api             Up
compreface-admin           Up
compreface-fe              Up
attendance-backend         Up
attendance-frontend        Up
```

Open each URL in the browser on the Windows machine:

| Service | URL |
|---------|-----|
| Heatmap Counter | http://localhost:8001 |
| Phone Detection | http://localhost:8002 |
| Attendance Dashboard | http://localhost:3000 |
| Attendance API docs | http://localhost:8080/docs |
| CompreFace UI | http://localhost:8000 |

---

## Useful Commands

```bash
# View real-time logs for all services
docker compose logs -f

# View logs for a specific service
docker compose logs -f heatmap-counter

# Restart a single service
docker compose restart phone-detection

# Stop everything (services stay stopped until manually started)
docker compose stop

# Start everything again
docker compose start

# Check service status
docker compose ps
```

---

## Troubleshooting

**Docker command not found in WSL**

If Docker was installed via Docker Desktop on Windows, make sure the WSL integration is enabled:
Open Docker Desktop → Settings → Resources → WSL Integration → enable for your Ubuntu distribution.

**GPU not available inside containers**

```bash
# Verify the container toolkit is configured
docker run --rm --gpus all nvidia/cuda:12.0-base-ubuntu22.04 nvidia-smi
```

If this fails, re-run the NVIDIA Container Toolkit installation from Step 2.

**CompreFace taking too long to start**

CompreFace needs to load ML models on first start and can take up to 3–4 minutes on the GTX 1650. Wait and re-check:
```bash
docker compose ps compreface-core
# Wait until status shows "healthy"
```

**`attendance-backend` stuck in restart loop**

It waits for `compreface-core` to be healthy before starting. Check CompreFace logs:
```bash
docker compose logs compreface-core
```

**Ports already in use**

```bash
# Find what is using a port (e.g. 8001)
sudo lsof -i :8001

# Or check all compose ports at once
docker compose ps
```

**Cron not running after WSL restart**

Confirm systemd is enabled (Step 3). Then check the cron service:
```bash
sudo systemctl status cron
sudo systemctl enable --now cron
```
