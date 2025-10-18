from flask import Flask, request, jsonify
import threading
import asyncio
import time
from generate_qrcode import get_qrcode_image, generate_new_transaction_id, save_base64_to_png, ACCESS_TOKEN
from bleak import BleakScanner

app = Flask(__name__)

# 全域儲存最後一次產生的結果
last_result = {"transactionId": None, "authUri": None, "image": None}

# BLE 設定（可由前端覆寫）
BLE_TARGET_ADDRESS = None
BLE_RSSI_THRESHOLD = -60
_ble_scanner_thread = None
_ble_scanner_running = False
_last_near_state = {}

def generate_qr_by_ref(ref_value: str):
    tid = generate_new_transaction_id()
    api_resp = get_qrcode_image(ref_value, ACCESS_TOKEN, tid)
    if not api_resp:
        return None
    qrcode_base64 = api_resp.get("qrcodeImage")
    auth_uri = api_resp.get("authUri")
    image_file = None
    if qrcode_base64:
        image_file = save_base64_to_png(qrcode_base64, ref_value)
    last_result.update({"transactionId": tid, "authUri": auth_uri, "image": image_file})
    return {"transactionId": tid, "authUri": auth_uri, "image": image_file}

@app.route("/generate_by_ref", methods=["POST"])
def api_generate_by_ref():
    data = request.get_json() or {}
    ref = data.get("ref")
    if not ref:
        return jsonify({"error": "missing ref"}), 400
    resp = generate_qr_by_ref(ref)
    if resp is None:
        return jsonify({"error": "API call failed"}), 500
    return jsonify(resp)

@app.route("/last", methods=["GET"])
def api_last():
    return jsonify(last_result)

@app.route("/start_scan", methods=["POST"])
def api_start_scan():
    global _ble_scanner_thread, _ble_scanner_running, BLE_TARGET_ADDRESS, BLE_RSSI_THRESHOLD
    data = request.get_json() or {}
    BLE_TARGET_ADDRESS = data.get("target_address", BLE_TARGET_ADDRESS)
    BLE_RSSI_THRESHOLD = data.get("rssi_threshold", BLE_RSSI_THRESHOLD)
    if _ble_scanner_running:
        return jsonify({"status": "already_running"}), 200
    def _bg(): asyncio.run(_ble_scan_loop())
    _ble_scanner_thread = threading.Thread(target=_bg, daemon=True)
    _ble_scanner_thread.start()
    _ble_scanner_running = True
    return jsonify({"status": "started"})

@app.route("/stop_scan", methods=["POST"])
def api_stop_scan():
    global _ble_scanner_running
    _ble_scanner_running = False
    return jsonify({"status": "stopping"})

async def _ble_scan_loop():
    global _ble_scanner_running, _last_near_state
    _ble_scanner_running = True
    print("BLE scan loop started")
    try:
        while _ble_scanner_running:
            devices = await BleakScanner.discover(timeout=3.0)
            for d in devices:
                if BLE_TARGET_ADDRESS and d.address.upper() != BLE_TARGET_ADDRESS.upper():
                    continue
                rssi = d.rssi
                name = d.name
                if rssi is None:
                    continue
                key = d.address.upper()
                was_near = _last_near_state.get(key, False)
                is_near = rssi > BLE_RSSI_THRESHOLD
                if is_near and not was_near:
                    if name:
                        print(f"[BLE_TRIGGER] {name} ({d.address}) RSSI={rssi} -> generate by ref=name")
                        generate_qr_by_ref(name)
                    else:
                        print("[BLE_TRIGGER] 沒有抓到ref (device.name is None) -- 不呼叫 API")
                    _last_near_state[key] = True
                elif not is_near and was_near:
                    _last_near_state[key] = False
                    print(f"[BLE_RESET] {d.address} moved far (RSSI={rssi})")
            await asyncio.sleep(1.0)
    except Exception as e:
        print(f"BLE scan loop error: {e}")
    finally:
        _ble_scanner_running = False
        print("BLE scan loop stopped")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)