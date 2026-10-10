#!/bin/bash
set -e
echo "Installing ROZ Hub..."

# Only install what is missing: a bare `pacman -Sy` on Arch can cause partial upgrades
if command -v pacman >/dev/null; then
  sudo pacman -S --needed --noconfirm python tk
elif command -v apt-get >/dev/null; then
  sudo apt-get install -y python3 python3-tk
elif command -v dnf >/dev/null; then
  sudo dnf install -y python3 python3-tkinter
fi

INSTALL_DIR="/opt/roz-hub"
sudo mkdir -p "$INSTALL_DIR"
sudo cp -r roz_he_configurator.py he60_usb.py keyboard.json logo "$INSTALL_DIR/"
sudo bash -c 'cat > /usr/local/bin/roz-hub << EOF
#!/bin/bash
cd /opt/roz-hub && exec python3 roz_he_configurator.py "\$@"
EOF'
sudo chmod +x /usr/local/bin/roz-hub

# Launcher entry (app menu, GNOME dash/taskbar, KDE, etc.) and hicolor icon
sudo install -Dm644 roz-hub.desktop /usr/share/applications/roz-hub.desktop
sudo install -Dm644 logo/roz-256.png /usr/share/icons/hicolor/256x256/apps/roz-hub.png
sudo gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor 2>/dev/null || true
sudo update-desktop-database -q /usr/share/applications 2>/dev/null || true

if command -v desktop-file-validate >/dev/null; then
  desktop-file-validate /usr/share/applications/roz-hub.desktop
fi

echo "✓ ROZ Hub installed! Open it from the app menu, or run: roz-hub"
