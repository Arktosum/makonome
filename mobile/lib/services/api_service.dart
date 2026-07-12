// lib/services/api_service.dart — Mako's REST API.
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'settings_service.dart';

class HealthResult {
  final bool reachable;
  final bool pushConfigured;
  HealthResult({required this.reachable, this.pushConfigured = false});
}

enum TokenStatus { valid, rejected, unknown }

class ApiService {
  final _settings = SettingsService();

  Map<String, String> get _authHeaders => {
        'Content-Type': 'application/json',
        if (_settings.token.isNotEmpty)
          'Authorization': 'Bearer ${_settings.token}',
      };

  /// Liveness probe — also what wakes a sleeping Render instance.
  Future<HealthResult> health({Duration timeout = const Duration(seconds: 8)}) async {
    try {
      final r = await http
          .get(Uri.parse('${_settings.serverUrl}/api/health'))
          .timeout(timeout);
      if (r.statusCode != 200) return HealthResult(reachable: false);
      final body = jsonDecode(r.body) as Map<String, dynamic>;
      return HealthResult(
        reachable: body['ok'] == true,
        pushConfigured: body['push'] == true,
      );
    } catch (_) {
      return HealthResult(reachable: false);
    }
  }

  /// Validate the token without side effects: an empty /api/chat body
  /// returns 400 when the token is accepted, 401 when it isn't.
  Future<TokenStatus> checkToken() async {
    try {
      final r = await http
          .post(Uri.parse('${_settings.serverUrl}/api/chat'),
              headers: _authHeaders, body: jsonEncode({}))
          .timeout(const Duration(seconds: 10));
      if (r.statusCode == 401) return TokenStatus.rejected;
      if (r.statusCode == 400 || r.statusCode == 503) return TokenStatus.valid;
      return TokenStatus.unknown;
    } catch (_) {
      return TokenStatus.unknown;
    }
  }

  /// Ask the server to fire a test push notification.
  Future<String?> pushTest() async {
    try {
      final r = await http
          .post(Uri.parse('${_settings.serverUrl}/api/push-test'),
              headers: _authHeaders)
          .timeout(const Duration(seconds: 15));
      if (r.statusCode == 200) return null; // success
      final body = jsonDecode(r.body) as Map<String, dynamic>;
      return body['error']?.toString() ?? 'push failed (HTTP ${r.statusCode})';
    } catch (e) {
      return 'could not reach the server';
    }
  }
}
