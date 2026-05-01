---
source: brief
introduced-in: first-run
last-updated: first-run
component: Input Automation
---

# ydotool + uinput

## Why Chosen
ydotool is the Wayland-native replacement for xdotool — works via the uinput kernel module rather than X11's XTEST extension. Required for Hyprland which is a pure Wayland compositor with no X11 compatibility layer for input injection.

## How It Fits
Provides keyboard and mouse input automation. Requires sudo modprobe uinput and user group membership (input). All keyboard/mouse actions from the MCP server route through ydotool.

## Problem Solved
X11-based input tools (xdotool, pyautogui) don't work under Wayland. ydotool is the only reliable way to inject keyboard/mouse events on a pure Wayland system.
