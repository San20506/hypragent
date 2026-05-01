---
source: brief
introduced-in: first-run
last-updated: first-run
component: Screenshot
---

# grim + slurp

## Why Chosen
grim is the standard Wayland screenshot utility — takes full-screen or region screenshots from Wayland compositors. slurp provides interactive region selection. Both are lightweight, scriptable, and widely available on Arch/CachyOS.

## How It Fits
Screenshot tool in the MCP server. grim captures the screen; output is base64-encoded and returned to the AI client for visual understanding. slurp enables region-specific captures.

## Problem Solved
Need for programmatic screen capture on Wayland — X11 tools like scrot/import don't work on pure Wayland compositors.
