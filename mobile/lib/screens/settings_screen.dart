// lib/screens/settings_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/mako_provider.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late TextEditingController _urlCtrl;

  @override
  void initState() {
    super.initState();
    final mako = context.read<MakoProvider>();
    _urlCtrl = TextEditingController(text: mako.serverUrl);
  }

  @override
  void dispose() {
    _urlCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<MakoProvider>(
      builder: (context, mako, _) => Scaffold(
        backgroundColor: const Color(0xFF07100A),
        appBar: AppBar(
          backgroundColor: const Color(0xFF07100A),
          elevation: 0,
          leading: IconButton(
            icon: const Icon(Icons.arrow_back_ios_rounded,
                color: Color(0xFF2A5A3A), size: 18),
            onPressed: () => Navigator.pop(context),
          ),
          title: const Text('SETTINGS',
              style: TextStyle(
                color: Color(0xFF00FF88),
                fontSize: 12,
                letterSpacing: 4,
                fontFamily: 'monospace',
              )),
          bottom: const PreferredSize(
            preferredSize: Size.fromHeight(1),
            child: Divider(color: Color(0xFF0A3A1A), height: 1),
          ),
        ),
        body: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            _sectionHeader('CONNECTION'),
            const SizedBox(height: 10),
            _SettingCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('SERVER URL',
                      style: TextStyle(
                        color: Color(0xFF2A5A3A),
                        fontSize: 9,
                        letterSpacing: 2,
                        fontFamily: 'monospace',
                      )),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _urlCtrl,
                    style: const TextStyle(
                      color: Color(0xFFB8DDC8),
                      fontSize: 13,
                      fontFamily: 'monospace',
                    ),
                    decoration: const InputDecoration(
                      border: InputBorder.none,
                      isDense: true,
                      contentPadding: EdgeInsets.zero,
                      hintText: 'wss://makonome.onrender.com/ws',
                      hintStyle: TextStyle(color: Color(0xFF1A4A2A)),
                    ),
                    onSubmitted: (val) {
                      mako.setServerUrl(val.trim());
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('Reconnecting...'),
                          backgroundColor: Color(0xFF001A0A),
                          duration: Duration(seconds: 2),
                        ),
                      );
                    },
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      _SmallButton(
                        label: 'APPLY',
                        onTap: () {
                          mako.setServerUrl(_urlCtrl.text.trim());
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(
                              content: Text('Reconnecting...'),
                              backgroundColor: Color(0xFF001A0A),
                            ),
                          );
                        },
                      ),
                      const SizedBox(width: 8),
                      _SmallButton(
                        label: 'LOCAL',
                        onTap: () {
                          _urlCtrl.text = 'ws://192.168.1.100:8765/ws';
                        },
                      ),
                      const SizedBox(width: 8),
                      _SmallButton(
                        label: 'RENDER',
                        onTap: () {
                          _urlCtrl.text = 'wss://makonome.onrender.com/ws';
                        },
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),
            _sectionHeader('VOICE'),
            const SizedBox(height: 10),
            _SettingCard(
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('VOICE OUTPUT',
                          style: TextStyle(
                            color: Color(0xFF9ECFB0),
                            fontSize: 13,
                          )),
                      SizedBox(height: 2),
                      Text('Mako speaks her responses',
                          style: TextStyle(
                            color: Color(0xFF2A5A3A),
                            fontSize: 11,
                          )),
                    ],
                  ),
                  Switch(
                    value: mako.voiceOutput,
                    onChanged: mako.setVoiceOutput,
                    activeColor: const Color(0xFF00FF88),
                    activeTrackColor: const Color(0xFF003A1A),
                    inactiveThumbColor: const Color(0xFF2A5A3A),
                    inactiveTrackColor: const Color(0xFF0A1A0D),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),
            _sectionHeader('CHAT'),
            const SizedBox(height: 10),
            _SettingCard(
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('CLEAR MESSAGES',
                          style: TextStyle(
                              color: Color(0xFF9ECFB0), fontSize: 13)),
                      SizedBox(height: 2),
                      Text('Remove messages from this session',
                          style: TextStyle(
                              color: Color(0xFF2A5A3A), fontSize: 11)),
                    ],
                  ),
                  _SmallButton(
                    label: 'CLEAR',
                    color: const Color(0xFFFF4455),
                    onTap: () {
                      mako.clearMessages();
                      Navigator.pop(context);
                    },
                  ),
                ],
              ),
            ),
            const SizedBox(height: 40),
            Center(
              child: Text(
                'MAKO v1.0 · makonome.onrender.com',
                style: const TextStyle(
                  color: Color(0xFF1A3A25),
                  fontSize: 10,
                  fontFamily: 'monospace',
                  letterSpacing: 1,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _sectionHeader(String label) => Text(
        label,
        style: const TextStyle(
          color: Color(0xFF2A5A3A),
          fontSize: 9,
          letterSpacing: 3,
          fontFamily: 'monospace',
        ),
      );
}

class _SettingCard extends StatelessWidget {
  final Widget child;
  const _SettingCard({required this.child});

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: const Color(0xFF0D1A10),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: const Color(0xFF1A3A25)),
        ),
        child: child,
      );
}

class _SmallButton extends StatelessWidget {
  final String label;
  final VoidCallback onTap;
  final Color? color;

  const _SmallButton({required this.label, required this.onTap, this.color});

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          decoration: BoxDecoration(
            border: Border.all(color: color ?? const Color(0xFF1A3A25)),
            borderRadius: BorderRadius.circular(4),
          ),
          child: Text(label,
              style: TextStyle(
                color: color ?? const Color(0xFF4A8A5A),
                fontSize: 9,
                letterSpacing: 1.5,
                fontFamily: 'monospace',
              )),
        ),
      );
}
