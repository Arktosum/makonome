// lib/widgets/status_bar.dart
import 'package:flutter/material.dart';
import '../providers/mako_provider.dart';
import '../services/websocket_service.dart';

class StatusBar extends StatelessWidget {
  final ConnectionStatus connStatus;
  final MakoStatus makoStatus;
  final VoidCallback onSettings;

  const StatusBar({
    super.key,
    required this.connStatus,
    required this.makoStatus,
    required this.onSettings,
  });

  @override
  Widget build(BuildContext context) {
    final isOnline = connStatus == ConnectionStatus.connected;
    final statusText = switch (makoStatus) {
      MakoStatus.thinking => 'THINKING',
      MakoStatus.speaking => 'SPEAKING',
      MakoStatus.listening => 'LISTENING',
      MakoStatus.idle => isOnline ? 'ONLINE' : 'CONNECTING',
    };
    final statusColor = switch (makoStatus) {
      MakoStatus.thinking => const Color(0xFFFFAA00),
      MakoStatus.speaking => const Color(0xFF00DDCC),
      MakoStatus.listening => const Color(0xFF00FF88),
      MakoStatus.idle =>
        isOnline ? const Color(0xFF00FF88) : const Color(0xFF2A5A3A),
    };

    return Container(
      height: 50,
      padding: const EdgeInsets.symmetric(horizontal: 18),
      decoration: const BoxDecoration(
        color: Color(0xFF07100A),
        border: Border(bottom: BorderSide(color: Color(0xFF0A3A1A))),
      ),
      child: Row(
        children: [
          // logo
          const Text('MAKO',
              style: TextStyle(
                color: Color(0xFF00FF88),
                fontSize: 16,
                letterSpacing: 5,
                fontWeight: FontWeight.bold,
                fontFamily: 'monospace',
              )),
          const Spacer(),
          // status dot + text
          AnimatedContainer(
            duration: const Duration(milliseconds: 400),
            width: 6,
            height: 6,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: statusColor,
              boxShadow: [
                BoxShadow(
                  color: statusColor.withOpacity(0.5),
                  blurRadius: 6,
                )
              ],
            ),
          ),
          const SizedBox(width: 7),
          Text(statusText,
              style: TextStyle(
                color: statusColor,
                fontSize: 9,
                letterSpacing: 2,
                fontFamily: 'monospace',
              )),
          const SizedBox(width: 14),
          // settings
          GestureDetector(
            onTap: onSettings,
            child: const Icon(Icons.tune_rounded,
                color: Color(0xFF2A5A3A), size: 20),
          ),
        ],
      ),
    );
  }
}
