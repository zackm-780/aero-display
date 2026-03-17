/* global L */
import { getAirlineLogoPath } from "./airlineLogos.js";

const CONNECTION = {
  DISCONNECTED: "disconnected",
  CONNECTING: "connecting",
  CONNECTED: "connected",
};

const RANGE_PRESETS = [20, 50];
const MAX_BOARD_FLIGHTS = 20;
const RADAR_LABEL_LIMIT = 12;

let socket;
let reconnectDelay = 1000;
let reconnectTimer = null;
let map;
let centerMarker;
let radarLayer;
let rangeLayer;
let lastCenter = null;
let currentRangeNm = 50;

let boardFlightsState = [];

const connectionEl = document.getElementById("connection-status");
const stalenessEl = document.getElementById("staleness-indicator");
const listEl = document.getElementById("flight-list");
const settingsButton = document.getElementById("settings-button");
const rangeButtons = Array.from(document.querySelectorAll(".range-button"));
const modalEl = document.getElementById("settings-modal");
const settingsForm = document.getElementById("settings-form");
const icaoInput = document.getElementById("icao-input");
const settingsError = document.getElementById("settings-error");
const settingsClose = document.getElementById("settings-close");

function setConnectionStatus(status) {
  if (!connectionEl) return;
  switch (status) {
    case CONNECTION.CONNECTED:
      connectionEl.textContent = "Live";
      connectionEl.classList.remove("status-pill--disconnected");
      connectionEl.classList.add("status-pill--connected");
      break;
    case CONNECTION.CONNECTING:
      connectionEl.textContent = "Connecting…";
      connectionEl.classList.remove("status-pill--connected");
      connectionEl.classList.add("status-pill--disconnected");
      break;
    default:
      connectionEl.textContent = "Disconnected";
      connectionEl.classList.remove("status-pill--connected");
      connectionEl.classList.add("status-pill--disconnected");
  }
}

function setStaleness(isStale) {
  if (!stalenessEl) return;
  if (isStale) {
    stalenessEl.textContent = "Stale";
    stalenessEl.classList.add("staleness--stale");
  } else {
    stalenessEl.textContent = "Fresh";
    stalenessEl.classList.remove("staleness--stale");
  }
}

function initMap() {
  map = L.map("map", {
    zoomControl: false,
    attributionControl: true,
    minZoom: 5,
    maxZoom: 11,
    dragging: false,
    scrollWheelZoom: false,
    doubleClickZoom: false,
    boxZoom: false,
    keyboard: false,
  }).setView([0, 0], 9);

  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: "abcd",
    maxZoom: 19,
  }).addTo(map);

  radarLayer = L.layerGroup().addTo(map);
  rangeLayer = L.layerGroup().addTo(map);
}

function nmToMeters(nm) {
  return nm * 1852;
}

function mpsToKnots(mps) {
  return mps * 1.943844;
}

function zoomForRangeNm(nm) {
  switch (nm) {
    case 20:
      return 10;
    case 50:
    default:
      return 9;
  }
}

function updateRangeButtons() {
  rangeButtons.forEach((btn) => {
    const value = Number(btn.dataset.range);
    btn.classList.toggle("range-button--active", value === currentRangeNm);
  });
}

function updateRangeRings(center, activeRangeNm) {
  if (!rangeLayer || !center) return;

  rangeLayer.clearLayers();
  RANGE_PRESETS.forEach((nm) => {
    const isActive = nm === activeRangeNm;
    L.circle([center.lat, center.lon], {
      radius: nmToMeters(nm),
      color: isActive ? "#fbbf24" : "#4b5563",
      weight: isActive ? 2.5 : 1,
      dashArray: isActive ? "4 6" : "2 8",
      fillOpacity: 0,
    }).addTo(rangeLayer);
  });
}

function formatAltitude(altitudeMeters, airportElevationFt, transitionAltitudeFt) {
  if (altitudeMeters == null) return "—";
  const feet = altitudeMeters * 3.28084;
  if (airportElevationFt != null && feet < airportElevationFt + 100) {
    return "—";
  }
  const roundedHundreds = Math.round(feet / 100) * 100;
  if (transitionAltitudeFt != null && roundedHundreds >= transitionAltitudeFt) {
    const fl = Math.round(roundedHundreds / 100);
    return `FL${fl}`;
  }
  return `${roundedHundreds.toLocaleString()} ft`;
}

function isAirborneFlight(f, airportElevationFt) {
  if (!f || typeof f.altitude !== "number") return false;
  const altitudeFt = f.altitude * 3.28084;
  if (typeof airportElevationFt === "number") {
    return altitudeFt >= airportElevationFt + 100;
  }
  return altitudeFt >= 100;
}

function radarOffsetClass(index) {
  const classes = [
    "radar-plane--offset-a",
    "radar-plane--offset-b",
    "radar-plane--offset-c",
    "radar-plane--offset-d",
  ];
  return classes[index % classes.length];
}

function updateMap(center, radarFlights, meta) {
  if (!map || !radarLayer) return;

  lastCenter = center;
  map.setView([center.lat, center.lon], zoomForRangeNm(currentRangeNm));
  map.invalidateSize();

  radarLayer.clearLayers();

  centerMarker = L.circleMarker([center.lat, center.lon], {
    radius: 4,
    color: "#38bdf8",
    weight: 2,
    fillColor: "#0ea5e9",
    fillOpacity: 0.9,
  }).addTo(radarLayer);

  const airportElevationFt =
    meta && typeof meta.airportElevationFt === "number" ? meta.airportElevationFt : null;

  const filtered = Array.isArray(radarFlights)
    ? radarFlights
        .filter(
          (f) =>
            typeof f.distanceNm === "number" &&
            f.distanceNm <= currentRangeNm &&
            isAirborneFlight(f, airportElevationFt),
        )
        .sort((a, b) => a.distanceNm - b.distanceNm)
    : [];

  filtered.forEach((f, index) => {
    const heading = typeof f.heading === "number" ? f.heading : 0;
    const callsign = f.callsign || f.icao24 || "Unknown";
    const altitudeText = formatAltitude(
      f.altitude,
      meta && typeof meta.airportElevationFt === "number" ? meta.airportElevationFt : null,
      meta && typeof meta.transitionAltitudeFt === "number" ? meta.transitionAltitudeFt : null,
    );
    const showLabel = index < RADAR_LABEL_LIMIT;
    const labelPart = showLabel
      ? `<span class="radar-leader-line"></span><span class="radar-plane-label">${callsign} · ${altitudeText}</span>`
      : "";

    const icon = L.divIcon({
      className: "radar-plane-icon",
      html: `
        <div class="radar-plane ${radarOffsetClass(index)}">
          <span class="radar-plane-arrow" style="transform: rotate(${heading}deg);"></span>
          ${labelPart}
        </div>
      `,
      iconSize: [150, 30],
      iconAnchor: [8, 8],
    });

    L.marker([f.lat, f.lon], { icon }).addTo(radarLayer);
  });

  updateRangeRings(center, currentRangeNm);
}

function createLogoNode(airlineCode) {
  const logoWrap = document.createElement("div");
  logoWrap.className = "flight-card-logo";

  const fallback = () => {
    logoWrap.innerHTML = "";
    const fallbackEl = document.createElement("div");
    fallbackEl.className = "flight-card-logo-fallback";
    fallbackEl.textContent = airlineCode || "";
    logoWrap.appendChild(fallbackEl);
  };

  const logoSrc = getAirlineLogoPath(airlineCode);
  if (!logoSrc) {
    fallback();
    return logoWrap;
  }

  const img = document.createElement("img");
  img.src = logoSrc;
  img.alt = `${airlineCode || "Airline"} logo`;
  img.className = "flight-card-logo-img";
  img.setAttribute("onerror", "this.dataset.failed='1'");
  img.addEventListener("error", fallback, { once: true });
  logoWrap.appendChild(img);
  return logoWrap;
}

function renderFlights(boardFlights, meta) {
  if (!listEl) return;

  const airportElevationFt =
    meta && typeof meta.airportElevationFt === "number" ? meta.airportElevationFt : null;

  const filtered = Array.isArray(boardFlights)
    ? boardFlights.filter((f) => isAirborneFlight(f, airportElevationFt))
    : [];

  boardFlightsState = filtered.slice(0, MAX_BOARD_FLIGHTS);
  renderFlightWindow();
}

function renderFlightWindow() {
  if (!listEl) return;

  const wrapper = document.createElement("div");
  wrapper.className = "flight-list-inner";

  if (boardFlightsState.length === 0) {
    const empty = document.createElement("div");
    empty.className = "flight-card flight-card--empty";
    empty.textContent = "No nearby airborne traffic";
    wrapper.appendChild(empty);
  } else {
    boardFlightsState.forEach((f) => {
      const callsign = f.callsign || f.icao24 || "Unknown";
      const airlineCode = f.airlineCode || (callsign ? callsign.slice(0, 3).toUpperCase() : "");
      const type = f.aircraftType || "—";
      const altitudeText = formatAltitude(f.altitude, null, null);
      const speedText = typeof f.velocity === "number" ? `${Math.round(mpsToKnots(f.velocity))} kt` : "—";
      const distanceText = typeof f.distanceNm === "number" ? `${f.distanceNm.toFixed(1)} nm` : "—";
      const headingText = f.heading != null ? `${Math.round(f.heading)}°` : "—";

      const row = document.createElement("div");
      row.className = "flight-card";

      row.appendChild(createLogoNode(airlineCode));

      const body = document.createElement("div");
      body.className = "flight-card-body";

      const title = document.createElement("div");
      title.className = "flight-card-title";
      const callsignEl = document.createElement("span");
      callsignEl.className = "flight-callsign";
      callsignEl.textContent = callsign;
      title.appendChild(callsignEl);

      const metaRow = document.createElement("div");
      metaRow.className = "flight-card-meta";
      [type, altitudeText, speedText, distanceText, headingText].forEach((value) => {
        const item = document.createElement("span");
        item.className = "flight-meta-item";
        item.textContent = value;
        metaRow.appendChild(item);
      });

      body.appendChild(title);
      body.appendChild(metaRow);
      row.appendChild(body);
      wrapper.appendChild(row);
    });
  }

  listEl.innerHTML = "";
  listEl.appendChild(wrapper);
}

function handleMessage(data) {
  if (!data) return;
  const { center, boardFlights, radarFlights, meta } = data;
  if (center && typeof center.lat === "number" && typeof center.lon === "number") {
    updateMap(center, radarFlights || [], meta || {});
  }
  if (Array.isArray(boardFlights)) {
    renderFlights(boardFlights, meta);
  }
  setStaleness(meta && meta.stale);
}

function connect() {
  const loc = window.location;
  const wsProtocol = loc.protocol === "https:" ? "wss:" : "ws:";
  const url = `${wsProtocol}//${loc.host}/ws`;

  setConnectionStatus(CONNECTION.CONNECTING);
  socket = new WebSocket(url);

  socket.onopen = () => {
    setConnectionStatus(CONNECTION.CONNECTED);
    reconnectDelay = 1000;
  };

  socket.onmessage = (event) => {
    let data;
    try {
      data = JSON.parse(event.data);
    } catch (e) {
      console.error("Malformed websocket payload", e);
      return;
    }

    try {
      handleMessage(data);
    } catch (e) {
      console.error("Failed to render websocket payload", e);
    }
  };

  socket.onclose = () => {
    setConnectionStatus(CONNECTION.DISCONNECTED);
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
    }
    reconnectTimer = setTimeout(() => {
      reconnectDelay = Math.min(reconnectDelay * 2, 15000);
      connect();
    }, reconnectDelay);
  };

  socket.onerror = () => {
    socket.close();
  };
}

function openSettings() {
  modalEl.classList.remove("modal--hidden");
  modalEl.setAttribute("aria-hidden", "false");
  icaoInput.focus();
}

function closeSettings() {
  modalEl.classList.add("modal--hidden");
  modalEl.setAttribute("aria-hidden", "true");
  settingsError.textContent = "";
}

rangeButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    const nm = Number(btn.dataset.range);
    if (!nm || nm === currentRangeNm) return;
    currentRangeNm = nm;
    updateRangeButtons();
    if (lastCenter && map) {
      map.setView([lastCenter.lat, lastCenter.lon], zoomForRangeNm(currentRangeNm));
      updateRangeRings(lastCenter, currentRangeNm);
    }
  });
});

settingsButton.addEventListener("click", openSettings);
settingsClose.addEventListener("click", closeSettings);
modalEl.addEventListener("click", (evt) => {
  if (evt.target === modalEl) {
    closeSettings();
  }
});

settingsForm.addEventListener("submit", async (evt) => {
  evt.preventDefault();
  const icao = icaoInput.value.trim().toUpperCase();
  if (!icao) return;

  try {
    const resp = await fetch("/api/center", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ icao }),
    });
    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      settingsError.textContent = data.detail || "Unable to update center";
      return;
    }
    closeSettings();
  } catch (_e) {
    settingsError.textContent = "Network error";
  }
});

window.addEventListener("load", () => {
  initMap();
  connect();
});
