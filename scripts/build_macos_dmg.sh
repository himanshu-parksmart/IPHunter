#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PROJECT_DIR}/venv/bin/python"
DMG_PATH="${PROJECT_DIR}/dist/IPHunter-macOS-arm64.dmg"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Missing venv. Run: python3 -m venv venv && venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

cd "${PROJECT_DIR}"
"${PYTHON_BIN}" -m PyInstaller --noconfirm --clean IPHunter.spec
codesign --force --deep --sign - "${PROJECT_DIR}/dist/IPHunter.app"

STAGING_DIR="$(mktemp -d /tmp/iphunter-dmg.XXXXXX)"
cleanup() {
  if [[ -n "${STAGING_DIR:-}" && -d "${STAGING_DIR}" ]]; then
    rm -rf "${STAGING_DIR}"
  fi
}
trap cleanup EXIT

cp -R "${PROJECT_DIR}/dist/IPHunter.app" "${STAGING_DIR}/IPHunter.app"
ln -s /Applications "${STAGING_DIR}/Applications"
rm -f "${DMG_PATH}"
hdiutil create \
  -volname "IPHunter" \
  -srcfolder "${STAGING_DIR}" \
  -ov \
  -format UDZO \
  "${DMG_PATH}"

echo "Created ${DMG_PATH}"
