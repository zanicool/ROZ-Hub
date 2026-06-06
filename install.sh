#!/bin/bash
set -e
echo "Installing ROZ Hub..."

sudo apt-get install -y python3 python3-tk 2>/dev/null || sudo dnf install -y python3 python3-tkinter 2>/dev/null || sudo pacman -Sy --noconfirm python tk 2>/dev/null

INSTALL_DIR="/opt/roz-hub"
sudo mkdir -p "$INSTALL_DIR"
sudo cp roz_he_configurator.py he60_usb.py keyboard.json "$INSTALL_DIR/"
sudo bash -c 'cat > /usr/local/bin/roz-hub << EOF
#!/bin/bash
cd /opt/roz-hub && python3 roz_he_configurator.py
EOF'
sudo chmod +x /usr/local/bin/roz-hub

echo "✓ ROZ Hub installed! Run: roz-hub"
