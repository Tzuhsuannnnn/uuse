import 'package:flutter/material.dart';
import 'tabs/manage_credentials_tab.dart';
import 'tabs/add_credentials_tab.dart';
import 'tabs/scan_tab.dart';
import 'tabs/profile_tab.dart';
import 'tabs/show_credentials_tab.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '出示憑證',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
        useMaterial3: true,
        scaffoldBackgroundColor: Colors.white,
      ),
      home: const ShowCredentialsPage(),
      debugShowCheckedModeBanner: false,
    );
  }
}

class ShowCredentialsPage extends StatefulWidget {
  const ShowCredentialsPage({super.key});

  @override
  State<ShowCredentialsPage> createState() => _ShowCredentialsPageState();
}

class _ShowCredentialsPageState extends State<ShowCredentialsPage> {
  int _currentIndex = 2; // 出示憑證 is the middle tab (index 2)
  static const List<String> _labels = [
    '管理憑證',
    '加入憑證',
    '出示憑證',
    '掃描',
    '個人',
  ];

  late final List<Widget> _tabs;

  int _lastIndex = 2;

  @override
  void initState() {
    super.initState();
    // Initialize tabs once, injecting the cancel callback for ScanTab
    _tabs = [
      const ManageCredentialsTab(),
      const AddCredentialsTab(),
      const ShowCredentialsTab(),
      ScanTab(
        onCancel: () {
          setState(() {
            _currentIndex = _lastIndex;
          });
        },
      ),
      const ProfileTab(),
    ];
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        centerTitle: true,
        title: Text(
          _labels[_currentIndex],
          style: const TextStyle(
            color: Colors.black,
            fontSize: 18,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      body: IndexedStack(
        index: _currentIndex,
        children: _tabs,
      ),
      bottomNavigationBar: Container(
        decoration: BoxDecoration(
          color: Colors.white,
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.05),
              blurRadius: 10,
              offset: const Offset(0, -2),
            ),
          ],
        ),
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 8.0),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                Expanded(
                  child: _buildBottomNavItem(
                    icon: Icons.credit_card_outlined,
                    label: '管理憑證',
                    index: 0,
                  ),
                ),
                Expanded(
                  child: _buildBottomNavItem(
                    icon: Icons.add_box_outlined,
                    label: '加入憑證',
                    index: 1,
                  ),
                ),
                Expanded(
                  child: _buildBottomNavItem(
                    icon: Icons.qr_code,
                    label: '出示憑證',
                    index: 2,
                  ),
                ),
                Expanded(
                  child: _buildBottomNavItem(
                    icon: Icons.crop_free,
                    label: '掃描',
                    index: 3,
                  ),
                ),
                Expanded(
                  child: _buildBottomNavItem(
                    icon: Icons.settings_outlined,
                    label: '個人',
                    index: 4,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  // _buildListItem removed; list UI lives inside ShowCredentialsTab now.

  Widget _buildBottomNavItem({
    required IconData icon,
    required String label,
    required int index,
  }) {
    bool isSelected = _currentIndex == index;

    return InkWell(
      onTap: () {
        setState(() {
          _lastIndex = _currentIndex;
          _currentIndex = index;
        });
      },
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            icon,
            color: isSelected ? Colors.blue : Colors.grey,
            size: 28,
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: TextStyle(
              fontSize: 12,
              color: isSelected ? Colors.blue : Colors.grey,
            ),
          ),
        ],
      ),
    );
  }
}
