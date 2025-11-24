# uuse

A Flutter mobile application with Flask API backend for credential presentation and proximity-based interactions.

## Overview

This project consists of:

- **Flutter Mobile App** (`flutter_project/`) - A credential management app with BLE proximity detection and quick-action UI
- **Flask API** (`generate_qrcode_api.py`) - Backend service for generating QR codes and authentication URIs
- **QR Code Generator** (`generate_qrcode.py`) - Utility functions for QR code generation

The Flutter app provides a tabbed interface for managing credentials, scanning, and displaying credentials with various use cases like transit, invoicing, library access, hotel access, and more.

## Features

### Flutter App

- **Credential Management**: Add, manage, and display digital credentials
- **Quick Actions**: Pre-configured buttons for common use cases:
  - 搭捷運 (Transit)
  - 載具 (Invoice carrier)
  - 借書 (Library borrowing)
  - 飯店門禁 (Hotel access)
  - 場館入場 (Venue entry)
  - 校園門禁 (Campus access)
  - 公司打卡 (Office check-in)
  - 會員登入 (Member login)
  - 會議報到 (Meeting check-in)
  - 停車場入場 (Parking entry)
  - 健身房入場 (Gym entry)
  - 診所報到 (Clinic check-in)
- **BLE Proximity Detection**: Bluetooth Low Energy scanning and proximity monitoring
- **Profile Management**: User profile and settings

### Flask API

- QR code generation endpoint
- Transaction ID management
- Authentication URI generation
- Health check endpoint

## Prerequisites

- **Flutter SDK**: 3.4.3 or higher
- **Python**: 3.8+ with pip
- **iOS/Android Development**: Xcode (iOS) or Android Studio (Android)
- **Virtual Environment**: Recommended for Python dependencies

## Setup

### 1. Python Backend

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

Install dependencies:

```bash
pip install flask
# Add other dependencies as needed
```

### 2. Flutter App

Navigate to the Flutter project:

```bash
cd flutter_project
```

Install Flutter dependencies:

```bash
flutter pub get
```

Configure the backend URL in `lib/config/env.dart`:

```dart
const String kBackendBaseUrl = 'http://localhost:5001';  // Adjust port as needed
```

## Running the Application

### Start the Flask Backend

```bash
python generate_qrcode_api.py
```

The API will start on port 5001 by default. If you encounter a "Port already in use" error:

1. Find and kill the process using the port:

   ```bash
   lsof -nP -iTCP:5001 | grep LISTEN
   kill <PID>
   ```

2. Or modify the port in `generate_qrcode_api.py`:

   ```python
   app.run(host="0.0.0.0", port=5005, debug=False)  # Change to available port
   ```

### Run the Flutter App

```bash
cd flutter_project

# For iOS Simulator
flutter run -d ios

# For Android Emulator/Device
flutter run -d android

# List available devices
flutter devices
```

## Project Structure

```text
uuse/
├── generate_qrcode_api.py          # Flask API server
├── generate_qrcode.py              # QR code utilities
└── flutter_project/               # Flutter mobile app
    ├── lib/
    │   ├── main.dart              # App entry point
    │   ├── config/
    │   │   └── env.dart           # Environment configuration
    │   ├── services/
    │   │   ├── backend_service.dart    # API communication
    │   │   └── oidvp_service.dart      # OIDC/VP services
    │   ├── tabs/
    │   │   ├── add_credentials_tab.dart      # Add credentials UI
    │   │   ├── manage_credentials_tab.dart   # Manage credentials UI
    │   │   ├── scan_tab.dart                # QR scanning UI
    │   │   ├── show_credentials_tab.dart     # Display credentials UI
    │   │   └── profile_tab.dart             # User profile UI
    │   ├── ble_proximity_screen.dart        # BLE proximity detection
    │   ├── simplified_proximity_screen.dart # Simplified proximity UI
    │   └── ...
    ├── pubspec.yaml               # Flutter dependencies
    ├── android/                   # Android platform files
    ├── ios/                      # iOS platform files
    └── ...
```

## API Endpoints

### Flask Backend

- `GET /health` - Health check endpoint
- `POST /api/generate_by_ref` - Generate QR code and auth URI

  ```json
  {
    "ref": "credential_reference_id"
  }
  ```

## Development

### Flutter Commands

```bash
# Analyze code for issues
flutter analyze

# Format code
flutter format lib/

# Run tests
flutter test

# Build APK (Android)
flutter build apk

# Build IPA (iOS)
flutter build ipa
```

### Python Development

```bash
# Install development dependencies
pip install flask python-dotenv

# Run with debug mode
export FLASK_DEBUG=1
python generate_qrcode_api.py
```

## Troubleshooting

### Port Conflicts

If you encounter "Address already in use" errors, check which process is using the port and either stop it or use a different port.

### Flutter Build Issues

- Run `flutter doctor` to check for setup issues
- Clear Flutter cache: `flutter clean && flutter pub get`
- Rebuild: `flutter build <platform>`

### BLE Permissions

Make sure to grant Bluetooth permissions on the device for proximity detection features.

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and commit: `git commit -am 'Add feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## License

This project does not currently include a license. Please add an appropriate license file if you plan to distribute this code.
