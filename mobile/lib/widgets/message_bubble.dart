// lib/widgets/message_bubble.dart — chat bubbles with entrance animation.
// Mako replies that carry inspector data are tappable → prompt breakdown.
import 'package:flutter/material.dart';
import '../providers/mako_provider.dart';
import '../theme.dart';
import 'prompt_inspector.dart';

class MessageBubble extends StatelessWidget {
  final ChatMessage message;
  const MessageBubble({super.key, required this.message});

  @override
  Widget build(BuildContext context) {
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: 1),
      duration: const Duration(milliseconds: 260),
      curve: Curves.easeOutCubic,
      builder: (_, v, child) => Opacity(
        opacity: v,
        child: Transform.translate(offset: Offset(0, 10 * (1 - v)), child: child),
      ),
      child: _build(context),
    );
  }

  Widget _build(BuildContext context) {
    switch (message.role) {
      case 'system':
        return _systemLine();
      case 'user':
        return _bubble(
          context,
          alignment: Alignment.centerRight,
          gradient: const LinearGradient(
            colors: [Color(0xFF0E4A2E), Color(0xFF0B3B34)],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          border: null,
          label: null,
        );
      case 'heartbeat':
        return _bubble(
          context,
          alignment: Alignment.centerLeft,
          color: MakoColors.surface,
          border: Border.all(color: MakoColors.accent.withValues(alpha: 0.5)),
          glow: MakoColors.accent.withValues(alpha: 0.12),
          label: '💓 checked in on you',
        );
      default: // mako
        return _bubble(
          context,
          alignment: Alignment.centerLeft,
          color: MakoColors.surface,
          border: Border.all(color: Colors.white.withValues(alpha: 0.06)),
          label: null,
        );
    }
  }

  Widget _systemLine() => Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Center(
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.04),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(
              message.text,
              style: const TextStyle(color: MakoColors.textDim, fontSize: 12),
              textAlign: TextAlign.center,
            ),
          ),
        ),
      );

  Widget _bubble(
    BuildContext context, {
    required Alignment alignment,
    Color? color,
    Gradient? gradient,
    Border? border,
    Color? glow,
    String? label,
  }) {
    final t = message.time;
    final timeStr =
        '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}';
    final hasInspector =
        message.role == 'mako' && (message.inspector?.isNotEmpty ?? false);

    final bubble = Container(
      margin: const EdgeInsets.symmetric(vertical: 4),
      padding: const EdgeInsets.fromLTRB(14, 10, 14, 8),
      constraints: const BoxConstraints(maxWidth: 320),
      decoration: BoxDecoration(
        color: color,
        gradient: gradient,
        border: border,
        borderRadius: BorderRadius.only(
          topLeft: const Radius.circular(18),
          topRight: const Radius.circular(18),
          bottomLeft:
              Radius.circular(alignment == Alignment.centerLeft ? 4 : 18),
          bottomRight:
              Radius.circular(alignment == Alignment.centerRight ? 4 : 18),
        ),
        boxShadow: [
          if (glow != null) BoxShadow(color: glow, blurRadius: 14),
          BoxShadow(
              color: Colors.black.withValues(alpha: 0.25),
              blurRadius: 6,
              offset: const Offset(0, 2)),
        ],
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
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(timeStr,
                  style: const TextStyle(
                      color: MakoColors.textDim, fontSize: 10)),
              if (hasInspector) ...[
                const SizedBox(width: 6),
                const Icon(Icons.data_usage,
                    size: 11, color: MakoColors.textDim),
                const Text(' tap for prompt',
                    style:
                        TextStyle(color: MakoColors.textDim, fontSize: 10)),
              ],
            ],
          ),
        ],
      ),
    );

    return Align(
      alignment: alignment,
      child: hasInspector
          ? GestureDetector(
              onTap: () => showPromptInspector(context, message.inspector!),
              child: bubble,
            )
          : bubble,
    );
  }
}
