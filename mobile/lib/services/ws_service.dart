// lib/services/ws_service.dart — live WebSocket to Mako.
// Thin transport: connects, streams events, reports closure.
// Reconnect policy lives in MakoProvider, which owns the status machine.
import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';

class MakoEvent {
  final String type;
  final Map<String, dynamic> data;
  final String time;
  MakoEvent({required this.type, required this.data, required this.time});

  factory MakoEvent.fromJson(Map<String, dynamic> json) => MakoEvent(
        type: json['type'] as String? ?? 'unknown',
        data: (json['data'] as Map<String, dynamic>?) ?? {},
        time: json['time'] as String? ?? '',
      );
}

class WsService {
  WebSocketChannel? _channel;
  Timer? _keepalive;

  final _events = StreamController<MakoEvent>.broadcast();
  final _closed = StreamController<void>.broadcast();

  Stream<MakoEvent> get events => _events.stream;
  Stream<void> get closed => _closed.stream;

  bool get isConnected => _channel != null;

  Future<void> connect(String url) async {
    disconnect();
    final channel = WebSocketChannel.connect(Uri.parse(url));
    _channel = channel;

    channel.stream.listen(
      (data) {
        try {
          final json = jsonDecode(data as String) as Map<String, dynamic>;
          if (json['type'] == 'ping') return;
          _events.add(MakoEvent.fromJson(json));
        } catch (_) {/* ignore malformed frames */}
      },
      onDone: () => _handleClose(channel),
      onError: (_) => _handleClose(channel),
    );

    // surfaces handshake failures (unreachable, 401 rejection...)
    await channel.ready;

    _keepalive?.cancel();
    _keepalive = Timer.periodic(const Duration(seconds: 20), (_) {
      try {
        _channel?.sink.add(jsonEncode({'type': 'ping'}));
      } catch (_) {}
    });
  }

  void _handleClose(WebSocketChannel channel) {
    if (_channel != channel) return; // stale connection
    _channel = null;
    _keepalive?.cancel();
    _closed.add(null);
  }

  void sendMessage(String text) {
    _channel?.sink.add(jsonEncode({'type': 'user_message', 'content': text}));
  }

  void disconnect() {
    _keepalive?.cancel();
    final c = _channel;
    _channel = null; // mark stale before closing so onDone is ignored
    c?.sink.close();
  }
}
