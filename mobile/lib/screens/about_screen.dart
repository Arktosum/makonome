// lib/screens/about_screen.dart — everything Mako does, documented in-app.
import 'package:flutter/material.dart';
import '../theme.dart';

class AboutScreen extends StatelessWidget {
  const AboutScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('About Mako')),
      body: ListView(
        padding: const EdgeInsets.all(18),
        children: const [
          _Hero(),
          _Section('🟢 CONNECTION STATES', [
            _Item('ONLINE', 'Live WebSocket to Mako — everything works.'),
            _Item('CHECKING', 'Probing the server before connecting.'),
            _Item('WAKING',
                'Render\'s free tier put Mako to sleep after ~15 idle minutes. '
                'The app is poking her awake — cold starts take 30–60s. '
                'The counter shows elapsed time.'),
            _Item('CONNECTING', 'Server is up; opening the live connection.'),
            _Item('ERROR',
                'Something needs your attention — wrong URL, rejected token, '
                'or the server would not wake after 2 minutes. The banner '
                'says exactly which, with a RETRY button.'),
          ]),
          _Section('💬 CHAT', [
            _Item('One continuous Mako',
                'This app, the web dashboard, and the API all talk to the '
                'same brain. Tell her something here, she knows it everywhere.'),
            _Item('Tap a reply → prompt breakdown',
                'Any Mako reply marked "tap for prompt" opens the inspector: '
                'a colored token bar showing exactly what was sent to the '
                'model — personality, identity notes, people, memories, your '
                'message — with per-section token estimates.'),
            _Item('💭 / 🔧 ticker',
                'While she thinks you see her live reasoning and which tool '
                'she is using (web search, weather, finance, notes...).'),
            _Item('History',
                'The last 200 messages are stored on this phone. Clearing '
                'them (Settings) does NOT touch Mako\'s real memory.'),
          ]),
          _Section('💓 HEARTBEAT — SHE TEXTS FIRST', [
            _Item('When',
                'Every hour she gets one genuine chance to reach out — an '
                'open thread whose moment arrived, something time-relevant. '
                'Recent conversation doesn\'t mute her, but almost every '
                'check ends in silence, on purpose.'),
            _Item('Limits',
                'Never between 23:00–08:00 · at most one attempt per hour · '
                'her own judgment (SILENT) is the real gate.'),
            _Item('In the chat',
                'Green-bordered 💓 bubbles are her check-ins. Small gray '
                'lines show when she checked in and chose silence, or when '
                'she 🪞 reflected / 🗜 consolidated memories.'),
            _Item('⚠️ Needs an awake server',
                'If Render is asleep, the heartbeat is too. A free uptime '
                'pinger (e.g. UptimeRobot) hitting /api/health every 10 min '
                'keeps her alive around the clock.'),
          ]),
          _Section('📲 PUSH NOTIFICATIONS', [
            _Item('How',
                'Heartbeat messages are also pushed to this phone through '
                'ntfy — they arrive even when this app is closed.'),
            _Item('Setup',
                '1. Server env: MAKO_NTFY_TOPIC = a long random secret\n'
                '2. Install the free "ntfy" app\n'
                '3. Subscribe to that exact topic\n'
                '4. Settings → "Send test notification" to verify\n'
                '5. Allow ntfy to ignore battery optimization'),
            _Item('What pushes',
                'Only unprompted heartbeat check-ins. Normal replies don\'t '
                'push — you\'re already in the app when they happen.'),
          ]),
          _Section('🧠 HOW HER MEMORY WORKS', [
            _Item('Episodic',
                'After meaningful exchanges a background curator saves what '
                'mattered. Retrieval mixes semantic similarity with recency.'),
            _Item('Notes',
                'Living documents: about you, current context, open threads, '
                'one note per person in your life, topic notes.'),
            _Item('Journal & reflection',
                'Mako keeps a first-person journal. Weekly she rereads it '
                'and rewrites her own identity — who she is emerges from '
                'your history together, not from a hardcoded prompt.'),
            _Item('Consolidation',
                'Weekly she distills raw memories into a "[week of ...]" '
                'summary, and your identity document evolves only from '
                'durable patterns — never single remarks.'),
          ]),
          _Section('⚙️ SETTINGS FIELDS', [
            _Item('Server URL',
                'The base https address (no /ws). Forgiving of pasted '
                'ws:// URLs — it normalizes them.'),
            _Item('Access token',
                'Must match MAKO_DASH_TOKEN on the server. "Test" checks '
                'reachability and whether the token is accepted.'),
            _Item('ntfy topic',
                'Stored here just for reference/copying — the real '
                'subscription lives in the ntfy app.'),
          ]),
          SizedBox(height: 10),
          Center(
            child: Text('Mako v2 · model-agnostic · she remembers 🌊',
                style: TextStyle(color: MakoColors.textDim, fontSize: 12)),
          ),
          SizedBox(height: 20),
        ],
      ),
    );
  }
}

class _Hero extends StatelessWidget {
  const _Hero();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            MakoColors.accent.withValues(alpha: 0.10),
            const Color(0xFF00B4D8).withValues(alpha: 0.06),
          ],
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: MakoColors.accent.withValues(alpha: 0.25)),
      ),
      child: const Text(
        'Mako is a personal AI with long-term memory, a personality that '
        'grows through lived experience, people she keeps track of, and the '
        'sense to text first only when it matters.',
        style: TextStyle(color: MakoColors.text, fontSize: 14, height: 1.5),
      ),
    );
  }
}

class _Section extends StatelessWidget {
  final String title;
  final List<_Item> items;
  const _Section(this.title, this.items);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title,
              style: const TextStyle(
                  color: MakoColors.accent,
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 1.5)),
          const SizedBox(height: 8),
          ...items,
        ],
      ),
    );
  }
}

class _Item extends StatelessWidget {
  final String title;
  final String body;
  const _Item(this.title, this.body);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title,
              style: const TextStyle(
                  color: MakoColors.text,
                  fontSize: 14,
                  fontWeight: FontWeight.w600)),
          const SizedBox(height: 3),
          Text(body,
              style: const TextStyle(
                  color: MakoColors.textDim, fontSize: 13, height: 1.45)),
        ],
      ),
    );
  }
}
