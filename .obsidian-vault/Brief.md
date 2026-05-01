---
source: docs-generated
generated-at: first-run
---

# HyprAgent

## What It Does
Native, model-agnostic computer use agent for Hyprland/Wayland. Exposes full Linux desktop control as MCP (Model Context Protocol) tools — works with Claude Code, OpenCode, or any MCP client.

## Primary Goal
Give AI agents native desktop control on Hyprland/Wayland without needing a browser-based or VM-based approach — pure system-level automation via MCP.

## Major Components
- **MCP Server** — Exposes desktop control tools via Model Context Protocol
- **Screenshot/OCR** — grim + slurp for screen capture; Tesseract for text extraction
- **Input Automation** — ydotool for keyboard/mouse control via uinput
- **Clipboard** — wl-clipboard for Wayland clipboard integration
- **Config** — config.yaml for agent settings

## Technology Stack
- Runtime: Python (uv project manager)
- Protocol: MCP (Model Context Protocol)
- Screenshot: grim, slurp
- Input: ydotool, uinput kernel module
- OCR: Tesseract
- Clipboard: wl-clipboard
- Wayland: Hyprland compositor

## Architectural Principles
- Model-agnostic: works with any MCP client
- Native Wayland-first (no X11 emulation layer)
- System-level desktop control via uinput
- Single config.yaml for all settings
