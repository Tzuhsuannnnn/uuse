import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../services/backend_service.dart';
import '../config/env.dart';

class ShowCredentialsTab extends StatefulWidget {
  const ShowCredentialsTab({super.key});

  @override
  State<ShowCredentialsTab> createState() => _ShowCredentialsTabState();
}

class _ShowCredentialsTabState extends State<ShowCredentialsTab> {
  bool _isExpanded = true;
  final Set<int> _favorites = {0, 1};
  late final BackendService _backend;

  @override
  void initState() {
    super.initState();
    // Centralized in env.dart; set kBackendBaseUrl to your environment.
    _backend = BackendService(baseUrl: kBackendBaseUrl);
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
            children: [
            // Search Bar
            Container(
              decoration: BoxDecoration(
              color: const Color(0xFFF5F5F5),
              borderRadius: BorderRadius.circular(12),
              ),
              child: TextField(
              decoration: InputDecoration(
                hintText: '搜尋55',
                hintStyle: TextStyle(
                color: Colors.grey[600],
                fontSize: 16,
                ),
                prefixIcon: Icon(
                Icons.search,
                color: Colors.grey[600],
                ),
                border: InputBorder.none,
                contentPadding: const EdgeInsets.symmetric(
                horizontal: 16,
                vertical: 14,
                ),
              ),
              onChanged: (value) {
                print('Search input changed: $value');
              },
              ),
            ),
            const SizedBox(height: 24),

            // 我的最愛 Section
            const Text(
              '我的最愛',
              style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
              color: Colors.black,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              '快點擊列表中的星形，將常用情境加入我的最愛吧！',
              style: TextStyle(
              fontSize: 14,
              color: Colors.grey[600],
              ),
            ),
            const SizedBox(height: 24),

            // 快速授權列表 Section
            InkWell(
              onTap: () {
              print('Toggling expansion state: $_isExpanded -> ${!_isExpanded}');
              setState(() {
                _isExpanded = !_isExpanded;
              });
              },
              child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                '快速授權列表',
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                  color: Colors.black,
                ),
                ),
                Icon(
                _isExpanded
                  ? Icons.keyboard_arrow_up
                  : Icons.keyboard_arrow_down,
                color: Colors.blue,
                ),
              ],
              ),
            ),
            const SizedBox(height: 16),

            // List Items
            if (_isExpanded) ...[
              _buildListItem(
              '搭捷運4',
              0,
              onTap: () {
                _handleQuickActionTap('00000000_iris_enter_mrt');
              },
              ),
              const SizedBox(height: 8),
              _buildListItem(
              '載具',
              1,
              onTap: () {
                _handleQuickActionTap('00000000_iris_invoice_code');
              },
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildListItem(String title, int index, {VoidCallback? onTap}) {
    final bool isFavorite = _favorites.contains(index);

    return InkWell(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: const Color(0xFFF8F8F8),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(
                    fontSize: 16,
                    color: Colors.black,
                  ),
                ),
              ),
              IconButton(
                icon: Icon(
                  isFavorite ? Icons.star : Icons.star_border,
                  color: isFavorite ? Colors.blue : Colors.grey,
                ),
                onPressed: () {
                  setState(() {
                    if (isFavorite) {
                      _favorites.remove(index);
                    } else {
                      _favorites.add(index);
                    }
                  });
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _handleQuickActionTap(String ref) async {
    // Lightweight modal progress
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => const Center(child: CircularProgressIndicator()),
    );

    try {
      final resp = await _backend.generateByRef(ref);
      final authUriStr = (resp['authUri'] ?? resp['auth_uri']) as String?;
      if (authUriStr == null || authUriStr.isEmpty) {
        _showSnack('未取得 authUri，請稍後重試');
        return;
      }

      final uri = Uri.parse(authUriStr);
      final can = await canLaunchUrl(uri);
      if (!can) {
        _showSnack('無法開啟連結');
        return;
      }

      final isHttp = uri.scheme == 'http' || uri.scheme == 'https';
      await launchUrl(
        uri,
        mode: isHttp
            ? LaunchMode.inAppBrowserView
            : LaunchMode.externalApplication,
      );
    } catch (e) {
      _showSnack('操作失敗：$e');
    } finally {
      if (context.mounted) Navigator.of(context).pop();
    }
  }

  void _showSnack(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(msg)),
    );
  }
}
