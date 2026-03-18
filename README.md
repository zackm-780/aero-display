## AeroDisplay

Local web application that repurposes legacy Android tablets to show a 50/50 split between a FlightWall-style flight board and an ATC-style radar map of nearby traffic. The backend runs on an Ubuntu box (FastAPI + Python) and pushes pre-processed flight data to a kiosk-mode tablet over your LAN.

Want to buy me a coffee?  [buymeacoffee.com/zackm](https://buymeacoffee.com/zackm)

![1000007581](https://github.com/user-attachments/assets/67969e3e-2af9-40c4-842c-a05a06286bce)

### Features

- **Flight board (left pane)**: Auto-scrolling list of flights within 200 NM, sorted by proximity.
- **Radar map (right pane)**: Dark-themed Leaflet map centered on a configurable ICAO, plotting flights within 50 NM plus a radar-sweep overlay.
- **Center ICAO control**: Settings modal to change the “home” ICAO; backend resolves it to coordinates using a bundled airport dataset.
- **Resilient polling**: Backend polls OpenSky Network every 10–15 seconds with backoff and pushes clean JSON over WebSockets.

### Tech stack

- **Backend**: Python, FastAPI, Uvicorn, httpx.
- **Frontend**: Vanilla HTML/CSS/JS, Leaflet.
- **Data source**: OpenSky Network REST API (hobbyist/free tier).

### Local development

1. **Clone and create a venv**

   ```bash
   git clone <your-repo-url> aero-display
   cd aero-display
   python3 -m venv venv
   source venv/bin/activate
   pip install -r backend/requirements.txt
   ```

2. **Environment configuration**

   Copy `.env.example` to `.env` and adjust as needed (OpenSky credentials, default center ICAO, etc.). For basic testing, you can run anonymously against OpenSky.

3. **Run backend**

   ```bash
   uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
   ```

4. **Open the UI**

   Visit `http://localhost:8000/ui/` in a browser. The root URL redirects to the app. You should see the split-screen layout; flights and radar blips populate via the WebSocket feed.

5. **Run tests**

   ```bash
   pytest backend/tests -q
   ```

### Ubuntu server deployment (headless)

1. **Install prerequisites**

   ```bash
   sudo apt update
   sudo apt install -y python3 python3-venv python3-pip git
   ```

2. **Clone and set up**

   ```bash
   cd ~
   git clone <your-repo-url> aerodisplay
   cd aerodisplay
   python3 -m venv venv
   source venv/bin/activate
   pip install -r backend/requirements.txt
   cp .env.example .env
   # edit .env to set OpenSky credentials and default center ICAO
   ```

3. **Test run**

   ```bash
   uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
   ```

   From another machine or the tablet, hit `http://<server-ip>:8000/ui` to confirm the UI loads.

4. **Systemd service**

    Create `/etc/systemd/system/aerodisplay.service` with:

    ```bash
    sudo tee /etc/systemd/system/aerodisplay.service >/dev/null <<'EOF'
    [Unit]
    Description=AeroDisplay FastAPI Server
    After=network.target

    [Service]
    Type=simple
    User=<your-ubuntu-username>
    WorkingDirectory=/home/<your-ubuntu-username>/aerodisplay
    Environment="PATH=/home/<your-ubuntu-username>/aerodisplay/venv/bin"
    ExecStart=/home/<your-ubuntu-username>/aerodisplay/venv/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
    Restart=always
    RestartSec=5

    [Install]
    WantedBy=multi-user.target
    EOF
    ```

    Reload systemd and start on boot:

    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable --now aerodisplay
    sudo systemctl status aerodisplay
    ```

    View logs:

    ```bash
    sudo journalctl -u aerodisplay -f
    ```

### Tablet setup (Android Tablet with Fully Kiosk)

1. Connect the tablet to the same Wi‑Fi network as the Ubuntu server.
2. Install and open Fully Kiosk Browser (or Chrome).
3. Set the start URL to `http://<server-ip>:8000/ui`.
4. Enable kiosk/fullscreen mode so the UI runs continuously without UI chrome.

### Updating the deployment

When you push new code to your main branch:

```bash
ssh <server>
cd ~/aerodisplay
git pull origin main
source venv/bin/activate
pip install -r backend/requirements.txt
sudo systemctl restart aerodisplay
```

### Airline logo credits

Airline logo images used by the nearby-flights board are sourced from the `flightaware_logos` dataset in the `Jxck-S/airline-logos` repository:
- [Jxck-S/airline-logos — flightaware_logos](https://github.com/Jxck-S/airline-logos/tree/main/flightaware_logos)

Logos are stored locally under `frontend/assets/logos/flightaware_logos/` and resolved by ICAO airline code filename (for example `UAL.png`, `DAL.png`).

### Troubleshooting

- **No flights shown**: Check your OpenSky rate limits and credentials; try running `pytest backend/tests -q` locally to ensure processing logic is healthy.
- **Tablet not connecting**: Verify the server IP, firewall rules, and that `systemctl status aerodisplay` reports `active (running)`.
- **Radar map blank**: Ensure the tablet has internet access for tile requests (Leaflet dark tiles).

