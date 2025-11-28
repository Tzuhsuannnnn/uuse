import os
import sys
from pathlib import Path as _Path
import uuid
import tempfile
import base64
from pathlib import Path

# Ensure env vars exist BEFORE importing modules that enforce them
os.environ.setdefault("API_KEY", "test-api-key")
os.environ.setdefault("IRIS_ACCESS_TOKEN", "test-access-token")

# Ensure repo root is importable
_REPO_ROOT = str(_Path(__file__).resolve().parents[1])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from generate_qrcode import generate_new_transaction_id, save_base64_to_png  # noqa: E402
from generate_qrcode_api import (  # noqa: E402
    _extract_carrier_label_and_value,
    _has_verified_student,
    _has_verified_older,
)


def test_generate_new_transaction_id_is_uuid_v4():
    tid = generate_new_transaction_id()
    parsed = uuid.UUID(tid, version=4)
    assert str(parsed) == tid


def test_save_base64_to_png_creates_file(tmp_path):
    # 1x1 transparent PNG
    png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
    )
    cwd = os.getcwd()
    try:
        # Ensure file lands in tmp dir
        os.chdir(tmp_path)
        fname = save_base64_to_png(png_b64, "testqr")
        assert fname is not None
        p = Path(fname)
        assert p.exists() and p.stat().st_size > 0
    finally:
        os.chdir(cwd)


def test_extract_carrier_label_and_value_with_invoice_claim():
    data = {
        "verifyResult": True,
        "data": [
            {
                "credentialType": "00000000_iris_invoice_code",
                "claims": [
                    {"ename": "invoicenum", "cname": "載具條碼", "value": "AB-1234567"}
                ],
            }
        ],
    }
    label, value = _extract_carrier_label_and_value(data)
    assert label in ("載具條碼", "卡號", None)
    assert value == "AB-1234567"


def test_has_verified_student_and_older_flags():
    base = {"verifyResult": True, "data": []}

    # Student present
    data_student = {
        **base,
        "data": [{"credentialType": "00000000_irisstudent"}],
    }
    assert _has_verified_student(data_student) is True
    assert _has_verified_older(data_student) is False

    # Older present
    data_older = {
        **base,
        "data": [{"credentialType": "00000000_irisold"}],
    }
    assert _has_verified_student(data_older) is False
    assert _has_verified_older(data_older) is True

    # Neither when verifyResult is False
    data_unverified = {"verifyResult": False, "data": [{"credentialType": "00000000_irisstudent"}]}
    assert _has_verified_student(data_unverified) is False
    assert _has_verified_older(data_unverified) is False
