// lib/screens/chat_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../providers/mako_provider.dart';
import '../services/websocket_service.dart';
import '../widgets/message_bubble.dart';
import '../widgets/mode_bar.dart';
import '../widgets/status_bar.dart';
import '../widgets/live_indicator.dart';
import 'settings_screen.dart';
import 'dart:async';
import 'package:speech_to_text/speech_to_text.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> with TickerProviderStateMixin {
  final TextEditingController _textCtrl = TextEditingController();
  final ScrollController _scrollCtrl = ScrollController();
  final SpeechToText _stt = SpeechToText();
  bool _sttAvailable = false;
  bool _isListening = false;
  String _interimText = '';
  Timer? _silenceTimer;
  late AnimationController _pulseCtrl;

  @override
  void initState() {
    super.initState();
    _pulseCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    )..repeat(reverse: true);
    _initStt();
  }

  Future<void> _initStt() async {
    _sttAvailable = await _stt.initialize(
      onStatus: _onSttStatus,
      onError: (e) => _stopListening(),
    );
    setState(() {});
  }

  void _onSttStatus(String status) {
    if (status == 'done' || status == 'notListening') {
      if (_isListening) {
        final mode = context.read<MakoProvider>().mode;
        if (mode == ConversationMode.live) {
          // restart in live mode
          Future.delayed(const Duration(milliseconds: 300), _startListening);
        } else {
          setState(() => _isListening = false);
          context.read<MakoProvider>().setListening(false);
        }
      }
    }
  }

  Future<void> _startListening() async {
    if (!_sttAvailable || _isListening) return;
    final mako = context.read<MakoProvider>();
    if (mako.makoStatus == MakoStatus.speaking) return;

    setState(() {
      _isListening = true;
      _interimText = '';
    });
    mako.setListening(true);

    await _stt.listen(
      onResult: (result) {
        setState(() => _interimText = result.recognizedWords);

        if (result.finalResult) {
          final text = result.recognizedWords.trim();
          _silenceTimer?.cancel();

          if (text.isNotEmpty) {
            setState(() {
              _interimText = '';
              _isListening = false;
            });
            mako.setListening(false);
            _stt.stop();

            // stop Mako speaking if she is
            mako.stopSpeaking();
            mako.sendMessage(text);

            // in live mode restart listening after response
            if (mako.mode == ConversationMode.live) {
              _waitAndResumeLive();
            }
          }
        } else {
          // reset silence timer on interim results
          _silenceTimer?.cancel();
          _silenceTimer = Timer(const Duration(milliseconds: 1500), () {
            if (_interimText.trim().isNotEmpty) {
              final text = _interimText.trim();
              setState(() {
                _interimText = '';
                _isListening = false;
              });
              mako.setListening(false);
              _stt.stop();
              mako.stopSpeaking();
              mako.sendMessage(text);
              if (mako.mode == ConversationMode.live) _waitAndResumeLive();
            }
          });
        }
      },
      listenFor: const Duration(seconds: 30),
      pauseFor: const Duration(seconds: 2),
      partialResults: true,
      cancelOnError: true,
    );
  }

  void _stopListening() {
    _silenceTimer?.cancel();
    _stt.stop();
    setState(() {
      _isListening = false;
      _interimText = '';
    });
    context.read<MakoProvider>().setListening(false);
  }

  void _waitAndResumeLive() {
    // listen for Mako to finish speaking then resume
    final mako = context.read<MakoProvider>();
    Timer.periodic(const Duration(milliseconds: 500), (timer) {
      if (mako.makoStatus != MakoStatus.speaking &&
          mako.makoStatus != MakoStatus.thinking) {
        timer.cancel();
        if (mako.mode == ConversationMode.live) _startListening();
      }
    });
  }

  void _onModeChanged(ConversationMode mode) {
    final mako = context.read<MakoProvider>();
    _stopListening();

    mako.setMode(mode).then((_) {
      if (mode == ConversationMode.live) {
        Future.delayed(const Duration(milliseconds: 400), _startListening);
      }
    });
  }

  void _sendText() {
    final text = _textCtrl.text.trim();
    if (text.isEmpty) return;
    _textCtrl.clear();
    HapticFeedback.lightImpact();
    context.read<MakoProvider>().sendMessage(text);
    _scrollToBottom();
  }

  void _scrollToBottom() {
    Future.delayed(const Duration(milliseconds: 100), () {
      if (_scrollCtrl.hasClients) {
        _scrollCtrl.animateTo(
          _scrollCtrl.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  void dispose() {
    _textCtrl.dispose();
    _scrollCtrl.dispose();
    _pulseCtrl.dispose();
    _silenceTimer?.cancel();
    _stt.stop();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<MakoProvider>(
      builder: (context, mako, _) {
        // auto scroll on new messages
        WidgetsBinding.instance.addPostFrameCallback((_) => _scrollToBottom());

        return Scaffold(
          backgroundColor: const Color(0xFF07100A),
          body: SafeArea(
            child: Column(
              children: [
                // ── Status bar ──────────────────────────────
                StatusBar(
                  connStatus: mako.connStatus,
                  makoStatus: mako.makoStatus,
                  onSettings: () => Navigator.push(
                      context,
                      MaterialPageRoute(
                          builder: (_) => const SettingsScreen())),
                ),

                // ── Messages ────────────────────────────────
                Expanded(
                  child: _buildMessageList(mako),
                ),

                // ── Live indicator ──────────────────────────
                if (mako.mode == ConversationMode.live)
                  LiveIndicator(
                    isListening: _isListening,
                    isSpeaking: mako.makoStatus == MakoStatus.speaking,
                    isThinking: mako.makoStatus == MakoStatus.thinking,
                    interimText: _interimText,
                    pulseCtrl: _pulseCtrl,
                  ),

                // ── Input area ──────────────────────────────
                if (mako.mode != ConversationMode.live) _buildInputArea(mako),

                // ── Mode bar ────────────────────────────────
                ModeBar(
                  currentMode: mako.mode,
                  onModeChanged: _onModeChanged,
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildMessageList(MakoProvider mako) {
    final msgs = mako.messages;
    return ListView.builder(
      controller: _scrollCtrl,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      itemCount: msgs.length + (mako.isThinking ? 1 : 0),
      itemBuilder: (context, i) {
        if (i == msgs.length && mako.isThinking) {
          return ThinkingBubble(text: mako.thinkingText);
        }
        return MessageBubble(
          message: msgs[i],
          onTap: msgs[i].debugData != null
              ? () => _showInspector(context, msgs[i])
              : null,
        );
      },
    );
  }

  Widget _buildInputArea(MakoProvider mako) {
    final isVoice = mako.mode == ConversationMode.voice;

    return Container(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
      decoration: const BoxDecoration(
        color: Color(0xFF07100A),
        border: Border(top: BorderSide(color: Color(0xFF0A3A1A), width: 1)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          if (!isVoice)
            Expanded(
              child: Container(
                constraints: const BoxConstraints(maxHeight: 120),
                decoration: BoxDecoration(
                  color: const Color(0xFF0D1A10),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: const Color(0xFF1A3A25)),
                ),
                child: TextField(
                  controller: _textCtrl,
                  maxLines: null,
                  style: const TextStyle(
                    color: Color(0xFFB8DDC8),
                    fontSize: 15,
                    fontFamily: 'monospace',
                  ),
                  decoration: const InputDecoration(
                    hintText: 'Talk to Mako...',
                    hintStyle:
                        TextStyle(color: Color(0xFF2A5A3A), fontSize: 15),
                    border: InputBorder.none,
                    contentPadding:
                        EdgeInsets.symmetric(horizontal: 14, vertical: 11),
                  ),
                  onSubmitted: (_) => _sendText(),
                ),
              ),
            ),

          const SizedBox(width: 10),

          // mic button
          if (isVoice || mako.mode == ConversationMode.voice)
            _MicButton(
              isListening: _isListening,
              pulseCtrl: _pulseCtrl,
              onTap: () {
                HapticFeedback.mediumImpact();
                if (_isListening)
                  _stopListening();
                else
                  _startListening();
              },
            ),

          // send button (text mode only)
          if (!isVoice) ...[
            const SizedBox(width: 8),
            GestureDetector(
              onTap: _sendText,
              child: Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: const Color(0xFF00FF88),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Icon(Icons.send_rounded,
                    color: Color(0xFF07100A), size: 20),
              ),
            ),
          ],
        ],
      ),
    );
  }

  void _showInspector(BuildContext context, ChatMessage msg) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => InspectorSheet(debugData: msg.debugData!),
    );
  }
}

// ── Mic button ────────────────────────────────────────────────────────────────
class _MicButton extends StatelessWidget {
  final bool isListening;
  final AnimationController pulseCtrl;
  final VoidCallback onTap;

  const _MicButton({
    required this.isListening,
    required this.pulseCtrl,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedBuilder(
        animation: pulseCtrl,
        builder: (_, __) {
          return Container(
            width: 56,
            height: 56,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: isListening
                  ? Color.lerp(const Color(0xFF001A0A), const Color(0xFF003A1A),
                      pulseCtrl.value)
                  : const Color(0xFF0D1A10),
              border: Border.all(
                color: isListening
                    ? Color.lerp(const Color(0xFF00FF88),
                        const Color(0xFF00AA55), pulseCtrl.value)!
                    : const Color(0xFF1A3A25),
                width: isListening ? 2 : 1,
              ),
              boxShadow: isListening
                  ? [
                      BoxShadow(
                        color: const Color(0xFF00FF88)
                            .withOpacity(0.15 + 0.15 * pulseCtrl.value),
                        blurRadius: 16,
                        spreadRadius: 2,
                      )
                    ]
                  : null,
            ),
            child: Icon(
              isListening ? Icons.mic : Icons.mic_none_rounded,
              color: isListening
                  ? const Color(0xFF00FF88)
                  : const Color(0xFF2A5A3A),
              size: 24,
            ),
          );
        },
      ),
    );
  }
}

// ── Inspector bottom sheet ────────────────────────────────────────────────────
class InspectorSheet extends StatelessWidget {
  final Map<String, dynamic> debugData;

  const InspectorSheet({super.key, required this.debugData});

  static const _colors = {
    'blue': Color(0xFF3B82F6),
    'purple': Color(0xFFA855F7),
    'green': Color(0xFF22C55E),
    'amber': Color(0xFFF59E0B),
    'cyan': Color(0xFF06B6D4),
    'red': Color(0xFFEF4444),
  };

  static const _bgColors = {
    'blue': Color(0xFF050E1A),
    'purple': Color(0xFF0B0515),
    'green': Color(0xFF020A04),
    'amber': Color(0xFF150900),
    'cyan': Color(0xFF020C0C),
    'red': Color(0xFF120303),
  };

  int _tokens(String text) =>
      (text.split(RegExp(r'\s+')).where((w) => w.isNotEmpty).length * 1.3)
          .round()
          .clamp(1, 999999);

  @override
  Widget build(BuildContext context) {
    final sections =
        (debugData['sections'] as List? ?? []).cast<Map<String, dynamic>>();
    final total = sections.fold<int>(0, (a, s) => a + _tokens(s['text'] ?? ''));

    return DraggableScrollableSheet(
      initialChildSize: 0.85,
      maxChildSize: 0.95,
      minChildSize: 0.4,
      builder: (_, ctrl) => Container(
        decoration: const BoxDecoration(
          color: Color(0xFF060D07),
          borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
          border: Border(top: BorderSide(color: Color(0xFF0A3A1A))),
        ),
        child: Column(
          children: [
            // handle
            Container(
              margin: const EdgeInsets.only(top: 10, bottom: 6),
              width: 36,
              height: 3,
              decoration: BoxDecoration(
                color: const Color(0xFF1A3A25),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            // header
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 4, 20, 12),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text('⬡ PROMPT INSPECTOR',
                      style: TextStyle(
                        color: Color(0xFF00FF88),
                        fontSize: 11,
                        letterSpacing: 2.5,
                        fontFamily: 'monospace',
                      )),
                  Text('$total TOKENS',
                      style: const TextStyle(
                        color: Color(0xFF2A5A3A),
                        fontSize: 11,
                        letterSpacing: 1,
                        fontFamily: 'monospace',
                      )),
                ],
              ),
            ),
            // token bar
            SizedBox(
              height: 3,
              child: Row(
                children: sections.map((s) {
                  final tok = _tokens(s['text'] ?? '');
                  final pct = total > 0 ? tok / total : 0.0;
                  return Expanded(
                    flex: (pct * 1000).round(),
                    child: Container(color: _colors[s['color']] ?? Colors.grey),
                  );
                }).toList(),
              ),
            ),
            // sections
            Expanded(
              child: ListView.separated(
                controller: ctrl,
                padding: const EdgeInsets.all(12),
                itemCount: sections.length,
                separatorBuilder: (_, __) => const SizedBox(height: 8),
                itemBuilder: (_, i) => _SectionCard(
                  section: sections[i],
                  accent: _colors[sections[i]['color']] ?? Colors.grey,
                  bg: _bgColors[sections[i]['color']] ??
                      const Color(0xFF060D07),
                  tokens: _tokens(sections[i]['text'] ?? ''),
                  total: total,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SectionCard extends StatefulWidget {
  final Map<String, dynamic> section;
  final Color accent;
  final Color bg;
  final int tokens;
  final int total;

  const _SectionCard({
    required this.section,
    required this.accent,
    required this.bg,
    required this.tokens,
    required this.total,
  });

  @override
  State<_SectionCard> createState() => _SectionCardState();
}

class _SectionCardState extends State<_SectionCard> {
  bool _expanded = true;

  @override
  Widget build(BuildContext context) {
    final pct = widget.total > 0
        ? (widget.tokens / widget.total * 100).toStringAsFixed(1)
        : '0';

    return Container(
      decoration: BoxDecoration(
        border: Border.all(color: widget.accent.withOpacity(0.3)),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Column(
        children: [
          GestureDetector(
            onTap: () => setState(() => _expanded = !_expanded),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
              decoration: BoxDecoration(
                color: widget.accent.withOpacity(0.08),
                borderRadius: _expanded
                    ? const BorderRadius.vertical(top: Radius.circular(5))
                    : BorderRadius.circular(5),
              ),
              child: Row(
                children: [
                  Container(
                    width: 7,
                    height: 7,
                    margin: const EdgeInsets.only(right: 9),
                    decoration: BoxDecoration(
                      color: widget.accent,
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(
                          color: widget.accent.withOpacity(0.4),
                          blurRadius: 5,
                        )
                      ],
                    ),
                  ),
                  Expanded(
                    child: Text(
                      widget.section['label'] ?? '',
                      style: TextStyle(
                        color: widget.accent,
                        fontSize: 9,
                        letterSpacing: 2,
                        fontFamily: 'monospace',
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  Text(
                    '${widget.tokens} tok · $pct%',
                    style: TextStyle(
                      color: widget.accent.withOpacity(0.5),
                      fontSize: 9,
                      fontFamily: 'monospace',
                    ),
                  ),
                  const SizedBox(width: 8),
                  Icon(
                    _expanded ? Icons.expand_less : Icons.expand_more,
                    color: widget.accent.withOpacity(0.4),
                    size: 16,
                  ),
                ],
              ),
            ),
          ),
          if (_expanded)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: widget.bg,
                borderRadius:
                    const BorderRadius.vertical(bottom: Radius.circular(5)),
              ),
              constraints: const BoxConstraints(maxHeight: 220),
              child: SingleChildScrollView(
                child: SelectableText(
                  widget.section['text'] ?? '',
                  style: TextStyle(
                    color: widget.accent.withOpacity(0.8),
                    fontSize: 11,
                    height: 1.7,
                    fontFamily: 'monospace',
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
