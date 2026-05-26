"""Gemini backend adapter."""

import os

import google.generativeai as genai

from agent.backends.base import AgentResponse, BackendAdapter

# Map JSON Schema types to Gemini proto types
_JSONSCHEMA_TO_GEMINI = {
    "string": genai.protos.Type.STRING,
    "integer": genai.protos.Type.INTEGER,
    "number": genai.protos.Type.NUMBER,
    "boolean": genai.protos.Type.BOOLEAN,
    "object": genai.protos.Type.OBJECT,
    "array": genai.protos.Type.ARRAY,
}


def _to_gemini_schema(jsonschema: dict) -> genai.protos.Schema:
    """Convert a JSON Schema property dict to a Gemini Schema.

    Recursively handles nested objects and type arrays.
    """
    schema_type = genai.protos.Type.STRING  # default

    raw_type = jsonschema.get("type", "string")
    if isinstance(raw_type, list):
        # ["string", "null"] → pick first non-null type
        for t in raw_type:
            if t != "null" and t in _JSONSCHEMA_TO_GEMINI:
                schema_type = _JSONSCHEMA_TO_GEMINI[t]
                break
    elif raw_type in _JSONSCHEMA_TO_GEMINI:
        schema_type = _JSONSCHEMA_TO_GEMINI[raw_type]

    schema_kwargs: dict = {"type": schema_type}

    # Description
    if "description" in jsonschema:
        schema_kwargs["description"] = jsonschema["description"]

    # Enum values
    if "enum" in jsonschema:
        schema_kwargs["enum"] = jsonschema["enum"]

    # Nested properties (for object types)
    if jsonschema.get("properties"):
        schema_kwargs["properties"] = {
            k: _to_gemini_schema(v)
            for k, v in jsonschema["properties"].items()
        }

    return genai.protos.Schema(**schema_kwargs)


class GeminiBackend(BackendAdapter):
    """Google Gemini backend (gemini-2.5-flash default)."""

    def __init__(self, config: dict) -> None:
        self.config = config
        self._model_name: str = config["model"]
        api_key = os.environ[config["api_key_env"]]
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(self._model_name)

    def send_message(
        self,
        messages: list[dict],
        tools: list[dict],
        images: list[str],
    ) -> AgentResponse:
        # Convert tools to Gemini function declarations with proper types
        gemini_tools = None
        if tools:
            function_declarations = []
            for t in tools:
                input_schema = t.get("inputSchema", {})
                params = _to_gemini_schema({
                    "type": "object",
                    "properties": input_schema.get("properties", {}),
                }) if input_schema.get("properties") else genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                )
                function_declarations.append(
                    genai.protos.FunctionDeclaration(
                        name=t["name"],
                        description=t.get("description", ""),
                        parameters=params,
                    )
                )
            gemini_tools = [genai.protos.Tool(function_declarations=function_declarations)]

        # Build contents list (Gemini uses "contents" not "messages")
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            content = msg["content"]
            if isinstance(content, str):
                contents.append({"role": role, "parts": [{"text": content}]})
            else:
                # Flatten list of blocks to text
                text = " ".join(
                    b.get("text", "") or b.get("content", "")
                    for b in content if isinstance(b, dict)
                )
                contents.append({"role": role, "parts": [{"text": text}]})

        # Inject screenshots into last user content
        if images and contents:
            last = contents[-1]
            for img_b64 in images:
                last["parts"].append({
                    "inline_data": {
                        "mime_type": "image/png",
                        "data": img_b64,
                    }
                })

        response = self._model.generate_content(
            contents,
            tools=gemini_tools,
        )

        content = ""
        tool_calls: list[dict] = []
        for part in response.parts:
            if hasattr(part, "text") and part.text:
                content = part.text
            elif hasattr(part, "function_call") and part.function_call:
                fc = part.function_call
                tool_calls.append({
                    "name": fc.name,
                    "input": dict(fc.args),
                    "id": fc.name,
                })

        stop_reason = "end_turn" if not tool_calls else "tool_use"
        return AgentResponse(content=content, tool_calls=tool_calls, stop_reason=stop_reason)

    def get_model_name(self) -> str:
        return self._model_name

    def supports_vision(self) -> bool:
        return True
