Product Requirements Document (PRD): AeroDisplay
================================================

Project Overview
----------------

**AeroDisplay** is a local web application designed to run in landscape Kiosk mode on a low-spec Android tablet (Galaxy Tab A 8" SM-T290). The UI features a 50/50 split screen: the left side emulates a scrolling "FlightWall" board of nearby flights, while the right side displays an interactive ATC-style radar map. To ensure smooth performance on older tablet hardware, all data fetching, distance calculations, and sorting are handled by a local Ubuntu headless server.

Hardware & Architecture Strategy
--------------------------------

*   **Client (Galaxy Tab A 8" SM-T290):** Acts as a "dumb terminal" running Fully Kiosk Browser (or Chrome pinned). Performs zero complex logic. Only renders standard HTML/CSS and a lightweight 2D map canvas.
    
*   **Server (AcePC Celeron Ubuntu Headless):** Hosts the backend API and serves the frontend assets. Runs a background loop to fetch, filter, sort, and package flight data, then pushes clean JSON to the tablet via WebSockets.
    
*   **Data Source:** OpenSky Network REST API (Free tier for hobbyists).
    
*   **Network:** Local Area Network (LAN) via Wi-Fi.
    

Functional Requirements
-----------------------

### Backend (Ubuntu Server)

*   **Data Ingestion:** Fetch real-time flight data from OpenSky API every 10–15 seconds.
    
*   **Filtering & Math:** \* Calculate the Haversine distance for all aircraft relative to a configurable "Home ICAO" coordinate set.
    
    *   **List A (Flight Board):** Filter flights within a 200 NM radius. Sort them by proximity (closest at the top).
        
    *   **List B (Radar):** Filter flights within a 50 NM radius.
        
*   **State Management:** Store the current "Center ICAO" so the radii calculations can be updated dynamically by the user.
    
*   **API Endpoints:**
    
    *   HTTP route to serve the static frontend files (index.html, style.css, app.js).
        
    *   WebSocket endpoint to push pre-calculated flight lists (List A & List B) to the frontend every few seconds.
        
    *   POST endpoint to receive a new ICAO code from the frontend, look up its coordinates, and update the center location.
        

### Frontend (Tablet)

*   **Split Layout:** 50vw / 100vh split. Black/dark gray aviation-themed UI to minimize screen glare.
    
*   **Left Pane (Flight Board):**
    
    *   Display a stylized list of flights (Flight Number, Airline, Aircraft Type, Altitude, Speed, Distance).
        
    *   Auto-cycle/scroll through the 200 NM list if it exceeds the screen height.
        
*   **Right Pane (Radar Screen):**
    
    *   Display a dark-mode map centered on the active ICAO location.
        
    *   Plot flights in the 50 NM radius using custom aircraft icons or blips.
        
    *   Include a subtle sweeping CSS animation overlay to mimic a radar sweep.
        
*   **Interactivity:**
    
    *   **Tap a Flight:** Pauses the auto-scroll. Highlights the flight on the radar in a distinct color and expands the list item to show expanded details (heading, origin/destination if available).
        
    *   **Settings Button:** A subtle UI element that opens a modal to input a new center ICAO code.
        

Non-Functional Requirements
---------------------------

*   **Performance:** The frontend must use hardware-accelerated CSS for animations and avoid heavy DOM repaints to prevent the tablet from freezing.
    
*   **Resilience:** The frontend must auto-reconnect to the backend via WebSockets if the LAN connection drops. The backend must handle OpenSky API rate limits gracefully without crashing.
    

Recommended Tech Stack
----------------------

*   **Backend:** Python with **FastAPI**. Incredibly fast, lightweight, and has built-in support for WebSockets.
    
*   **Frontend:** Vanilla JavaScript, HTML, and CSS. Avoid heavy frameworks like React or Angular to spare the tablet's memory.
    
*   **Map Library:** **Leaflet.js** (configured with a dark mode tile provider like CartoDB Dark Matter). Lighter than Google Maps and renders well on older Android WebViews.
    

Ubuntu Server Implementation Guide
----------------------------------

Agent: ignore this section for development purposes, it is only context so you know how it will be deployed. Be sure to build this section (and expand if needed!) into the final README about the project.

This section outlines how to deploy the AeroDisplay backend on your headless AcePC Ubuntu server.

### Prerequisites

Ensure your Ubuntu server has Python 3 and pip installed. Connect via SSH:

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   sudo apt update  sudo apt install python3 python3-pip python3-venv git   `

### Step 1: Project Setup (Git Clone)

Once you have initialized a Git repository for your project (e.g., on GitHub), clone it directly to your server and set up the Python virtual environment.

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   # Replace with your actual repository URL  git clone [https://github.com/yourusername/aerodisplay.git](https://github.com/yourusername/aerodisplay.git) ~/aerodisplay  cd ~/aerodisplay  python3 -m venv venv  source venv/bin/activate   `

### Step 2: Install Dependencies

Install FastAPI, the ASGI server (Uvicorn), and required networking libraries.

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   pip install fastapi uvicorn websockets requests   `

### Step 3: Running the Application

To test the backend before setting up a permanent service, start the server and bind it to 0.0.0.0 so it is accessible from your tablet.

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   uvicorn main:app --host 0.0.0.0 --port 8000   `

_Note: Find your Ubuntu server's local IP address by running ip a or hostname -I (e.g., 192.168.1.50). Your tablet will point to http://192.168.1.50:8000._

### Step 4: Running as a Background Service (Systemd)

To ensure AeroDisplay runs automatically when the AcePC reboots, create a systemd service.

1.  Create the service file:
    

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   sudo nano /etc/systemd/system/aerodisplay.service   `

1.  Paste the following configuration (replace yourusername with your actual Ubuntu username):
    

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   [Unit]  Description=AeroDisplay FastAPI Server  After=network.target  [Service]  User=yourusername  WorkingDirectory=/home/yourusername/aerodisplay  Environment="PATH=/home/yourusername/aerodisplay/venv/bin"  ExecStart=/home/yourusername/aerodisplay/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000  [Install]  WantedBy=multi-user.target   `

1.  Enable and start the service:
    

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   sudo systemctl daemon-reload  sudo systemctl enable aerodisplay  sudo systemctl start aerodisplay  sudo systemctl status aerodisplay   `

### Step 5: Tablet Setup

1.  Connect the Galaxy Tab A to the same Wi-Fi network.
    
2.  Open Fully Kiosk Browser (or Chrome).
    
3.  Navigate to your server's IP (e.g., http://192.168.1.50:8000).
    
4.  Pin the app or lock the browser into Kiosk mode.
    

### Step 6: Updating the Application from Git

Once your project is fully built, you will likely make ongoing adjustments in your IDE (Cursor/Replit) and push them to your Git repository. To deploy those updates to your Ubuntu server, SSH in and run:

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   cd ~/aerodisplay  # Pull the latest code from your repository's main branch  git pull origin main   # If you added new dependencies in requirements.txt, run:  # source venv/bin/activate && pip install -r requirements.txt  # Restart the background service to apply the new changes  sudo systemctl restart aerodisplay   `

_(Optional Automation: You can place these commands in a deploy.sh script or hook them up to a cron job to automatically sync your changes.)_
