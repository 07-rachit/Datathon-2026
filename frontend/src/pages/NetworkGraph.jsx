import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import {
  forceSimulation,
  forceLink,
  forceManyBody,
  forceCenter,
  forceCollide,
} from "d3-force-3d";
import { fetchNetworkGraph, fetchNetworkGroups } from "../lib/api.js";

/* ─── Color Palette ────────────────────────────────────────────────────────── */
const COL = {
  bg:     0x0b0f17,
  teal:   0x3fd6c1,
  amber:  0xf0a202,
  crit:   0xe23d5b,
  violet: 0x8b5cf6,
  slate:  0x5b6b7c,
};

const SEVERITY_HEX = {
  low: 0x3fd6c1, medium: 0xf0a202, high: 0xe8833a, critical: 0xe23d5b,
};

/* ─── Node geometry factory ────────────────────────────────────────────────── */
function makeMesh(node) {
  let geo, color;
  if (node.type === "case") {
    geo   = new THREE.BoxGeometry(3.2, 3.2, 3.2);
    color = SEVERITY_HEX[node.severity] ?? COL.teal;
  } else if (node.type === "account") {
    geo   = new THREE.OctahedronGeometry(2.0);
    color = COL.violet;
  } else {
    geo   = new THREE.SphereGeometry(1.6, 16, 12);
    color = COL.slate;
  }
  const mat  = new THREE.MeshStandardMaterial({
    color, emissive: color, emissiveIntensity: 0.45,
    roughness: 0.5, metalness: 0.35,
  });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.userData = { nodeData: node, baseColor: color };
  return mesh;
}

/* ─── Label sprite ─────────────────────────────────────────────────────────── */
function makeLabel(text, hexColor) {
  const r = (hexColor >> 16 & 0xff).toString(16).padStart(2, "0");
  const g = (hexColor >> 8  & 0xff).toString(16).padStart(2, "0");
  const b = (hexColor       & 0xff).toString(16).padStart(2, "0");
  const cssCol = `#${r}${g}${b}`;

  const canvas = document.createElement("canvas");
  const ctx    = canvas.getContext("2d");
  const fs     = 24;
  ctx.font     = `${fs}px monospace`;
  const w      = Math.ceil(ctx.measureText(text.slice(0, 24)).width) + 14;
  const h      = fs + 10;
  canvas.width = w; canvas.height = h;
  ctx.font        = `${fs}px monospace`;
  ctx.fillStyle   = cssCol;
  ctx.textBaseline = "middle";
  ctx.fillText(text.slice(0, 24), 7, h / 2);

  const tex  = new THREE.CanvasTexture(canvas);
  tex.minFilter = THREE.LinearFilter;
  const spr  = new THREE.Sprite(
    new THREE.SpriteMaterial({ map: tex, transparent: true, opacity: 0.9, depthTest: false })
  );
  spr.scale.set(w / 24, h / 24, 1);
  return spr;
}

/* ─── Edge line ────────────────────────────────────────────────────────────── */
function makeEdge(kind) {
  const pts  = [new THREE.Vector3(), new THREE.Vector3()];
  const geo  = new THREE.BufferGeometry().setFromPoints(pts);
  let mat;
  if (kind === "shared_phone") {
    mat = new THREE.LineDashedMaterial({ color: COL.crit, transparent: true, opacity: 0.85, dashSize: 2, gapSize: 1.2 });
  } else if (kind === "financial_transfer") {
    mat = new THREE.LineBasicMaterial({ color: COL.amber, transparent: true, opacity: 0.7 });
  } else if (kind === "owns_account") {
    mat = new THREE.LineBasicMaterial({ color: COL.violet, transparent: true, opacity: 0.5 });
  } else {
    mat = new THREE.LineBasicMaterial({ color: COL.teal, transparent: true, opacity: 0.25 });
  }
  const line = new THREE.Line(geo, mat);
  line.frustumCulled = false;
  if (kind === "shared_phone") line.computeLineDistances();
  return line;
}

/* ─── Starfield ────────────────────────────────────────────────────────────── */
function makeStarfield() {
  const N   = 1800;
  const pos = new Float32Array(N * 3);
  const col = new Float32Array(N * 3);
  for (let i = 0; i < N; i++) {
    const theta = Math.random() * Math.PI * 2;
    const phi   = Math.acos(2 * Math.random() - 1);
    const r     = 400 + Math.random() * 180;
    pos[i * 3]     = r * Math.sin(phi) * Math.cos(theta);
    pos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
    pos[i * 3 + 2] = r * Math.cos(phi);
    const t = Math.random();
    if (t < 0.40)      { col[i * 3] = 0.25; col[i * 3 + 1] = 0.84; col[i * 3 + 2] = 0.76; } // teal
    else if (t < 0.55) { col[i * 3] = 0.94; col[i * 3 + 1] = 0.63; col[i * 3 + 2] = 0.01; } // amber
    else { const v = 0.5 + Math.random() * 0.4; col[i * 3] = v; col[i * 3 + 1] = v + 0.05; col[i * 3 + 2] = v + 0.12; }
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  geo.setAttribute("color",    new THREE.BufferAttribute(col, 3));
  return new THREE.Points(
    geo,
    new THREE.PointsMaterial({ size: 0.85, vertexColors: true, transparent: true, opacity: 0.18, sizeAttenuation: true, depthWrite: false })
  );
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/*  Component                                                                  */
/* ═══════════════════════════════════════════════════════════════════════════ */
export default function NetworkGraph() {
  const canvasRef = useRef(null);
  const navigate  = useNavigate();

  const [graph, setGraph]                 = useState({ nodes: [], edges: [], recurring_links: 0 });
  const [groups, setGroups]               = useState([]);
  const [selectedGroup, setSelectedGroup] = useState(null);
  const [district, setDistrict]           = useState("");
  const [includeFinancial, setIncludeFinancial] = useState(true);
  const [searchQuery, setSearchQuery]     = useState("");
  const [autoRotate, setAutoRotate]       = useState(true);
  const [error, setError]                 = useState("");
  const [selected, setSelected]           = useState(null);
  const [hovering, setHovering]           = useState(false);
  const [loading, setLoading]             = useState(true);

  // Three.js objects ref
  const threeRef = useRef({
    scene: null, camera: null, renderer: null, controls: null,
    meshMap: new Map(), labelMap: new Map(), edgeObjs: [],
    clusterSphere: null, starfield: null, animId: null,
    sim: null, cameraTarget: null, nodeById: new Map(),
  });

  /* ── Data fetch ─────────────────────────────────────────────────────────── */
  const loadData = useCallback(() => {
    setLoading(true);
    setError("");
    const params = { include_financial: includeFinancial };
    if (district) params.district = district;

    Promise.all([
      fetchNetworkGraph(params),
      fetchNetworkGroups().catch(() => []),
    ]).then(([g, grps]) => {
      setGraph(g);
      setGroups(grps);
      setLoading(false);
    }).catch(() => {
      setError("Could not load the network graph. Is the API running?");
      setLoading(false);
    });
  }, [district, includeFinancial]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Extract unique districts from cases for filter dropdown
  const availableDistricts = useMemo(() => {
    const caseDistricts = graph.nodes
      .filter((n) => n.type === "case" && n.district)
      .map((n) => n.district);
    return Array.from(new Set(caseDistricts)).sort();
  }, [graph.nodes]);

  /* ── Build / rebuild Three.js scene ─────────────────────────────────────── */
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !graph.nodes.length) return;

    const T = threeRef.current;

    // ── Teardown old scene ──
    if (T.animId) cancelAnimationFrame(T.animId);
    if (T.sim)    T.sim.stop();
    if (T.controls) T.controls.dispose();
    if (T.renderer) T.renderer.dispose();
    if (T.scene) T.scene.clear();

    // ── Scene ──
    const scene      = new THREE.Scene();
    scene.background = new THREE.Color(COL.bg);
    scene.fog        = new THREE.FogExp2(COL.bg, 0.0025);
    T.scene          = scene;

    // ── Camera ──
    const w = canvas.clientWidth  || canvas.offsetWidth  || 800;
    const h = canvas.clientHeight || canvas.offsetHeight || 600;
    const camera = new THREE.PerspectiveCamera(55, w / h, 0.1, 1200);
    camera.position.set(0, 30, 110);
    T.camera = camera;

    // ── Renderer ──
    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
    renderer.setSize(w, h, false);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping         = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.1;
    T.renderer = renderer;

    // ── OrbitControls ──
    const controls = new OrbitControls(camera, canvas);
    controls.enableDamping   = true;
    controls.dampingFactor   = 0.08;
    controls.minDistance     = 15;
    controls.maxDistance     = 500;
    controls.autoRotate      = autoRotate;
    controls.autoRotateSpeed = 0.25;
    T.controls = controls;

    // ── Lights ──
    scene.add(new THREE.AmbientLight(0xffffff, 0.65));
    const pl1 = new THREE.PointLight(COL.teal,   1.2, 400); pl1.position.set( 60, 80,  60); scene.add(pl1);
    const pl2 = new THREE.PointLight(COL.amber,  0.6, 300); pl2.position.set(-50,-30, -50); scene.add(pl2);
    const pl3 = new THREE.PointLight(COL.violet, 0.4, 250); pl3.position.set(  0, 60, -80); scene.add(pl3);

    // ── Starfield & Grid ──
    const stars = makeStarfield();
    scene.add(stars);
    T.starfield = stars;

    const grid = new THREE.GridHelper(320, 40, 0x1a2433, 0x0f1520);
    grid.position.y = -55;
    grid.material.transparent = true;
    grid.material.opacity = 0.12;
    scene.add(grid);

    // ── Deduplicate nodes ──
    const seen = new Set();
    const simNodes = [];
    for (const n of graph.nodes) {
      if (!seen.has(n.id)) {
        seen.add(n.id);
        simNodes.push({
          ...n,
          x: (Math.random() - 0.5) * 60,
          y: (Math.random() - 0.5) * 60,
          z: (Math.random() - 0.5) * 60,
        });
      }
    }
    const nodeById = new Map(simNodes.map((n) => [n.id, n]));
    T.nodeById = nodeById;

    const simLinks = graph.edges
      .filter((e) => nodeById.has(e.source) && nodeById.has(e.target))
      .map((e) => ({ ...e }));

    // ── Create Meshes & Labels ──
    const meshMap  = new Map();
    const labelMap = new Map();
    for (const node of simNodes) {
      const mesh = makeMesh(node);
      scene.add(mesh);
      meshMap.set(node.id, mesh);

      const lc  = node.type === "case" ? COL.teal : node.type === "account" ? COL.violet : COL.slate;
      const lbl = makeLabel(node.label, lc);
      scene.add(lbl);
      labelMap.set(node.id, lbl);
    }
    T.meshMap  = meshMap;
    T.labelMap = labelMap;

    // ── Create Edges ──
    const edgeObjs = [];
    for (const edge of simLinks) {
      const line = makeEdge(edge.kind);
      scene.add(line);
      edgeObjs.push({ line, edge });
    }
    T.edgeObjs = edgeObjs;

    // ── 3D Force Simulation ──
    const sim = forceSimulation(simNodes, 3)
      .force("link",    forceLink(simLinks).id((d) => d.id).distance((l) => l.kind === "shared_phone" ? 32 : 24).strength(0.5))
      .force("charge",  forceManyBody().strength(-85))
      .force("center",  forceCenter(0, 0, 0))
      .force("collide", forceCollide().radius(5).strength(0.6))
      .alpha(1)
      .alphaDecay(0.018)
      .velocityDecay(0.4);
    T.sim = sim;

    // ── Resize Observer ──
    const ro = new ResizeObserver(() => {
      const rw = canvas.clientWidth;
      const rh = canvas.clientHeight;
      if (rw > 0 && rh > 0) {
        camera.aspect = rw / rh;
        camera.updateProjectionMatrix();
        renderer.setSize(rw, rh, false);
      }
    });
    ro.observe(canvas);

    // ── Animation Loop ──
    function animate() {
      T.animId = requestAnimationFrame(animate);

      if (sim.alpha() > 0.001) sim.tick();

      // Update mesh & label positions with NaN safety
      for (const node of simNodes) {
        const nx = isNaN(node.x) ? 0 : node.x;
        const ny = isNaN(node.y) ? 0 : node.y;
        const nz = isNaN(node.z) ? 0 : node.z;

        const mesh = meshMap.get(node.id);
        if (mesh) {
          mesh.position.set(nx, ny, nz);
          if (node.type === "case")    { mesh.rotation.y += 0.004; mesh.rotation.x += 0.001; }
          if (node.type === "account") { mesh.rotation.y += 0.008; }
        }
        const lbl = labelMap.get(node.id);
        if (lbl) lbl.position.set(nx + 3.0, ny + 3.0, nz);
      }

      // Update edge lines with NaN safety
      for (const { line, edge } of edgeObjs) {
        const src = typeof edge.source === "object" ? edge.source : nodeById.get(edge.source);
        const tgt = typeof edge.target === "object" ? edge.target : nodeById.get(edge.target);
        if (src && tgt) {
          const sx = isNaN(src.x) ? 0 : src.x;
          const sy = isNaN(src.y) ? 0 : src.y;
          const sz = isNaN(src.z) ? 0 : src.z;
          const tx = isNaN(tgt.x) ? 0 : tgt.x;
          const ty = isNaN(tgt.y) ? 0 : tgt.y;
          const tz = isNaN(tgt.z) ? 0 : tgt.z;
          const arr = line.geometry.attributes.position.array;
          arr[0] = sx; arr[1] = sy; arr[2] = sz;
          arr[3] = tx; arr[4] = ty; arr[5] = tz;
          line.geometry.attributes.position.needsUpdate = true;
          if (edge.kind === "shared_phone") line.computeLineDistances();
        }
      }

      if (T.starfield) {
        T.starfield.rotation.y += 0.00009;
        T.starfield.rotation.x += 0.00003;
      }

      // Smooth camera lerp for fly-to
      if (T.cameraTarget) {
        camera.position.lerp(T.cameraTarget.pos, 0.05);
        controls.target.lerp(T.cameraTarget.lookAt, 0.05);
        if (camera.position.distanceTo(T.cameraTarget.pos) < 1.5) {
          T.cameraTarget = null;
        }
      }

      controls.update();
      renderer.render(scene, camera);
    }
    animate();

    return () => {
      ro.disconnect();
      cancelAnimationFrame(T.animId);
      sim.stop();
      controls.dispose();
      renderer.dispose();
      scene.clear();
    };
  }, [graph]); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-rotate toggle handler
  useEffect(() => {
    if (threeRef.current.controls) {
      threeRef.current.controls.autoRotate = autoRotate;
    }
  }, [autoRotate]);

  /* ── Group highlighting ──────────────────────────────────────────────────── */
  useEffect(() => {
    const T     = threeRef.current;
    const scene = T.scene;
    if (!scene) return;

    if (T.clusterSphere) {
      scene.remove(T.clusterSphere);
      T.clusterSphere.geometry.dispose();
      T.clusterSphere.material.dispose();
      T.clusterSphere = null;
    }

    const memberIds = selectedGroup
      ? new Set(selectedGroup.members.map((m) => m.person_node_id))
      : null;

    for (const [id, mesh] of T.meshMap.entries()) {
      const base = mesh.userData.baseColor;
      if (memberIds && memberIds.has(id)) {
        mesh.material.color.setHex(COL.amber);
        mesh.material.emissive.setHex(COL.crit);
        mesh.material.emissiveIntensity = 0.85;
        mesh.scale.setScalar(1.6);
      } else {
        mesh.material.color.setHex(base);
        mesh.material.emissive.setHex(base);
        mesh.material.emissiveIntensity = 0.4;
        mesh.scale.setScalar(1.0);
      }
    }

    if (selectedGroup && memberIds) {
      const positions = [];
      for (const id of memberIds) {
        const m = T.meshMap.get(id);
        if (m) positions.push(m.position.clone());
      }
      if (positions.length) {
        const centroid = new THREE.Vector3();
        positions.forEach((p) => centroid.add(p));
        centroid.divideScalar(positions.length);

        let maxDist = 8;
        positions.forEach((p) => {
          const d = p.distanceTo(centroid);
          if (d > maxDist) maxDist = d;
        });
        const radius = maxDist + 8;

        const sphere = new THREE.Mesh(
          new THREE.SphereGeometry(radius, 24, 16),
          new THREE.MeshBasicMaterial({ color: COL.amber, transparent: true, opacity: 0.08, side: THREE.DoubleSide, depthWrite: false })
        );
        sphere.position.copy(centroid);
        scene.add(sphere);
        T.clusterSphere = sphere;

        T.cameraTarget = {
          pos:    centroid.clone().add(new THREE.Vector3(0, radius * 0.5, radius * 2.2)),
          lookAt: centroid.clone(),
        };
      }
    }
  }, [selectedGroup]);

  /* ── Fly to single node when clicked or searched ───────────────────────── */
  const handleFlyToNode = (node) => {
    setSelected(node);
    const T = threeRef.current;
    const mesh = T.meshMap.get(node.id);
    if (mesh && T.camera && T.controls) {
      const targetPos = mesh.position.clone();
      T.cameraTarget = {
        pos: targetPos.clone().add(new THREE.Vector3(0, 10, 30)),
        lookAt: targetPos.clone(),
      };
    }
  };

  /* ── Reset Camera View ──────────────────────────────────────────────────── */
  const handleResetCamera = () => {
    setSelected(null);
    setSelectedGroup(null);
    const T = threeRef.current;
    if (T.camera && T.controls) {
      T.cameraTarget = {
        pos: new THREE.Vector3(0, 30, 110),
        lookAt: new THREE.Vector3(0, 0, 0),
      };
    }
  };

  /* ── Raycaster Click & Hover ────────────────────────────────────────────── */
  const handleClick = useCallback((e) => {
    const T = threeRef.current;
    if (!T.renderer || !T.camera) return;
    const rect  = canvasRef.current.getBoundingClientRect();
    const mouse = new THREE.Vector2(
      ((e.clientX - rect.left) / rect.width)  *  2 - 1,
      ((e.clientY - rect.top)  / rect.height) * -2 + 1
    );
    const rc = new THREE.Raycaster();
    rc.setFromCamera(mouse, T.camera);
    const hits = rc.intersectObjects([...T.meshMap.values()], false);
    if (hits.length) {
      const nd = hits[0].object.userData.nodeData;
      setSelected(nd);
      handleFlyToNode(nd);
    }
  }, []);

  const handleMouseMove = useCallback((e) => {
    const T = threeRef.current;
    if (!T.renderer || !T.camera) return;
    const rect  = canvasRef.current.getBoundingClientRect();
    const mouse = new THREE.Vector2(
      ((e.clientX - rect.left) / rect.width)  *  2 - 1,
      ((e.clientY - rect.top)  / rect.height) * -2 + 1
    );
    const rc = new THREE.Raycaster();
    rc.setFromCamera(mouse, T.camera);
    setHovering(rc.intersectObjects([...T.meshMap.values()], false).length > 0);
  }, []);

  // Filtered search results for quick node lookup
  const searchResults = useMemo(() => {
    if (!searchQuery.trim()) return [];
    const q = searchQuery.toLowerCase().trim();
    return graph.nodes.filter(
      (n) =>
        n.label?.toLowerCase().includes(q) ||
        n.sublabel?.toLowerCase().includes(q) ||
        n.phone?.toLowerCase().includes(q)
    ).slice(0, 8);
  }, [graph.nodes, searchQuery]);

  return (
    <div className="flex h-screen bg-base text-ink overflow-hidden flex-col md:flex-row">
      {/* ── Main 3D Graph Canvas Area ── */}
      <div className="flex-1 relative flex flex-col min-w-0">

        {/* Header Bar */}
        <div className="shrink-0 px-4 py-3 border-b border-line bg-panel flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-violet animate-pulse" />
              <span className="font-mono text-xs text-teal tracking-[0.2em] uppercase">INTELLIGENCE NETWORK</span>
            </div>
            <h2 className="font-display text-xl leading-tight">Criminal &amp; Financial Network Graph</h2>
          </div>

          {/* Controls & Filter Bar */}
          <div className="flex items-center gap-2.5 flex-wrap">
            {/* Search Node Input */}
            <div className="relative min-w-[200px]">
              <input
                type="text"
                placeholder="Search suspect, case, account..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="bg-panel2 border border-line rounded px-3 py-1.5 text-ink text-xs focus:outline-none focus:ring-1 focus:ring-teal pl-7 w-full"
              />
              <span className="absolute left-2.5 top-1.5 text-muted text-xs">🔍</span>
              {searchQuery && (
                <div className="absolute top-full left-0 right-0 mt-1 bg-panel border border-line rounded shadow-2xl z-50 max-h-48 overflow-y-auto">
                  {searchResults.length === 0 ? (
                    <div className="p-2 text-xs font-mono text-muted text-center">No nodes found</div>
                  ) : (
                    searchResults.map((n) => (
                      <div
                        key={n.id}
                        onClick={() => {
                          handleFlyToNode(n);
                          setSearchQuery("");
                        }}
                        className="p-2 hover:bg-panel2 border-b border-line/50 text-xs font-mono cursor-pointer flex items-center justify-between"
                      >
                        <span className="font-semibold text-teal truncate">{n.label}</span>
                        <span className="text-[10px] text-muted capitalize ml-2">{n.type}</span>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>

            {/* District Filter Dropdown */}
            {availableDistricts.length > 0 && (
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
            )}

            {/* Financial Overlay Checkbox */}
            <label className="flex items-center gap-1.5 text-xs font-mono text-muted cursor-pointer bg-panel2 border border-line px-2.5 py-1.5 rounded hover:text-ink">
              <input
                type="checkbox"
                checked={includeFinancial}
                onChange={(e) => setIncludeFinancial(e.target.checked)}
                className="accent-violet rounded"
              />
              Financial Transfers
            </label>

            {/* Auto-Rotate Toggle */}
            <button
              onClick={() => setAutoRotate(!autoRotate)}
              className={`px-2.5 py-1.5 rounded text-xs font-mono border transition ${
                autoRotate
                  ? "bg-teal/20 text-teal border-teal/40"
                  : "bg-panel2 text-muted border-line hover:text-ink"
              }`}
              title="Toggle automatic 3D rotation"
            >
              🔄 Orbit: {autoRotate ? "ON" : "OFF"}
            </button>

            {/* Reset View */}
            <button
              onClick={handleResetCamera}
              className="px-2.5 py-1.5 bg-panel2 hover:bg-line border border-line text-ink rounded text-xs font-mono transition"
              title="Reset 3D camera to home position"
            >
              🎯 Reset View
            </button>
          </div>
        </div>

        {/* Legend Bar */}
        <div className="shrink-0 px-4 py-2 border-b border-line bg-panel2/60 flex items-center justify-between text-[11px] font-mono flex-wrap gap-2">
          <div className="flex items-center gap-4 flex-wrap">
            <span className="flex items-center gap-1.5"><span className="inline-block w-2.5 h-2.5 bg-teal" /> Case File</span>
            <span className="flex items-center gap-1.5"><span className="inline-block w-2.5 h-2.5 rounded-full bg-[#5B6B7C]" /> Person / Suspect</span>
            <span className="flex items-center gap-1.5"><span className="inline-block w-2.5 h-2.5 bg-[#8B5CF6] rotate-45" /> Bank Account</span>
            <span className="flex items-center gap-1.5 text-crit"><span className="inline-block w-4 border-t-2 border-dashed border-crit" /> Shared Phone Link</span>
            <span className="flex items-center gap-1.5 text-amber"><span className="inline-block w-4 border-t-2 border-amber" /> Financial Transfer</span>
            <span className="flex items-center gap-1.5 text-amber"><span className="inline-block w-2.5 h-2.5 rounded-full bg-amber" /> Gang Member</span>
          </div>

          <div className="text-muted">
            Nodes: <strong className="text-teal">{graph.nodes.length}</strong> &middot; Links: <strong className="text-amber">{graph.edges.length}</strong> &middot; Recurring Phone Links: <strong className="text-crit">{graph.recurring_links}</strong>
          </div>
        </div>

        {/* 3D Canvas Container */}
        <div className="flex-1 relative bg-[#0B0F17]">
          {error && (
            <div className="absolute top-4 left-4 z-10 text-crit text-xs font-mono bg-crit/10 border border-crit/40 px-3 py-2 rounded">
              ⚠️ {error}
            </div>
          )}
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center z-10 bg-base/60 backdrop-blur">
              <div className="flex items-center gap-3 font-mono text-teal text-sm animate-pulse">
                <span className="w-3 h-3 rounded-full bg-teal" />
                Constructing 3D Network Graph &amp; Force Physics...
              </div>
            </div>
          )}
          <canvas
            ref={canvasRef}
            onClick={handleClick}
            onMouseMove={handleMouseMove}
            style={{
              display: "block",
              width: "100%",
              height: "100%",
              cursor: hovering ? "pointer" : "grab",
            }}
          />
          <div
            className="absolute inset-0 pointer-events-none"
            style={{ background: "radial-gradient(ellipse at 50% 40%, rgba(63,214,193,0.035) 0%, transparent 55%)" }}
          />
        </div>
      </div>

      {/* ── Sidebar: Gang Detection & Node Inspector ── */}
      <div className="w-full md:w-80 shrink-0 border-l border-line bg-panel p-4 flex flex-col gap-4 overflow-y-auto">
        {/* Section 1: Detected Syndicates */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <h3 className="font-display text-lg text-ink">Detected Syndicates</h3>
            <span className="font-mono text-xs text-amber bg-amber/10 px-2 py-0.5 rounded border border-amber/20">
              {groups.length} clusters
            </span>
          </div>
          <p className="text-muted text-[11px] font-mono mb-3">
            Multi-vector clustering (Co-accused, Shared Phone, Wire Transfers)
          </p>

          {groups.length === 0 ? (
            <div className="p-4 text-center border border-line bg-panel2/40 rounded text-muted font-mono text-xs">
              No qualifying gang clusters detected.
            </div>
          ) : (
            <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
              {groups.map((g) => {
                const isSelected = selectedGroup?.group_id === g.group_id;
                return (
                  <div
                    key={g.group_id}
                    onClick={() => setSelectedGroup(isSelected ? null : g)}
                    className={`border rounded-md p-3 text-xs font-mono cursor-pointer transition-all ${
                      isSelected
                        ? "bg-amber/10 border-amber text-amber ring-1 ring-amber/50"
                        : "bg-panel2 border-line text-ink hover:border-teal/50 hover:bg-panel2/80"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold text-sm leading-tight text-ink">{g.name}</span>
                      <span className="shrink-0 px-2 py-0.5 rounded bg-crit/10 text-crit border border-crit/40 text-[10px] font-bold">
                        Risk: {g.group_risk_score}
                      </span>
                    </div>
                    <p className="text-muted text-[11px] mb-1">
                      👥 Members: {g.member_count} &middot; 📂 Cases: {g.linked_cases}
                    </p>
                    <div className="text-[10px] text-teal font-bold flex items-center justify-between pt-1 border-t border-line/40">
                      <span>{isSelected ? "🎯 Centroid Focused" : "Click to zoom cluster"}</span>
                      <span>&rarr;</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Section 2: Selected Node Inspector */}
        <div className="border-t border-line pt-4 flex-1">
          <h4 className="font-display text-base text-teal mb-2 flex items-center justify-between">
            <span>Node Details Inspector</span>
            {selected && (
              <button
                onClick={() => setSelected(null)}
                className="text-xs text-muted hover:text-ink font-mono"
              >
                Clear ✕
              </button>
            )}
          </h4>

          {selected ? (
            <div className="bg-panel2 border border-line rounded-lg p-3 text-xs font-mono space-y-2.5">
              <div className="flex items-center justify-between border-b border-line/60 pb-2">
                <span className="text-teal font-bold text-sm tracking-wide">{selected.label}</span>
                <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-teal/10 text-teal border border-teal/30">
                  {selected.type}
                </span>
              </div>

              {selected.sublabel && (
                <p className="text-muted leading-relaxed">
                  <strong>Description/Role:</strong> {selected.sublabel}
                </p>
              )}

              {selected.phone && (
                <p className="text-crit font-semibold flex items-center gap-1">
                  📞 Phone: {selected.phone}
                </p>
              )}

              {selected.severity && (
                <p className="text-amber font-semibold uppercase flex items-center gap-1">
                  ⚠️ Severity: {selected.severity}
                </p>
              )}

              {selected.district && (
                <p className="text-muted flex items-center gap-1">
                  🏢 District: {selected.district}
                </p>
              )}

              {/* Navigation buttons */}
              <div className="pt-2 border-t border-line space-y-1.5">
                {selected.type === "case" && selected.ref_id && (
                  <button
                    onClick={() => navigate(`/cases/${selected.ref_id}`)}
                    className="w-full text-center py-1.5 rounded bg-amber text-base font-bold text-xs hover:bg-amber/90 transition"
                  >
                    📂 Open Case File &rarr;
                  </button>
                )}

                {selected.type === "person" && (
                  <button
                    onClick={() => navigate(`/offenders`)}
                    className="w-full text-center py-1.5 rounded bg-panel border border-teal/40 text-teal font-semibold text-xs hover:bg-teal/10 transition"
                  >
                    👤 View Offender Directory &rarr;
                  </button>
                )}

                {selected.type === "account" && selected.ref_id && (
                  <button
                    onClick={() => navigate(`/cases`)}
                    className="w-full text-center py-1.5 rounded bg-panel border border-violet/40 text-violet font-semibold text-xs hover:bg-violet/10 transition"
                  >
                    💳 Financial Trail View &rarr;
                  </button>
                )}
              </div>
            </div>
          ) : (
            <div className="p-4 border border-line/60 bg-panel2/30 rounded-lg text-center text-muted font-mono text-xs">
              👈 Click any node in the 3D graph or search above to inspect full details.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
