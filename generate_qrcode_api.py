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
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, 'Noto Sans', sans-serif; margin: 24px; color: #111; }}
    .card {{ border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px; margin-bottom: 16px; background: #fff; }}
    h1 {{ font-size: 20px; margin: 0 0 12px 0; }}
    h2 {{ font-size: 16px; margin: 16px 0 8px 0; }}
    pre {{ background: #f8fafc; padding: 12px; overflow: auto; border-radius: 8px; border: 1px solid #e5e7eb; }}
    .muted {{ color: #6b7280; }}
    .ok {{ color: #059669; font-weight: 600; }}
    .warn {{ color: #d97706; font-weight: 600; }}
    .err {{ color: #dc2626; font-weight: 600; }}
    a.button {{ display: inline-block; padding: 8px 12px; border-radius: 8px; border: 1px solid #e5e7eb; text-decoration: none; color: #111; background: #f8fafc; }}
  </style>
    <!-- Auto-refresh removed by request; manual navigation only -->
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


def _render_result_summary(data: dict) -> str:
    # Try to extract a few common fields if present; fallback to pretty JSON.
    # Since exact schema may vary, we keep this defensive.
    status = data.get("status") or data.get("code") or data.get("result")
    ts = data.get("time") or data.get("timestamp")

    # Look for potential claims/payload areas
    subject = None
    credential_subject = None
    if isinstance(data.get("payload"), dict):
        payload = data["payload"]
        subject = payload.get("subject") or payload.get("sub")
        credential_subject = payload.get("credentialSubject") or payload.get("claims")

    lines = ["<div class='card'>", f"<h1>驗證結果</h1>"]
    if status is not None:
        lines.append(f"<div>狀態：<span class='ok'>{status}</span></div>")
    if ts:
        lines.append(f"<div class='muted'>時間：{ts}</div>")
    if subject:
        lines.append(f"<div>對象：{subject}</div>")
    if credential_subject:
        # Print a small subset if it's large
        snippet = json.dumps(credential_subject, ensure_ascii=False)[:600]
        lines.append("<h2>主體內容 (節錄)</h2>")
        lines.append(f"<pre>{snippet}</pre>")
    lines.append("</div>")

    # Full JSON
    pretty = json.dumps(data, ensure_ascii=False, indent=2)
    lines.append("<div class='card'>")
    lines.append("<h2>原始回應 JSON</h2>")
    lines.append(f"<pre>{pretty}</pre>")
    lines.append("</div>")
    return "\n".join(lines)

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
            "<div class='card'><h1>尚未產生交易</h1>"
            "<div class='muted'>請先在 App 端點擊出示以產生 QR，或以 API 產生一筆交易。</div>"
            "</div>"
        )
        return _html_page("驗證結果", body)
    
      
    data = get_verification_result(tid, ACCESS_TOKEN)
    if data is None:
        body = (
            f"<div class='card'><h1>尚未取得驗證結果</h1>"
            f"<div>交易序號：<code>{tid}</code></div>"
            "<div class='muted'>請稍後再試。</div>"
            "</div>"
        )
        return _html_page("驗證結果 - 等待中", body)

    # 交易資訊：預設金額 100，身份為已驗證學生時 9 折
    amount_val = 100.0
    invoice_code = _extract_invoice_code(data)
    has_student = _has_verified_student(data)
    has_older = _has_verified_older(data)
    
    # Determine discount and identity
    if has_student:
        total = amount_val * 0.9
        identity_label = "學生（已驗證）"
        discount_note = "（學生9折）"
    elif has_older:
        total = amount_val * 0.8  # Assuming 20% discount for older adults
        identity_label = "長者（已驗證）"
        discount_note = "（長者8折）"
    else:
        total = amount_val
        identity_label = "一般"
        discount_note = ""
    
    total_display = f"{total:.2f}"

    summary_html = (
        f"<div class='card'>"
        f"<h2>交易資訊</h2>"
        f"<div>載具條碼：<code>{invoice_code or '未提供'}</code></div>"
        f"<div>原價：<strong>{amount_val:.2f}</strong></div>"
        f"<div>身份：{identity_label}</div>"
        f"<div>總價：<strong>{total_display}</strong> {discount_note}</div>"
        f"</div>"
    )

    body = summary_html + _render_result_summary(data)
    return _html_page("驗證結果", body)






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
def _extract_invoice_code(data: dict):
    """
    依照固定回傳格式直接抓取載具條碼：
    - 找到 credentialType == "00000000_iris_invoice_code" 的物件
    - 於其 "claims" 陣列中，找到 ename == "invoicenum" 或 cname == "載具條碼" 的項目
    - 回傳該項目的 value 字串

    若上述路徑未找到，保守地回傳 None（或可擴充為其他 fallback）。
    """
    target_type = "00000000_iris_invoice_code"

    for node in _iter_objects(data):
        if not isinstance(node, dict):
            continue
        if node.get("credentialType") != target_type:
            continue

        # 直接從 claims 陣列找指定的欄位
        claims = node.get("claims")
        if isinstance(claims, list):
            for claim in claims:
                if not isinstance(claim, dict):
                    continue
                ename = claim.get("ename")
                cname = claim.get("cname")
                if ename == "invoicenum" or cname == "載具條碼":
                    val = claim.get("value")
                    if isinstance(val, (str, int, float)) and str(val).strip():
                        return str(val)

        # 一些資料可能把 claims 放在 credentialSubject 底下
        cred_subj = node.get("credentialSubject")
        if isinstance(cred_subj, dict):
            claims2 = cred_subj.get("claims")
            if isinstance(claims2, list):
                for claim in claims2:
                    if not isinstance(claim, dict):
                        continue
                    ename = claim.get("ename")
                    cname = claim.get("cname")
                    if ename == "invoicenum" or cname == "載具條碼":
                        val = claim.get("value")
                        if isinstance(val, (str, int, float)) and str(val).strip():
                            return str(val)

    return None

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
    app.run(host="0.0.0.0", port=5001, debug=False)