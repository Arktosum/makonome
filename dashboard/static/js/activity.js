// js/activity.js — activity panel, event feed, neural map
const Activity = (() => {
  let panelOpen = true;

  // ── Panel toggle ─────────────────────────────────────
  function togglePanel() {
    panelOpen = !panelOpen;
    document.getElementById('activity-panel').classList.add('open');
    document.getElementById('chat-area').classList.add('panel-open');
    document.getElementById('toggle-btn').classList.add('active');
  }

  // ── Tabs ─────────────────────────────────────────────
  function switchTab(name) {
    document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === name));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.toggle('active', t.id === `tab-${name}`));
  }

  // ── Event feed ───────────────────────────────────────
  function addEvent(event) {
    const feed = document.getElementById('event-feed');
    const card = document.createElement('div');
    card.className = 'event-card';
    card.innerHTML = buildCard(event);
    feed.appendChild(card);
    feed.scrollTop = feed.scrollHeight;
  }

  function buildCard(event) {
    const badge = buildBadge(event.type);
    const time  = `<span class="event-time">${event.time || ''}</span>`;
    let body = '';

    if (event.type === 'message') {
      const isUser = event.data?.role === 'user';
      body = `<div class="event-body" style="color:${isUser?'#88ccff':'#4dff8f'}">
        ${isUser ? '▶ YOU' : '◀ MAKO'}: 
        <span style="color:#8aab95">${event.data?.content || ''}</span>
      </div>`;
    } else if (event.type === 'tool_call') {
      body = `<div class="tool-box">
        <div class="tool-name">⚡ ${event.data?.tool}</div>
        <pre class="tool-args">${JSON.stringify(event.data?.args, null, 2)}</pre>
      </div>`;
    } else if (event.type === 'tool_result') {
      body = `<div class="result-box">
        <div class="result-lbl">↩ ${event.data?.tool}</div>
        <pre class="result-txt">${event.data?.result || ''}</pre>
      </div>`;
    } else if (event.type === 'memory') {
      const hits = (event.data?.results || []).map(r => `<div class="mem-hit">· ${r}</div>`).join('');
      body = `<div class="mem-box">
        <div class="mem-query">🔍 "${event.data?.query}"</div>
        ${hits}
      </div>`;
    } else if (event.type === 'thought') {
      body = `<div class="think-box">
        <div class="think-txt">💭 ${event.data?.content}</div>
      </div>`;
    }

    return `<div class="event-top">${badge}${time}</div>${body}`;
  }

  function buildBadge(type) {
    const map = {
      message:     ['badge-msg',    'MSG'   ],
      tool_call:   ['badge-tool',   'TOOL'  ],
      tool_result: ['badge-result', 'RESULT'],
      memory:      ['badge-mem',    'MEM'   ],
      thought:     ['badge-think',  'THINK' ],
    };
    const [cls, label] = map[type] || ['badge-msg', type.toUpperCase()];
    return `<span class="badge ${cls}">${label}</span>`;
  }

  // ── Neural map ────────────────────────────────────────
  const NODES = {
    ears:   { x:15, y:50, icon:'🎤', label:'EARS'   },
    memory: { x:38, y:18, icon:'💾', label:'MEMORY' },
    brain:  { x:50, y:50, icon:'⚡', label:'BRAIN'  },
    tools:  { x:62, y:82, icon:'🔧', label:'TOOLS'  },
    mouth:  { x:85, y:50, icon:'🔊', label:'MOUTH'  },
  };
  const EDGES = [
    ['ears','brain'],['brain','memory'],['memory','brain'],
    ['brain','tools'],['tools','brain'],['brain','mouth'],
  ];

  function buildMap() {
    const svg = document.getElementById('neural-svg');
    const ns = 'http://www.w3.org/2000/svg';
    svg.innerHTML = `<defs>
      <filter id="glow">
        <feGaussianBlur stdDeviation="1.5" result="b"/>
        <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter></defs>`;

    EDGES.forEach(([a,b]) => {
      const line = document.createElementNS(ns,'line');
      line.setAttribute('x1',NODES[a].x); line.setAttribute('y1',NODES[a].y);
      line.setAttribute('x2',NODES[b].x); line.setAttribute('y2',NODES[b].y);
      line.setAttribute('stroke','#1a3a2a'); line.setAttribute('stroke-width','0.4');
      line.id = `edge-${a}-${b}`; line.style.transition='all 0.4s';
      svg.appendChild(line);
    });

    Object.entries(NODES).forEach(([name,n]) => {
      const g = document.createElementNS(ns,'g'); g.id = `node-${name}`;
      const r = name==='brain'?7:5;
      const c = document.createElementNS(ns,'circle');
      c.setAttribute('cx',n.x); c.setAttribute('cy',n.y); c.setAttribute('r',r);
      c.setAttribute('fill','#060f0a'); c.setAttribute('stroke','#1a4a2a'); c.setAttribute('stroke-width','0.6');
      c.style.transition='all 0.4s'; g.appendChild(c);
      const ic = document.createElementNS(ns,'text');
      ic.setAttribute('x',n.x); ic.setAttribute('y',n.y+0.8);
      ic.setAttribute('text-anchor','middle'); ic.setAttribute('font-size',name==='brain'?'5':'4');
      ic.setAttribute('fill','#2a6a3a'); ic.textContent=n.icon; ic.style.transition='all 0.4s'; g.appendChild(ic);
      const lb = document.createElementNS(ns,'text');
      lb.setAttribute('x',n.x); lb.setAttribute('y',n.y+(name==='brain'?11:9));
      lb.setAttribute('text-anchor','middle'); lb.setAttribute('font-size','3');
      lb.setAttribute('fill','#1a4a2a'); lb.setAttribute('font-family','monospace'); lb.textContent=n.label; g.appendChild(lb);
      svg.appendChild(g);
    });
  }

  function setActiveNodes(active) {
    Object.keys(NODES).forEach(name => {
      const g = document.getElementById(`node-${name}`);
      if (!g) return;
      const on = active.includes(name);
      const c = g.querySelector('circle');
      const ic = g.querySelector('text');
      c.setAttribute('stroke', on?'#1df2a0':'#1a4a2a');
      c.setAttribute('stroke-width', on?'1.2':'0.6');
      c.setAttribute('filter', on?'url(#glow)':'');
      ic.setAttribute('fill', on?'#1df2a0':'#2a6a3a');
    });
    EDGES.forEach(([a,b]) => {
      const line = document.getElementById(`edge-${a}-${b}`);
      if (!line) return;
      const on = active.includes(a) && active.includes(b);
      line.setAttribute('stroke', on?'#1df2a0':'#1a3a2a');
      line.setAttribute('stroke-width', on?'0.9':'0.4');
      line.setAttribute('filter', on?'url(#glow)':'');
      line.setAttribute('stroke-dasharray', on?'2 1':'none');
    });
  }

  function activeNodesFor(event) {
    if (event.type==='message' && event.data?.role==='user')      return ['ears','brain'];
    if (event.type==='message' && event.data?.role==='assistant') return ['brain','mouth'];
    if (event.type==='memory')      return ['brain','memory'];
    if (event.type==='tool_call')   return ['brain','tools'];
    if (event.type==='tool_result') return ['tools','brain'];
    if (event.type==='thought')     return ['brain'];
    return ['brain'];
  }

  return { togglePanel, switchTab, addEvent, buildMap, setActiveNodes, activeNodesFor };
})();