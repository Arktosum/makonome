// lib/services/websocket_service.dart
import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';

enum ConnectionStatus { disconnected, connecting, connected }

class MakoEvent {
  final String type;
  final Map<String, dynamic> data;
  final String time;

  MakoEvent({required this.type, required this.data, required this.time});

  factory MakoEvent.fromJson(Map<String, dynamic> json) {
    return MakoEvent(
      type: json['type'] ?? 'unknown',
      data: json['data'] ?? {},
      time: json['time'] ?? '',
    );
  }
}

class WebSocketService {
  static final WebSocketService _instance = WebSocketService._internal();
  factory WebSocketService() => _instance;
  WebSocketService._internal();

  WebSocketChannel? _channel;
  Timer? _reconnectTimer;
  Timer? _keepaliveTimer;

  final _eventController = StreamController<MakoEvent>.broadcast();
  final _statusController = StreamController<ConnectionStatus>.broadcast();

  Stream<MakoEvent> get events => _eventController.stream;
  Stream<ConnectionStatus> get status => _statusController.stream;

  ConnectionStatus _currentStatus = ConnectionStatus.disconnected;
  ConnectionStatus get currentStatus => _currentStatus;

  String _serverUrl = 'wss://makonome.onrender.com/ws';
  String get serverUrl => _serverUrl;

  void setServerUrl(String url) {
    _serverUrl = url;
  }

  void connect() {
    if (_currentStatus == ConnectionStatus.connected) return;
    _setStatus(ConnectionStatus.connecting);

    try {
      final uri = Uri.parse(_serverUrl);
      _channel = WebSocketChannel.connect(uri);

      _channel!.stream.listen(
        (data) {
          try {
            final json = jsonDecode(data as String) as Map<String, dynamic>;
            if (json['type'] == 'ping') return;
            final event = MakoEvent.fromJson(json);
            _eventController.add(event);

            // mark connected on first message
            if (_currentStatus != ConnectionStatus.connected) {
              _setStatus(ConnectionStatus.connected);
            }
          } catch (e) {
            // ignore parse errors
          }
        },
        onDone: () {
          _setStatus(ConnectionStatus.disconnected);
          _scheduleReconnect();
        },
        onError: (e) {
          _setStatus(ConnectionStatus.disconnected);
          _scheduleReconnect();
        },
      );

      // consider connected after successful channel creation
      _setStatus(ConnectionStatus.connected);
      _startKeepalive();

    } catch (e) {
      _setStatus(ConnectionStatus.disconnected);
      _scheduleReconnect();
    }
  }

  void send(Map<String, dynamic> message) {
    if (_currentStatus != ConnectionStatus.connected) return;
    try {
      _channel?.sink.add(jsonEncode(message));
    } catch (e) {
      // channel might be dead
      _setStatus(ConnectionStatus.disconnected);
      _scheduleReconnect();
    }
  }

  void sendMessage(String text) {
    send({'type': 'user_message', 'content': text});
  }

  void disconnect() {
    _reconnectTimer?.cancel();
    _keepaliveTimer?.cancel();
    _channel?.sink.close();
    _setStatus(ConnectionStatus.disconnected);
  }

  void _setStatus(ConnectionStatus status) {
    _currentStatus = status;
    _statusController.add(status);
  }

  void _scheduleReconnect() {
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(const Duration(seconds: 3), () {
      if (_currentStatus == ConnectionStatus.disconnected) connect();
    });
  }

  void _startKeepalive() {
    _keepaliveTimer?.cancel();
    _keepaliveTimer = Timer.periodic(const Duration(seconds: 20), (_) {
      send({'type': 'ping'});
    });
  }

  void dispose() {
    _eventController.close();
    _statusController.close();
    disconnect();
  }
}