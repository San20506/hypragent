---
source: brief
introduced-in: first-run
last-updated: first-run
component: MCP Server
---

# MCP (Model Context Protocol)

## Why Chosen
MCP is the standard protocol for exposing tools to AI agents. Using MCP makes HyprAgent model-agnostic — Claude Code, OpenCode, and any future MCP client can use it without changes. The protocol handles tool discovery, parameter schemas, and result formatting.

## How It Fits
HyprAgent runs as an MCP server. Clients add it via `claude mcp add hypr-agent -- uv run ...`. Each desktop action (screenshot, click, type, clipboard read/write) is an MCP tool.

## Problem Solved
Need for a standard interface that decouples the desktop control implementation from the AI client — avoids building Claude-specific or OpenAI-specific integrations.
