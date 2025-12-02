from flask import Flask, request, jsonify, Response, make_response,redirect
import os
from functools import wraps
from dotenv import load_dotenv
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from markupsafe import escape
from generate_qrcode import (
    get_qrcode_image,
    save_base64_to_png,
    generate_new_transaction_id,
    get_verification_result,
    ACCESS_TOKEN,
)
import json
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Security: CORS configuration - only allow specific origins
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:*", "http://127.0.0.1:*"],  # 只允許本地開發
        "methods": ["GET", "POST"],
        "allow_headers": ["Content-Type", "X-API-Key"]
    }
})

# Security: Rate limiting to prevent abuse
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

# Security: API Key from environment
API_KEY = os.getenv('API_KEY', '')
if not API_KEY:
    raise ValueError("API_KEY not found in environment variables. Please set it in .env file.")

# Security: Whitelist of valid ref values
VALID_REFS = {
    '00000000_iris_enter_mrt',
    '00000000_iris_invoice_code',
    '00000000_iris_easycard',
    '00000000_irisstudent',
    '00000000_irisold',
}

# Security: Time-limited sensitive data storage (expires after 10 minutes)
last_result = {"transactionId": None, "authUri": None, "image": None, "ref": None, "expires_at": None}

def require_api_key(f):
    """Decorator to require API Key authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != API_KEY:
            app.logger.warning(f"Unauthorized access attempt from {request.remote_addr}")
            return jsonify({"error": "Unauthorized. Valid API Key required."}), 401
        return f(*args, **kwargs)
    return decorated_function

def clear_expired_data():
    """Clear sensitive data if expired"""
    if last_result.get("expires_at"):
        if datetime.now() > last_result["expires_at"]:
            last_result.update({"transactionId": None, "authUri": None, "image": None, "ref": None, "expires_at": None})
@app.route("/health", methods=["GET"])
def health():
    """Simple liveness check to verify network reachability from devices."""
    return Response("ok", mimetype="text/plain")




@app.route("/api/generate_by_ref", methods=["POST"])
@limiter.limit("10 per minute")  # 每分鐘最多 10 次請求
@require_api_key
def api_generate_by_ref():
    """
    POST JSON: {"ref": "<ref_value>"}
    Headers: {"X-API-Key": "your-api-key"}
    回傳 JSON: {"transactionId": "...", "authUri": "...", "image": "<filepath>"}
    """
    try:
        data = request.get_json() or {}
        ref = data.get("ref")
        
        # Input validation
        if not ref:
            return jsonify({"error": "missing ref"}), 400
        
        # Whitelist validation
        if ref not in VALID_REFS:
            app.logger.warning(f"Invalid ref attempted: {ref} from {request.remote_addr}")
            return jsonify({"error": "invalid ref value"}), 400
    except Exception as e:
        app.logger.error(f"Request validation error: {str(e)}")
        return jsonify({"error": "Invalid request format"}), 400
    
    ref = data.get("ref")
    if not ref:
        return jsonify({"error": "missing ref"}), 400

    try:
        transaction_id = generate_new_transaction_id()
        api_resp = get_qrcode_image(ref, ACCESS_TOKEN, transaction_id)
        if not api_resp:
            app.logger.error("Failed to get QR code from external API")
            return jsonify({"error": "Service temporarily unavailable"}), 502

        # 取回可能的 transactionId / qrcode / authUri
        tid = api_resp.get("transactionId", transaction_id)
        qrcode_b64 = api_resp.get("qrcodeImage")
        auth_uri = api_resp.get("authUri")

        image_path = None
        if qrcode_b64:
            try:
                image_path = save_base64_to_png(qrcode_b64, ref)
            except Exception as e:
                # 儲存失敗但不阻擋回傳
                image_path = None
                app.logger.warning(f"save image failed: {e}")

        # Security: Set expiration time for sensitive data (10 minutes)
        expires_at = datetime.now() + timedelta(minutes=10)
        last_result.update({
            "transactionId": tid, 
            "authUri": auth_uri, 
            "image": image_path, 
            "ref": ref,
            "expires_at": expires_at
        })
        return jsonify({"transactionId": tid, "authUri": auth_uri, "image": image_path})
    except Exception as e:
        app.logger.error(f"Error in generate_by_ref: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/result", methods=["POST"])
@limiter.limit("20 per minute")  # 查詢結果允許較高頻率
@require_api_key
def api_result():
    """
    POST JSON: {"transactionId": "..."}
    Headers: {"X-API-Key": "your-api-key"}
    直接呼叫 get_verification_result 並回傳原始結果
    """
    try:
        data = request.get_json() or {}
        tid = data.get("transactionId")
        if not tid:
            return jsonify({"error": "missing transactionId"}), 400

        result = get_verification_result(tid, ACCESS_TOKEN)
        if result is None:
            return jsonify({"error": "Verification result not available yet"}), 404
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Error in api_result: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500




def _html_page(title: str, body_html: str) -> Response:
    safe_title = escape(title)
    html = f"""
<!doctype html>
<html lang=zh-Hant>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{safe_title}</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ 
      font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Helvetica Neue', Helvetica, Arial, sans-serif; 
      background: #f2f2f7; 
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }}
    .pos-container {{ 
      background: #ffffff; 
      border-radius: 20px; 
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1), 0 1px 8px rgba(0, 0, 0, 0.05);
      max-width: 400px; 
      width: 100%; 
      overflow: hidden;
    }}
    .pos-header {{ 
      background: linear-gradient(135deg, #007AFF 0%, #5856D6 100%);
      color: white; 
      padding: 24px; 
      text-align: center; 
    }}
    .pos-header h1 {{ 
      font-size: 22px; 
      font-weight: 600; 
      margin-bottom: 4px;
      letter-spacing: -0.5px;
    }}
    .pos-header .subtitle {{ 
      font-size: 14px; 
      opacity: 0.85; 
      font-weight: 400;
    }}
    .pos-content {{ 
      padding: 24px; 
    }}
    .receipt-section {{ 
      border-bottom: 1px dashed #d1d1d6; 
      padding-bottom: 20px; 
      margin-bottom: 20px; 
    }}
    .receipt-section:last-child {{ 
      border-bottom: none; 
      margin-bottom: 0; 
    }}
    .receipt-row {{ 
      display: flex; 
      justify-content: space-between; 
      align-items: center; 
      margin-bottom: 12px; 
    }}
    .receipt-row:last-child {{ 
      margin-bottom: 0; 
    }}
    .receipt-label {{ 
      font-size: 15px; 
      color: #48484a; 
      font-weight: 400;
    }}
    .receipt-value {{ 
      font-size: 15px; 
      color: #1c1c1e; 
      font-weight: 500;
      text-align: right;
      max-width: 60%;
      word-break: break-all;
    }}
    .total-row {{ 
      font-size: 18px; 
      font-weight: 600; 
      padding-top: 12px; 
      border-top: 2px solid #007AFF;
    }}
    .total-row .receipt-label {{ 
      color: #1c1c1e; 
      font-weight: 600;
    }}
    .total-row .receipt-value {{ 
      color: #007AFF; 
      font-size: 20px;
    }}
    .status-badge {{ 
      display: inline-block; 
      padding: 6px 12px; 
      border-radius: 12px; 
      font-size: 13px; 
      font-weight: 600; 
      text-transform: uppercase; 
      letter-spacing: 0.5px;
    }}
    .status-verified {{ 
      background: #e6f7ed; 
      color: #059669; 
    }}
    .status-pending {{ 
      background: #fef3e6; 
      color: #d97706; 
    }}
    .status-error {{ 
      background: #fee6e6; 
      color: #dc2626; 
    }}
    .discount-note {{ 
      font-size: 13px; 
      color: #ff3b30; 
      font-weight: 500; 
      margin-left: 8px;
    }}
    .transaction-id {{ 
      font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', monospace; 
      font-size: 12px; 
      color: #8e8e93; 
      text-align: center; 
      padding: 16px; 
      background: #f9f9f9; 
      margin: -24px -24px 0 -24px; 
      border-top: 1px solid #e5e5ea;
    }}
    .empty-state {{ 
      text-align: center; 
      padding: 40px 24px; 
    }}
    .empty-state h2 {{ 
      font-size: 18px; 
      color: #1c1c1e; 
      margin-bottom: 8px; 
      font-weight: 600;
    }}
    .empty-state p {{ 
      font-size: 15px; 
      color: #8e8e93; 
      line-height: 1.4;
    }}
    .debug-section {{ 
      margin-top: 20px; 
      padding-top: 20px; 
      border-top: 1px solid #e5e5ea; 
    }}
    .debug-toggle {{ 
      background: #f2f2f7; 
      border: none; 
      padding: 10px 16px; 
      border-radius: 10px; 
      font-size: 13px; 
      color: #007AFF; 
      cursor: pointer; 
      width: 100%;
      font-weight: 500;
    }}
    .debug-content {{ 
      display: none; 
      margin-top: 12px; 
      background: #f9f9f9; 
      border-radius: 10px; 
      padding: 16px; 
    }}
    .debug-content pre {{ 
      font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', monospace; 
      font-size: 11px; 
      color: #48484a; 
      line-height: 1.4; 
      overflow-x: auto;
      white-space: pre-wrap;
      word-break: break-word;
    }}
  </style>
  <script>
    function toggleDebug() {{
      const content = document.getElementById('debug-content');
      const button = document.getElementById('debug-toggle');
      if (content.style.display === 'none' || content.style.display === '') {{
        content.style.display = 'block';
        button.textContent = '隱藏詳細資訊';
      }} else {{
        content.style.display = 'none';
        button.textContent = '顯示詳細資訊';
      }}
    }}
  </script>
</head>
<body>
{body_html}
</body>
</html>
"""
    resp = make_response(html)
    resp.mimetype = "text/html"
    resp.charset = "utf-8"
    # Prevent caching so reloading always fetches the latest
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp




# http://192.168.0.236:5001/view/result 
@app.route("/view/result", methods=["GET"])
def view_result():
    tid = request.args.get("transactionId") 
    # 若網址沒有 transactionId，就用最近一次的結果
    if not tid and last_result.get("transactionId"):
        tid = last_result["transactionId"]
        # 這時候 redirect 到有 transactionId 的 URL
        return redirect(f"/view/result?transactionId={tid}", code=302)

    # 如果仍然沒有 transactionId，就顯示「尚未產生交易」
    if not tid:
        body = (
            "<div class='pos-container'>"
            "<div class='pos-header'>"
            "<h1>POS 收銀系統</h1>"
            "<div class='subtitle'>等待交易</div>"
            "</div>"
            "<div class='empty-state'>"
            "<h2>尚未產生交易</h2>"
            "<p>請先在 App 端點擊出示以產生 QR Code<br>或透過 API 產生交易</p>"
            "</div>"
            "</div>"
        )
        return _html_page("POS 收銀系統", body)
    
    safe_tid = escape(tid)
      
    data = get_verification_result(tid, ACCESS_TOKEN)
    if data is None:
        body = (
            "<div class='pos-container'>"
            "<div class='pos-header'>"
            "<h1>POS 收銀系統</h1>"
            "<div class='subtitle'>處理中</div>"
            "</div>"
            "<div class='empty-state'>"
            "<h2>等待驗證結果</h2>"
            "<p>正在驗證數位身份證件<br>請稍後...</p>"
            "</div>"
            f"<div class='transaction-id'>交易序號: {safe_tid}</div>"
            "</div>"
        )
        return _html_page("POS 收銀系統 - 處理中", body)

    # 交易資訊：預設金額 100，身份為已驗證學生時 9 折
    amount_val = 100.0
    # 動態抓取顯示標籤（來自第一個 claims 的 cname）與值
    carrier_label, invoice_code = _extract_carrier_label_and_value(data)
    has_student = _has_verified_student(data)
    has_older = _has_verified_older(data)
    
    # Determine discount and identity
    discount_amount = 0
    if has_student:
        total = amount_val * 0.9
        identity_label = "學生"
        discount_amount = amount_val * 0.1
        discount_note = "-10%"
    elif has_older:
        total = amount_val * 0.8
        identity_label = "長者"
        discount_amount = amount_val * 0.2
        discount_note = "-20%"
    else:
        total = amount_val
        identity_label = "一般"
        discount_note = ""
    
    verification_status = "已驗證" if data.get("verifyResult") else "待驗證"
    status_class = "status-verified" if data.get("verifyResult") else "status-pending"
    
    # Generate POS-style receipt
    body = f"""
<div class='pos-container'>
<div class='pos-header'>
<h1>POS 收銀系統</h1>
<div class='subtitle'>交易完成</div>
</div>
<div class='pos-content'>

<div class='receipt-section'>
<div class='receipt-row'>
<span class='receipt-label'>身份驗證</span>
<span class='status-badge {status_class}'>{verification_status}</span>
</div>
<div class='receipt-row'>
<span class='receipt-label'>身份類別</span>
<span class='receipt-value'>{identity_label}</span>
</div>"""
    
    # Add carrier information if available
    if invoice_code:
        label_display = carrier_label or "載具條碼 "
        body += f"""
<div class='receipt-row'>
<span class='receipt-label'>{label_display}</span>
<span class='receipt-value'>{invoice_code}</span>
</div>"""
    
    body += """
</div>

<div class='receipt-section'>
<div class='receipt-row'>
<span class='receipt-label'>商品金額</span>
<span class='receipt-value'>NT$ {:.0f}</span>
</div>""".format(amount_val)
    
    # Add discount row if applicable
    if discount_amount > 0:
        body += f"""
<div class='receipt-row'>
<span class='receipt-label'>優惠折扣 {discount_note}</span>
<span class='receipt-value discount-note'>-NT$ {discount_amount:.0f}</span>
</div>"""
    
    # Total amount
    body += f"""
<div class='receipt-row total-row'>
<span class='receipt-label'>應付金額</span>
<span class='receipt-value'>NT$ {total:.0f}</span>
</div>
</div>"""
    
    # Debug section for developers
    if data:
        pretty_json = json.dumps(data, ensure_ascii=False, indent=2)
        body += f"""
<div class='debug-section'>
<button id='debug-toggle' class='debug-toggle' onclick='toggleDebug()'>顯示詳細資訊</button>
<div id='debug-content' class='debug-content'>
<pre>{pretty_json}</pre>
</div>
</div>"""
    
    body += f"""
</div>
<div class='transaction-id'>交易序號: {safe_tid}</div>
</div>
"""

    return _html_page("POS 收銀系統", body)






# -------- Helpers for business extraction --------
def _iter_objects(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _iter_objects(v)
    elif isinstance(obj, list):
        for item in obj:
            yield from _iter_objects(item)

def _find_claim_in_list(claims_list, recognized_enames, recognized_cnames):
    """Helper to find a recognized claim in a list of claims."""
    if not isinstance(claims_list, list):
        return None
    for claim in claims_list:
        if not isinstance(claim, dict):
            continue
        ename = claim.get("ename")
        cname = claim.get("cname")
        if (ename in recognized_enames) or (cname in recognized_cnames):
            val = claim.get("value")
            if isinstance(val, (str, int, float)) and str(val).strip():
                return {"label": cname or "載具條碼", "value": str(val)}
    return None

def _find_first_non_empty_claim(claims_list):
    """Helper to find the first non-empty claim as a fallback."""
    if not isinstance(claims_list, list):
        return None
    for claim in claims_list:
        if not isinstance(claim, dict):
            continue
        v = claim.get("value")
        if isinstance(v, (str, int, float)) and str(v).strip():
            return {"label": claim.get("cname") or "載具條碼", "value": str(v)}
    return None

def _extract_carrier_label_and_value(data: dict):
    """
    Extracts a display label and value from the data structure based on credential types.
    - Supports '00000000_iris_invoice_code' and '00000000_iris_easycard'.
    - Searches for specific claim names ('invoicenum', 'easycard_ID', etc.).
    - Falls back to the first non-empty claim if specific ones are not found.
    Returns: (label: Optional[str], value: Optional[str])
    """
    target_types = {"00000000_iris_invoice_code", "00000000_iris_easycard"}
    recognized_enames = {"invoicenum", "easycard_ID"}
    recognized_cnames = {"載具條碼", "卡號"}

    for node in _iter_objects(data):
        if not isinstance(node, dict) or node.get("credentialType") not in target_types:
            continue

        claims_sources = [node.get("claims")]
        cred_subj = node.get("credentialSubject")
        if isinstance(cred_subj, dict):
            claims_sources.append(cred_subj.get("claims"))

        # Search for recognized claims, then fallback to first non-empty
        for claims in claims_sources:
            hit = _find_claim_in_list(claims, recognized_enames, recognized_cnames)
            if hit:
                return hit.get("label"), hit.get("value")
            
            fallback = _find_first_non_empty_claim(claims)
            if fallback:
                return fallback.get("label"), fallback.get("value")

    return None, None

def _extract_invoice_code(data: dict):
    """保留舊介面：只回傳值（供現有呼叫者使用）。"""
    _, value = _extract_carrier_label_and_value(data)
    return value

def _has_verified_student(data: dict) -> bool:
    target_type = "00000000_irisstudent"

    # 先確認 verifyResult 為 True
    if not data.get("verifyResult"):
        return False

    # 再檢查 data 陣列中是否包含該 credentialType
    for item in data.get("data", []):
        if isinstance(item, dict) and item.get("credentialType") == target_type:
            return True

    return False

def _has_verified_older(data: dict) -> bool:
    target_type = "00000000_irisold"

    # 先確認 verifyResult 為 True
    if not data.get("verifyResult"):
        return False

    # 再檢查 data 陣列中是否包含該 credentialType
    for item in data.get("data", []):
        if isinstance(item, dict) and item.get("credentialType") == target_type:
            return True

    return False



if __name__ == "__main__":
    # 執行：在 uuse 資料夾啟動 python generate_qrcode_api.py
    app.run(host="127.0.0.1", port=5001, debug=False)