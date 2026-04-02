#!/usr/bin/env bash
# HyprAgent system dependency installer (CachyOS/Arch)
# Run once as your normal user from the project root.
set -euo pipefail

echo "==> Installing system packages..."
sudo pacman -S --needed grim slurp ydotool wl-clipboard tesseract tesseract-data-eng

echo "==> Loading uinput kernel module..."
sudo modprobe uinput
echo "uinput" | sudo tee /etc/modules-load.d/uinput.conf

echo "==> Adding user to input group (re-login required to take effect)..."
sudo usermod -aG input "$USER"

echo "==> Enabling ydotoold systemd user service..."
systemctl --user enable --now ydotoold

echo "==> Installing Python dependencies via uv..."
uv sync

echo "==> Installing Playwright Chromium..."
uv run playwright install chromium

echo ""
echo "Done! Re-login for input group membership to take effect."
echo "Then verify with: ydotool --help && systemctl --user is-active ydotoold"
