import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/env.dart';

class BackendService {
  BackendService({http.Client? client, String? baseUrl})
      : _client = client ?? http.Client(),
        _baseUrl = baseUrl ?? kBackendBaseUrl;

  final http.Client _client;
  final String _baseUrl;

  Future<Map<String, dynamic>> generateByRef(String ref) async {
    final uri = Uri.parse('$_baseUrl/api/generate_by_ref');
    final resp = await _client
        .post(
          uri,
          headers: {
            'Content-Type': 'application/json',
            'X-API-Key': kApiKey, // 加入 API Key 驗證
          },
          body: json.encode({'ref': ref}),
        )
        .timeout(const Duration(seconds: 30));

    if (resp.statusCode == 401) {
      throw Exception('Unauthorized: Invalid API Key');
    }
    if (resp.statusCode != 200) {
      throw Exception('Backend error ${resp.statusCode}: ${resp.body}');
    }
    final Map<String, dynamic> body =
        json.decode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>;
    return body;
  }
}
