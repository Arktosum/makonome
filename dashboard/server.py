# dashboard/server.py
import json
import threading
from queue import Queue
from datetime import datetime
from flask import Flask, send_from_directory
from flask_sock import Sock
import os

app = Flask(__name__)
sock = Sock(app)

_clients = []
_clients_lock = threading.Lock()
event_queue = Queue()

# this will be set by main.py to point at the think function
_think_fn = None


def set_think_fn(fn):
    """Register the brain's think function so we can call it from here."""
    global _think_fn
    _think_fn = fn


# ── Serve static files ────────────────────────────────
STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')


@app.route('/')
def index():
    return send_from_directory(STATIC_DIR, 'index.html')


@app.route('/css/<path:filename>')
def css(filename):
    return send_from_directory(os.path.join(STATIC_DIR, 'css'), filename)


@app.route('/js/<path:filename>')
def js(filename):
    return send_from_directory(os.path.join(STATIC_DIR, 'js'), filename)

@app.route('/api/clear-memories', methods=['POST'])
def clear_memories_endpoint():
    try:
        from memory import clear_memories
        clear_memories()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}, 500
# ── WebSocket ─────────────────────────────────────────


@sock.route('/ws')
def handle(ws):
    with _clients_lock:
        _clients.append(ws)
    print(f"📊 Dashboard connected ({len(_clients)} active)", flush=True)
    try:
        while True:
            data = ws.receive(timeout=60)
            if data is None:
                continue
            msg = json.loads(data)

            # browser sent a user message — run it through Mako in a thread
            # so we don't block the WebSocket handler
            if msg.get('type') == 'user_message' and _think_fn:
                def process(text=msg['content']):
                    _think_fn(text)
                threading.Thread(target=process, daemon=True).start()

            # browser sent a keepalive ping — ignore
            elif msg.get('type') == 'ping':
                pass

    except Exception:
        pass
    finally:
        with _clients_lock:
            if ws in _clients:
                _clients.remove(ws)
        print(f"📊 Dashboard disconnected ({len(_clients)} active)", flush=True)

# ── Broadcaster ───────────────────────────────────────


def _broadcaster():
    while True:
        event = event_queue.get()
        event.setdefault("time", datetime.now().strftime("%H:%M:%S"))
        message = json.dumps(event)
        with _clients_lock:
            dead = []
            for client in _clients:
                try:
                    client.send(message)
                except Exception:
                    dead.append(client)
            for client in dead:
                _clients.remove(client)


def _keepalive():
    """Ping all clients every 20 seconds to prevent idle disconnects."""
    import time
    while True:
        time.sleep(20)
        with _clients_lock:
            dead = []
            for client in _clients:
                try:
                    client.send(json.dumps({"type": "ping"}))
                except Exception:
                    dead.append(client)
            for client in dead:
                _clients.remove(client)

def on_startup():
    """Called by Gunicorn post-fork or directly by main.py locally."""
    threading.Thread(target=_broadcaster, daemon=True).start()
    threading.Thread(target=_keepalive, daemon=True).start()
    print("📊 Background threads started", flush=True)

def start_server():
    on_startup()
    port = int(os.environ.get("PORT", 8765))
    print(f"📊 Dashboard on port {port}", flush=True)
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# Gunicorn calls this on worker startup
def post_fork(server, worker):
    on_startup()
    
if os.environ.get("RENDER"):
    import sys
    # delay import to avoid circular imports
    def _cloud_init():
        import time
        time.sleep(2)  # wait for Gunicorn to finish setup
        try:
            from brain import think
            from main import on_heartbeat_message
            from heartbeat import start_heartbeat
            set_think_fn(think)
            start_heartbeat(on_heartbeat_message)
            on_startup()
            print("☁️  Cloud init complete", flush=True)
        except Exception as e:
            print(f"⚠️  Cloud init failed: {e}", flush=True)
    threading.Thread(target=_cloud_init, daemon=True).start()
    
    