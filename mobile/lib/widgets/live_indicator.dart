// lib/widgets/live_indicator.dart
import 'package:flutter/material.dart';

class LiveIndicator extends StatelessWidget {
  final bool isListening;
  final bool isSpeaking;
  final bool isThinking;
  final String interimText;
  final AnimationController pulseCtrl;

  const LiveIndicator({
    super.key,
    required this.isListening,
    required this.isSpeaking,
    required this.isThinking,
    required this.interimText,
    required this.pulseCtrl,
  });

  @override
  Widget build(BuildContext context) {
    final color = isSpeaking
        ? const Color(0xFF00DDCC)
        : isThinking
            ? const Color(0xFFFFAA00)
            : isListening
                ? const Color(0xFF00FF88)
                : const Color(0xFF1A3A25);

    final label = isSpeaking
        ? 'SPEAKING'
        : isThinking
            ? 'THINKING'
            : isListening
                ? 'LISTENING'
                : 'STANDBY';

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      decoration: BoxDecoration(
        color: const Color(0xFF060D07),
        border: Border(
          top: BorderSide(color: color.withOpacity(0.3)),
        ),
      ),
      child: Column(
        children: [
          // waveform
          AnimatedBuilder(
            animation: pulseCtrl,
            builder: (_, __) => Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: List.generate(9, (i) {
                final phase = (i / 9.0 + pulseCtrl.value) % 1.0;
                final height = isListening
                    ? 4.0 +
                        20.0 *
                            (0.5 +
                                0.5 *
                                    (phase < 0.5
                                        ? phase * 2
                                        : (1.0 - phase) * 2))
                    : 4.0;
                return AnimatedContainer(
                  duration: const Duration(milliseconds: 100),
                  margin: const EdgeInsets.symmetric(horizontal: 2),
                  width: 3,
                  height: height,
                  decoration: BoxDecoration(
                    color: color.withOpacity(isListening ? 0.8 : 0.2),
                    borderRadius: BorderRadius.circular(2),
                  ),
                );
              }),
            ),
          ),
          const SizedBox(height: 10),
          // status label
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                width: 5,
                height: 5,
                margin: const EdgeInsets.only(right: 7),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: color,
                  boxShadow: [
                    BoxShadow(
                      color: color.withOpacity(0.5),
                      blurRadius: 6,
                    )
                  ],
                ),
              ),
              Text(label,
                  style: TextStyle(
                    color: color,
                    fontSize: 9,
                    letterSpacing: 3,
                    fontFamily: 'monospace',
                  )),
            ],
          ),
          // interim transcript
          if (interimText.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              interimText,
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: Color(0xFF3A6A4A),
                fontSize: 13,
                fontStyle: FontStyle.italic,
              ),
            ),
          ],
        ],
      ),
    );
  }
}
