// lib/providers/mako_provider.dart
import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../services/websocket_service.dart';

// ── Message model ─────────────────────────────────────────────────────────────
enum MessageRole { user, mako }

class ChatMessage {
  final String id;
  final MessageRole role;
  final String content;
  final DateTime time;
  final Map<String, dynamic>? debugData; // prompt inspector data

  ChatMessage({
    required this.id,
    required this.role,
    required this.content,
    required this.time,
    this.debugData,
  });
}

// ── Conversation mode ─────────────────────────────────────────────────────────
enum ConversationMode { text, voice, live }

// ── Mako status ───────────────────────────────────────────────────────────────
enum MakoStatus { idle, thinking, speaking, listening }

// ── Provider ─────────────────────────────────────────────────────────────────
class MakoProvider extends ChangeNotifier {
  final WebSocketService _ws = WebSocketService();
  final FlutterTts _tts = FlutterTts();
  StreamSubscription? _eventSub;
  StreamSubscription? _statusSub;

  // ── State ──────────────────────────────────────────────────────────────────
  final List<ChatMessage> _messages = [];
  List<ChatMessage> get messages => List.unmodifiable(_messages);

  ConversationMode _mode = ConversationMode.text;
  ConversationMode get mode => _mode;

  MakoStatus _makoStatus = MakoStatus.idle;
  MakoStatus get makoStatus => _makoStatus;

  ConnectionStatus _connStatus = ConnectionStatus.disconnected;
  ConnectionStatus get connStatus => _connStatus;

  bool _voiceOutput = true;
  bool get voiceOutput => _voiceOutput;

  bool _isThinking = false;
  bool get isThinking => _isThinking;

  String _thinkingText = '';
  String get thinkingText => _thinkingText;

  String _currentThought = '';
  String get currentThought => _currentThought;

  // last user message key for inspector
  String? _lastUserMessage;

  // prompt debug store: userMessage -> debugData
  final Map<String, Map<String, dynamic>> _debugStore = {};
  Map<String, dynamic>? getDebugData(String userMessage) =>
      _debugStore[userMessage];

  // ── Init ───────────────────────────────────────────────────────────────────
  Future<void> init() async {
    await _loadPrefs();
    await _initTts();
    _listenToWs();
    _ws.connect();
  }

  Future<void> _loadPrefs() async {
    final prefs = await SharedPreferences.getInstance();
    _voiceOutput = prefs.getBool('voice_output') ?? true;
    final savedUrl = prefs.getString('server_url');
    if (savedUrl != null) _ws.setServerUrl(savedUrl);
    final savedMode = prefs.getInt('conversation_mode') ?? 0;
    _mode = ConversationMode.values[savedMode];
  }

  Future<void> _initTts() async {
    await _tts.setLanguage('en-US');
    await _tts.setSpeechRate(0.48);
    await _tts.setVolume(1.0);
    await _tts.setPitch(1.05);

    _tts.setCompletionHandler(() {
      _setMakoStatus(MakoStatus.idle);
    });

    _tts.setErrorHandler((msg) {
      _setMakoStatus(MakoStatus.idle);
    });
  }

  void _listenToWs() {
    _statusSub = _ws.status.listen((status) {
      _connStatus = status;
      notifyListeners();
    });

    _eventSub = _ws.events.listen((event) {
      switch (event.type) {
        case 'message':
          _handleMessage(event);
          break;
        case 'thought':
          _handleThought(event);
          break;
        case 'tool_call':
          _handleToolCall(event);
          break;
        case 'prompt_debug':
          _handlePromptDebug(event);
          break;
        default:
          break;
      }
    });
  }

  // ── Event handlers ─────────────────────────────────────────────────────────
  void _handleMessage(MakoEvent event) {
    final role = event.data['role'] as String?;
    final content = event.data['content'] as String? ?? '';

    if (role == 'assistant') {
      _isThinking = false;
      _thinkingText = '';
      _currentThought = '';

      // attach debug data if available
      Map<String, dynamic>? debug;
      if (_lastUserMessage != null &&
          _debugStore.containsKey(_lastUserMessage)) {
        debug = _debugStore[_lastUserMessage];
      }

      _messages.add(ChatMessage(
        id: DateTime.now().millisecondsSinceEpoch.toString(),
        role: MessageRole.mako,
        content: content,
        time: DateTime.now(),
        debugData: debug,
      ));

      // speak if voice output enabled
      if (_voiceOutput &&
          (_mode == ConversationMode.voice || _mode == ConversationMode.live)) {
        _speak(content);
      } else {
        _setMakoStatus(MakoStatus.idle);
      }

      notifyListeners();
    }
  }

  void _handleThought(MakoEvent event) {
    _currentThought = event.data['content'] as String? ?? '';
    _isThinking = true;
    _thinkingText = _currentThought;
    _setMakoStatus(MakoStatus.thinking);
    notifyListeners();
  }

  void _handleToolCall(MakoEvent event) {
    final tool = event.data['tool'] as String? ?? '';
    _thinkingText = 'Using $tool...';
    _setMakoStatus(MakoStatus.thinking);
    notifyListeners();
  }

  void _handlePromptDebug(MakoEvent event) {
    final userMsg = event.data['user_message'] as String?;
    if (userMsg != null) {
      _debugStore[userMsg] = event.data;
    }
  }

  // ── Send message ───────────────────────────────────────────────────────────
  void sendMessage(String text) {
    if (text.trim().isEmpty) return;

    _lastUserMessage = text;
    _isThinking = true;
    _thinkingText = '';
    _setMakoStatus(MakoStatus.thinking);

    _messages.add(ChatMessage(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      role: MessageRole.user,
      content: text,
      time: DateTime.now(),
    ));

    _ws.sendMessage(text);
    notifyListeners();
  }

  // ── TTS ────────────────────────────────────────────────────────────────────
  Future<void> _speak(String text) async {
    // strip markdown symbols before speaking
    final clean = text
        .replaceAll(RegExp(r'\*+'), '')
        .replaceAll(RegExp(r'#+'), '')
        .replaceAll(RegExp(r'`+'), '')
        .trim();

    _setMakoStatus(MakoStatus.speaking);
    await _tts.speak(clean);
  }

  Future<void> stopSpeaking() async {
    await _tts.stop();
    _setMakoStatus(MakoStatus.idle);
  }

  // ── Mode ───────────────────────────────────────────────────────────────────
  Future<void> setMode(ConversationMode mode) async {
    _mode = mode;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt('conversation_mode', mode.index);
    notifyListeners();
  }

  // ── Voice output toggle ────────────────────────────────────────────────────
  Future<void> setVoiceOutput(bool val) async {
    _voiceOutput = val;
    if (!val) await _tts.stop();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('voice_output', val);
    notifyListeners();
  }

  // ── Server URL ─────────────────────────────────────────────────────────────
  Future<void> setServerUrl(String url) async {
    _ws.setServerUrl(url);
    _ws.disconnect();
    _ws.connect();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('server_url', url);
    notifyListeners();
  }

  String get serverUrl => _ws.serverUrl;

  // ── Clear messages ─────────────────────────────────────────────────────────
  void clearMessages() {
    _messages.clear();
    _isThinking = false;
    _thinkingText = '';
    notifyListeners();
  }

  // ── Helpers ────────────────────────────────────────────────────────────────
  void _setMakoStatus(MakoStatus status) {
    _makoStatus = status;
    notifyListeners();
  }

  void setListening(bool val) {
    _setMakoStatus(val ? MakoStatus.listening : MakoStatus.idle);
  }

  @override
  void dispose() {
    _eventSub?.cancel();
    _statusSub?.cancel();
    _tts.stop();
    _ws.dispose();
    super.dispose();
  }
}
