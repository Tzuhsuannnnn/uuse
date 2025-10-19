import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:url_launcher/url_launcher.dart';

class ScanTab extends StatefulWidget {
  const ScanTab({super.key, this.onCancel});

  final VoidCallback? onCancel;

  @override
  State<ScanTab> createState() => _ScanTabState();
}

class _ScanTabState extends State<ScanTab> with WidgetsBindingObserver {
  final MobileScannerController _controller = MobileScannerController(
    formats: const [BarcodeFormat.qrCode],
    detectionSpeed: DetectionSpeed.noDuplicates,
    facing: CameraFacing.back,
  );

  bool _isHandlingResult = false;
  bool _scannerPaused = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _controller.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (!mounted) return;
    if (state == AppLifecycleState.paused) {
      _controller.stop();
    } else if (state == AppLifecycleState.resumed) {
      _controller.start();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        // Camera preview
        MobileScanner(
          controller: _controller,
          errorBuilder: (context, error, child) {
            return Center(
              child: Text(
                '相機啟動失敗：${error.toString()}',
                style: const TextStyle(color: Colors.white),
                textAlign: TextAlign.center,
              ),
            );
          },
          onDetect: (capture) => _onDetect(capture),
        ),

        // Top instruction text
        Positioned(
          left: 0,
          right: 0,
          top: MediaQuery.of(context).padding.top + 24,
          child: const Text(
            '請對準有效QR-Code，將自動進行掃描',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Colors.white,
              fontSize: 18,
              fontWeight: FontWeight.w500,
              shadows: [Shadow(blurRadius: 4, color: Colors.black54)],
            ),
          ),
        ),

        // Scanning frame overlay (rounded corners)
        Center(
          child: SizedBox(
            width: MediaQuery.of(context).size.width * 0.72,
            height: MediaQuery.of(context).size.width * 0.72,
            child: CustomPaint(
              painter: _ScanFramePainter(color: Colors.white, strokeWidth: 8),
            ),
          ),
        ),

        // Bottom cancel button above preview
        Positioned(
          bottom: 72,
          left: 0,
          right: 0,
          child: Center(
            child: ElevatedButton(
              style: ElevatedButton.styleFrom(
                shape: const CircleBorder(),
                backgroundColor: Colors.white,
                padding: const EdgeInsets.all(16),
                elevation: 2,
              ),
              onPressed: () {
                widget.onCancel?.call();
              },
              child: const Icon(
                Icons.close,
                color: Color(0xFF4A5AB8),
                size: 28,
              ),
            ),
          ),
        ),
      ],
    );
  }

  Future<void> _onDetect(BarcodeCapture capture) async {
    if (_isHandlingResult) return;

    // Extract the first non-empty value from the captured barcodes
  String? value;
    for (final b in capture.barcodes) {
      final v = b.rawValue ?? b.displayValue;
      if (v != null && v.isNotEmpty) {
        value = v;
        break;
      }
    }

  if (value == null || !mounted) return;
  final String result = value;

    _isHandlingResult = true;
    try {
      await _controller.stop();
      _scannerPaused = true;
      HapticFeedback.lightImpact();

      // If it's a link, open it; supports http(s) and custom schemes like modadigitalwallet
      final uri = _parseUriConsideringSchemeless(result);
      if (uri != null) {
        if (uri.scheme == 'http' || uri.scheme == 'https') {
          await launchUrl(uri, mode: LaunchMode.inAppBrowserView);
        } else {
          // Try to open the custom scheme app, e.g., modadigitalwallet://
          final can = await canLaunchUrl(uri);
          if (can) {
            await launchUrl(uri, mode: LaunchMode.externalApplication);
          } else {
            // Fallback: try request_uri query parameter (often https)
            final fallback = _extractRequestUri(uri);
            if (fallback != null) {
              await launchUrl(fallback, mode: LaunchMode.inAppBrowserView);
            } else {
              // If no fallback, show the raw result
              await _showResultSheet(result);
            }
          }
        }
      } else {
        await showModalBottomSheet<void>(
          context: context,
          backgroundColor: Colors.white,
          shape: const RoundedRectangleBorder(
            borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
          ),
          builder: (context) {
            return Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    '掃描結果',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(height: 12),
                  SelectableText(
                    result,
                    style: const TextStyle(fontSize: 16, color: Colors.black87),
                  ),
                  const SizedBox(height: 16),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      TextButton.icon(
                        onPressed: () async {
                          await Clipboard.setData(ClipboardData(text: result));
                          if (context.mounted) {
                            Navigator.of(context).pop();
                          }
                        },
                        icon: const Icon(Icons.copy, size: 18),
                        label: const Text('複製'),
                      ),
                      const SizedBox(width: 8),
                      ElevatedButton(
                        onPressed: () => Navigator.of(context).pop(),
                        child: const Text('關閉'),
                      ),
                    ],
                  ),
                ],
              ),
            );
          },
        );
      }
    } finally {
      if (mounted && _scannerPaused) {
        try {
          await _controller.start();
        } catch (_) {
          // Ignore if already started
        }
        _scannerPaused = false;
      }
      _isHandlingResult = false;
    }
  }

  Future<void> _showResultSheet(String result) async {
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (context) {
        return Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                '掃描結果',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 12),
              SelectableText(
                result,
                style: const TextStyle(fontSize: 16, color: Colors.black87),
              ),
              const SizedBox(height: 16),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton.icon(
                    onPressed: () async {
                      await Clipboard.setData(ClipboardData(text: result));
                      if (context.mounted) {
                        Navigator.of(context).pop();
                      }
                    },
                    icon: const Icon(Icons.copy, size: 18),
                    label: const Text('複製'),
                  ),
                  const SizedBox(width: 8),
                  ElevatedButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: const Text('關閉'),
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }

  Uri? _parseUriConsideringSchemeless(String value) {
    final trimmed = value.trim();
    final direct = Uri.tryParse(trimmed);
    if (direct != null && direct.hasScheme) return direct;
    // If no scheme but looks like a domain, prefix https
    final lower = trimmed.toLowerCase();
    final domain = RegExp(r'^[a-z0-9.-]+\.[a-z]{2,}(/.*)?$');
    if (domain.hasMatch(lower)) {
      return Uri.tryParse('https://$trimmed');
    }
    return null;
  }

  Uri? _extractRequestUri(Uri uri) {
    final raw = uri.queryParameters['request_uri'];
    if (raw == null || raw.isEmpty) return null;
    final decoded = Uri.decodeComponent(raw);
    return Uri.tryParse(decoded);
  }
}

class _ScanFramePainter extends CustomPainter {
  _ScanFramePainter({required this.color, this.strokeWidth = 6});

  final Color color;
  final double strokeWidth;

  @override
  void paint(Canvas canvas, Size size) {
    final Paint paint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    const double radius = 24;
    const double segment = 40;

    final RRect rrect = RRect.fromRectAndRadius(
      Offset.zero & size,
      const Radius.circular(radius),
    );

    // Draw only the corners by clipping path and drawing partial segments
    final Path path = Path()..addRRect(rrect);
    canvas.save();
    canvas.clipPath(path);

    // Top-left
    canvas.drawLine(const Offset(0, segment), Offset.zero, paint);
    canvas.drawLine(const Offset(segment, 0), Offset.zero, paint);

    // Top-right
    canvas.drawLine(
        Offset(size.width - segment, 0), Offset(size.width, 0), paint);
    canvas.drawLine(Offset(size.width, segment), Offset(size.width, 0), paint);

    // Bottom-left
    canvas.drawLine(
        Offset(0, size.height - segment), Offset(0, size.height), paint);
    canvas.drawLine(
        Offset(segment, size.height), Offset(0, size.height), paint);

    // Bottom-right
    canvas.drawLine(Offset(size.width - segment, size.height),
        Offset(size.width, size.height), paint);
    canvas.drawLine(Offset(size.width, size.height - segment),
        Offset(size.width, size.height), paint);

    canvas.restore();
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
