// js/stats.js — stat counters
const Stats = (() => {
  const counts = { msg: 0, tools: 0, mem: 0 };

  function update(eventType) {
    if (eventType === 'message')   counts.msg++;
    if (eventType === 'tool_call') counts.tools++;
    if (eventType === 'memory')    counts.mem++;
    document.getElementById('stat-msg').textContent   = counts.msg;
    document.getElementById('stat-tools').textContent = counts.tools;
    document.getElementById('stat-mem').textContent   = counts.mem;
  }

  return { update };
})();