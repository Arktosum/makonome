// lib/providers/mako_provider.dart — app state + the connection status machine.
//
// Status flow:
//   offline → checking → (waking, if Render is asleep) → connecting → online
//                     ↘ error (unreachable / token rejected)
// Any drop from online goes back to checking with auto-retry.
import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import '../services/api_service.dart';
import '../services/settings_service.dart';
import '../services/ws_service.dart';

enum MakoStatus { offline, checking, waking, connecting, online, error }

class ChatMessage {
  final String role; // 'user' | 'mako' | 'heartbeat' | 'system'
  final String text;
  final DateTime time;
  ChatMessage(this.role, this.text, {DateTime? time})
      : time = time ?? DateTime.now();

  Map<String, dynamic> toJson() =>
      {'role': role, 'text': text, 'time': time.toIso8601String()};
  factory ChatMessage.fromJson(Map<String, dynamic> j) => ChatMessage(
        j['role'] as String? ?? 'system',
        j['text'] as String? ?? '',
        time: DateTime.tryParse(j['time'] as String? ?? '') ?? DateTime.now(),
      );
}

class MakoProvider extends ChangeNotifier {
  final _settings = SettingsService();
  final _api = ApiService();
  final _ws = WsService();

  MakoStatus status = MakoStatus.offline;
  String statusDetail = '';
  bool serverPushConfigured = false;

  final List<ChatMessage> messages = [];
  bool thinking = false;
  String? thought; // live 💭 while she reasons
  String? toolNote; // live 🔧 while she uses a tool

  Timer? _retryTimer;
  Timer? _wakeTimer;
  int _wakeSeconds = 0;
  String? _lastHeartbeatText; // dedupe: heartbeat also arrives as a message
  bool _disposed = false;

  MakoProvider() {
    _loadHistory();
    _ws.events.listen(_onEvent);
    _ws.closed.listen((_) => _onDropped());
    connect();
  }

  // ── connection machine ────────────────────────────────────

  Future<void> connect() async {
    _retryTimer?.cancel();
    _wakeTimer?.cancel();
    _set(MakoStatus.checking, 'looking for Mako…');

    final health = await _api.health();
    if (_disposed) return;

    if (!health.reachable) {
      _startWaking();
      return;
    }
    serverPushConfigured = health.pushConfigured;
    await _validateAndOpen();
  }

  /// Render's free tier sleeps after ~15 idle minutes; the health probe both
  /// detects that and pokes it awake. Poll until it responds (or give up).
  void _startWaking() {
    _wakeSeconds = 0;
    _set(MakoStatus.waking, 'Mako seems to be asleep — waking her up…');

    _wakeTimer = Timer.periodic(const Duration(seconds: 5), (t) async {
      _wakeSeconds += 5;
      if (_wakeSeconds >= 120) {
        t.cancel();
        _set(MakoStatus.error,
            "Couldn't wake Mako after 2 minutes. Is the server deployed and the URL right?");
        _scheduleRetry(const Duration(seconds: 30));
        return;
      }
      _set(MakoStatus.waking,
          'Mako seems to be asleep — waking her up… ${_wakeSeconds}s '
          '(Render cold starts take 30–60s)');
      final health = await _api.health(timeout: const Duration(seconds: 4));
      if (_disposed || status != MakoStatus.waking) return;
      if (health.reachable) {
        t.cancel();
        serverPushConfigured = health.pushConfigured;
        await _validateAndOpen();
      }
    });
  }

  Future<void> _validateAndOpen() async {
    final tokenStatus = await _api.checkToken();
    if (_disposed) return;
    if (tokenStatus == TokenStatus.rejected) {
      _set(MakoStatus.error,
          'Mako is up, but she rejected the token. Set it in Settings.');
      return; // no auto-retry — a bad token won't fix itself
    }

    _set(MakoStatus.connecting, 'connecting…');
    try {
      await _ws.connect(_settings.wsUrl);
      if (_disposed) return;
      _set(MakoStatus.online, '');
    } catch (_) {
      _set(MakoStatus.error, 'The live connection failed. Retrying…');
      _scheduleRetry(const Duration(seconds: 5));
    }
  }

  void _onDropped() {
    if (_disposed) return;
    thinking = false;
    _set(MakoStatus.offline, 'connection lost — reconnecting…');
    _scheduleRetry(const Duration(seconds: 3));
  }

  void _scheduleRetry(Duration d) {
    _retryTimer?.cancel();
    _retryTimer = Timer(d, connect);
  }

  Future<void> reconnect() async {
    _ws.disconnect();
    await connect();
  }

  // ── chat ──────────────────────────────────────────────────

  void send(String text) {
    if (text.trim().isEmpty || status != MakoStatus.online) return;
    _add(ChatMessage('user', text.trim()));
    thinking = true;
    thought = null;
    toolNote = null;
    _ws.sendMessage(text.trim());
    notifyListeners();
  }

  void _onEvent(MakoEvent e) {
    switch (e.type) {
      case 'message':
        final role = e.data['role'] as String?;
        final content = (e.data['content'] as String?) ?? '';
        if (role == 'assistant') {
          thinking = false;
          thought = null;
          toolNote = null;
          if (content == _lastHeartbeatText) {
            _lastHeartbeatText = null; // already shown as a heartbeat bubble
          } else {
            _add(ChatMessage('mako', content));
          }
        }
        // own user messages are echoed locally on send; ignore the broadcast
        break;
      case 'thought':
        thought = (e.data['content'] as String?) ?? '';
        break;
      case 'tool_call':
        toolNote = 'using ${e.data['tool'] ?? 'a tool'}…';
        break;
      case 'tool_result':
        toolNote = null;
        break;
      case 'heartbeat':
        final decision = e.data['decision'] as String?;
        if (decision == 'spoke') {
          _lastHeartbeatText = (e.data['message'] as String?) ?? '';
          _add(ChatMessage('heartbeat', _lastHeartbeatText!));
        } else if (decision == 'silent') {
          _add(ChatMessage('system', '💓 checked in quietly — nothing to say'));
        } else if (decision == 'reflected') {
          _add(ChatMessage('system', '🪞 Mako reflected on who she is becoming'));
        } else if (decision == 'consolidated') {
          _add(ChatMessage('system', '🗜 Mako distilled this week\'s memories'));
        }
        break;
    }
    notifyListeners();
  }

  // ── history persistence ───────────────────────────────────

  void _add(ChatMessage m) {
    messages.add(m);
    if (messages.length > 200) messages.removeRange(0, messages.length - 200);
    _settings.chatHistory =
        jsonEncode(messages.map((m) => m.toJson()).toList());
  }

  void _loadHistory() {
    try {
      final raw = _settings.chatHistory;
      if (raw.isEmpty) return;
      final list = jsonDecode(raw) as List<dynamic>;
      messages.addAll(
          list.map((j) => ChatMessage.fromJson(j as Map<String, dynamic>)));
    } catch (_) {/* corrupt history is not worth crashing over */}
  }

  void clearHistory() {
    messages.clear();
    _settings.chatHistory = '';
    notifyListeners();
  }

  // ── plumbing ──────────────────────────────────────────────

  void _set(MakoStatus s, String detail) {
    status = s;
    statusDetail = detail;
    notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    _retryTimer?.cancel();
    _wakeTimer?.cancel();
    _ws.disconnect();
    super.dispose();
  }
}
