#!/usr/bin/env bash
set -e

echo "Starting MCP Server for Home Assistant..."
echo "HA Base URL: ${HA_BASE_URL:-http://homeassistant:8123}"

exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8099 \
    --log-level info \
    --no-access-log
