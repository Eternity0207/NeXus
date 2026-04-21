import { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../api';
import { useRepo } from '../context/useRepo';
import { useToast } from '../components/useToast';
import CopyButton from '../components/CopyButton';

// ── Styling tokens (kept in JS so canvas can use them directly) ──
const NODE_COLORS = {
  File:     '#6366f1',
  Class:    '#06b6d4',
  Function: '#10b981',
  Module:   '#f59e0b',
  Method:   '#a78bfa',
  Default:  '#94a3b8',
};

const EDGE_COLORS = {
  IMPORTS: 'rgba(99, 102, 241, 0.55)',
  CONTAINS: 'rgba(6, 182, 212, 0.45)',
  CALLS:    'rgba(16, 185, 129, 0.55)',
  EXTENDS:  'rgba(245, 158, 11, 0.55)',
  DEFAULT:  'rgba(148, 163, 184, 0.3)',
};

const NODE_TYPES = ['File', 'Class', 'Function', 'Module'];

// Node radius by type (canvas pixels).
const nodeRadius = (type) => {
  switch (type) {
    case 'File': return 14;
    case 'Class': return 11;
    case 'Module': return 10;
    default: return 8;
  }
};

// ── Force simulation ────────────────────────────────────────────
// Light-weight force-directed layout: O(n²) repulsion + spring edges.
// Good enough for graphs up to a few hundred nodes without adding deps.
function runSimulation(nodes, edges, { iterations = 260, width = 1100, height = 700 } = {}) {
  if (!nodes.length) return;

  const idToNode = new Map(nodes.map((n) => [n.id, n]));
  const cx = width / 2;
  const cy = height / 2;
  const k = Math.sqrt((width * height) / Math.max(nodes.length, 1)) * 0.75; // ideal distance
  const springLen = 55;
  const springStrength = 0.04;
  const repelStrength = k * k * 0.12;
  const centerStrength = 0.0025;
  const damping = 0.86;

  nodes.forEach((n, i) => {
    if (typeof n.x !== 'number' || typeof n.y !== 'number') {
      const a = (i / nodes.length) * Math.PI * 2;
      const r = 160 + Math.random() * 140;
      n.x = cx + Math.cos(a) * r;
      n.y = cy + Math.sin(a) * r;
    }
    n.vx = 0; n.vy = 0;
  });

  for (let step = 0; step < iterations; step++) {
    // Repulsion
    for (let i = 0; i < nodes.length; i++) {
      const a = nodes[i];
      for (let j = i + 1; j < nodes.length; j++) {
        const b = nodes[j];
        const dx = a.x - b.x;
        const dy = a.y - b.y;
        const d2 = dx * dx + dy * dy || 0.01;
        const d = Math.sqrt(d2);
        const f = repelStrength / d2;
        const fx = (dx / d) * f;
        const fy = (dy / d) * f;
        a.vx += fx; a.vy += fy;
        b.vx -= fx; b.vy -= fy;
      }
    }

    // Springs
    for (const e of edges) {
      const a = idToNode.get(e.source);
      const b = idToNode.get(e.target);
      if (!a || !b) continue;
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const d = Math.sqrt(dx * dx + dy * dy) || 0.01;
      const f = (d - springLen) * springStrength;
      const fx = (dx / d) * f;
      const fy = (dy / d) * f;
      a.vx += fx; a.vy += fy;
      b.vx -= fx; b.vy -= fy;
    }

    // Center pull + integrate
    for (const n of nodes) {
      n.vx += (cx - n.x) * centerStrength;
      n.vy += (cy - n.y) * centerStrength;
      n.vx *= damping;
      n.vy *= damping;
      n.x += n.vx;
      n.y += n.vy;
    }
  }
}

export default function Graph() {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);

  const toast = useToast();
  const { activeRepoId, setActiveRepoId } = useRepo();
  const [searchParams, setSearchParams] = useSearchParams();

  // ── Query input ──
  const urlRepo = searchParams.get('repo_id') || '';
  const [repoId, setRepoId] = useState(urlRepo || activeRepoId || '');
  const [depth, setDepth] = useState(Number(searchParams.get('depth') || 2));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // ── Data ──
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [stats, setStats] = useState({ nodes: 0, edges: 0 });

  // ── View state ──
  const [view, setView] = useState({ scale: 1, tx: 0, ty: 0 });
  const [selectedId, setSelectedId] = useState(null);
  const [hoverId, setHoverId] = useState(null);
  const [search, setSearch] = useState('');
  const [visibleTypes, setVisibleTypes] = useState(new Set(NODE_TYPES));

  // ── Interaction refs ──
  const panRef = useRef(null);     // { startX, startY, tx0, ty0 }
  const dragRef = useRef(null);    // { nodeId, offsetX, offsetY }
  const rafRef = useRef(null);

  // Sync with shared context
  useEffect(() => {
    if (urlRepo && urlRepo !== repoId) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setRepoId(urlRepo);
    } else if (!urlRepo && activeRepoId && !repoId) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setRepoId(activeRepoId);
    }
  }, [urlRepo, activeRepoId]); // eslint-disable-line react-hooks/exhaustive-deps

  const fitToView = useCallback((ns = nodes) => {
    const container = containerRef.current;
    if (!container || !ns.length) return;
    const w = container.clientWidth;
    const h = container.clientHeight;
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const n of ns) {
      if (n.x < minX) minX = n.x;
      if (n.y < minY) minY = n.y;
      if (n.x > maxX) maxX = n.x;
      if (n.y > maxY) maxY = n.y;
    }
    const pad = 80;
    const worldW = (maxX - minX) + pad * 2;
    const worldH = (maxY - minY) + pad * 2;
    const scale = Math.min(w / worldW, h / worldH, 1.6);
    const tx = w / 2 - ((minX + maxX) / 2) * scale;
    const ty = h / 2 - ((minY + maxY) / 2) * scale;
    setView({ scale, tx, ty });
  }, [nodes]);

  const fetchGraph = useCallback(async (id = repoId, d = depth) => {
    const target = (id || '').trim();
    if (!target) {
      setError('Enter a repository ID (or pick one from the Dashboard).');
      return;
    }
    setError('');
    setLoading(true);
    try {
      const data = await api.getGraph(target, d);
      const rawNodes = (data?.nodes || []).map((n) => {
        const type = (n.labels || [])[0] || 'File';
        const label = n.properties?.name || n.properties?.path || `Node ${n.id}`;
        return {
          id: n.id,
          label,
          type,
          path: n.properties?.path || '',
          properties: n.properties || {},
        };
      });
      const rawEdges = (data?.edges || []).map((e) => ({
        source: e.source,
        target: e.target,
        type: e.relationship || e.type || 'DEFAULT',
      }));
      runSimulation(rawNodes, rawEdges, {
        width: containerRef.current?.clientWidth || 1100,
        height: containerRef.current?.clientHeight || 700,
      });
      setNodes(rawNodes);
      setEdges(rawEdges);
      setStats({ nodes: data?.node_count ?? rawNodes.length, edges: data?.edge_count ?? rawEdges.length });
      setSelectedId(null);
      setActiveRepoId(target);
      setSearchParams((p) => {
        p.set('repo_id', target);
        p.set('depth', String(d));
        return p;
      }, { replace: true });
      // Auto-fit after layout
      requestAnimationFrame(() => fitToView(rawNodes));
      if (rawNodes.length === 0) {
        toast.info('Graph is empty for this repo. Ingest + parsing may still be in progress.');
      }
    } catch (err) {
      setError(err.message || 'Failed to load graph');
    }
    setLoading(false);
  }, [repoId, depth, setActiveRepoId, setSearchParams, toast, fitToView]);

  // ── Draw on canvas ───────────────────────────────────────────
  const idToNode = useMemo(() => new Map(nodes.map((n) => [n.id, n])), [nodes]);
  const matchesSearch = useCallback((node) => {
    if (!search.trim()) return true;
    const q = search.trim().toLowerCase();
    return (
      (node.label || '').toLowerCase().includes(q) ||
      (node.path || '').toLowerCase().includes(q)
    );
  }, [search]);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const dpr = window.devicePixelRatio || 1;
    const w = container.clientWidth;
    const h = container.clientHeight;

    if (canvas.width !== w * dpr || canvas.height !== h * dpr) {
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
    }

    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    // Background grid for context during pan/zoom
    const grid = 48 * view.scale;
    if (grid >= 14) {
      ctx.strokeStyle = 'rgba(255,255,255,0.03)';
      ctx.lineWidth = 1;
      const offX = ((view.tx % grid) + grid) % grid;
      const offY = ((view.ty % grid) + grid) % grid;
      ctx.beginPath();
      for (let x = offX; x < w; x += grid) { ctx.moveTo(x, 0); ctx.lineTo(x, h); }
      for (let y = offY; y < h; y += grid) { ctx.moveTo(0, y); ctx.lineTo(w, y); }
      ctx.stroke();
    }

    if (!nodes.length) {
      ctx.fillStyle = '#64748b';
      ctx.font = '500 14px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('Load a repository above to visualize its dependency graph.', w / 2, h / 2);
      return;
    }

    // Apply view transform for scene
    ctx.save();
    ctx.translate(view.tx, view.ty);
    ctx.scale(view.scale, view.scale);

    const connected = new Set();
    if (selectedId != null) {
      for (const e of edges) {
        if (e.source === selectedId) connected.add(e.target);
        if (e.target === selectedId) connected.add(e.source);
      }
      connected.add(selectedId);
    }

    // Edges
    for (const e of edges) {
      const s = idToNode.get(e.source);
      const t = idToNode.get(e.target);
      if (!s || !t) continue;
      if (!visibleTypes.has(s.type) || !visibleTypes.has(t.type)) continue;

      const highlighted = selectedId != null && (e.source === selectedId || e.target === selectedId);
      const dimmed = selectedId != null && !highlighted;

      ctx.strokeStyle = highlighted
        ? (EDGE_COLORS[e.type] || EDGE_COLORS.DEFAULT).replace(/[\d.]+\)$/, '0.95)')
        : dimmed
        ? 'rgba(148,163,184,0.08)'
        : (EDGE_COLORS[e.type] || EDGE_COLORS.DEFAULT);
      ctx.lineWidth = highlighted ? 1.8 : 1;
      ctx.beginPath();
      ctx.moveTo(s.x, s.y);
      ctx.lineTo(t.x, t.y);
      ctx.stroke();

      // Arrowhead at midpoint for direction
      if (!dimmed) {
        const midX = (s.x + t.x) / 2;
        const midY = (s.y + t.y) / 2;
        const angle = Math.atan2(t.y - s.y, t.x - s.x);
        const aLen = 6;
        ctx.beginPath();
        ctx.moveTo(midX, midY);
        ctx.lineTo(midX - aLen * Math.cos(angle - 0.4), midY - aLen * Math.sin(angle - 0.4));
        ctx.moveTo(midX, midY);
        ctx.lineTo(midX - aLen * Math.cos(angle + 0.4), midY - aLen * Math.sin(angle + 0.4));
        ctx.stroke();
      }
    }

    // Nodes
    for (const n of nodes) {
      if (!visibleTypes.has(n.type)) continue;
      const color = NODE_COLORS[n.type] || NODE_COLORS.Default;
      const r = nodeRadius(n.type);
      const isSelected = selectedId === n.id;
      const isConnected = connected.has(n.id);
      const isHover = hoverId === n.id;
      const matches = matchesSearch(n);
      const dimmed = (!matches) || (selectedId != null && !isConnected);

      if (isSelected || isHover) {
        ctx.beginPath();
        ctx.arc(n.x, n.y, r + 6, 0, Math.PI * 2);
        ctx.fillStyle = color + '33';
        ctx.fill();
      }

      ctx.globalAlpha = dimmed ? 0.22 : 1;

      ctx.beginPath();
      ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
      ctx.fillStyle = isSelected ? color : color + '55';
      ctx.fill();
      ctx.strokeStyle = color;
      ctx.lineWidth = isSelected ? 2.4 : 1.4;
      ctx.stroke();

      // Label for larger zooms or selection
      if (view.scale >= 0.7 || isSelected || isHover) {
        ctx.fillStyle = '#e2e8f0';
        ctx.font = `500 ${11 / Math.max(view.scale, 0.85)}px Inter, sans-serif`;
        ctx.textAlign = 'center';
        const text = (n.label || '').length > 22 ? n.label.slice(0, 20) + '…' : n.label;
        ctx.fillText(text, n.x, n.y + r + 12 / Math.max(view.scale, 0.85));
      }

      ctx.globalAlpha = 1;
    }

    ctx.restore();

    // ── Minimap overlay ──
    if (nodes.length > 0) {
      const mm = { x: w - 160, y: h - 120, w: 150, h: 110 };
      ctx.save();
      ctx.fillStyle = 'rgba(10,14,26,0.78)';
      ctx.strokeStyle = 'rgba(255,255,255,0.08)';
      ctx.lineWidth = 1;
      ctx.fillRect(mm.x, mm.y, mm.w, mm.h);
      ctx.strokeRect(mm.x, mm.y, mm.w, mm.h);

      // Compute world bounds
      let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
      for (const n of nodes) {
        if (n.x < minX) minX = n.x;
        if (n.y < minY) minY = n.y;
        if (n.x > maxX) maxX = n.x;
        if (n.y > maxY) maxY = n.y;
      }
      const pad = 30;
      minX -= pad; minY -= pad; maxX += pad; maxY += pad;
      const worldW = maxX - minX || 1;
      const worldH = maxY - minY || 1;
      const scale = Math.min(mm.w / worldW, mm.h / worldH);
      const toMM = (x, y) => ({ mx: mm.x + (x - minX) * scale, my: mm.y + (y - minY) * scale });

      for (const n of nodes) {
        if (!visibleTypes.has(n.type)) continue;
        const { mx, my } = toMM(n.x, n.y);
        ctx.fillStyle = NODE_COLORS[n.type] || NODE_COLORS.Default;
        ctx.globalAlpha = 0.8;
        ctx.fillRect(mx - 1, my - 1, 2, 2);
      }
      ctx.globalAlpha = 1;

      // Current viewport rect in minimap
      const viewLeft = (-view.tx) / view.scale;
      const viewTop = (-view.ty) / view.scale;
      const viewRight = viewLeft + w / view.scale;
      const viewBottom = viewTop + h / view.scale;
      const tl = toMM(viewLeft, viewTop);
      const br = toMM(viewRight, viewBottom);
      ctx.strokeStyle = 'rgba(99,102,241,0.9)';
      ctx.lineWidth = 1;
      ctx.strokeRect(tl.mx, tl.my, br.mx - tl.mx, br.my - tl.my);
      ctx.restore();
    }
  }, [nodes, edges, idToNode, view, selectedId, hoverId, visibleTypes, matchesSearch]);

  // Schedule repaint any time drawable state changes
  useEffect(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(draw);
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current); };
  }, [draw]);

  // Redraw on resize
  useEffect(() => {
    const onResize = () => draw();
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [draw]);

  // ── Coordinate helpers ──
  const screenToWorld = (sx, sy) => ({
    x: (sx - view.tx) / view.scale,
    y: (sy - view.ty) / view.scale,
  });
  const mousePos = (e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  };
  const nodeAt = (sx, sy) => {
    const { x, y } = screenToWorld(sx, sy);
    for (let i = nodes.length - 1; i >= 0; i--) {
      const n = nodes[i];
      if (!visibleTypes.has(n.type)) continue;
      const r = nodeRadius(n.type) + 4;
      if ((n.x - x) ** 2 + (n.y - y) ** 2 <= r * r) return n;
    }
    return null;
  };

  // ── Interactions ──
  const onWheel = (e) => {
    e.preventDefault();
    const { x: sx, y: sy } = mousePos(e);
    const factor = Math.exp(-e.deltaY * 0.0016);
    const newScale = Math.min(3.5, Math.max(0.18, view.scale * factor));
    const worldX = (sx - view.tx) / view.scale;
    const worldY = (sy - view.ty) / view.scale;
    const newTx = sx - worldX * newScale;
    const newTy = sy - worldY * newScale;
    setView({ scale: newScale, tx: newTx, ty: newTy });
  };

  const onMouseDown = (e) => {
    const { x: sx, y: sy } = mousePos(e);
    const hit = nodeAt(sx, sy);
    if (hit && !e.shiftKey) {
      const { x, y } = screenToWorld(sx, sy);
      dragRef.current = { nodeId: hit.id, offsetX: hit.x - x, offsetY: hit.y - y, moved: false };
      setSelectedId(hit.id);
    } else {
      panRef.current = { startX: sx, startY: sy, tx0: view.tx, ty0: view.ty, moved: false };
    }
  };

  const onMouseMove = (e) => {
    const { x: sx, y: sy } = mousePos(e);

    if (dragRef.current) {
      const { nodeId, offsetX, offsetY } = dragRef.current;
      const { x, y } = screenToWorld(sx, sy);
      const node = idToNode.get(nodeId);
      if (node) {
        node.x = x + offsetX;
        node.y = y + offsetY;
        dragRef.current.moved = true;
        setNodes((ns) => ns.slice());
      }
      return;
    }

    if (panRef.current) {
      const dx = sx - panRef.current.startX;
      const dy = sy - panRef.current.startY;
      if (Math.abs(dx) + Math.abs(dy) > 2) panRef.current.moved = true;
      setView((v) => ({ ...v, tx: panRef.current.tx0 + dx, ty: panRef.current.ty0 + dy }));
      return;
    }

    const hit = nodeAt(sx, sy);
    setHoverId(hit ? hit.id : null);
    canvasRef.current.style.cursor = hit ? 'grab' : 'default';
  };

  const onMouseUp = (e) => {
    const { x: sx, y: sy } = mousePos(e);
    if (panRef.current) {
      if (!panRef.current.moved) {
        // Click on empty canvas → clear selection
        const hit = nodeAt(sx, sy);
        if (!hit) setSelectedId(null);
      }
      panRef.current = null;
    }
    if (dragRef.current) {
      if (!dragRef.current.moved) setSelectedId(dragRef.current.nodeId);
      dragRef.current = null;
    }
  };

  const zoomBy = (factor) => {
    const container = containerRef.current;
    if (!container) return;
    const w = container.clientWidth;
    const h = container.clientHeight;
    const cx = w / 2, cy = h / 2;
    const newScale = Math.min(3.5, Math.max(0.18, view.scale * factor));
    const worldX = (cx - view.tx) / view.scale;
    const worldY = (cy - view.ty) / view.scale;
    setView({
      scale: newScale,
      tx: cx - worldX * newScale,
      ty: cy - worldY * newScale,
    });
  };

  // Keyboard shortcuts
  useEffect(() => {
    const onKey = (e) => {
      if (document.activeElement?.tagName === 'INPUT') return;
      if (e.key === '+' || e.key === '=') { zoomBy(1.2); e.preventDefault(); }
      else if (e.key === '-' || e.key === '_') { zoomBy(1 / 1.2); e.preventDefault(); }
      else if (e.key === '0') { fitToView(); e.preventDefault(); }
      else if (e.key === 'Escape') setSelectedId(null);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [nodes, view]); // eslint-disable-line react-hooks/exhaustive-deps

  const exportPng = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const url = canvas.toDataURL('image/png');
    const link = document.createElement('a');
    link.href = url;
    link.download = `nexus-graph-${(repoId || 'graph').slice(0, 8)}.png`;
    link.click();
    toast.success('Graph exported as PNG');
  };

  const toggleType = (t) => {
    setVisibleTypes((prev) => {
      const next = new Set(prev);
      if (next.has(t)) next.delete(t); else next.add(t);
      return next;
    });
  };

  const selected = selectedId != null ? idToNode.get(selectedId) : null;
  const selectedConnections = useMemo(() => {
    if (!selected) return { out: [], in: [] };
    const out = [];
    const incoming = [];
    for (const e of edges) {
      if (e.source === selected.id) {
        const t = idToNode.get(e.target);
        if (t) out.push({ type: e.type, node: t });
      } else if (e.target === selected.id) {
        const s = idToNode.get(e.source);
        if (s) incoming.push({ type: e.type, node: s });
      }
    }
    return { out, in: incoming };
  }, [selected, edges, idToNode]);

  return (
    <div className="fade-in graph-page">
      <div className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem', flexWrap: 'wrap' }}>
          <div>
            <h1 className="page-title">Dependency Graph</h1>
            <p className="page-subtitle">
              Zoom with the mouse wheel · drag empty space to pan · click nodes to inspect · drag nodes to rearrange
            </p>
          </div>
          <div className="graph-kbd-hints">
            <span><kbd>Wheel</kbd> zoom</span>
            <span><kbd>Drag</kbd> pan</span>
            <span><kbd>+</kbd>/<kbd>-</kbd> zoom</span>
            <span><kbd>0</kbd> fit</span>
            <span><kbd>Esc</kbd> deselect</span>
          </div>
        </div>
      </div>

      {/* Controls row */}
      <div className="graph-toolbar">
        <div className="graph-toolbar-left">
          <div className="input-group" style={{ flex: 1 }}>
            <input
              className="input"
              type="text"
              placeholder="Repository ID (UUID)"
              value={repoId}
              onChange={(e) => setRepoId(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && fetchGraph()}
              style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}
            />
            {repoId && <CopyButton value={repoId} label="Repo ID" compact />}
            <button className="btn btn-primary" onClick={() => fetchGraph()} disabled={loading}>
              {loading ? 'Loading…' : '🔗 Load'}
            </button>
          </div>
        </div>
        <div className="graph-toolbar-right">
          <label className="depth-control">
            <span>Depth</span>
            <input
              type="range"
              min="1"
              max="5"
              value={depth}
              onChange={(e) => setDepth(Number(e.target.value))}
              onMouseUp={() => repoId && fetchGraph(repoId, depth)}
            />
            <span className="depth-value">{depth}</span>
          </label>
        </div>
      </div>

      {/* Type filters + search */}
      <div className="graph-filter-row">
        <div className="type-toggles">
          {NODE_TYPES.map((t) => (
            <button
              key={t}
              type="button"
              className={`type-toggle ${visibleTypes.has(t) ? 'on' : 'off'}`}
              onClick={() => toggleType(t)}
              style={{ '--toggle-color': NODE_COLORS[t] }}
            >
              <span className="type-dot" /> {t}
            </button>
          ))}
        </div>
        <input
          className="input graph-search"
          placeholder="🔎 Filter nodes by name / path…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {error && (
        <div className="alert alert-warning">
          {error}
        </div>
      )}

      <div className="graph-layout">
        <div
          className="graph-container"
          ref={containerRef}
        >
          <canvas
            ref={canvasRef}
            className="graph-canvas"
            onWheel={onWheel}
            onMouseDown={onMouseDown}
            onMouseMove={onMouseMove}
            onMouseUp={onMouseUp}
            onMouseLeave={() => { panRef.current = null; dragRef.current = null; setHoverId(null); }}
          />

          {/* Floating controls */}
          <div className="graph-controls">
            <button type="button" className="graph-ctrl-btn" onClick={() => zoomBy(1.2)} title="Zoom in">＋</button>
            <button type="button" className="graph-ctrl-btn" onClick={() => zoomBy(1 / 1.2)} title="Zoom out">−</button>
            <button type="button" className="graph-ctrl-btn" onClick={() => fitToView()} title="Fit to view">⌧</button>
            <button type="button" className="graph-ctrl-btn" onClick={exportPng} title="Export PNG">⤓</button>
          </div>

          {/* Legend */}
          <div className="graph-legend">
            {NODE_TYPES.map((t) => (
              <div key={t} className={`legend-item ${visibleTypes.has(t) ? '' : 'off'}`} onClick={() => toggleType(t)}>
                <span className="legend-dot" style={{ background: NODE_COLORS[t] }} />
                <span>{t}</span>
              </div>
            ))}
          </div>

          {/* Stats corner */}
          <div className="graph-stats">
            <span>{stats.nodes} nodes</span>
            <span>{stats.edges} edges</span>
            <span>{Math.round(view.scale * 100)}%</span>
          </div>
        </div>

        {/* Detail panel */}
        <aside className="graph-detail">
          {selected ? (
            <>
              <div className="detail-header">
                <span
                  className="detail-type-pill"
                  style={{ '--type-color': NODE_COLORS[selected.type] || NODE_COLORS.Default }}
                >
                  {selected.type}
                </span>
                <h3 className="detail-title" title={selected.label}>{selected.label}</h3>
              </div>

              {selected.path && (
                <div className="detail-row">
                  <span className="detail-label">Path</span>
                  <div className="detail-path">
                    <code title={selected.path}>{selected.path}</code>
                    <CopyButton value={selected.path} label="Path" compact />
                  </div>
                </div>
              )}

              <div className="detail-stats">
                <div>
                  <div className="detail-stat-num">{selectedConnections.out.length}</div>
                  <div className="detail-stat-label">outgoing</div>
                </div>
                <div>
                  <div className="detail-stat-num">{selectedConnections.in.length}</div>
                  <div className="detail-stat-label">incoming</div>
                </div>
              </div>

              {Object.keys(selected.properties || {}).length > 0 && (
                <div className="detail-section">
                  <h4>Properties</h4>
                  <div className="detail-props">
                    {Object.entries(selected.properties).map(([k, v]) => (
                      <div key={k} className="detail-prop">
                        <span className="detail-prop-key">{k}</span>
                        <span className="detail-prop-val" title={String(v)}>
                          {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {selectedConnections.out.length > 0 && (
                <div className="detail-section">
                  <h4>Depends on</h4>
                  <ul className="detail-list">
                    {selectedConnections.out.slice(0, 30).map(({ type, node }, i) => (
                      <li key={`o-${i}`} onClick={() => setSelectedId(node.id)}>
                        <span className="rel-pill">{type}</span>
                        <span className="rel-target" title={node.path || node.label}>{node.label}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {selectedConnections.in.length > 0 && (
                <div className="detail-section">
                  <h4>Depended on by</h4>
                  <ul className="detail-list">
                    {selectedConnections.in.slice(0, 30).map(({ type, node }, i) => (
                      <li key={`i-${i}`} onClick={() => setSelectedId(node.id)}>
                        <span className="rel-pill">{type}</span>
                        <span className="rel-target" title={node.path || node.label}>{node.label}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          ) : (
            <div className="detail-empty">
              <div className="detail-empty-icon">🎯</div>
              <p>Select a node to inspect.</p>
              <p className="text-muted" style={{ fontSize: '0.8rem' }}>
                Click any node on the graph to see its properties, dependencies, and dependents here.
              </p>
              <ul className="detail-help">
                <li><kbd>Wheel</kbd> zoom in / out at cursor</li>
                <li><kbd>Drag</kbd> empty space to pan</li>
                <li><kbd>Drag</kbd> a node to move it</li>
                <li><kbd>+</kbd> / <kbd>-</kbd> / <kbd>0</kbd> keyboard zoom + fit</li>
                <li><kbd>Esc</kbd> deselect</li>
              </ul>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
