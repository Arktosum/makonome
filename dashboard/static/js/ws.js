// js/ws.js — WebSocket connection manager
const WS = (() => {
  let _ws = null;
  let _handlers = {};
  let _reconnectTimer = null;

  function on(type, fn) {
    if (!_handlers[type]) _handlers[type] = [];
    _handlers[type].push(fn);
  }

  function _dispatch(type, data) {
    (_handlers[type] || []).forEach(fn => fn(data));
    (_handlers['any'] || []).forEach(fn => fn(data));
  }

  function send(obj) {
    if (_ws && _ws.readyState === WebSocket.OPEN) {
      _ws.send(JSON.stringify(obj));
    }
  }

  function connect() {
    if (_reconnectTimer) { clearTimeout(_reconnectTimer); _reconnectTimer = null; }
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    _ws = new WebSocket(`${proto}//${location.host}/ws`);

    _ws.onopen = () => {
      console.log('[WS] connected');
      _dispatch('connected', {});
    };

    _ws.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data);
        if (event.type === 'ping') return;
        _dispatch(event.type, event);
      } catch(err) {
        console.warn('[WS] parse error', err);
      }
    };

    _ws.onclose = () => {
      console.log('[WS] disconnected, reconnecting in 2s...');
      _dispatch('disconnected', {});
      _reconnectTimer = setTimeout(connect, 2000);
    };

    _ws.onerror = (e) => {
      console.warn('[WS] error', e);
      _ws.close();
    };
  }

  return { on, send, connect };
})();