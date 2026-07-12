// lib/widgets/status_banner.dart — human-readable connection state.
// Hidden while online; otherwise a slim banner explaining exactly what's
// happening (checking / Render waking with elapsed seconds / errors).
import 'package:flutter/material.dart';
import '../providers/mako_provider.dart';
import '../theme.dart';

class StatusBanner extends StatelessWidget {
  final MakoStatus status;
  final String detail;
  final VoidCallback onRetry;
  const StatusBanner(
      {super.key,
      required this.status,
      required this.detail,
      required this.onRetry});

  @override
  Widget build(BuildContext context) {
    if (status == MakoStatus.online) return const SizedBox.shrink();

    final (color, icon, showSpinner) = switch (status) {
      MakoStatus.checking => (MakoColors.textDim, Icons.search, true),
      MakoStatus.waking => (MakoColors.warn, Icons.bedtime_outlined, true),
      MakoStatus.connecting => (MakoColors.accent, Icons.wifi, true),
      MakoStatus.error => (MakoColors.err, Icons.error_outline, false),
      _ => (MakoColors.textDim, Icons.cloud_off, false),
    };

    return Material(
      color: color.withValues(alpha: 0.12),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        child: Row(
          children: [
            if (showSpinner)
              SizedBox(
                  width: 14,
                  height: 14,
                  child: CircularProgressIndicator(
                      strokeWidth: 2, color: color))
            else
              Icon(icon, size: 16, color: color),
            const SizedBox(width: 10),
            Expanded(
              child: Text(detail,
                  style: TextStyle(color: color, fontSize: 13, height: 1.3)),
            ),
            if (status == MakoStatus.error)
              TextButton(
                onPressed: onRetry,
                child: const Text('RETRY',
                    style: TextStyle(
                        color: MakoColors.accent,
                        fontSize: 12,
                        fontWeight: FontWeight.bold)),
              ),
          ],
        ),
      ),
    );
  }
}

/// Small colored dot + label for the app bar.
class StatusPill extends StatelessWidget {
  final MakoStatus status;
  const StatusPill({super.key, required this.status});

  @override
  Widget build(BuildContext context) {
    final (color, label) = switch (status) {
      MakoStatus.online => (MakoColors.accent, 'ONLINE'),
      MakoStatus.waking => (MakoColors.warn, 'WAKING'),
      MakoStatus.checking => (MakoColors.textDim, 'CHECKING'),
      MakoStatus.connecting => (MakoColors.warn, 'CONNECTING'),
      MakoStatus.error => (MakoColors.err, 'ERROR'),
      _ => (MakoColors.textDim, 'OFFLINE'),
    };
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(
            color: color,
            shape: BoxShape.circle,
            boxShadow: [
              if (status == MakoStatus.online)
                BoxShadow(color: color.withValues(alpha: 0.6), blurRadius: 6),
            ],
          ),
        ),
        const SizedBox(width: 6),
        Text(label,
            style: TextStyle(
                color: color,
                fontSize: 11,
                fontWeight: FontWeight.w600,
                letterSpacing: 1.2)),
      ],
    );
  }
}
