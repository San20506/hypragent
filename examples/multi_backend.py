"""Example: swap backends without changing code.

Demonstrates loading claude, gemini, and ollama backends
from different config dicts at runtime.
"""

import os
from agent.backends import load_backend

# ── Claude ────────────────────────────────────────────────────────────────────

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-your-key-here")

claude_config = {
    "backend": {
        "active": "claude",
        "claude": {
            "model": "claude-sonnet-4-6",
            "api_key_env": "ANTHROPIC_API_KEY",
        }
    }
}

backend = load_backend(claude_config)
print(f"Claude:  model={backend.get_model_name()}, vision={backend.supports_vision()}")

# ── Gemini ────────────────────────────────────────────────────────────────────

os.environ.setdefault("GEMINI_API_KEY", "AIza-your-key-here")

gemini_config = {
    "backend": {
        "active": "gemini",
        "gemini": {
            "model": "gemini-2.5-flash",
            "api_key_env": "GEMINI_API_KEY",
        }
    }
}

backend = load_backend(gemini_config)
print(f"Gemini:  model={backend.get_model_name()}, vision={backend.supports_vision()}")

# ── Ollama (local) ────────────────────────────────────────────────────────────

ollama_config = {
    "backend": {
        "active": "ollama",
        "ollama": {
            "model": "llava",
            "endpoint": "http://localhost:11434",
        }
    }
}

backend = load_backend(ollama_config)
print(f"Ollama:  model={backend.get_model_name()}, vision={backend.supports_vision()}")

print("\nAll backends loaded. Switch 'backend.active' in config.yaml to change.")
