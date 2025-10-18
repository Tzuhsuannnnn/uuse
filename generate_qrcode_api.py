from flask import Flask, request, jsonify
import os
from generate_qrcode import (
    get_qrcode_image,
    save_base64_to_png,
    generate_new_transaction_id,
    get_verification_result,
    ACCESS_TOKEN,
)

app = Flask(__name__)

# 儲存最後一次產生的結果
last_result = {"transactionId": None, "authUri": None, "image": None, "ref": None}


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


@app.route("/api/last", methods=["GET"])
def api_last():
    return jsonify(last_result)


if __name__ == "__main__":
    # 執行：在 uuse 資料夾啟動 python generate_qrcode_api.py
    # 需要安裝 flask：pip install flask
    app.run(host="0.0.0.0", port=5001, debug=False)