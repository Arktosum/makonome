// lib/screens/chat_screen.dart — the conversation.
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/mako_provider.dart';
import '../theme.dart';
import '../widgets/animated_background.dart';
import '../widgets/message_bubble.dart';
import '../widgets/status_banner.dart';
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
                const Text('Mako',
                    style: TextStyle(
                        color: MakoColors.accent,
                        fontWeight: FontWeight.bold,
                        fontSize: 22)),
                const SizedBox(width: 12),
                StatusPill(status: mako.status),
              ],
            ),
            actions: [
              IconButton(
                icon: const Icon(Icons.settings_outlined,
                    color: MakoColors.textDim),
                onPressed: () => Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => const SettingsScreen()),
                ),
              ),
            ],
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
        padding: const EdgeInsets.fromLTRB(12, 8, 8, 10),
        child: Row(
          children: [
            Expanded(
              child: TextField(
                controller: _input,
                enabled: online,
                style: const TextStyle(color: MakoColors.text),
                textInputAction: TextInputAction.send,
                onSubmitted: (_) => _send(mako),
                minLines: 1,
                maxLines: 4,
                decoration: InputDecoration(
                  hintText: online ? 'talk to Mako…' : 'waiting for connection…',
                  hintStyle: const TextStyle(color: MakoColors.textDim),
                  filled: true,
                  fillColor: MakoColors.surfaceLight,
                  contentPadding:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(24),
                    borderSide: BorderSide.none,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 6),
            IconButton(
              onPressed: online ? () => _send(mako) : null,
              icon: Icon(Icons.send_rounded,
                  color: online ? MakoColors.accent : MakoColors.textDim),
              iconSize: 26,
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
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 6),
      child: Row(
        children: [
          const SizedBox(
            width: 12,
            height: 12,
            child: CircularProgressIndicator(
                strokeWidth: 2, color: MakoColors.accent),
          ),
          const SizedBox(width: 10),
          Expanded(
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
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('🌊', style: TextStyle(fontSize: 42)),
          SizedBox(height: 12),
          Text('Say something — Mako remembers everything.',
              style: TextStyle(color: MakoColors.textDim, fontSize: 14)),
        ],
      ),
    );
  }
}
