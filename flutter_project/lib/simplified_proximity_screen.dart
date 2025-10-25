import 'package:flutter/material.dart';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';
import 'dart:async';
import 'package:url_launcher/url_launcher.dart';
import '../services/backend_service.dart';
import '../config/env.dart';

class SimplifiedProximityScreen extends StatefulWidget {
  const SimplifiedProximityScreen({super.key});

  @override
  State<SimplifiedProximityScreen> createState() => _SimplifiedProximityScreenState();
}

class _SimplifiedProximityScreenState extends State<SimplifiedProximityScreen> {
  // Target device info
  static const String targetDeviceName = "Ray_Chen的筆記型電腦";
  static const String targetDeviceId = "428A26D3-FC17-А3С5-8B29-20F58A8ACC67";
  
  // Current state
  int _currentRssi = 0;
  bool _isDetecting = false;
  bool _deviceFound = false;
  String _statusMessage = "Starting Mac detection automatically...";
  String _proximityMessage = "";
  
  // Monitoring
  StreamSubscription<List<ScanResult>>? _scanSubscription;
  Timer? _updateTimer;
  DateTime? _lastUpdate;
  bool _showGetClose = false;
  Timer? _getCloseTimer;
  late final BackendService _backend;

  @override
  void initState() {
    super.initState();
    // Initialize backend service
    _backend = BackendService(baseUrl: kBackendBaseUrl);
    // Automatically start detection when screen opens
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _startDetection();
    });
  }

  @override
  void dispose() {
    _stopDetection();
    _getCloseTimer?.cancel();
    super.dispose();
  }

  Future<void> _startDetection() async {
    if (_isDetecting) return;

    setState(() {
      _isDetecting = true;
      _deviceFound = false;
      _statusMessage = "🔍 Searching for your Mac...";
      _proximityMessage = "";
    });

    try {
      // Start continuous BLE scanning with shorter timeout for frequent updates
      await FlutterBluePlus.startScan(
        timeout: const Duration(milliseconds: 500), // Short timeout for frequent scans
        androidUsesFineLocation: true,
      );

      // Listen for scan results
      _scanSubscription = FlutterBluePlus.scanResults.listen((results) {
        if (!mounted) return;
        
        bool foundInThisScan = false;
        
        for (ScanResult result in results) {
          // Check if this is Ray's Mac by name or device ID
          bool isTargetDevice = false;
          
          // Check by device name
          String deviceName = "";
          if (result.device.platformName.isNotEmpty) {
            deviceName = result.device.platformName;
          } else if (result.advertisementData.advName.isNotEmpty) {
            deviceName = result.advertisementData.advName;
          }
          
          if (deviceName == targetDeviceName) {
            isTargetDevice = true;
          }
          
          // Check by device ID
          if (result.device.remoteId.toString().toUpperCase() == targetDeviceId.toUpperCase()) {
            isTargetDevice = true;
          }
          
          if (isTargetDevice) {
            foundInThisScan = true;
            _lastUpdate = DateTime.now();
            if (mounted) {
              setState(() {
                _deviceFound = true;
                _currentRssi = result.rssi;
                _updateStatusAndProximity();
              });
            }
            break;
          }
        }
        
        // If we didn't find the device in this scan cycle
        if (!foundInThisScan && mounted) {
          // Only update status if we haven't found it recently
          if (_lastUpdate == null || 
              DateTime.now().difference(_lastUpdate!).inSeconds > 3) {
            setState(() {
              _deviceFound = false;
              _statusMessage = "🔍 Searching for Ray_Chen的筆記型電腦...";
              _proximityMessage = "Mac not detected";
            });
          }
        }
      });

      // Set up a timer to restart scanning every second for consistent updates
      _updateTimer = Timer.periodic(const Duration(seconds: 1), (timer) async {
        if (!mounted || !_isDetecting) {
          timer.cancel();
          return;
        }
        
        try {
          // Stop current scan
          await FlutterBluePlus.stopScan();
          
          // Start a new scan
          await FlutterBluePlus.startScan(
            timeout: const Duration(milliseconds: 500),
            androidUsesFineLocation: true,
          );
        } catch (e) {
          // Handle scan restart errors silently
        }
      });

    } catch (e) {
      if (mounted) {
        setState(() {
          _isDetecting = false;
          _statusMessage = "❌ Error starting detection: $e";
        });
      }
    }
  }

  Future<void> _stopDetection() async {
    if (!_isDetecting) return;

    setState(() {
      _isDetecting = false;
      _deviceFound = false;
      _statusMessage = "Detection stopped";
      _proximityMessage = "";
    });

    try {
      // Cancel timer first
      _updateTimer?.cancel();
      _updateTimer = null;
      // Cancel get-close timer
      _getCloseTimer?.cancel();
      _getCloseTimer = null;
      
      // Stop scanning
      await FlutterBluePlus.stopScan();
      
      // Cancel subscription
      await _scanSubscription?.cancel();
      _scanSubscription = null;
      
      // Reset last update
      _lastUpdate = null;
    } catch (e) {
      // Handle error silently
    }
  }

  void _updateStatusAndProximity() {
    if (!_deviceFound) return;
    String timeStr = DateTime.now().toString().substring(11, 19);
    _statusMessage = "✅ Mac found! RSSI: $_currentRssi dBm (Updated: $timeStr)";

    // Determine previous proximity before updating
    final String prevProximity = _proximityMessage;

    // Check proximity based on RSSI
    // Per user requirement: "once RSSI is bigger than -50, show 'far'"
    if (_currentRssi > -50) {
      _proximityMessage = "far";
    } else {
      _proximityMessage = "close";
    }

    // If we transitioned from far -> close, show transient "get close" message
    if (prevProximity == "far" && _proximityMessage == "close") {
      // cancel any existing timer
      _getCloseTimer?.cancel();
      _showGetClose = true;
      // clear after 2 seconds
      _getCloseTimer = Timer(const Duration(seconds: 2), () {
        if (mounted) {
          setState(() {
            _showGetClose = false;
          });
        }
      });
      // also show a quick snackbar
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('get close'), duration: Duration(seconds: 2)),
        );
      }
      // Trigger MRT quick action
      _handleQuickActionTap('00000000_iris_enter_mrt');
    }
  }

  Color _getProximityColor() {
    if (!_deviceFound) return Colors.grey;
    if (_currentRssi > -50) return Colors.red; // far - red color
    return Colors.green; // close - green color
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mac Proximity Detector'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          children: [
            const SizedBox(height: 20),
            // Title
            const Text(
              'Simplified Mac Detection',
              style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            // Transient get-close banner
            if (_showGetClose)
              Container(
                margin: const EdgeInsets.only(top: 8, bottom: 8),
                padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 16),
                decoration: BoxDecoration(
                  color: Colors.orange.shade700,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Text(
                  'get close',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white),
                ),
              ),
            const SizedBox(height: 20),
            
            // Target Device Info
            Card(
              elevation: 4,
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  children: [
                    const Icon(Icons.computer, size: 40, color: Colors.blue),
                    const SizedBox(height: 12),
                    const Text(
                      'Target Device:',
                      style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      targetDeviceName,
                      style: const TextStyle(fontSize: 16, color: Colors.green),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'ID: ${targetDeviceId.substring(0, 17)}...',
                      style: TextStyle(fontSize: 11, color: Colors.grey.shade600),
                    ),
                  ],
                ),
              ),
            ),
            
            const SizedBox(height: 20),
            
            // Current RSSI Display
            if (_deviceFound) ...[
              Card(
                elevation: 4,
                color: _getProximityColor().withOpacity(0.1),
                child: Padding(
                  padding: const EdgeInsets.all(20.0),
                  child: Column(
                    children: [
                      Text(
                        '$_currentRssi',
                        style: TextStyle(
                          fontSize: 42,
                          fontWeight: FontWeight.bold,
                          color: _getProximityColor(),
                        ),
                      ),
                      const Text('RSSI (dBm)', style: TextStyle(fontSize: 14)),
                      const SizedBox(height: 12),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                        decoration: BoxDecoration(
                          color: _getProximityColor(),
                          borderRadius: BorderRadius.circular(16),
                        ),
                        child: Text(
                          _proximityMessage.toUpperCase(),
                          style: const TextStyle(
                            fontSize: 20,
                            fontWeight: FontWeight.bold,
                            color: Colors.white,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
            ],
            
            // Status Message
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: _deviceFound ? Colors.green.shade50 : Colors.blue.shade50,
                border: Border.all(
                  color: _deviceFound ? Colors.green : Colors.blue,
                ),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                _statusMessage,
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: _deviceFound ? Colors.green.shade800 : Colors.blue.shade800,
                ),
                textAlign: TextAlign.center,
              ),
            ),
            
            const SizedBox(height: 30),
            
            // Control Button
            if (_isDetecting)
              SizedBox(
                width: double.infinity,
                height: 60,
                child: ElevatedButton(
                  onPressed: _stopDetection,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.red,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  child: const Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.stop, size: 28),
                      SizedBox(width: 12),
                      Text(
                        'Stop Detection',
                        style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                ),
              ),
              
            if (!_isDetecting)
              SizedBox(
                width: double.infinity,
                height: 60,
                child: ElevatedButton(
                  onPressed: _startDetection,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.green,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  child: const Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.refresh, size: 28),
                      SizedBox(width: 12),
                      Text(
                        'Restart Detection',
                        style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                ),
              ),
            
            const SizedBox(height: 20),
            
            // Info Text
            if (!_isDetecting)
              Text(
                'Detection stopped. Tap "Restart Detection" to\nbegin scanning for your Mac again.',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 14,
                  color: Colors.grey.shade600,
                ),
              ),
              
            if (_isDetecting && !_deviceFound)
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                  const SizedBox(width: 12),
                  Text(
                    'Auto-scanning for your Mac...',
                    style: TextStyle(
                      fontSize: 14,
                      color: Colors.grey.shade600,
                    ),
                  ),
                ],
              ),
              
            if (_isDetecting && _deviceFound)
              Text(
                'Detection active. RSSI updates every second.',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 14,
                  color: Colors.green.shade600,
                  fontWeight: FontWeight.bold,
                ),
              ),
            
            // Bottom padding to prevent overflow
            const SizedBox(height: 40),
          ],
        ),
      ),
    );
  }
}