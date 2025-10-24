import 'dart:convert';
import 'package:http/http.dart' as http;

class OidvpService {
  OidvpService({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;

  static const String _baseUrl =
      'https://verifier-sandbox.wallet.gov.tw/api/oidvp/qrcode';

  /// Calls the OIDVP QRCode API and returns a map with keys: transactionId, qrcodeImage, authUri.
  /// Throws an Exception on non-200 responses.
  Future<Map<String, dynamic>> fetchQrCode({
    required String ref,
    required String accessToken,
    required String transactionId,
  }) async {
    final uri = Uri.parse(_baseUrl).replace(queryParameters: {
      'ref': ref,
      'transactionId': transactionId,
    });

    final response = await _client.get(
      uri,
      headers: {
        'accept': '*/*',
        'Access-Token': accessToken,
      },
    );

    if (response.statusCode != 200) {
      throw Exception('HTTP ${response.statusCode}: ${response.body}');
    }

    final Map<String, dynamic> jsonBody =
        json.decode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
    return jsonBody;
  }
}
