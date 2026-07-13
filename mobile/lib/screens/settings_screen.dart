// lib/screens/settings_screen.dart — server, auth, and push setup.
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../providers/mako_provider.dart';
import '../services/api_service.dart';
import '../services/settings_service.dart';
import '../theme.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _settings = SettingsService();
  final _api = ApiService();

  late final TextEditingController _url;
  late final TextEditingController _token;
  late final TextEditingController _ntfy;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _url = TextEditingController(text: _settings.serverUrl);
    _token = TextEditingController(text: _settings.token);
    _ntfy = TextEditingController(text: _settings.ntfyTopic);
  }

  void _snack(String msg, {bool ok = true}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(msg,
          style: TextStyle(color: ok ? MakoColors.accent : MakoColors.err)),
    ));
  }

  Future<void> _save() async {
    _settings.serverUrl = _url.text;
    _settings.token = _token.text;
    _settings.ntfyTopic = _ntfy.text;
    _url.text = _settings.serverUrl; // show the normalized form
    _snack('Saved — reconnecting…');
    await context.read<MakoProvider>().reconnect();
  }

  Future<void> _testConnection() async {
    setState(() => _busy = true);
    _settings.serverUrl = _url.text;
    _settings.token = _token.text;

    final health = await _api.health(timeout: const Duration(seconds: 15));
    if (!health.reachable) {
      _snack("Can't reach Mako — she may be waking up (Render takes 30–60s). "
          'Try again shortly.', ok: false);
    } else {
      final token = await _api.checkToken();
      switch (token) {
        case TokenStatus.valid:
          _snack('Connected! Token accepted. '
              'Server push: ${health.pushConfigured ? "configured ✓" : "NOT configured"}');
        case TokenStatus.rejected:
          _snack('Server is up, but the token was rejected.', ok: false);
        case TokenStatus.unknown:
          _snack('Server is up; token check was inconclusive.', ok: false);
      }
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _testPush() async {
    setState(() => _busy = true);
    _settings.serverUrl = _url.text;
    _settings.token = _token.text;
    final err = await _api.pushTest();
    _snack(err == null
        ? 'Test push sent — check your notifications! 🎉'
        : 'Push failed: $err', ok: err == null);
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _sectionTitle('SERVER'),
          _field(_url, 'Server URL (base — no /ws)', 'https://makonome.onrender.com'),
          const SizedBox(height: 12),
          _field(_token, 'Access token (MAKO_DASH_TOKEN)', 'leave empty if unset',
              obscure: true),
          const SizedBox(height: 12),
          Row(children: [
            Expanded(
              child: FilledButton(
                onPressed: _busy ? null : _save,
                style: FilledButton.styleFrom(
                    backgroundColor: MakoColors.accent,
                    foregroundColor: Colors.black),
                child: const Text('Save & reconnect'),
              ),
            ),
            const SizedBox(width: 10),
            OutlinedButton(
              onPressed: _busy ? null : _testConnection,
              child: const Text('Test',
                  style: TextStyle(color: MakoColors.accent)),
            ),
          ]),
          const SizedBox(height: 28),
          _sectionTitle('PUSH NOTIFICATIONS'),
          const Text(
            'Mako reaches your phone through ntfy — even when this app is '
            'closed.\n\n'
            '1. Install the "ntfy" app (Play Store, free)\n'
            '2. In ntfy: Subscribe to topic → enter the same topic that is set '
            'as MAKO_NTFY_TOPIC on the server\n'
            '3. Fire a test below — if your phone buzzes, Mako is omnipresent',
            style: TextStyle(
                color: MakoColors.textDim, fontSize: 13, height: 1.5),
          ),
          const SizedBox(height: 14),
          _field(_ntfy, 'Your ntfy topic (for reference)', 'mako-…',
              suffix: IconButton(
                icon: const Icon(Icons.copy,
                    size: 18, color: MakoColors.textDim),
                onPressed: () {
                  Clipboard.setData(ClipboardData(text: _ntfy.text));
                  _snack('Topic copied');
                },
              )),
          const SizedBox(height: 12),
          OutlinedButton.icon(
            onPressed: _busy ? null : _testPush,
            icon: const Icon(Icons.notifications_active_outlined,
                color: MakoColors.accent, size: 18),
            label: const Text('Send test notification',
                style: TextStyle(color: MakoColors.accent)),
          ),
          const SizedBox(height: 28),
          _sectionTitle('DATA'),
          OutlinedButton.icon(
            onPressed: () {
              context.read<MakoProvider>().clearHistory();
              _snack('Local chat history cleared (Mako still remembers — '
                  'this only clears the phone)');
            },
            icon: const Icon(Icons.delete_outline,
                color: MakoColors.err, size: 18),
            label: const Text('Clear local chat history',
                style: TextStyle(color: MakoColors.err)),
          ),
          const SizedBox(height: 24),
          if (_busy)
            const Center(
                child: CircularProgressIndicator(color: MakoColors.accent)),
        ],
      ),
    );
  }

  Widget _sectionTitle(String t) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: Text(t,
            style: const TextStyle(
                color: MakoColors.accent,
                fontSize: 12,
                fontWeight: FontWeight.bold,
                letterSpacing: 1.5)),
      );

  Widget _field(TextEditingController c, String label, String hint,
      {bool obscure = false, Widget? suffix}) {
    return TextField(
      controller: c,
      obscureText: obscure,
      style: const TextStyle(color: MakoColors.text, fontSize: 14),
      decoration: InputDecoration(
        labelText: label,
        labelStyle: const TextStyle(color: MakoColors.textDim, fontSize: 13),
        hintText: hint,
        hintStyle: TextStyle(
            color: MakoColors.textDim.withValues(alpha: 0.5), fontSize: 13),
        filled: true,
        fillColor: MakoColors.surfaceLight,
        suffixIcon: suffix,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: BorderSide.none,
        ),
      ),
    );
  }

  @override
  void dispose() {
    _url.dispose();
    _token.dispose();
    _ntfy.dispose();
    super.dispose();
  }
}
