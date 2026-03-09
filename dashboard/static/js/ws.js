// js/ws.js — WebSocket connection, dispatches events to other modules
const WS = (() => {
  let _ws = null;
  let _handlers = {};

  function on(type, fn) {
    if (!_handlers[type]) _handlers[type] = [];
    _handlers[type].push(fn);
  }

  function dispatch(type, data) {
    (_handlers[type] || []).forEach(fn => fn(data));
    (_handlers['*'] || []).forEach(fn => fn({ type, ...data }));
  }

  function send(obj) {
    if (_ws && _ws.readyState === WebSocket.OPEN) {
      _ws.send(JSON.stringify(obj));
    }
  }

  function connect() {
    if (_ws && (_ws.readyState === WebSocket.OPEN || _ws.readyState === WebSocket.CONNECTING)) return;

    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    _ws = new WebSocket(`${protocol}//${location.host}/ws`);

    _ws.onopen = () => {
      console.log('WS connected');
      dispatch('connected', {});
    };

    _ws.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data);
        if (event.type === 'ping') return;
        dispatch(event.type, event);
        dispatch('any', event);
      } catch(err) {
        console.error('WS parse error', err);
      }
    };

    _ws.onclose = () => {
      console.log('WS disconnected, retrying in 2s...');
      dispatch('disconnected', {});
      _ws = null;
      setTimeout(connect, 2000);
    };

    _ws.onerror = () => _ws && _ws.close();
  }

  return { connect, send, on };
})();