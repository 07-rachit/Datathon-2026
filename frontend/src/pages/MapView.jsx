import { useEffect, useRef, useState, useMemo } from "react";
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

function markerIcon(color, isSelected = false) {
  const size = isSelected ? 20 : 14;
  const border = isSelected ? "3px solid #FFFFFF" : "2px solid #0B0F17";
  const shadow = isSelected ? `0 0 12px ${color}` : `0 0 0 2px ${color}55`;
  return L.divIcon({
    className: "",
    html: `<div style="
      width:${size}px;height:${size}px;border-radius:50%;
      background:${color};border:${border};
      box-shadow:${shadow};
      transition: all 0.2s ease;
    "></div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

export default function MapView() {
  const mapRef = useRef(null);
  const leafletMap = useRef(null);
  const markersLayer = useRef(null);
  const markersMapRef = useRef({});

  // Filter states
  const [status, setStatus] = useState("");
  const [district, setDistrict] = useState("");
  const [crimeType, setCrimeType] = useState("");
  const [severity, setSeverity] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  // UI & Data states
  const [cases, setCases] = useState([]);
  const [selectedCaseId, setSelectedCaseId] = useState(null);
  const [showSidebar, setShowSidebar] = useState(true);
  const [error, setError] = useState("");

  // Initialize Leaflet Map
  useEffect(() => {
    if (!leafletMap.current && mapRef.current) {
      leafletMap.current = L.map(mapRef.current, {
        zoomControl: true,
      }).setView([30.901, 75.857], 12); // Default to Ludhiana

      L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
        attribution: '&copy; OpenStreetMap &copy; CARTO',
        maxZoom: 19,
      }).addTo(leafletMap.current);

      markersLayer.current = L.layerGroup().addTo(leafletMap.current);
    }
  }, []);

  // Fetch all map cases from backend
  async function loadCases() {
    setError("");
    try {
      const params = {};
      if (status) params.status = status;
      if (district) params.district = district;
      if (crimeType) params.crime_type = crimeType;
      if (severity) params.severity = severity;
      const { data } = await api.get("/cases/map", { params });
      setCases(data);
    } catch (err) {
      setError("Could not load map data. Is the API running?");
    }
  }

  useEffect(() => {
    loadCases();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, district, crimeType, severity]);

  // Dynamic filter dropdown lists
  const availableDistricts = useMemo(() => {
    const set = new Set(cases.map((c) => c.district).filter(Boolean));
    return Array.from(set).sort();
  }, [cases]);

  const availableCrimeTypes = useMemo(() => {
    const set = new Set(cases.map((c) => c.crime_type).filter(Boolean));
    return Array.from(set).sort();
  }, [cases]);

  // Client-side search filtering
  const filteredCases = useMemo(() => {
    if (!searchQuery.trim()) return cases;
    const q = searchQuery.toLowerCase().trim();
    return cases.filter(
      (c) =>
        c.case_id?.toLowerCase().includes(q) ||
        c.title?.toLowerCase().includes(q) ||
        c.district?.toLowerCase().includes(q) ||
        c.crime_type?.toLowerCase().includes(q) ||
        c.status?.toLowerCase().includes(q)
    );
  }, [cases, searchQuery]);

  // Severity counts breakdown
  const counts = useMemo(() => {
    return filteredCases.reduce((acc, c) => {
      acc[c.severity] = (acc[c.severity] || 0) + 1;
      return acc;
    }, {});
  }, [filteredCases]);

  // Re-render markers on Leaflet map whenever filteredCases changes
  useEffect(() => {
    if (!markersLayer.current) return;
    markersLayer.current.clearLayers();
    markersMapRef.current = {};

    filteredCases.forEach((c) => {
      if (c.latitude == null || c.longitude == null) return;

      const isSel = c.id === selectedCaseId;
      const marker = L.marker([c.latitude, c.longitude], {
        icon: markerIcon(SEVERITY_COLOR[c.severity] || "#7C8AA3", isSel),
      });

      const popupHtml = `
        <div style="font-family: system-ui, sans-serif; min-width:220px; padding:4px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
            <span style="font-family: monospace; font-size:11px; color:#3FD6C1; font-weight:bold;">${c.case_id}</span>
            <span style="font-size:10px; font-weight:700; text-transform:uppercase; padding:2px 6px; border-radius:3px; background:${SEVERITY_COLOR[c.severity] || '#7C8AA3'}33; color:${SEVERITY_COLOR[c.severity] || '#7C8AA3'};">${c.severity}</span>
          </div>
          <div style="font-size:13px; font-weight:700; margin:2px 0 6px 0; color:#1E293B;">${c.title}</div>
          <div style="font-size:11px; color:#64748B; margin-bottom:10px;">
            🏢 <b>${c.district}</b> &middot; 🏷️ ${c.crime_type} &middot; 📌 <span style="text-transform:capitalize;">${c.status ? c.status.replace("_", " ") : "N/A"}</span>
          </div>
          <div style="font-size:10px; font-family:monospace; color:#94A3B8; margin-bottom:10px;">
            📍 ${c.latitude.toFixed(4)}, ${c.longitude.toFixed(4)}
          </div>
          <a href="/cases/${c.id}" style="display:block; text-align:center; padding:6px 10px; background:#F0A202; color:#0B0F17; font-size:11px; font-weight:700; border-radius:4px; text-decoration:none; box-shadow:0 1px 3px rgba(0,0,0,0.2);">📂 OPEN CASE FILE &rarr;</a>
        </div>
      `;
      marker.bindPopup(popupHtml);

      marker.on("click", () => {
        setSelectedCaseId(c.id);
      });

      marker.addTo(markersLayer.current);
      markersMapRef.current[c.id] = marker;
    });

    // Auto-fit bounds if coords exist
    const validCoords = filteredCases
      .filter((c) => c.latitude != null && c.longitude != null)
      .map((c) => [c.latitude, c.longitude]);

    if (validCoords.length > 0 && leafletMap.current && !selectedCaseId) {
      leafletMap.current.fitBounds(validCoords, { padding: [50, 50], maxZoom: 14 });
    }
  }, [filteredCases, selectedCaseId]);

  // Function to fly to location when clicked from sidebar/filter list
  const handleFlyToCase = (c) => {
    setSelectedCaseId(c.id);
    if (leafletMap.current && c.latitude != null && c.longitude != null) {
      leafletMap.current.flyTo([c.latitude, c.longitude], 15, {
        duration: 1.2,
        easeLinearity: 0.25,
      });

      const marker = markersMapRef.current[c.id];
      if (marker) {
        marker.openPopup();
      }
    }
  };

  // Reset all active filters
  const resetFilters = () => {
    setStatus("");
    setDistrict("");
    setCrimeType("");
    setSeverity("");
    setSearchQuery("");
    setSelectedCaseId(null);
  };

  // Fit all markers button handler
  const handleFitAll = () => {
    const validCoords = filteredCases
      .filter((c) => c.latitude != null && c.longitude != null)
      .map((c) => [c.latitude, c.longitude]);

    if (validCoords.length > 0 && leafletMap.current) {
      leafletMap.current.fitBounds(validCoords, { padding: [40, 40], maxZoom: 13 });
    }
  };

  return (
    <div className="p-6 h-screen flex flex-col bg-base overflow-hidden">
      {/* Header Section */}
      <div className="mb-4 flex flex-col gap-3">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-teal animate-pulse" />
              <p className="font-mono text-teal text-xs tracking-[0.3em] uppercase">GEOSPATIAL INTELLIGENCE</p>
            </div>
            <h2 className="font-display text-3xl text-ink tracking-wide">Hotspot Map & Incident Locations</h2>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {/* Fit all view */}
            <button
              onClick={handleFitAll}
              className="px-3 py-1.5 bg-panel2 hover:bg-line border border-line text-ink rounded text-xs font-mono transition flex items-center gap-1.5"
              title="Reset map view to show all visible pins"
            >
              🔍 Fit All Hotspots
            </button>

            {/* Toggle Sidebar Button */}
            <button
              onClick={() => setShowSidebar(!showSidebar)}
              className={`px-3 py-1.5 rounded text-xs font-mono border transition flex items-center gap-1.5 ${
                showSidebar
                  ? "bg-teal/20 text-teal border-teal/40"
                  : "bg-panel2 text-muted border-line hover:text-ink"
              }`}
            >
              {showSidebar ? "📂 Hide Hotspot Panel" : "📋 Show Hotspot Panel"} ({filteredCases.length})
            </button>
          </div>
        </div>

        {/* Filters Bar */}
        <div className="bg-panel border border-line rounded-lg p-3 flex flex-wrap items-center gap-3 justify-between">
          {/* Left: Search & Dropdowns */}
          <div className="flex items-center flex-wrap gap-2.5 flex-1 min-w-[300px]">
            {/* Search Box */}
            <div className="relative flex-1 min-w-[180px]">
              <input
                type="text"
                placeholder="Search case, district, title..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-panel2 border border-line rounded px-3 py-1.5 text-ink text-xs focus:outline-none focus:ring-1 focus:ring-teal pl-8"
              />
              <span className="absolute left-2.5 top-1.5 text-muted text-xs">🔍</span>
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery("")}
                  className="absolute right-2.5 top-1.5 text-muted hover:text-ink text-xs"
                >
                  ✕
                </button>
              )}
            </div>

            {/* District Dropdown */}
            <select
              value={district}
              onChange={(e) => setDistrict(e.target.value)}
              className="bg-panel2 border border-line rounded px-2.5 py-1.5 text-ink text-xs focus:outline-none focus:ring-1 focus:ring-teal"
            >
              <option value="">All Districts</option>
              {availableDistricts.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>

            {/* Crime Type Dropdown */}
            <select
              value={crimeType}
              onChange={(e) => setCrimeType(e.target.value)}
              className="bg-panel2 border border-line rounded px-2.5 py-1.5 text-ink text-xs focus:outline-none focus:ring-1 focus:ring-teal"
            >
              <option value="">All Crime Types</option>
              {availableCrimeTypes.map((ct) => (
                <option key={ct} value={ct}>{ct}</option>
              ))}
            </select>

            {/* Status Dropdown */}
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="bg-panel2 border border-line rounded px-2.5 py-1.5 text-ink text-xs focus:outline-none focus:ring-1 focus:ring-teal"
            >
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>{s ? s.replace("_", " ") : "All Statuses"}</option>
              ))}
            </select>

            {/* Reset Filters */}
            {(district || status || crimeType || severity || searchQuery) && (
              <button
                onClick={resetFilters}
                className="text-xs font-mono text-crit hover:underline px-2 py-1 bg-crit/10 border border-crit/30 rounded"
              >
                Clear Filters ✕
              </button>
            )}
          </div>

          {/* Right: Severity Pills */}
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-[11px] font-mono text-muted mr-1">Severity:</span>
            <button
              onClick={() => setSeverity("")}
              className={`px-2 py-1 rounded text-[11px] font-mono border transition ${
                severity === ""
                  ? "bg-teal/20 text-teal border-teal/40 font-bold"
                  : "bg-panel2 text-muted border-line hover:text-ink"
              }`}
            >
              All ({filteredCases.length})
            </button>
            {Object.entries(SEVERITY_COLOR).map(([sev, color]) => {
              const isSelected = severity === sev;
              return (
                <button
                  key={sev}
                  onClick={() => setSeverity(severity === sev ? "" : sev)}
                  className={`px-2 py-1 rounded text-[11px] font-mono border transition flex items-center gap-1 ${
                    isSelected
                      ? "bg-panel2 text-ink border-teal shadow-sm"
                      : "bg-panel2/60 text-muted border-line hover:text-ink"
                  }`}
                  style={{ borderColor: isSelected ? color : undefined }}
                >
                  <span className="w-2 h-2 rounded-full" style={{ background: color }} />
                  <span className="capitalize">{sev}</span>
                  <span className="opacity-80">({counts[sev] || 0})</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* District Quick Jump Chips */}
        {availableDistricts.length > 0 && (
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
            <span className="text-[11px] font-mono text-muted whitespace-nowrap">District Jump:</span>
            {availableDistricts.map((d) => (
              <button
                key={d}
                onClick={() => setDistrict(district === d ? "" : d)}
                className={`px-2.5 py-0.5 rounded-full font-mono text-[11px] whitespace-nowrap border transition ${
                  district === d
                    ? "bg-teal/20 text-teal border-teal/50 font-semibold"
                    : "bg-panel2 text-muted border-line hover:border-teal/30 hover:text-ink"
                }`}
              >
                📍 {d}
              </button>
            ))}
          </div>
        )}
      </div>

      {error && (
        <p className="text-crit text-sm font-mono border border-crit/40 bg-crit/10 rounded px-4 py-2.5 mb-3">
          ⚠️ {error}
        </p>
      )}

      {/* Main Map & Hotspots Sidebar Layout */}
      <div className="flex-1 flex rounded-lg overflow-hidden border border-line relative">
        {/* Leaflet Map Canvas */}
        <div className="flex-1 h-full relative">
          <div ref={mapRef} className="w-full h-full" style={{ minHeight: "450px" }} />

          {/* Map Overlay Badge */}
          <div className="absolute bottom-3 left-3 z-[1000] bg-base/90 backdrop-blur border border-line rounded px-3 py-1.5 text-xs font-mono text-muted flex items-center gap-2 shadow-lg">
            <span>📍 Active Pins: <strong className="text-teal">{filteredCases.length}</strong></span>
            <span>&middot;</span>
            <Link to="/cases" className="text-amber hover:underline">View All Cases &rarr;</Link>
          </div>
        </div>

        {/* Hotspot Sidebar List */}
        {showSidebar && (
          <div className="w-80 sm:w-96 bg-panel border-l border-line flex flex-col h-full z-[1001] shadow-2xl transition-all">
            {/* Sidebar Header */}
            <div className="p-3 border-b border-line bg-panel2 flex items-center justify-between">
              <div>
                <h3 className="font-display text-lg text-ink">Filtered Hotspots</h3>
                <p className="text-[11px] font-mono text-muted">
                  Click any hotspot to zoom directly to location
                </p>
              </div>
              <span className="font-mono text-xs text-teal bg-teal/10 px-2 py-0.5 rounded border border-teal/20">
                {filteredCases.length} locations
              </span>
            </div>

            {/* Scrollable Hotspot Cards List */}
            <div className="flex-1 overflow-y-auto p-2.5 space-y-2.5 custom-scrollbar">
              {filteredCases.length === 0 ? (
                <div className="p-8 text-center text-muted font-mono text-xs">
                  <p className="text-2xl mb-2">🗺️</p>
                  No hotspot locations match the selected filters.
                  <button
                    onClick={resetFilters}
                    className="block mx-auto mt-3 text-teal underline"
                  >
                    Reset all filters
                  </button>
                </div>
              ) : (
                filteredCases.map((c) => {
                  const isSelected = c.id === selectedCaseId;
                  const color = SEVERITY_COLOR[c.severity] || "#7C8AA3";

                  return (
                    <div
                      key={c.id}
                      onClick={() => handleFlyToCase(c)}
                      className={`p-3 rounded-md border transition-all cursor-pointer group ${
                        isSelected
                          ? "bg-panel2 border-teal shadow-md ring-1 ring-teal/50"
                          : "bg-panel2/50 border-line hover:border-line hover:bg-panel2"
                      }`}
                    >
                      {/* Top row: Case ID & Severity Badge */}
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="font-mono text-xs font-bold text-teal tracking-wide">
                          {c.case_id}
                        </span>
                        <span
                          className="text-[10px] font-mono uppercase font-bold px-2 py-0.5 rounded"
                          style={{
                            backgroundColor: `${color}22`,
                            color: color,
                            border: `1px solid ${color}44`,
                          }}
                        >
                          {c.severity}
                        </span>
                      </div>

                      {/* Title */}
                      <h4 className="text-sm font-semibold text-ink group-hover:text-amber transition line-clamp-1 mb-1">
                        {c.title}
                      </h4>

                      {/* Details row */}
                      <div className="text-[11px] text-muted flex items-center justify-between gap-1 mb-2">
                        <span>🏢 {c.district}</span>
                        <span>&middot;</span>
                        <span className="truncate">🏷️ {c.crime_type}</span>
                        <span>&middot;</span>
                        <span className="capitalize">{c.status ? c.status.replace("_", " ") : "Open"}</span>
                      </div>

                      {/* Bottom action row: Coordinates & Fly To button */}
                      <div className="pt-2 border-t border-line/50 flex items-center justify-between text-[10px] font-mono">
                        <span className="text-muted flex items-center gap-1">
                          📍 {c.latitude?.toFixed(4)}, {c.longitude?.toFixed(4)}
                        </span>

                        <div className="flex items-center gap-2">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleFlyToCase(c);
                            }}
                            className="text-teal hover:text-ink font-bold flex items-center gap-1 bg-teal/10 hover:bg-teal/20 px-2 py-0.5 rounded transition"
                          >
                            <span>🎯 Fly To</span>
                          </button>
                          <Link
                            to={`/cases/${c.id}`}
                            onClick={(e) => e.stopPropagation()}
                            className="text-amber hover:underline font-bold"
                          >
                            Open ➔
                          </Link>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
