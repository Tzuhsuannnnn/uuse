import asyncio
from bleak import BleakScanner, BLEDevice, AdvertisementData

# --- 【必須設定】目標裝置的參數 ---
TARGET_ADDRESS = "47:13:a0:a3:69:4f" # 您的目標位址
RSSI_THRESHOLD = -70 # 近距離閾值

# --- 全域變數用於儲存最新的 RSSI ---
# 由於掃描是持續進行的，我們需要一個地方儲存最新的數據
latest_rssi = None
latest_detection_time = 0

# --- 核心執行邏輯：判斷並輸出結果 ---
def determine_proximity(rssi: int):
    if rssi > RSSI_THRESHOLD:
        print(f"RSSI: {rssi} dBm -> near")
    else:
        print(f"RSSI: {rssi} dBm -> far")

# --- 核心掃描回調函數 (Callback) ---
def detection_callback(device: BLEDevice, advertisement_data: AdvertisementData):
    """
    當掃描器偵測到廣告包時，會立即呼叫此函數。
    這個方法能更可靠地獲取 RSSI。
    """
    global latest_rssi, latest_detection_time

    # 檢查是否為目標裝置
    if device.address.upper() == TARGET_ADDRESS.upper():
        # 確認 RSSI 存在
        if advertisement_data.rssi is not None:
            latest_rssi = advertisement_data.rssi
            latest_detection_time = time.time()
            # 在回調函數中處理 RSSI 即可
            determine_proximity(latest_rssi)

# --- 藍牙掃描主程式 ---
async def scan_for_target():
    global latest_rssi

    print("=" * 40)
    print(f"BLE 距離判斷程式已啟動 (目標: {TARGET_ADDRESS})")
    print(f"近距離閾值 (near threshold): > {RSSI_THRESHOLD} dBm")
    print("=" * 40)

    # 初始化掃描器，並傳入我們的回調函數
    scanner = BleakScanner(detection_callback=detection_callback)

    try:
        # 開始持續掃描
        await scanner.start()

        # 主迴圈不需要執行掃描，只需持續檢查時間或保持運行
        while True:
            await asyncio.sleep(1) # 讓程式保持運行，等待回調函數輸出結果

    finally:
        await scanner.stop()
        
# --- 程式入口點 ---
import time
if __name__ == "__main__":
    try:
        asyncio.run(scan_for_target())
    #ctrl + C 停止程式
    except KeyboardInterrupt:
        print("\n程式已手動停止。")
    except Exception as e:
        print(f"程式運行期間發生嚴重錯誤: {e}")