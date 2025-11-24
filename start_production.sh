#!/bin/bash
# Production startup script using Gunicorn

# 啟動 Gunicorn WSGI server
gunicorn \
    --bind 127.0.0.1:5001 \
    --workers 4 \
    --timeout 120 \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log \
    --log-level info \
    generate_qrcode_api:app
