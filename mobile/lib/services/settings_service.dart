// lib/services/settings_service.dart — persisted app settings.
import 'package:shared_preferences/shared_preferences.dart';

class SettingsService {
  static final SettingsService _i = SettingsService._();
  factory SettingsService() => _i;
  SettingsService._();

  late SharedPreferences _prefs;

  Future<void> init() async {
    _prefs = await SharedPreferences.getInstance();
  }

  String get serverUrl =>
      _prefs.getString('server_url') ?? 'https://makonome.onrender.com';
  set serverUrl(String v) =>
      _prefs.setString('server_url', v.trim().replaceAll(RegExp(r'/+$'), ''));

  String get token => _prefs.getString('token') ?? '';
  set token(String v) => _prefs.setString('token', v.trim());

  String get ntfyTopic => _prefs.getString('ntfy_topic') ?? '';
  set ntfyTopic(String v) => _prefs.setString('ntfy_topic', v.trim());

  String get chatHistory => _prefs.getString('chat_history') ?? '';
  set chatHistory(String v) => _prefs.setString('chat_history', v);

  /// ws(s):// version of the server URL, with token if set.
  String get wsUrl {
    var url = serverUrl
        .replaceFirst('https://', 'wss://')
        .replaceFirst('http://', 'ws://');
    url = '$url/ws';
    if (token.isNotEmpty) url = '$url?token=${Uri.encodeQueryComponent(token)}';
    return url;
  }
}
