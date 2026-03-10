// js/stats.js — topbar counters
const Stats = (() => {
  const _counts = { msg: 0, tools: 0, mem: 0 };

  function update(type) {
    if (type === 'message') { _counts.msg++; _set('stat-msg', _counts.msg); }
    if (type === 'tool_call') { _counts.tools++; _set('stat-tools', _counts.tools); }
    if (type === 'memory') { _counts.mem++; _set('stat-mem', _counts.mem); }
  }

  function _set(id, val) {
    const el = document.getElementById(id);
    if (el) {
      el.textContent = val;
      el.style.transform = 'scale(1.3)';
      setTimeout(() => el.style.transform = '', 200);
    }
  }

  return { update };
})();