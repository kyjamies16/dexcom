#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/dexcom_2}"
SERVICE_NAME="dexcom2.service"

echo "[dexcom] Installing to ${APP_DIR}"

sudo mkdir -p "${APP_DIR}"
sudo rsync -a --delete "./" "${APP_DIR}/"

python3 -m venv "${APP_DIR}/venv"
"${APP_DIR}/venv/bin/pip" install --upgrade pip
"${APP_DIR}/venv/bin/pip" install -r "${APP_DIR}/requirements.txt"

# Render systemd unit with chosen APP_DIR
sudo mkdir -p /etc/systemd/system
sudo sed "s|@APP_DIR@|${APP_DIR}|g" "${APP_DIR}/scripts/dexcom2.service" | sudo tee "/etc/systemd/system/${SERVICE_NAME}" >/dev/null

sudo systemctl daemon-reload
sudo systemctl enable --now "${SERVICE_NAME}"

echo "Installed and started ${SERVICE_NAME}. To switch to minimal mode, edit ExecStart in /etc/systemd/system/${SERVICE_NAME} and add --mode minimal, then run: sudo systemctl daemon-reload && sudo systemctl restart ${SERVICE_NAME}"
