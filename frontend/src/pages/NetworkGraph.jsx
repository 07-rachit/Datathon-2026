import { useEffect, useRef, useState, useCallback } from "react";
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
    geo   = new THREE.BoxGeometry(3, 3, 3);
    color = SEVERITY_HEX[node.severity] ?? COL.teal;
  } else if (node.type === "account") {
    geo   = new THREE.OctahedronGeometry(1.8);
    color = COL.violet;
  } else {
    geo   = new THREE.SphereGeometry(1.4, 16, 12);
    color = COL.slate;
  }
  const mat  = new THREE.MeshStandardMaterial({
    color, emissive: color, emissiveIntensity: 0.4,
    roughness: 0.55, metalness: 0.3,
  });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.userData = { nodeData: node, baseColor: color };
  return mesh;
}

/* ─── Label sprite ─────────────────────────────────────────────────────────── */
function makeLabel(text, hexColor) {
  const r = (hexColor >> 16 & 0xff).toString(16).padStart(2,"0");
  const g = (hexColor >> 8  & 0xff).toString(16).padStart(2,"0");
  const b = (hexColor       & 0xff).toString(16).padStart(2,"0");
  const cssCol = `#${r}${g}${b}`;

  const canvas = document.createElement("canvas");
  const ctx    = canvas.getContext("2d");
  const fs     = 24;
  ctx.font     = `${fs}px monospace`;
  const w      = Math.ceil(ctx.measureText(text.slice(0,22)).width) + 14;
  const h      = fs + 10;
  canvas.width = w; canvas.height = h;
  ctx.font        = `${fs}px monospace`;
  ctx.fillStyle   = cssCol;
  ctx.textBaseline = "middle";
  ctx.fillText(text.slice(0,22), 7, h / 2);

  const tex  = new THREE.CanvasTexture(canvas);
  tex.minFilter = THREE.LinearFilter;
  const spr  = new THREE.Sprite(
    new THREE.SpriteMaterial({ map: tex, transparent: true, opacity: 0.85, depthTest: false })
  );
  spr.scale.set(w / 26, h / 26, 1);
  return spr;
}

/* ─── Edge line ────────────────────────────────────────────────────────────── */
function makeEdge(kind) {
  const pts  = [new THREE.Vector3(), new THREE.Vector3()];
  const geo  = new THREE.BufferGeometry().setFromPoints(pts);
  let mat;
  if (kind === "shared_phone") {
    mat = new THREE.LineDashedMaterial({ color: COL.crit, transparent: true, opacity: 0.75, dashSize: 2, gapSize: 1.2 });
  } else if (kind === "financial_transfer") {
    mat = new THREE.LineBasicMaterial({ color: COL.amber, transparent: true, opacity: 0.6 });
  } else if (kind === "owns_account") {
    mat = new THREE.LineBasicMaterial({ color: COL.violet, transparent: true, opacity: 0.4 });
  } else {
    mat = new THREE.LineBasicMaterial({ color: COL.teal, transparent: true, opacity: 0.2 });
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
    pos[i*3]   = r * Math.sin(phi) * Math.cos(theta);
    pos[i*3+1] = r * Math.sin(phi) * Math.sin(theta);
    pos[i*3+2] = r * Math.cos(phi);
    const t = Math.random();
    if (t < 0.40) { col[i*3]=0.25; col[i*3+1]=0.84; col[i*3+2]=0.76; }      // teal
    else if (t < 0.55) { col[i*3]=0.94; col[i*3+1]=0.63; col[i*3+2]=0.01; } // amber
    else { const v=0.5+Math.random()*0.4; col[i*3]=v; col[i*3+1]=v+0.05; col[i*3+2]=v+0.12; }
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
  const canvasRef    = useRef(null);   // ← explicit <canvas> in JSX
  const navigate     = useNavigate();

  const [graph, setGraph]         = useState({ nodes: [], edges: [], recurring_links: 0 });
  const [groups, setGroups]       = useState([]);
  const [selectedGroup, setSelectedGroup] = useState(null);
  const [error, setError]         = useState("");
  const [selected, setSelected]   = useState(null);
  const [hovering, setHovering]   = useState(false);
  const [loading, setLoading]     = useState(true);

  // Three.js objects that outlive renders
  const threeRef = useRef({
    scene: null, camera: null, renderer: null, controls: null,
    meshMap: new Map(), labelMap: new Map(), edgeObjs: [],
    clusterSphere: null, starfield: null, animId: null,
    sim: null, cameraTarget: null, nodeById: new Map(),
  });

  /* ── Data fetch ─────────────────────────────────────────────────────────── */
  useEffect(() => {
    Promise.all([
      fetchNetworkGraph({ include_financial: true }),
      fetchNetworkGroups().catch(() => []),
    ]).then(([g, grps]) => {
      setGraph(g);
      setGroups(grps);
      setLoading(false);
    }).catch(() => {
      setError("Could not load the network graph. Is the API running?");
      setLoading(false);
    });
  }, []);

  /* ── Build / rebuild Three.js scene whenever graph changes ─────────────── */
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !graph.nodes.length) return;

    const T = threeRef.current;

    // ── Teardown old scene if any ──
    if (T.animId) cancelAnimationFrame(T.animId);
    if (T.sim)    T.sim.stop();
    if (T.controls) T.controls.dispose();
    if (T.renderer) T.renderer.dispose();
    if (T.scene) T.scene.clear();

    // ── Scene ──
    const scene    = new THREE.Scene();
    scene.background = new THREE.Color(COL.bg);
    scene.fog        = new THREE.FogExp2(COL.bg, 0.0025);
    T.scene          = scene;

    // ── Camera ──
    const w = canvas.clientWidth  || canvas.offsetWidth  || 800;
    const h = canvas.clientHeight || canvas.offsetHeight || 600;
    const camera = new THREE.PerspectiveCamera(55, w / h, 0.1, 1200);
    camera.position.set(0, 30, 110);
    T.camera = camera;

    // ── Renderer — pass the existing <canvas> element ──
    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
    renderer.setSize(w, h, false);   // false = don't override CSS size
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping         = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.1;
    T.renderer = renderer;

    // ── OrbitControls ──
    const controls = new OrbitControls(camera, canvas);
    controls.enableDamping    = true;
    controls.dampingFactor    = 0.08;
    controls.minDistance      = 15;
    controls.maxDistance      = 500;
    controls.autoRotate       = true;
    controls.autoRotateSpeed  = 0.2;
    T.controls = controls;

    // ── Lights ──
    scene.add(new THREE.AmbientLight(0xffffff, 0.6));
    const pl1 = new THREE.PointLight(COL.teal,   1.2, 400); pl1.position.set( 60, 80,  60); scene.add(pl1);
    const pl2 = new THREE.PointLight(COL.amber,  0.6, 300); pl2.position.set(-50,-30, -50); scene.add(pl2);
    const pl3 = new THREE.PointLight(COL.violet, 0.4, 250); pl3.position.set(  0, 60, -80); scene.add(pl3);

    // ── Starfield ──
    const stars = makeStarfield();
    scene.add(stars);
    T.starfield = stars;

    // ── Grid floor ──
    const grid = new THREE.GridHelper(300, 40, 0x1a2433, 0x0f1520);
    grid.position.y = -55;
    grid.material.transparent = true;
    grid.material.opacity = 0.12;
    scene.add(grid);

    // ── Deduplicate nodes ──
    const seen = new Set();
    const simNodes = [];
    for (const n of graph.nodes) {
      if (!seen.has(n.id)) { seen.add(n.id); simNodes.push({ ...n, x:0, y:0, z:0 }); }
    }
    const nodeById = new Map(simNodes.map(n => [n.id, n]));
    T.nodeById = nodeById;

    const simLinks = graph.edges
      .filter(e => nodeById.has(e.source) && nodeById.has(e.target))
      .map(e => ({ ...e }));

    // ── Meshes ──
    const meshMap  = new Map();
    const labelMap = new Map();
    for (const node of simNodes) {
      const mesh  = makeMesh(node);
      scene.add(mesh);
      meshMap.set(node.id, mesh);

      const lc  = node.type === "case" ? COL.teal : node.type === "account" ? COL.violet : COL.slate;
      const lbl = makeLabel(node.label, lc);
      scene.add(lbl);
      labelMap.set(node.id, lbl);
    }
    T.meshMap  = meshMap;
    T.labelMap = labelMap;

    // ── Edges ──
    const edgeObjs = [];
    for (const edge of simLinks) {
      const line = makeEdge(edge.kind);
      scene.add(line);
      edgeObjs.push({ line, edge });
    }
    T.edgeObjs = edgeObjs;

    // ── Force simulation (3D) ──
    const sim = forceSimulation(simNodes, 3)
      .force("link",    forceLink(simLinks).id(d => d.id).distance(l => l.kind === "shared_phone" ? 30 : 22).strength(0.5))
      .force("charge",  forceManyBody().strength(-80))
      .force("center",  forceCenter(0, 0, 0))
      .force("collide", forceCollide().radius(5).strength(0.6))
      .alpha(1)
      .alphaDecay(0.018)
      .velocityDecay(0.4);
    T.sim = sim;

    // ── Resize observer ──
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

    // ── Animate ──
    function animate() {
      T.animId = requestAnimationFrame(animate);

      if (sim.alpha() > 0.001) sim.tick();

      // Update node positions
      for (const node of simNodes) {
        const mesh = meshMap.get(node.id);
        if (mesh) {
          mesh.position.set(node.x ?? 0, node.y ?? 0, node.z ?? 0);
          if (node.type === "case")    { mesh.rotation.y += 0.004; mesh.rotation.x += 0.001; }
          if (node.type === "account") { mesh.rotation.y += 0.008; }
        }
        const lbl = labelMap.get(node.id);
        if (lbl) lbl.position.set((node.x ?? 0) + 2.8, (node.y ?? 0) + 2.8, node.z ?? 0);
      }

      // Update edge geometry
      for (const { line, edge } of edgeObjs) {
        const src = typeof edge.source === "object" ? edge.source : nodeById.get(edge.source);
        const tgt = typeof edge.target === "object" ? edge.target : nodeById.get(edge.target);
        if (src && tgt) {
          const arr = line.geometry.attributes.position.array;
          arr[0]=src.x??0; arr[1]=src.y??0; arr[2]=src.z??0;
          arr[3]=tgt.x??0; arr[4]=tgt.y??0; arr[5]=tgt.z??0;
          line.geometry.attributes.position.needsUpdate = true;
          if (edge.kind === "shared_phone") line.computeLineDistances();
        }
      }

      // Rotate starfield
      if (T.starfield) { T.starfield.rotation.y += 0.00009; T.starfield.rotation.x += 0.00003; }

      // Camera fly-to for group highlight
      if (T.cameraTarget) {
        camera.position.lerp(T.cameraTarget.pos,    0.04);
        controls.target.lerp(T.cameraTarget.lookAt, 0.04);
        if (camera.position.distanceTo(T.cameraTarget.pos) < 2) T.cameraTarget = null;
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

  /* ── Group highlighting (no scene rebuild needed) ───────────────────────── */
  useEffect(() => {
    const T     = threeRef.current;
    const scene = T.scene;
    if (!scene) return;

    // Remove old cluster sphere
    if (T.clusterSphere) {
      scene.remove(T.clusterSphere);
      T.clusterSphere.geometry.dispose();
      T.clusterSphere.material.dispose();
      T.clusterSphere = null;
    }

    const memberIds = selectedGroup
      ? new Set(selectedGroup.members.map(m => m.person_node_id))
      : null;

    // Reset / highlight node materials
    for (const [id, mesh] of T.meshMap.entries()) {
      const base = mesh.userData.baseColor;
      if (memberIds && memberIds.has(id)) {
        mesh.material.color.setHex(COL.amber);
        mesh.material.emissive.setHex(COL.crit);
        mesh.material.emissiveIntensity = 0.8;
        mesh.scale.setScalar(1.5);
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
        positions.forEach(p => centroid.add(p));
        centroid.divideScalar(positions.length);

        let maxDist = 8;
        positions.forEach(p => { const d = p.distanceTo(centroid); if (d > maxDist) maxDist = d; });
        const radius = maxDist + 7;

        const sphere = new THREE.Mesh(
          new THREE.SphereGeometry(radius, 24, 16),
          new THREE.MeshBasicMaterial({ color: COL.amber, transparent: true, opacity: 0.07, side: THREE.DoubleSide, depthWrite: false })
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

  /* ── Click / hover via raycaster ────────────────────────────────────────── */
  const handleClick = useCallback((e) => {
    const T = threeRef.current;
    if (!T.renderer || !T.camera) return;
    const rect  = canvasRef.current.getBoundingClientRect();
    const mouse = new THREE.Vector2(
      ((e.clientX - rect.left) / rect.width)  *  2 - 1,
      ((e.clientY - rect.top)  / rect.height) * -2 + 1,
    );
    const rc = new THREE.Raycaster();
    rc.setFromCamera(mouse, T.camera);
    const hits = rc.intersectObjects([...T.meshMap.values()], false);
    if (hits.length) {
      const nd = hits[0].object.userData.nodeData;
      if (nd.type === "case") navigate(`/cases/${nd.ref_id}`);
      else setSelected(nd);
    }
  }, [navigate]);

  const handleMouseMove = useCallback((e) => {
    const T = threeRef.current;
    if (!T.renderer || !T.camera) return;
    const rect  = canvasRef.current.getBoundingClientRect();
    const mouse = new THREE.Vector2(
      ((e.clientX - rect.left) / rect.width)  *  2 - 1,
      ((e.clientY - rect.top)  / rect.height) * -2 + 1,
    );
    const rc = new THREE.Raycaster();
    rc.setFromCamera(mouse, T.camera);
    setHovering(rc.intersectObjects([...T.meshMap.values()], false).length > 0);
  }, []);

  /* ─────────────────────────────────────────────────────────────────────── */
  return (
    <div className="flex h-screen bg-base text-ink overflow-hidden">
      {/* ── Main graph area ── */}
      <div className="flex-1 relative flex flex-col min-w-0">

        {/* Header + Legend */}
        <div className="shrink-0 px-4 py-3 border-b border-line bg-panel flex items-center justify-between gap-4">
          <div>
            <h2 className="font-display text-xl leading-tight">Criminal &amp; Financial Network Graph</h2>
            <p className="text-muted text-[11px] font-mono">
              3D force-directed &middot; Drag: orbit &middot; Scroll: zoom &middot; Click node for details
            </p>
          </div>
          <div className="flex items-center gap-3 text-[11px] font-mono flex-wrap justify-end">
            <span className="flex items-center gap-1.5"><span className="inline-block w-2.5 h-2.5 bg-teal"  style={{clipPath:"inset(0)"}} /> Case</span>
            <span className="flex items-center gap-1.5"><span className="inline-block w-2.5 h-2.5 rounded-full bg-[#5B6B7C]" /> Person</span>
            <span className="flex items-center gap-1.5"><span className="inline-block w-2.5 h-2.5 bg-[#8B5CF6]" style={{clipPath:"polygon(50% 0%,100% 50%,50% 100%,0% 50%)"}} /> Account</span>
            <span className="flex items-center gap-1.5 text-crit"><span className="inline-block w-4 border-t-2 border-dashed border-crit" /> Shared Phone</span>
            <span className="flex items-center gap-1.5 text-amber"><span className="inline-block w-4 border-t-2 border-amber" /> Financial</span>
            <span className="flex items-center gap-1.5"><span className="inline-block w-2.5 h-2.5 rounded-full bg-amber" /> Gang Member</span>
          </div>
        </div>

        {/* Canvas fills the rest */}
        <div className="flex-1 relative" style={{ background: "#0B0F17" }}>
          {error && (
            <div className="absolute top-4 left-4 z-10 text-crit text-xs font-mono bg-crit/10 border border-crit/40 px-3 py-2 rounded">
              {error}
            </div>
          )}
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center z-10">
              <span className="text-teal text-sm font-mono animate-pulse">Loading graph…</span>
            </div>
          )}
          {/* ← Explicit canvas element; Three.js gets this ref directly */}
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
          {/* Subtle radial glow overlay */}
          <div
            className="absolute inset-0 pointer-events-none"
            style={{ background: "radial-gradient(ellipse at 50% 40%, rgba(63,214,193,0.035) 0%, transparent 55%)" }}
          />
        </div>
      </div>

      {/* ── Sidebar ── */}
      <div className="w-72 shrink-0 border-l border-line bg-panel p-4 flex flex-col gap-5 overflow-y-auto">
        <div>
          <h3 className="font-display text-lg mb-1">Detected Syndicates ({groups.length})</h3>
          <p className="text-muted text-[11px] font-mono mb-3">
            Connected clusters sharing multiple link vectors
          </p>
          {groups.length === 0 ? (
            <p className="text-muted text-xs font-mono">No qualifying gang clusters detected.</p>
          ) : (
            <div className="space-y-2">
              {groups.map((g) => (
                <div
                  key={g.group_id}
                  onClick={() => setSelectedGroup(selectedGroup?.group_id === g.group_id ? null : g)}
                  className={`border rounded p-3 text-xs font-mono cursor-pointer transition-colors ${
                    selectedGroup?.group_id === g.group_id
                      ? "bg-amber/10 border-amber text-amber"
                      : "bg-panel2 border-line text-ink hover:border-teal"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold leading-tight">{g.name}</span>
                    <span className="ml-2 shrink-0 px-1.5 py-0.5 rounded bg-crit/10 text-crit border border-crit/40 text-[10px]">
                      Risk: {g.group_risk_score}
                    </span>
                  </div>
                  <p className="text-muted text-[11px]">
                    Members: {g.member_count} &middot; Cases: {g.linked_cases}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>

        {selected && (
          <div className="border-t border-line pt-4">
            <h4 className="font-display text-base text-teal mb-2">Node Details</h4>
            <div className="bg-panel2 border border-line rounded p-3 text-xs font-mono space-y-1">
              <p className="text-ink font-semibold">{selected.label}</p>
              <p className="text-muted">{selected.sublabel}</p>
              {selected.phone && <p className="text-teal">{selected.phone}</p>}
              <p className="text-muted mt-1 text-[10px] uppercase tracking-wider">
                {selected.type === "account" ? "Financial Account" : "Person of Interest"}
              </p>
              {selected.type !== "case" && selected.ref_id && (
                <button
                  onClick={() => navigate(`/offenders`)}
                  className="mt-2 w-full text-center py-1 rounded border border-teal/40 text-teal text-[10px] hover:bg-teal/10 transition-colors"
                >
                  View Offender Profile →
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
