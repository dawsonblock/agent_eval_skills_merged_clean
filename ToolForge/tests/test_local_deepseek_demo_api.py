from __future__ import annotations

from pathlib import Path

import pytest

try:
    from fastapi.testclient import TestClient

    from apps.local_deepseek_demo import server as demo_server
    from apps.local_deepseek_demo.toolforge_adapter import ToolForgeAdapter
except Exception as exc:  # pragma: no cover - environment guard for optional deps
    pytest.skip(
        f"local_deepseek_demo API tests require optional demo dependencies: {exc}",
        allow_module_level=True,
    )


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    demo_server.WORKSPACE_ROOT = tmp_path
    demo_server.adapter = ToolForgeAdapter(tmp_path)
    return TestClient(demo_server.app)


def _register_demo_tool(tmp_path: Path) -> str:
    slug = "demo-api-tool"
    tool_dir = tmp_path / "tools" / "generated" / slug
    tool_dir.mkdir(parents=True, exist_ok=True)

    (tool_dir / "tool.py").write_text(
        "from __future__ import annotations\n\n"
        "import json\n"
        "import os\n"
        "from pathlib import Path\n\n"
        "def main() -> int:\n"
        "    payload = json.loads(os.environ.get('TOOLFORGE_INPUTS', '{}'))\n"
        "    out_dir = Path(os.environ.get('TOOLFORGE_DEMO_OUTPUT_DIR', '.'))\n"
        "    out_dir.mkdir(parents=True, exist_ok=True)\n"
        "    (out_dir / 'api_result.json').write_text(\n"
        "        json.dumps({'ok': True, 'payload': payload}) + '\\n',\n"
        "        encoding='utf-8',\n"
        "    )\n"
        "    print(json.dumps({'ok': True}))\n"
        "    return 0\n\n"
        "if __name__ == '__main__':\n"
        "    raise SystemExit(main())\n",
        encoding="utf-8",
    )

    (tool_dir / "toolforge.yaml").write_text(
        "name: demo-api-tool\n"
        "slug: demo-api-tool\n"
        "description: Demo API tool\n"
        "language: python\n"
        "entry_point: tool.py\n"
        "parameters:\n"
        "  - name: request\n"
        "    type: string\n"
        "    description: Request text\n"
        "    required: true\n"
        "output:\n"
        "  type: object\n"
        "  description: Result payload\n"
        "security:\n"
        "  required_capabilities: [read_files, write_files]\n"
        "  requires_network: false\n"
        "  requires_shell: false\n"
        "  requires_filesystem: true\n"
        "  allowed_read_paths: ['./**']\n"
        "  allowed_write_paths: ['./generated_tools/_outputs/**']\n"
        "sandbox_level: 2\n",
        encoding="utf-8",
    )

    demo_server.adapter.registry.register_tool(
        {
            "name": slug,
            "type": "python",
            "entrypoint": str((tool_dir / "tool.py").relative_to(tmp_path)),
            "working_dir": str(tool_dir.relative_to(tmp_path)),
            "description": "api demo",
            "permissions": ["read_files", "write_files"],
            "risk_level": "low",
            "validated": True,
            "mcp_server": None,
        }
    )
    return slug


def test_health_and_models(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-chat")

    health = client.get("/api/health")
    assert health.status_code == 200
    payload = health.json()
    assert payload["status"] == "ok"
    assert payload["deepseek_key_configured"] is True

    models = client.get("/api/models")
    assert models.status_code == 200
    models_payload = models.json()
    assert "presets" in models_payload
    assert "deepseek-chat" in models_payload["presets"]


def test_chat_with_mocked_deepseek(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    async def fake_chat(*args, **kwargs):
        captured.update(kwargs)
        return {
            "message": {"content": "mocked response", "tool_calls": []},
            "tool_calls": [],
            "raw": {"choices": []},
        }

    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr(demo_server.DeepSeekClient, "chat", fake_chat)

    resp = client.post(
        "/api/chat",
        json={
            "messages": [{"role": "user", "content": "hello"}],
            "selected_model": "deepseek-chat",
            "mode": "normal",
            "tool_mode": False,
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["message_type"] == "assistant"
    assert body["assistant"] == "mocked response"
    sent_messages = captured.get("messages")
    assert isinstance(sent_messages, list)
    assert sent_messages
    assert sent_messages[0]["role"] == "system"
    assert "Local DeepSeek Tool UI assistant" in sent_messages[0]["content"]


def test_generated_tools_endpoint_lists_created_tool(
    client: TestClient,
    tmp_path: Path,
) -> None:
    slug = _register_demo_tool(tmp_path)

    generated_dir = tmp_path / "generated_tools" / slug
    generated_dir.mkdir(parents=True, exist_ok=True)
    (generated_dir / "tool.py").write_text("def run(inputs):\n    return {'ok': True}\n", encoding="utf-8")
    (generated_dir / "toolforge.yaml").write_text("name: demo-api-tool\nslug: demo-api-tool\n", encoding="utf-8")
    (generated_dir / "README.md").write_text("# demo-api-tool\n", encoding="utf-8")

    resp = client.get("/api/generated-tools")
    assert resp.status_code == 200
    payload = resp.json()
    tools = payload["tools"]
    names = [item["name"] for item in tools]
    assert slug in names


def test_set_api_key_endpoint(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    save = client.post(
        "/api/config/api-key",
        json={"api_key": "sk-test123456"},
    )
    assert save.status_code == 200
    save_payload = save.json()
    assert save_payload["configured"] is True
    assert save_payload["masked_key"]

    clear = client.post(
        "/api/config/api-key",
        json={"api_key": ""},
    )
    assert clear.status_code == 200
    clear_payload = clear.json()
    assert clear_payload["configured"] is False


def test_tool_run_preview_then_approve(client: TestClient, tmp_path: Path) -> None:
    slug = _register_demo_tool(tmp_path)

    preview = client.post(
        "/api/tools/run",
        json={
            "tool_name": slug,
            "args": {"request": "hello"},
            "approve": False,
        },
    )
    assert preview.status_code == 200
    preview_payload = preview.json()
    assert preview_payload["message_type"] == "safety_warning"
    assert preview_payload["requires_approval"] is True

    run_resp = client.post(
        "/api/tools/run",
        json={
            "tool_name": slug,
            "args": {"request": "hello"},
            "approve": True,
        },
    )
    assert run_resp.status_code == 200
    run_payload = run_resp.json()
    assert run_payload["message_type"] == "tool_result"
    assert run_payload["result"]["exit_code"] == 0

    artifacts = run_payload["result"]["artifacts"]
    assert artifacts
    first = artifacts[0]
    output_resp = client.get("/api/output", params={"path": first})
    assert output_resp.status_code == 200


def test_tool_run_rejects_unknown_argument_key(
    client: TestClient,
    tmp_path: Path,
) -> None:
    slug = _register_demo_tool(tmp_path)

    resp = client.post(
        "/api/tools/run",
        json={
            "tool_name": slug,
            "args": {"request": "ok", "extra": "blocked"},
            "approve": False,
        },
    )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["message_type"] == "safety_warning"
    assert payload["validation"]["allowed"] is False
    joined = "\n".join(payload["validation"]["errors"])
    assert "Unknown argument keys" in joined
