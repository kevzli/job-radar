#!/bin/bash
# Install Job Radar as a macOS login service: the web app stays up at
# http://localhost:8787 and runs a scan automatically every scan_every_days (14).
#   ./install.sh            install / reinstall
#   ./install.sh uninstall  remove
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
LABEL="com.jobradar.server"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
if [ "${1:-}" = "uninstall" ]; then
  rm -f "$PLIST"; echo "Removed $LABEL"; exit 0
fi

mkdir -p "$HOME/Library/LaunchAgents" "$DIR/data"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array><string>/usr/bin/python3</string><string>$DIR/server.py</string></array>
  <key>WorkingDirectory</key><string>$DIR</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$DIR/data/server.log</string>
  <key>StandardErrorPath</key><string>$DIR/data/server.log</string>
</dict></plist>
EOF
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "Installed. Job Radar: http://localhost:8787 (scans every 14 days; log at data/server.log)"
