// Mako — personal AI assistant client.
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'providers/mako_provider.dart';
import 'screens/chat_screen.dart';
import 'services/settings_service.dart';
import 'theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await SettingsService().init();
  runApp(const MakoApp());
}

class MakoApp extends StatelessWidget {
  const MakoApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => MakoProvider(),
      child: MaterialApp(
        title: 'Mako',
        debugShowCheckedModeBanner: false,
        theme: makoTheme,
        home: const ChatScreen(),
      ),
    );
  }
}
