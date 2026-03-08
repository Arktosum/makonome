// js/chat.js — chat bubbles, typing indicator
const Chat = (() => {
  let _thinkingEl = null;

  function addBubble(role, content, time) {
    removeThinking();
    const wrap = document.createElement('div');
    wrap.className = `bubble-wrap ${role} fade-in`;
    const name = role === 'user' ? 'YOU' : 'MAKO';
    wrap.innerHTML = `
      <div class="bubble-name">${name}</div>
      <div class="bubble ${role}"><p>${renderMarkdown(content)}</p></div>
      <div class="bubble-time">${time || ''}</div>`;
    document.getElementById('messages').appendChild(wrap);
    scrollToBottom();
}

  function showThinking() {
    if (_thinkingEl) return;
    const wrap = document.createElement('div');
    wrap.className = 'bubble-wrap mako fade-in';
    wrap.id = 'thinking-wrap';
    wrap.innerHTML = `
      <div class="bubble-name">MAKO</div>
      <div class="bubble thinking">
        <div class="typing">
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
        </div>
      </div>`;
    document.getElementById('messages').appendChild(wrap);
    _thinkingEl = wrap;
    scrollToBottom();
  }

  function updateThinking(text) {
    if (!_thinkingEl) showThinking();
    const bubble = _thinkingEl.querySelector('.bubble');
    bubble.innerHTML = `<span style="font-size:11px;color:var(--green2)">💭 ${escapeHtml(text)}</span>`;
    scrollToBottom();
  }

  function removeThinking() {
    if (_thinkingEl) { _thinkingEl.remove(); _thinkingEl = null; }
  }

  function scrollToBottom() {
    const m = document.getElementById('messages');
    m.scrollTop = m.scrollHeight;
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function setInputEnabled(enabled) {
    document.getElementById('msg-input').disabled = !enabled;
    document.getElementById('send-btn').disabled  = !enabled;
  }
  function renderMarkdown(str) {
    return String(str)
        // escape html first
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        // bold
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<strong>$1</strong>')
        // line breaks
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br/>')
        // numbered lists
        .replace(/^\d+\.\s(.+)/gm, '<div class="list-item">$1</div>');
}
  return { addBubble, showThinking, updateThinking, removeThinking, setInputEnabled ,renderMarkdown};
})();