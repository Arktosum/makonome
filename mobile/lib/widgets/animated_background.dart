// lib/widgets/animated_background.dart — slow-breathing aurora behind the chat.
// Three soft green orbs drifting on long sine paths; subtle enough that text
// stays perfectly readable, alive enough that the app doesn't feel like a
// dead terminal.
import 'dart:math' as math;
import 'package:flutter/material.dart';

class AnimatedBackground extends StatefulWidget {
  final Widget child;
  const AnimatedBackground({super.key, required this.child});

  @override
  State<AnimatedBackground> createState() => _AnimatedBackgroundState();
}

class _AnimatedBackgroundState extends State<AnimatedBackground>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(seconds: 30),
  )..repeat();

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        Positioned.fill(
          child: AnimatedBuilder(
            animation: _controller,
            builder: (_, __) => CustomPaint(
              painter: _AuroraPainter(_controller.value),
            ),
          ),
        ),
        widget.child,
      ],
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }
}

class _Orb {
  final double cx, cy; // resting center (fraction of screen)
  final double rx, ry; // drift radius (fraction of screen)
  final double speed; // full drift cycles per controller loop
  final double phase;
  final double radius; // fraction of the shorter side
  final Color color;
  const _Orb(this.cx, this.cy, this.rx, this.ry, this.speed, this.phase,
      this.radius, this.color);
}

class _AuroraPainter extends CustomPainter {
  final double t; // 0..1
  _AuroraPainter(this.t);

  static const _orbs = [
    _Orb(0.15, 0.20, 0.18, 0.10, 1, 0.0, 0.85, Color(0xFF00E68A)),
    _Orb(0.90, 0.55, 0.12, 0.16, 2, 2.1, 0.70, Color(0xFF0E7A55)),
    _Orb(0.35, 0.95, 0.20, 0.08, 1, 4.2, 0.95, Color(0xFF00B4D8)),
    _Orb(0.70, 0.05, 0.15, 0.12, 1, 1.3, 0.60, Color(0xFF7A5CFF)),
  ];

  @override
  void paint(Canvas canvas, Size size) {
    final base = math.min(size.width, size.height);
    for (final o in _orbs) {
      final angle = 2 * math.pi * (t * o.speed) + o.phase;
      final center = Offset(
        (o.cx + o.rx * math.cos(angle)) * size.width,
        (o.cy + o.ry * math.sin(angle * 0.9)) * size.height,
      );
      // gentle breathing on top of the drift
      final breathe = 0.9 + 0.1 * math.sin(angle * 1.3);
      final radius = o.radius * base * breathe;

      final paint = Paint()
        ..shader = RadialGradient(
          colors: [
            o.color.withValues(alpha: 0.16),
            o.color.withValues(alpha: 0.05),
            o.color.withValues(alpha: 0.0),
          ],
          stops: const [0.0, 0.6, 1.0],
        ).createShader(Rect.fromCircle(center: center, radius: radius));
      canvas.drawCircle(center, radius, paint);
    }
  }

  @override
  bool shouldRepaint(_AuroraPainter old) => old.t != t;
}
