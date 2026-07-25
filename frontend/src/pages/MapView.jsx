import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import api from "../lib/api.js";

const SEVERITY_COLOR = {
  low: "#3FD6C1",
  medium: "#F0A202",
  high: "#E8833A",
  critical: "#E23D5B",
};

const STATUS_OPTIONS = ["", "open", "closed", "under_review"];

function markerIcon(color) {
  return L.divIcon({
    className: "",
    html: `<div style="
      width:14px;height:14px;border-radius:50%;
      background:${color};border:2px solid #0B0F17;
      box-shadow:0 0 0 2px ${color}55;
    "></div>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  });
}

export default function MapView() {
  const mapRef = useRef(null);
  const leafletMap = useRef(null);
  const markersLayer = useRef(null);
  const [status, setStatus] = useState("");
  const [cases, setCases] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!leafletMap.current) {
      leafletMap.current = L.map(mapRef.current, {
        zoomControl: true,
      }).setView([30.901, 75.857], 12); // Ludhiana

      L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
        attribution: '&copy; OpenStreetMap &copy; CARTO',
        maxZoom: 19,
      }).addTo(leafletMap.current);

      markersLayer.current = L.layerGroup().addTo(leafletMap.current);
    }
  }, []);

  async function loadCases() {
    setError("");
    try {
      const params = {};
      if (status) params.status = status;
      const { data } = await api.get("/cases/map", { params });
      setCases(data);
    } catch (err) {
      setError("Could not load map data. Is the API running?");
    }
  }

  useEffect(() => {
    loadCases();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  useEffect(() => {
    if (!markersLayer.current) return;
    markersLayer.current.clearLayers();
    cases.forEach((c) => {
      if (c.latitude == null || c.longitude == null) return;
      const marker = L.marker([c.latitude, c.longitude], {
        icon: markerIcon(SEVERITY_COLOR[c.severity] || "#7C8AA3"),
      });
      const popupHtml = `
        <div style="font-family: Inter, sans-serif; min-width:180px;">
          <div style="font-family: 'JetBrains Mono', monospace; font-size:11px; color:#3FD6C1;">${c.case_id}</div>
          <div style="font-size:13px; font-weight:600; margin:2px 0;">${c.title}</div>
          <div style="font-size:11px; color:#555;">${c.district} &middot; ${c.crime_type}</div>
        </div>
      `;
      marker.bindPopup(popupHtml);
      marker.addTo(markersLayer.current);
    });
  }, [cases]);

  const counts = cases.reduce((acc, c) => {
    acc[c.severity] = (acc[c.severity] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="p-8 h-screen flex flex-col">
      <div className="mb-4 flex items-end justify-between flex-wrap gap-3">
        <div>
          <p className="font-mono text-teal text-xs tracking-[0.3em] mb-1">GEOSPATIAL</p>
          <h2 className="font-display text-3xl text-ink">Hotspot Map</h2>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="bg-panel2 border border-line rounded px-3 py-2 text-ink text-sm focus:outline-none focus:ring-1 focus:ring-teal"
          >
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>{s ? s.replace("_", " ") : "All statuses"}</option>
            ))}
          </select>
          {Object.entries(SEVERITY_COLOR).map(([sev, color]) => (
            <div key={sev} className="flex items-center gap-1.5 text-xs text-muted font-mono">
              <span className="w-2.5 h-2.5 rounded-full" style={{ background: color }} />
              {sev} ({counts[sev] || 0})
            </div>
          ))}
        </div>
      </div>

      {error && (
        <p className="text-crit text-sm font-mono border border-crit/40 bg-crit/10 rounded px-4 py-3 mb-4">
          {error}
        </p>
      )}

      <div className="flex-1 rounded-md overflow-hidden border border-line">
        <div ref={mapRef} className="w-full h-full" style={{ minHeight: "500px" }} />
      </div>
      <p className="text-muted text-xs font-mono mt-2">
        {cases.length} plotted case(s) &middot; click a marker for details, or view the{" "}
        <Link to="/cases" className="text-teal hover:underline">full case list</Link>
      </p>
    </div>
  );
}
