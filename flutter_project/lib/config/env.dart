// Environment configuration
// 開發環境：先開 Flask，再根據你的網路環境修改這裡
library env;

// Backend URL configuration
// iOS Simulator: 使用 'http://127.0.0.1:5001'
// Android Emulator: 使用 'http://10.0.2.2:5001'
// Physical Device: 使用 'http://YOUR_COMPUTER_IP:5001' (例如: 'http://192.168.1.10:5001')
const String kBackendBaseUrl = String.fromEnvironment(
  'BACKEND_URL',
  defaultValue: 'http://127.0.0.1:5001', // 預設為本機 localhost
);

// API Key for backend authentication
// 注意：生產環境應該從安全的儲存取得，不要硬編碼在程式中
const String kApiKey = String.fromEnvironment(
  'API_KEY',
  defaultValue: 'your-secret-api-key-change-this-in-production',
);