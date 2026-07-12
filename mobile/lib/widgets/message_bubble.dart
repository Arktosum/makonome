// lib/widgets/message_bubble.dart
import 'package:flutter/material.dart';
import '../providers/mako_provider.dart';
import '../theme.dart';

class MessageBubble extends StatelessWidget {
  final ChatMessage message;
  const MessageBubble({super.key, required this.message});

  @override
  Widget build(BuildContext context) {
    switch (message.role) {
      case 'system':
        return _systemLine();
      case 'user':
        return _bubble(
          alignment: Alignment.centerRight,
          color: MakoColors.userBubble,
          border: null,
          label: null,
        );
      case 'heartbeat':
        return _bubble(
          alignment: Alignment.centerLeft,
          color: MakoColors.surface,
          border: Border.all(color: MakoColors.accent.withValues(alpha: 0.45)),
          label: '💓 checked in on you',
        );
      default: // mako
        return _bubble(
          alignment: Alignment.centerLeft,
          color: MakoColors.surface,
          border: null,
          label: null,
        );
    }
  }

  Widget _systemLine() => Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Center(
          child: Text(
            message.text,
            style: const TextStyle(color: MakoColors.textDim, fontSize: 12),
            textAlign: TextAlign.center,
          ),
        ),
      );

  Widget _bubble({
    required Alignment alignment,
    required Color color,
    Border? border,
    String? label,
  }) {
    final t = message.time;
    final timeStr =
        '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}';

    return Align(
      alignment: alignment,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.fromLTRB(14, 10, 14, 8),
        constraints: const BoxConstraints(maxWidth: 320),
        decoration: BoxDecoration(
          color: color,
          border: border,
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(16),
            topRight: const Radius.circular(16),
            bottomLeft: Radius.circular(
                alignment == Alignment.centerLeft ? 4 : 16),
            bottomRight: Radius.circular(
                alignment == Alignment.centerRight ? 4 : 16),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            if (label != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 4),
                child: Text(label,
                    style: const TextStyle(
                        color: MakoColors.accent,
                        fontSize: 11,
                        fontWeight: FontWeight.w600)),
              ),
            SelectableText(message.text,
                style: const TextStyle(
                    color: MakoColors.text, fontSize: 15, height: 1.35)),
            const SizedBox(height: 3),
            Text(timeStr,
                style:
                    const TextStyle(color: MakoColors.textDim, fontSize: 10)),
          ],
        ),
      ),
    );
  }
}
