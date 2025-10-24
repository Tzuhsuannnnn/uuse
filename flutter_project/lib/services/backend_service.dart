import 'dart:convert';
import 'package:http/http.dart' as http;

class BackendService {
  BackendService({http.Client? client, String? baseUrl})
      : _client = client ?? http.Client(),
        _baseUrl = baseUrl ?? defaultBaseUrl;

  final http.Client _client;
  final String _baseUrl;

  // Adjust this to your environment:
  // - iOS Simulator: http://127.0.0.1:5001
  // - Physical iPhone: http://<YOUR-MAC-LAN-IP>:5001 (e.g., http://192.168.1.10:5001)
  static const String defaultBaseUrl = 'http://127.0.0.1:5001';

  Future<Map<String, dynamic>> generateByRef(String ref) async {
    final uri = Uri.parse('$_baseUrl/api/generate_by_ref');
    final resp = await _client
        .post(
          uri,
          headers: const {
            'Content-Type': 'application/json',
          },
          body: json.encode({'ref': ref}),
        )
        .timeout(const Duration(seconds: 30));

    if (resp.statusCode != 200) {
      throw Exception('Backend error ${resp.statusCode}: ${resp.body}');
    }
    final Map<String, dynamic> body =
        json.decode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>;
    return body;
  }
}
