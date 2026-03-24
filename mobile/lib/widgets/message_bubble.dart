// lib/widgets/message_bubble.dart
import 'package:flutter/material.dart';
import '../providers/mako_provider.dart';

class MessageBubble extends StatelessWidget {
  final ChatMessage message;
  final VoidCallback? onTap;

  const MessageBubble({super.key, required this.message, this.onTap});

  @override
  Widget build(BuildContext context) {
    final isUser = message.role == MessageRole.user;

    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment:
            isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
        children: [
          // label
          Padding(
            padding: const EdgeInsets.only(bottom: 4, left: 4, right: 4),
            child: Text(
              isUser ? 'YOU' : 'MAKO',
              style: TextStyle(
                fontSize: 8,
                letterSpacing: 2.5,
                color:
                    isUser ? const Color(0xFF2A5A7A) : const Color(0xFF2A5A3A),
                fontFamily: 'monospace',
              ),
            ),
          ),
          // bubble
          GestureDetector(
            onTap: onTap,
            child: Container(
              constraints: BoxConstraints(
                maxWidth: MediaQuery.of(context).size.width * 0.82,
              ),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                color:
                    isUser ? const Color(0xFF001828) : const Color(0xFF001A0A),
                borderRadius: BorderRadius.only(
                  topLeft: const Radius.circular(14),
                  topRight: const Radius.circular(14),
                  bottomLeft: Radius.circular(isUser ? 14 : 3),
                  bottomRight: Radius.circular(isUser ? 3 : 14),
                ),
                border: Border.all(
                  color: isUser
                      ? const Color(0xFF003355)
                      : const Color(0xFF0A3A1A),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildContent(message.content, isUser),
                  if (onTap != null) ...[
                    const SizedBox(height: 6),
                    const Text(
                      '⬡ tap to inspect',
                      style: TextStyle(
                        fontSize: 8,
                        color: Color(0xFF1A4A2A),
                        letterSpacing: 1,
                        fontFamily: 'monospace',
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
          // time
          Padding(
            padding: const EdgeInsets.only(top: 4, left: 4, right: 4),
            child: Text(
              _formatTime(message.time),
              style: const TextStyle(
                fontSize: 8,
                color: Color(0xFF1A3A25),
                fontFamily: 'monospace',
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildContent(String content, bool isUser) {
    // simple markdown — bold and line breaks
    final spans = <TextSpan>[];
    final parts = content.split(RegExp(r'(\*\*.*?\*\*|\*.*?\*)'));
    final boldPattern = RegExp(r'^\*\*?(.*?)\*\*?$');

    for (final part in content.split('\n')) {
      if (spans.isNotEmpty) {
        spans.add(const TextSpan(text: '\n'));
      }
      final words = part.split(RegExp(r'(\*\*[^*]+\*\*|\*[^*]+\*)'));
      for (final word in words) {
        final boldMatch = boldPattern.firstMatch(word);
        if (boldMatch != null) {
          spans.add(TextSpan(
            text: boldMatch.group(1),
            style: const TextStyle(
              fontWeight: FontWeight.bold,
              color: Color(0xFF00FF88),
            ),
          ));
        } else {
          spans.add(TextSpan(text: word));
        }
      }
    }

    return RichText(
      text: TextSpan(
        style: TextStyle(
          color: isUser ? const Color(0xFF7AB8DD) : const Color(0xFFB8DDC8),
          fontSize: 15,
          height: 1.55,
          fontFamily: 'sans-serif',
        ),
        children: spans.isEmpty ? [TextSpan(text: content)] : spans,
      ),
    );
  }

  String _formatTime(DateTime t) {
    final h = t.hour.toString().padLeft(2, '0');
    final m = t.minute.toString().padLeft(2, '0');
    final s = t.second.toString().padLeft(2, '0');
    return '$h:$m:$s';
  }
}

// ── Thinking bubble ───────────────────────────────────────────────────────────
class ThinkingBubble extends StatefulWidget {
  final String text;
  const ThinkingBubble({super.key, required this.text});

  @override
  State<ThinkingBubble> createState() => _ThinkingBubbleState();
}

class _ThinkingBubbleState extends State<ThinkingBubble>
    with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 900))
      ..repeat(reverse: true);
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.only(bottom: 4, left: 4),
            child: Text('MAKO',
                style: TextStyle(
                  fontSize: 8,
                  letterSpacing: 2.5,
                  color: Color(0xFF2A5A3A),
                  fontFamily: 'monospace',
                )),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              color: const Color(0xFF0A1A0D),
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(14),
                topRight: Radius.circular(14),
                bottomLeft: Radius.circular(3),
                bottomRight: Radius.circular(14),
              ),
              border: Border.all(
                  color: const Color(0xFF0A3A1A), style: BorderStyle.solid),
            ),
            child: widget.text.isEmpty
                ? Row(
                    mainAxisSize: MainAxisSize.min,
                    children: List.generate(
                        3,
                        (i) => AnimatedBuilder(
                              animation: _ctrl,
                              builder: (_, __) => Container(
                                margin:
                                    const EdgeInsets.symmetric(horizontal: 3),
                                width: 5,
                                height: 5,
                                decoration: BoxDecoration(
                                  shape: BoxShape.circle,
                                  color: Color.lerp(
                                    const Color(0xFF1A4A2A),
                                    const Color(0xFF00FF88),
                                    ((_ctrl.value + i * 0.33) % 1.0),
                                  ),
                                ),
                              ),
                            )),
                  )
                : Text(
                    '💭 ${widget.text}',
                    style: const TextStyle(
                      color: Color(0xFF3A6A4A),
                      fontSize: 12,
                      fontStyle: FontStyle.italic,
                      fontFamily: 'monospace',
                    ),
                  ),
          ),
        ],
      ),
    );
  }
}
