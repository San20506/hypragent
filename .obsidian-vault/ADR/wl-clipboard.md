---
source: brief
introduced-in: first-run
last-updated: first-run
component: Clipboard
---

# wl-clipboard

## Why Chosen
wl-copy and wl-paste are the standard Wayland clipboard utilities — native, no X11 dependency. Scriptable from the command line, making them trivial to wrap as MCP tool calls.

## How It Fits
Clipboard read (wl-paste) and write (wl-copy) operations exposed as MCP tools. Enables AI agents to read current clipboard content or set clipboard data as part of automation workflows.

## Problem Solved
xclip/xsel don't work on Wayland. wl-clipboard is the correct native solution for clipboard interaction on Hyprland.
