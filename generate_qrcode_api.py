from flask import Flask, request, jsonify, Response, make_response,redirect
import os
from generate_qrcode import (
    get_qrcode_image,
    save_base64_to_png,
    generate_new_transaction_id,
    get_verification_result,
    ACCESS_TOKEN,
)
import json

app = Flask(__name__)

# 儲存最後一次產生的結果
last_result = {"transactionId": None, "authUri": None, "image": None, "ref": None}
@app.route("/health", methods=["GET"])
def health():
    """Simple liveness check to verify network reachability from devices."""
    return Response("ok", mimetype="text/plain")




@app.route("/api/generate_by_ref", methods=["POST"])
def api_generate_by_ref():
    """
    POST JSON: {"ref": "<ref_value>"}
    回傳 JSON: {"transactionId": "...", "authUri": "...", "image": "<filepath>"}
    """
    data = request.get_json() or {}
    ref = data.get("ref")
    if not ref:
        return jsonify({"error": "missing ref"}), 400

    transaction_id = generate_new_transaction_id()
    api_resp = get_qrcode_image(ref, ACCESS_TOKEN, transaction_id)
    if not api_resp:
        return jsonify({"error": "qrcode api call failed"}), 502

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

    last_result.update({"transactionId": tid, "authUri": auth_uri, "image": image_path, "ref": ref})
    return jsonify({"transactionId": tid, "authUri": auth_uri, "image": image_path})


@app.route("/api/result", methods=["POST"])
def api_result():
    """
    POST JSON: {"transactionId": "..."}
    直接呼叫 get_verification_result 並回傳原始結果
    """
    data = request.get_json() or {}
    tid = data.get("transactionId")
    if not tid:
        return jsonify({"error": "missing transactionId"}), 400

    result = get_verification_result(tid, ACCESS_TOKEN)
    if result is None:
        return jsonify({"error": "query failed or no result yet"}), 502
    return jsonify(result)




def _html_page(title: str, body_html: str) -> Response:
    html = f"""
<!doctype html>
<html lang=zh-Hant>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
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
            f"<div class='transaction-id'>交易序號: {tid}</div>"
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
        status_class = "status-verified"
        discount_amount = amount_val * 0.1
        discount_note = "-10%"
    elif has_older:
        total = amount_val * 0.8
        identity_label = "長者"
        status_class = "status-verified"
        discount_amount = amount_val * 0.2
        discount_note = "-20%"
    else:
        total = amount_val
        identity_label = "一般"
        status_class = "status-verified"
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
        label_display = carrier_label or "載具條碼"
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
<div class='transaction-id'>交易序號: {tid}</div>
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

#00000000_iris_easycard
def _extract_carrier_label_and_value(data: dict):
    """
    依照固定回傳格式抓取顯示標籤與值：
    - 支援多種 credentialType：
      - 00000000_iris_invoice_code
      - 00000000_iris_easycard
    - 先嘗試於 claims/credentialSubject.claims 陣列中，尋找下列欄位名稱之一：
      - ename: "invoicenum"（發票載具）
      - cname: "載具條碼"
      - ename: "easycard_ID"（悠遊卡）
      - cname: "卡號"
    - 若無上述欄位，fallback：回傳第一個 claims 的 cname 與其值（非空），以符合「顯示第一個 cname 與第一個值」的需求。

    回傳：(label: Optional[str], value: Optional[str])
    """
    target_types = {"00000000_iris_invoice_code", "00000000_iris_easycard"}

    # 可擴充的欄位名稱白名單（避免誤抓）
    # 發票載具: invoicenum / 載具條碼
    # 悠遊卡: easycard_ID / 卡號
    recognized_enames = {"invoicenum", "easycard_ID"}
    recognized_cnames = {"載具條碼", "卡號"}

    def _extract_from_claims(claims_list):
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

    for node in _iter_objects(data):
        if not isinstance(node, dict):
            continue
        if node.get("credentialType") not in target_types:
            continue

        # 直接從 claims 陣列找指定的欄位
        claims1 = node.get("claims")
        hit = _extract_from_claims(claims1)
        if hit:
            return hit.get("label"), hit.get("value")

        # 一些資料可能把 claims 放在 credentialSubject 底下
        cred_subj = node.get("credentialSubject")
        if isinstance(cred_subj, dict):
            claims2 = cred_subj.get("claims")
            hit = _extract_from_claims(claims2)
            if hit:
                return hit.get("label"), hit.get("value")

        # Fallback：若上述欄位名稱皆未命中，回傳該 credential 第一個 claim 的 value（非空）
        # 以符合「載具條碼為第一個 claims 的第一個值」的需求。
        def _first_non_empty_value(claims_list):
            if not isinstance(claims_list, list):
                return None
            for claim in claims_list:
                if not isinstance(claim, dict):
                    continue
                v = claim.get("value")
                if isinstance(v, (str, int, float)) and str(v).strip():
                    return {"label": claim.get("cname") or "載具條碼", "value": str(v)}
            return None

        v1 = _first_non_empty_value(claims1)
        if v1:
            return v1.get("label"), v1.get("value")
        if isinstance(cred_subj, dict):
            v2 = _first_non_empty_value(cred_subj.get("claims"))
            if v2:
                return v2.get("label"), v2.get("value")

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