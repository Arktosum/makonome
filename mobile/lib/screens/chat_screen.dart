// lib/screens/chat_screen.dart — the conversation.
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/mako_provider.dart';
import '../theme.dart';
import '../widgets/animated_background.dart';
import '../widgets/message_bubble.dart';
import '../widgets/status_banner.dart';
import 'about_screen.dart';
import 'settings_screen.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _input = TextEditingController();
  final _scroll = ScrollController();

  void _send(MakoProvider mako) {
    final text = _input.text.trim();
    if (text.isEmpty) return;
    mako.send(text);
    _input.clear();
    _scrollDown();
  }

  void _scrollDown() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.animateTo(_scroll.position.maxScrollExtent,
            duration: const Duration(milliseconds: 250),
            curve: Curves.easeOut);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<MakoProvider>(
      builder: (context, mako, _) {
        // keep view pinned to the latest message
        _scrollDown();
        final online = mako.status == MakoStatus.online;

        return Scaffold(
          appBar: AppBar(
            title: Row(
              children: [
                ShaderMask(
                  shaderCallback: (r) => const LinearGradient(
                    colors: [MakoColors.accent, Color(0xFF00B4D8)],
                  ).createShader(r),
                  child: const Text('MAKO',
                      style: TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w900,
                          fontSize: 22,
                          letterSpacing: 3)),
                ),
                const SizedBox(width: 12),
                StatusPill(status: mako.status),
              ],
            ),
            actions: [
              IconButton(
                tooltip: 'About Mako',
                icon: const Icon(Icons.auto_awesome_outlined,
                    color: MakoColors.textDim, size: 21),
                onPressed: () => Navigator.push(context,
                    MaterialPageRoute(builder: (_) => const AboutScreen())),
              ),
              IconButton(
                tooltip: 'Settings',
                icon: const Icon(Icons.settings_outlined,
                    color: MakoColors.textDim, size: 21),
                onPressed: () => Navigator.push(context,
                    MaterialPageRoute(builder: (_) => const SettingsScreen())),
              ),
            ],
            bottom: PreferredSize(
              preferredSize: const Size.fromHeight(1),
              child: Container(
                  height: 1, color: Colors.white.withValues(alpha: 0.05)),
            ),
          ),
          body: AnimatedBackground(
            child: Column(
              children: [
                StatusBanner(
                  status: mako.status,
                  detail: mako.statusDetail,
                  onRetry: mako.connect,
                ),
                Expanded(
                  child: mako.messages.isEmpty
                      ? const _EmptyState()
                      : ListView.builder(
                          controller: _scroll,
                          padding: const EdgeInsets.fromLTRB(14, 12, 14, 4),
                          itemCount: mako.messages.length,
                          itemBuilder: (_, i) =>
                              MessageBubble(message: mako.messages[i]),
                        ),
                ),
                if (mako.thinking) _ThinkingBar(mako: mako),
                _inputBar(mako, online),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _inputBar(MakoProvider mako, bool online) {
    return SafeArea(
      child: Container(
        padding: const EdgeInsets.fromLTRB(12, 8, 10, 12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Expanded(
              child: Container(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(26),
                  boxShadow: [
                    if (online)
                      BoxShadow(
                          color: MakoColors.accent.withValues(alpha: 0.07),
                          blurRadius: 12),
                  ],
                ),
                child: TextField(
                  controller: _input,
                  enabled: online,
                  style: const TextStyle(color: MakoColors.text),
                  textInputAction: TextInputAction.send,
                  onSubmitted: (_) => _send(mako),
                  minLines: 1,
                  maxLines: 4,
                  decoration: InputDecoration(
                    hintText:
                        online ? 'talk to Mako…' : 'waiting for connection…',
                    hintStyle: const TextStyle(color: MakoColors.textDim),
                    filled: true,
                    fillColor: MakoColors.surfaceLight,
                    contentPadding: const EdgeInsets.symmetric(
                        horizontal: 18, vertical: 11),
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(26),
                      borderSide: BorderSide(
                          color: Colors.white.withValues(alpha: 0.06)),
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(26),
                      borderSide: BorderSide(
                          color: MakoColors.accent.withValues(alpha: 0.45)),
                    ),
                    disabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(26),
                      borderSide: BorderSide.none,
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(width: 8),
            GestureDetector(
              onTap: online ? () => _send(mako) : null,
              child: Container(
                width: 46,
                height: 46,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: online
                      ? const LinearGradient(
                          colors: [MakoColors.accent, Color(0xFF00B4D8)],
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight)
                      : null,
                  color: online ? null : MakoColors.surfaceLight,
                  boxShadow: [
                    if (online)
                      BoxShadow(
                          color: MakoColors.accent.withValues(alpha: 0.3),
                          blurRadius: 10),
                  ],
                ),
                child: Icon(Icons.arrow_upward_rounded,
                    color: online ? Colors.black : MakoColors.textDim,
                    size: 24),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ThinkingBar extends StatelessWidget {
  final MakoProvider mako;
  const _ThinkingBar({required this.mako});

  @override
  Widget build(BuildContext context) {
    final note = mako.toolNote != null
        ? '🔧 ${mako.toolNote}'
        : mako.thought != null
            ? '💭 ${mako.thought}'
            : 'thinking…';
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.fromLTRB(14, 2, 60, 6),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(
          color: MakoColors.surface.withValues(alpha: 0.8),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: MakoColors.accent.withValues(alpha: 0.2)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const _PulsingDot(),
            const SizedBox(width: 10),
            Flexible(
              child: Text(
                note,
                style: const TextStyle(
                    color: MakoColors.textDim,
                    fontSize: 12,
                    fontStyle: FontStyle.italic),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PulsingDot extends StatefulWidget {
  const _PulsingDot();

  @override
  State<_PulsingDot> createState() => _PulsingDotState();
}

class _PulsingDotState extends State<_PulsingDot>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
      vsync: this, duration: const Duration(milliseconds: 900))
    ..repeat(reverse: true);

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: Tween(begin: 0.3, end: 1.0).animate(_c),
      child: Container(
        width: 9,
        height: 9,
        decoration: const BoxDecoration(
            color: MakoColors.accent, shape: BoxShape.circle),
      ),
    );
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          ShaderMask(
            shaderCallback: (r) => const LinearGradient(
              colors: [MakoColors.accent, Color(0xFF00B4D8)],
            ).createShader(r),
            child: const Text('🌊',
                style: TextStyle(fontSize: 46, color: Colors.white)),
          ),
          const SizedBox(height: 14),
          const Text('Say something — Mako remembers everything.',
              style: TextStyle(color: MakoColors.textDim, fontSize: 14)),
          const SizedBox(height: 6),
          const Text('tap ✨ up top to see everything she can do',
              style: TextStyle(color: MakoColors.textDim, fontSize: 12)),
        ],
      ),
    );
  }
}
