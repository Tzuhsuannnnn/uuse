#驗證端 - QR Code 產生
import requests
import uuid
import base64
import json
import os
from datetime import datetime
from dotenv import load_dotenv
from typing import Optional

# Load environment variables
load_dotenv()

# --- 配置區 ---
ACCESS_TOKEN = os.getenv('IRIS_ACCESS_TOKEN', '')
if not ACCESS_TOKEN:
    raise ValueError("IRIS_ACCESS_TOKEN not found in environment variables. Please set it in .env file.")
    
API_BASE_URL = "https://verifier-sandbox.wallet.gov.tw/api/oidvp/qrcode"
# --- 配置區 ---


def generate_new_transaction_id():
    """自動產生 UUID v4 格式的唯一交易序號"""
    return str(uuid.uuid4())

def get_qrcode_image(ref_value: str, access_token: str, transaction_id: str) -> Optional[dict]:
    """
    呼叫數位憑證皮夾驗證端 API 產生 QR Code
    
    Args:
        ref_value: 驗證服務代碼 (ref)。
        access_token: 驗證端沙盒系統的 AccessToken。
        transaction_id: 本次請求的唯一交易序號 (UUID)。

    Returns:
        包含 API 回應資料 (transactionId, qrcodeImage, authUri) 的字典。
    """
    
    # 設置請求參數
    params = {
        "ref": ref_value,
        "transactionId": transaction_id
    }
    
    # 設置請求標頭
    headers = {
        "accept": "*/*",
        "Access-Token": access_token
    }
    
    print("--- 步驟 1: 發送 QR Code 產生請求 ---")
    print(f"使用的 ref: {ref_value}")
    print(f"使用的 transactionId: {transaction_id}")
    
    try:
        response = requests.get(API_BASE_URL, headers=headers, params=params, verify=True)
        response.raise_for_status()  # 對 HTTP 錯誤狀態碼 (如 4xx, 5xx) 拋出異常

        # API 成功回應 (200 OK)
        response_data = response.json()
        print("API 請求成功 (HTTP 200 OK)")
        return response_data
    
    except requests.exceptions.HTTPError as errh:
        # 處理 HTTP 錯誤
        print(f"HTTP 錯誤發生: {errh}")
        print(f"伺服器回應內容: {errh.response.text}")
        return None
    except requests.exceptions.RequestException as err:
        # 處理其他請求錯誤 (如連線失敗)
        print(f"請求失敗: {err}")
        return None

def save_base64_to_png(base64_data: str, filename_prefix: str = "qrcode_output") -> Optional[str]:
    """
    將 Data URI 格式的 Base64 圖片資料儲存為 PNG 檔案。
    
    Args:
        base64_data: 以 'data:image/png;base64,' 開頭的 Base64 字串。
        filename_prefix: 圖片檔名的前綴。

    Returns:
        儲存的檔案名稱。
    """
    # 移除 Data URI 的前綴部分
    if base64_data.startswith("data:image/png;base64,"):
        base64_content = base64_data.split(",")[1]
    else:
        # 假設如果沒有前綴，整個字串就是 base64 內容
        base64_content = base64_data

    # 解碼 Base64 內容
    try:
        image_bytes = base64.b64decode(base64_content)
    except Exception as e:
        print(f"Base64 解碼失敗: {e}")
        return None
        
    # Sanitize the filename_prefix to prevent path traversal
    safe_prefix = os.path.basename(filename_prefix)

    # 組合檔案名稱並寫入
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{safe_prefix}_{timestamp}.png"
    
    with open(filename, "wb") as f:
        f.write(image_bytes)
        
    return filename


def main_workflow(ref_to_test: str):
    """
    主流程：生成交易ID -> 呼叫API獲取QR Code -> 儲存圖片。
    
    Args:
        ref_to_test: 您要測試的驗證服務代碼。
    """
    
    # 1. transactionId 自動產生
    new_transaction_id = generate_new_transaction_id()

    # 2. call API (return: QR Code) 
    api_response = get_qrcode_image(ref_to_test, ACCESS_TOKEN, new_transaction_id)

    if api_response is None:
        print("\n 測試中止：API 呼叫失敗或發生錯誤。")
        return None

    # 3. save QR Code png
    qrcode_base64 = api_response.get("qrcodeImage")
    auth_uri = api_response.get("authUri")
    
    if qrcode_base64:
        image_filename = save_base64_to_png(qrcode_base64, ref_to_test)
        
        if image_filename:
            print("\n--- 成功結果 ---")
            print(f"儲存的 QR Code 圖片檔名: {os.path.abspath(image_filename)}")
            print("請用數位憑證皮夾 APP 掃描圖片，並在 5 分鐘內完成上傳。")
            print("\n--- 後續查詢參數 ---")
            print(f"transactionId (用於 POST /result): {new_transaction_id}")
            print(f"authUri (DeepLink): {auth_uri}")
        else:
            print("\n 圖片儲存失敗。")
    else:
        print("\n API 回應中未包含 qrcodeImage 欄位，請檢查 API 回應結構。")

    # 回傳 transactionId 供外部流程使用（即自動查詢）
    return new_transaction_id



#取得驗證內資料 
def get_verification_result(transaction_id: str, access_token: str):
    """
    查詢使用者掃描 QR Code 後的驗證結果。
    """
    url = "https://verifier-sandbox.wallet.gov.tw/api/oidvp/result"
    headers = {
        "Content-Type": "application/json",
        "Access-Token": access_token
    }
    payload = {"transactionId": transaction_id}

    print("\n--- 步驟 2: 查詢驗證結果 ---")
    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        print("成功取得驗證結果")
        result = response.json()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return result
    elif response.status_code == 400:
        print("用戶尚未上傳資料，請稍後再查詢")
    else:
        print(f"查詢失敗，HTTP {response.status_code}")
        print(response.text)
    return None



if __name__ == "__main__":
   
    test_ref = "00000000_iris_enter_mrt" 

    # 產生 QR Code 並取得 transactionId
    transaction_id = main_workflow(test_ref)