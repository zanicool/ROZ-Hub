#!/bin/bash
echo "Uninstalling ROZ Hub..."
sudo rm -rf /opt/roz-hub
sudo rm -f /usr/local/bin/roz-hub
sudo rm -f /usr/share/applications/roz-hub.desktop
sudo rm -f /usr/share/icons/hicolor/256x256/apps/roz-hub.png
sudo gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor 2>/dev/null || true
sudo update-desktop-database -q /usr/share/applications 2>/dev/null || true
echo "✓ ROZ Hub removed."
