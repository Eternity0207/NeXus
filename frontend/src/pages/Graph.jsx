import { useState, useRef, useEffect } from 'react';

const mockNodes = [
  { id: '1', label: 'main.py', type: 'File', x: 400, y: 100 },
  { id: '2', label: 'config.py', type: 'File', x: 200, y: 250 },
  { id: '3', label: 'models.py', type: 'File', x: 600, y: 250 },
  { id: '4', label: 'routes/', type: 'File', x: 400, y: 400 },
  { id: '5', label: 'UserModel', type: 'Class', x: 700, y: 400 },
  { id: '6', label: 'get_db', type: 'Function', x: 150, y: 420 },
  { id: '7', label: 'auth.py', type: 'File', x: 550, y: 550 },
  { id: '8', label: 'validate', type: 'Function', x: 300, y: 560 },
];

const mockEdges = [
  { source: '1', target: '2', type: 'IMPORTS' },
  { source: '1', target: '3', type: 'IMPORTS' },
  { source: '1', target: '4', type: 'IMPORTS' },
  { source: '4', target: '3', type: 'IMPORTS' },
  { source: '3', target: '5', type: 'CONTAINS' },
  { source: '2', target: '6', type: 'CONTAINS' },
  { source: '4', target: '7', type: 'IMPORTS' },
  { source: '7', target: '8', type: 'CONTAINS' },
  { source: '4', target: '8', type: 'CALLS' },
];

const nodeColors = {
  File: '#6366f1',
  Class: '#06b6d4',
  Function: '#10b981',
  Module: '#f59e0b',
};

const edgeColors = {
  IMPORTS: 'rgba(99, 102, 241, 0.4)',
  CONTAINS: 'rgba(6, 182, 212, 0.3)',
  CALLS: 'rgba(16, 185, 129, 0.4)',
  EXTENDS: 'rgba(245, 158, 11, 0.4)',
};

export default function Graph() {
  const canvasRef = useRef(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;

    canvas.width = canvas.offsetWidth * dpr;
    canvas.height = canvas.offsetHeight * dpr;
    ctx.scale(dpr, dpr);

    const w = canvas.offsetWidth;
    const h = canvas.offsetHeight;

    ctx.clearRect(0, 0, w, h);

    // Draw edges
    mockEdges.forEach(({ source, target, type }) => {
      const s = mockNodes.find(n => n.id === source);
      const t = mockNodes.find(n => n.id === target);
      if (!s || !t) return;

      ctx.beginPath();
      ctx.moveTo(s.x, s.y);
      ctx.lineTo(t.x, t.y);
      ctx.strokeStyle = edgeColors[type] || 'rgba(255,255,255,0.1)';
      ctx.lineWidth = 1.5;
      ctx.stroke();

      // Arrow
      const angle = Math.atan2(t.y - s.y, t.x - s.x);
      const arrowLen = 10;
      const midX = (s.x + t.x) / 2;
      const midY = (s.y + t.y) / 2;
      ctx.beginPath();
      ctx.moveTo(midX, midY);
      ctx.lineTo(midX - arrowLen * Math.cos(angle - 0.4), midY - arrowLen * Math.sin(angle - 0.4));
      ctx.moveTo(midX, midY);
      ctx.lineTo(midX - arrowLen * Math.cos(angle + 0.4), midY - arrowLen * Math.sin(angle + 0.4));
      ctx.stroke();
    });

    // Draw nodes
    mockNodes.forEach((node) => {
      if (filter !== 'all' && node.type !== filter) return;

      const color = nodeColors[node.type] || '#6366f1';
      const radius = node.type === 'File' ? 24 : 18;
      const isSelected = selectedNode === node.id;

      // Glow
      if (isSelected) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius + 8, 0, Math.PI * 2);
        ctx.fillStyle = color.replace(')', ', 0.15)').replace('rgb', 'rgba');
        ctx.fill();
      }

      // Node circle
      ctx.beginPath();
      ctx.arc(node.x, node.y, radius, 0, Math.PI * 2);
      ctx.fillStyle = isSelected ? color : color + '33';
      ctx.fill();
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.stroke();

      // Label
      ctx.fillStyle = '#f1f5f9';
      ctx.font = '500 11px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(node.label, node.x, node.y + radius + 16);

      // Type badge
      ctx.fillStyle = color;
      ctx.font = '600 8px Inter, sans-serif';
      ctx.fillText(node.type, node.x, node.y + 4);
    });
  }, [selectedNode, filter]);

  const handleCanvasClick = (e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const clicked = mockNodes.find(n => 
      Math.sqrt((n.x - x) ** 2 + (n.y - y) ** 2) < 24
    );
    setSelectedNode(clicked ? clicked.id : null);
  };

  const selected = mockNodes.find(n => n.id === selectedNode);

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1 className="page-title">Dependency Graph</h1>
        <p className="page-subtitle">Visualize file-level and function-level dependencies</p>
      </div>

      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
        {['all', 'File', 'Class', 'Function'].map(f => (
          <button
            key={f}
            className={`btn ${filter === f ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setFilter(f)}
            style={{ fontSize: '0.8rem', padding: '0.4rem 0.875rem' }}
          >
            {f === 'all' ? '🌐 All' : `${f === 'File' ? '📄' : f === 'Class' ? '🏗️' : '⚡'} ${f}`}
          </button>
        ))}
      </div>

      <div style={{ display: 'flex', gap: '1.25rem' }}>
        <div className="graph-container" style={{ flex: 1 }}>
          <canvas
            ref={canvasRef}
            className="graph-canvas"
            onClick={handleCanvasClick}
            style={{ cursor: 'pointer' }}
          />
          {/* Legend */}
          <div style={{ position: 'absolute', bottom: '1rem', left: '1rem', display: 'flex', gap: '1rem', fontSize: '0.7rem' }}>
            {Object.entries(nodeColors).map(([type, color]) => (
              <div key={type} style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                <div style={{ width: 10, height: 10, borderRadius: '50%', background: color }} />
                <span style={{ color: 'var(--text-muted)' }}>{type}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Node Details Panel */}
        {selected && (
          <div className="card" style={{ width: '260px', alignSelf: 'flex-start' }}>
            <h3 className="card-title" style={{ marginBottom: '1rem' }}>{selected.label}</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.85rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Type</span>
                <span className="badge badge-primary">{selected.type}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Connections</span>
                <span>{mockEdges.filter(e => e.source === selected.id || e.target === selected.id).length}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>ID</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>{selected.id}</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
