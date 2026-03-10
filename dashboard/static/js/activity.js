// js/activity.js — activity panel, event feed, neural map
const Activity = (() => {
  let _panelOpen = false;
  let _currentTab = 'feed';

  const NODES = {
    ears:   { x: 15, y: 50, label: 'EARS' },
    memory: { x: 38, y: 22, label: 'MEM' },
    brain:  { x: 60, y: 50, label: 'BRAIN' },
    tools:  { x: 38, y: 78, label: 'TOOLS' },
    mouth:  { x: 82, y: 50, label: 'OUT' },
  };

  const EDGES = [
    ['ears','brain'], ['brain','memory'], ['memory','brain'],
    ['brain','tools'], ['tools','brain'], ['brain','mouth']
  ];

  function togglePanel() {
    _panelOpen = !_panelOpen;
    const panel = document.getElementById('activity-panel');
    const chat  = document.getElementById('chat-area');
    const btn   = document.getElementById('toggle-btn');
    panel.classList.toggle('open', _panelOpen);
    chat.classList.toggle('panel-open', _panelOpen);
    btn.classList.toggle('active', _panelOpen);
  }

  function switchTab(tab) {
    _currentTab = tab;
    document.querySelectorAll('.tab').forEach(t =>
      t.classList.toggle('active', t.dataset.tab === tab));
    document.querySelectorAll('.tab-content').forEach(c =>
      c.classList.toggle('active', c.id === `tab-${tab}`));
  }

  function addEvent(event) {
    const feed = document.getElementById('event-feed');
    if (!feed) return;

    const card = document.createElement('div');
    card.className = 'event-card';
    const time = event.time || new Date().toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit',second:'2-digit'});

    let badge = '', body = '';

    if (event.type === 'message' && event.data?.role === 'assistant') {
      badge = '<span class="badge badge-msg">MSG</span>';
      const preview = (event.data.content || '').substring(0, 80);
      body = `<div class="event-body">${escHtml(preview)}${event.data.content?.length > 80 ? '…' : ''}</div>`;
    } else if (event.type === 'thought') {
      badge = '<span class="badge badge-think">THOUGHT</span>';
      body = `<div class="think-box"><div class="think-txt">${escHtml(event.data?.content || '')}</div></div>`;
    } else if (event.type === 'tool_call') {
      badge = '<span class="badge badge-tool">TOOL</span>';
      body = `<div class="tool-box">
        <div class="tool-name">${escHtml(event.data?.tool || '')}</div>
        <div class="tool-args">${escHtml(JSON.stringify(event.data?.args || {}, null, 2))}</div>
      </div>`;
    } else if (event.type === 'tool_result') {
      badge = '<span class="badge badge-result">RESULT</span>';
      body = `<div class="result-box">
        <div class="result-lbl">${escHtml(event.data?.tool || '')}</div>
        <div class="result-txt">${escHtml((event.data?.result || '').substring(0, 300))}</div>
      </div>`;
    } else if (event.type === 'memory') {
      badge = '<span class="badge badge-mem">MEMORY</span>';
      const hits = (event.data?.results || []).slice(0, 3);
      body = `<div class="mem-box">
        <div class="mem-query">↳ ${escHtml(event.data?.query || '')}</div>
        ${hits.map(h => `<div class="mem-hit">${escHtml(h)}</div>`).join('')}
      </div>`;
    } else { return; }

    card.innerHTML = `
      <div class="event-top">${badge}<span class="event-time">${time}</span></div>
      ${body}`;
    feed.insertBefore(card, feed.firstChild);

    // keep feed tidy
    while (feed.children.length > 60) feed.removeChild(feed.lastChild);
  }

  function activeNodesFor(event) {
    const map = {
      message:    ['ears','brain','mouth'],
      thought:    ['brain'],
      tool_call:  ['brain','tools'],
      tool_result:['tools','brain'],
      memory:     ['brain','memory'],
    };
    return map[event.type] || [];
  }

  function setActiveNodes(nodeIds) {
    document.querySelectorAll('.neural-node').forEach(el => {
      el.classList.toggle('active', nodeIds.includes(el.dataset.id));
    });
    document.querySelectorAll('.neural-edge').forEach(el => {
      const [a, b] = [el.dataset.from, el.dataset.to];
      el.classList.toggle('active', nodeIds.includes(a) && nodeIds.includes(b));
    });
  }

  function buildMap() {
    const svg = document.getElementById('neural-svg');
    if (!svg) return;
    svg.innerHTML = '';

    // edges
    EDGES.forEach(([a, b]) => {
      const na = NODES[a], nb = NODES[b];
      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', na.x); line.setAttribute('y1', na.y);
      line.setAttribute('x2', nb.x); line.setAttribute('y2', nb.y);
      line.setAttribute('stroke', '#0a2a12');
      line.setAttribute('stroke-width', '0.8');
      line.classList.add('neural-edge');
      line.dataset.from = a; line.dataset.to = b;
      svg.appendChild(line);
    });

    // nodes
    Object.entries(NODES).forEach(([id, n]) => {
      const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      g.classList.add('neural-node');
      g.dataset.id = id;

      const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      circle.setAttribute('cx', n.x); circle.setAttribute('cy', n.y); circle.setAttribute('r', '7');
      circle.setAttribute('fill', '#010d04'); circle.setAttribute('stroke', '#0a3a1a');
      circle.setAttribute('stroke-width', '1');

      const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      text.setAttribute('x', n.x); text.setAttribute('y', n.y + 14);
      text.setAttribute('text-anchor', 'middle'); text.setAttribute('font-size', '4');
      text.setAttribute('fill', '#1a4a2a'); text.setAttribute('font-family', 'Space Mono, monospace');
      text.textContent = n.label;

      g.appendChild(circle); g.appendChild(text);
      svg.appendChild(g);
    });

    // inject active styles
    const style = document.createElementNS('http://www.w3.org/2000/svg', 'style');
    style.textContent = `
      .neural-node.active circle { stroke: #00ff88; fill: #001a0a; filter: drop-shadow(0 0 4px #00ff8888); }
      .neural-node.active text   { fill: #00ff88; }
      .neural-edge.active        { stroke: #00ff4444; stroke-width: 1.5; }
      .neural-node circle, .neural-edge { transition: all 0.3s; }
    `;
    svg.appendChild(style);
  }

  function escHtml(str) {
    return String(str||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  return { togglePanel, switchTab, addEvent, activeNodesFor, setActiveNodes, buildMap };
})();