// lib/widgets/mode_bar.dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../providers/mako_provider.dart';

class ModeBar extends StatelessWidget {
  final ConversationMode currentMode;
  final ValueChanged<ConversationMode> onModeChanged;

  const ModeBar({
    super.key,
    required this.currentMode,
    required this.onModeChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 56,
      decoration: const BoxDecoration(
        color: Color(0xFF060D07),
        border: Border(top: BorderSide(color: Color(0xFF0A3A1A))),
      ),
      child: Row(
        children: ConversationMode.values.map((mode) {
          final active = currentMode == mode;
          return Expanded(
            child: GestureDetector(
              onTap: () {
                if (mode != currentMode) {
                  HapticFeedback.selectionClick();
                  onModeChanged(mode);
                }
              },
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                decoration: BoxDecoration(
                  border: Border(
                    top: BorderSide(
                      color:
                          active ? const Color(0xFF00FF88) : Colors.transparent,
                      width: 2,
                    ),
                  ),
                ),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      _iconFor(mode),
                      size: 18,
                      color: active
                          ? const Color(0xFF00FF88)
                          : const Color(0xFF2A5A3A),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      _labelFor(mode),
                      style: TextStyle(
                        fontSize: 8,
                        letterSpacing: 1.5,
                        fontFamily: 'monospace',
                        color: active
                            ? const Color(0xFF00FF88)
                            : const Color(0xFF2A5A3A),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          );
        }).toList(),
      ),
    );
  }

  IconData _iconFor(ConversationMode mode) => switch (mode) {
        ConversationMode.text => Icons.keyboard_rounded,
        ConversationMode.voice => Icons.mic_rounded,
        ConversationMode.live => Icons.wifi_tethering_rounded,
      };

  String _labelFor(ConversationMode mode) => switch (mode) {
        ConversationMode.text => 'TEXT',
        ConversationMode.voice => 'VOICE',
        ConversationMode.live => 'LIVE',
      };
}
