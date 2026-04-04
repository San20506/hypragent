#!/usr/bin/env bash
# HyprAgent system dependency installer (CachyOS/Arch)
# Run once as your normal user from the project root.
set -euo pipefail

echo "==> Installing system packages..."
sudo pacman -S --needed grim slurp wl-clipboard tesseract tesseract-data-eng

echo "==> Loading uinput kernel module..."
sudo modprobe uinput
echo "uinput" | sudo tee /etc/modules-load.d/uinput.conf

echo "==> Adding user to input group (re-login required to take effect)..."
sudo usermod -aG input "$USER"

echo "==> Installing Python dependencies via uv..."
uv sync
# Note: evdev is installed as a Python dependency via uv (see pyproject.toml)

echo "==> Installing Playwright Chromium..."
uv run playwright install chromium

echo ""
echo "Done! Re-login for input group membership to take effect."
echo "Then verify with: python3 -c \"from evdev import UInput; print('evdev ok')\""
