/* global L */

const CONNECTION = {
  DISCONNECTED: "disconnected",
  CONNECTING: "connecting",
  CONNECTED: "connected",
};

let socket;
let reconnectDelay = 1000;
let reconnectTimer = null;
let map;
let centerMarker;
let radarLayer;
let rangeLayer;
let radarMarkers = [];
let autoScrollTimer = null;
let autoScrollPaused = false;
let lastCenter = null;
let currentRangeNm = 50;

const RANGE_PRESETS = [20, 50, 100, 200];

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
    stalenessEl.textContent = "Live";
    stalenessEl.classList.remove("staleness--stale");
  }
}

function initMap() {
  map = L.map("map", {
    zoomControl: false,
    attributionControl: true,
    minZoom: 4,
    maxZoom: 12,
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

function zoomForRangeNm(nm) {
  switch (nm) {
    case 20:
      return 10;
    case 50:
      return 9;
    case 100:
      return 8;
    case 200:
    default:
      return 7;
  }
}

function updateRangeButtons() {
  rangeButtons.forEach((btn) => {
    const value = Number(btn.dataset.range);
    if (value === currentRangeNm) {
      btn.classList.add("range-button--active");
    } else {
      btn.classList.remove("range-button--active");
    }
  });
}

function updateRangeRings(center, activeRangeNm) {
  if (!rangeLayer || !center) return;

  rangeLayer.clearLayers();

  RANGE_PRESETS.forEach((nm) => {
    const isActive = nm === activeRangeNm;
    const circle = L.circle([center.lat, center.lon], {
      radius: nmToMeters(nm),
      color: isActive ? "#fbbf24" : "#4b5563",
      weight: isActive ? 2.5 : 1,
      dashArray: isActive ? "4 6" : "2 8",
      fillOpacity: 0,
    });
    circle.addTo(rangeLayer);
  });
}

function updateMap(center, radarFlights) {
  if (!map || !radarLayer) return;
  lastCenter = center;
  map.setView([center.lat, center.lon], zoomForRangeNm(currentRangeNm));

  radarLayer.clearLayers();
  radarMarkers = [];

  centerMarker = L.circleMarker([center.lat, center.lon], {
    radius: 4,
    color: "#38bdf8",
    weight: 2,
    fillColor: "#0ea5e9",
    fillOpacity: 0.9,
  }).addTo(radarLayer);

  radarFlights.forEach((f) => {
    const marker = L.circleMarker([f.lat, f.lon], {
      radius: 3,
      color: "#22c55e",
      weight: 1,
      fillColor: "#22c55e",
      fillOpacity: 0.9,
    }).addTo(radarLayer);
    radarMarkers.push(marker);
  });

  updateRangeRings(center, currentRangeNm);
}

function renderFlights(boardFlights) {
  if (!listEl) return;
  const wrapper = document.createElement("div");
  wrapper.className = "flight-list-inner";

  const header = document.createElement("div");
  header.className = "flight-row flight-row-header";
  header.innerHTML = `
    <span>Flight</span>
    <span>Type</span>
    <span>Alt</span>
    <span>Speed</span>
    <span>Dist</span>
    <span>Dir</span>
  `;
  wrapper.appendChild(header);

  boardFlights.forEach((f, index) => {
    const row = document.createElement("div");
    row.className = "flight-row";
    row.dataset.index = String(index);
    row.innerHTML = `
      <span class="flight-callsign">${f.callsign || f.icao24}</span>
      <span>${f.aircraftType || "\u2014"}</span>
      <span class="flight-altitude">${f.altitude ? Math.round(f.altitude) + " ft" : "\u2014"}</span>
      <span class="flight-speed">${f.velocity ? Math.round(f.velocity) + " kt" : "\u2014"}</span>
      <span class="flight-distance">${f.distanceNm.toFixed(1)} nm</span>
      <span>${f.heading != null ? Math.round(f.heading) + "\u00b0" : "\u2014"}</span>
    `;
    wrapper.appendChild(row);
  });

  listEl.innerHTML = "";
  listEl.appendChild(wrapper);

  setupRowInteractions(boardFlights);
}

function highlightSelection(index) {
  const rows = listEl.querySelectorAll(".flight-row");
  rows.forEach((row) => {
    if (row.dataset.index === String(index)) {
      row.classList.add("flight-row--highlighted");
    } else {
      row.classList.remove("flight-row--highlighted");
    }
  });

  radarMarkers.forEach((marker, i) => {
    if (i === index && marker.setStyle) {
      marker.setStyle({ color: "#f97316", fillColor: "#fed7aa" });
    } else if (marker.setStyle) {
      marker.setStyle({ color: "#22c55e", fillColor: "#22c55e" });
    }
  });
}

function setupRowInteractions() {
  const rows = listEl.querySelectorAll(".flight-row");
  rows.forEach((row) => {
    const index = row.dataset.index;
    if (index == null) return;
    row.addEventListener("click", () => {
      autoScrollPaused = true;
      highlightSelection(Number(index));
    });
  });
}

function startAutoScroll() {
  if (!listEl) return;
  const inner = listEl.querySelector(".flight-list-inner");
  if (!inner) return;

  if (autoScrollTimer) {
    clearInterval(autoScrollTimer);
  }

  let offset = 0;
  const rowHeight = 32; // approximate

  autoScrollTimer = setInterval(() => {
    if (autoScrollPaused) return;
    offset += 0.5;
    inner.style.transform = `translateY(${-offset}px)`;
    if (offset > inner.scrollHeight) {
      offset = 0;
    }
  }, 50);
}

function handleMessage(data) {
  if (!data) return;
  const { center, boardFlights, radarFlights, meta } = data;
  if (center && typeof center.lat === "number" && typeof center.lon === "number") {
    updateMap(center, radarFlights || []);
  }
  if (Array.isArray(boardFlights)) {
    renderFlights(boardFlights);
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
    try {
      const data = JSON.parse(event.data);
      handleMessage(data);
    } catch (e) {
      // ignore malformed
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
  } catch (e) {
    settingsError.textContent = "Network error";
  }
});

window.addEventListener("load", () => {
  initMap();
  connect();
  startAutoScroll();
});

