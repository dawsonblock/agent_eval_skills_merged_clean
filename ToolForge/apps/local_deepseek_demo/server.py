from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from apps.local_deepseek_demo.toolforge_adapter import AdapterError, ToolForgeAdapter
from packages.providers.deepseek_client import (
    DeepSeekAuthError,
    DeepSeekClient,
    DeepSeekClientError,
)


load_dotenv()

APP_ROOT = Path(__file__).resolve().parent
WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = APP_ROOT / "static"

app = FastAPI(title="Local DeepSeek Tool UI Demo", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

adapter = ToolForgeAdapter(WORKSPACE_ROOT)

MODEL_PRESETS = [
    "deepseek-chat",
    "deepseek-v4-flash",
    "deepseek-v4-pro",
    "deepseek-reasoner",
]


class ChatRequest(BaseModel):
    messages: list[dict[str, Any]]
    selected_model: str | None = None
    mode: str = Field(default="normal", pattern="^(normal|tool_use|tool_builder)$")
    tool_mode: bool = False
    temperature: float = 0.2


class ToolRunRequest(BaseModel):
    tool_name: str
    args: dict[str, Any] = Field(default_factory=dict)
    approve: bool = False


class ToolPlanRequest(BaseModel):
    prompt: str
    selected_model: str | None = None


class ToolCreateRequest(BaseModel):
    plan: dict[str, Any]
    allow_overwrite: bool = False


class ToolValidateRequest(BaseModel):
    path: str


class ApiKeyRequest(BaseModel):
    api_key: str = ""


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, Any]:
    deepseek = DeepSeekClient()
    tools = adapter.list_tools()
    return {
        "status": "ok",
        "demo_mode": "local",
        "deepseek_key_configured": deepseek.configured,
        "available_tools_count": len(tools),
        "workspace": str(WORKSPACE_ROOT),
    }


@app.get("/api/models")
def models() -> dict[str, Any]:
    current = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    presets = MODEL_PRESETS.copy()
    if current not in presets:
        presets.insert(0, current)
    return {
        "configured_model": current,
        "presets": presets,
        "editable": True,
    }


@app.post("/api/config/api-key")
def set_api_key(request: ApiKeyRequest) -> dict[str, Any]:
    value = request.api_key.strip()
    if value:
        os.environ["DEEPSEEK_API_KEY"] = value
    else:
        os.environ.pop("DEEPSEEK_API_KEY", None)

    configured = bool(os.getenv("DEEPSEEK_API_KEY"))
    masked = ""
    if configured:
        raw = os.getenv("DEEPSEEK_API_KEY", "")
        if len(raw) > 8:
            masked = raw[:5] + "..." + raw[-3:]
        else:
            masked = "***"

    return {
        "configured": configured,
        "masked_key": masked,
    }


@app.get("/api/tools")
def tools() -> dict[str, Any]:
    return {"tools": adapter.list_tools()}


@app.post("/api/chat")
async def chat(request: ChatRequest) -> dict[str, Any]:
    deepseek = DeepSeekClient(model=request.selected_model or None)

    tools_payload: list[dict[str, Any]] | None = None
    if request.mode in {"tool_use", "tool_builder"} or request.tool_mode:
        tool_entries = adapter.list_tools()
        tools_payload = [
            {
                "type": "function",
                "function": {
                    "name": str(t.get("name", "tool")),
                    "description": str(t.get("description", "")),
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": True,
                    },
                },
            }
            for t in tool_entries[:20]
            if t.get("name")
        ]

    try:
        response = await deepseek.chat(
            messages=request.messages,
            tools=tools_payload,
            temperature=request.temperature,
            model=request.selected_model,
        )
    except DeepSeekAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DeepSeekClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    message = response.get("message") or {}
    content = message.get("content") if isinstance(message, dict) else ""

    suggestions: list[dict[str, Any]] = []
    tool_calls = response.get("tool_calls")
    if isinstance(tool_calls, list):
        for call in tool_calls:
            if isinstance(call, dict):
                fn = call.get("function") or {}
                suggestions.append(
                    {
                        "tool": fn.get("name"),
                        "arguments": fn.get("arguments"),
                        "source": "tool_call",
                    }
                )

    if request.mode == "tool_builder":
        return {
            "message_type": "tool_plan",
            "assistant": content,
            "tool_suggestions": suggestions,
            "raw": response,
        }

    return {
        "message_type": "assistant",
        "assistant": content,
        "tool_suggestions": suggestions,
        "raw": response,
    }


@app.post("/api/tools/run")
def tools_run(request: ToolRunRequest) -> dict[str, Any]:
    validation = adapter.validate_tool_request(request.tool_name, request.args)
    if not validation["allowed"]:
        return {
            "message_type": "safety_warning",
            "requires_approval": False,
            "validation": validation,
            "result": None,
        }

    if not request.approve:
        return {
            "message_type": "safety_warning",
            "requires_approval": True,
            "validation": validation,
            "result": None,
        }

    try:
        result = adapter.run_tool(request.tool_name, request.args)
    except AdapterError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "message_type": "tool_result",
        "requires_approval": False,
        "validation": validation,
        "result": result,
    }


@app.post("/api/tools/plan")
async def tools_plan(request: ToolPlanRequest) -> dict[str, Any]:
    deepseek = DeepSeekClient(model=request.selected_model or None)
    planner_prompt = (
        "Return only JSON with keys: tool_name, purpose, inputs, outputs, file_paths, "
        "safety_risks, validation_plan.\n"
        f"User request: {request.prompt}"
    )
    messages = [
        {
            "role": "system",
            "content": "You are a cautious tool planning assistant. Output valid JSON only.",
        },
        {"role": "user", "content": planner_prompt},
    ]

    try:
        response = await deepseek.chat(
            messages=messages,
            tools=None,
            temperature=0.1,
            model=request.selected_model,
        )
        message = response.get("message") or {}
        raw_content = message.get("content", "") if isinstance(message, dict) else ""
        parsed = _parse_json_object(raw_content)
        if parsed is None:
            parsed = adapter.plan_tool_creation(request.prompt)
    except (DeepSeekClientError, DeepSeekAuthError):
        parsed = adapter.plan_tool_creation(request.prompt)

    return {
        "message_type": "tool_plan",
        "plan": parsed,
    }


@app.post("/api/tools/create")
def tools_create(request: ToolCreateRequest) -> dict[str, Any]:
    try:
        result = adapter.create_tool_from_plan(
            request.plan,
            allow_overwrite=request.allow_overwrite,
        )
    except AdapterError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "message_type": "tool_result",
        "result": result,
    }


@app.post("/api/tools/validate")
def tools_validate(request: ToolValidateRequest) -> dict[str, Any]:
    try:
        result = adapter.validate_generated_tool(request.path)
    except AdapterError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "message_type": "tool_result" if result.get("passed") else "validation_error",
        "result": result,
    }


@app.get("/api/output")
def output_view(path: str) -> JSONResponse:
    candidate = (WORKSPACE_ROOT / path).resolve()
    allowed_roots = [adapter.outputs_root.resolve(), adapter.generated_root.resolve()]
    if not any(str(candidate).startswith(str(root)) for root in allowed_roots):
        raise HTTPException(status_code=400, detail="Path is outside allowed output roots")
    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(status_code=404, detail="Output file not found")

    if candidate.suffix.lower() in {".json"}:
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
            return JSONResponse({"kind": "json", "payload": payload})
        except Exception:
            pass

    return JSONResponse(
        {
            "kind": "text",
            "payload": candidate.read_text(encoding="utf-8", errors="replace"),
        }
    )


@app.get("/api/open-output-folder")
def open_output_folder() -> dict[str, Any]:
    # Keep local demo non-invasive: UI can open this path client-side.
    return {"output_folder": str(adapter.outputs_root.resolve())}


def _parse_json_object(content: str) -> dict[str, Any] | None:
    if not content:
        return None
    text = content.strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(text[start : end + 1])
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return None
    return None
