from __future__ import annotations

import ast
import json
import re
import time
from pathlib import Path
from typing import Any

from packages.core.tool_spec import OutputSpec, SecuritySpec, ToolCapability, ToolLanguage, ToolSpec
from packages.runners.tool_runner import run_tool
from packages.validators.schema_validator import validate_yaml_file
from skillforge_ai.planner import SkillPlanner
from skillforge_ai.tool_registry import SkillForgeRegistry
from skillforge_ai.yaml_utils import load_yaml


BLOCKED_PATH_FRAGMENTS = (
    "..",
    "/.git",
    "\\.git",
    "/.env",
    "\\.env",
    "/release_artifacts",
    "\\release_artifacts",
    "/Users/",
    "\\Users\\",
)

BLOCKED_PREFIXES = (
    str(Path.home() / ".ssh"),
    str(Path.home() / ".aws"),
    str(Path.home() / ".config"),
)


def is_under(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


class AdapterError(RuntimeError):
    """Raised for adapter validation or execution failures."""


class ToolForgeAdapter:
    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.resolve()
        self.registry = SkillForgeRegistry(self.workspace_root)
        self.generated_root = self.workspace_root / "generated_tools"
        self.outputs_root = self.generated_root / "_outputs"
        self.generated_root.mkdir(parents=True, exist_ok=True)
        self.outputs_root.mkdir(parents=True, exist_ok=True)

    def list_tools(self) -> list[dict[str, Any]]:
        tools = self.registry.list_registered_tools()
        normalized: list[dict[str, Any]] = []
        for item in tools:
            if not isinstance(item, dict):
                continue
            normalized.append(
                {
                    "name": item.get("name"),
                    "description": item.get("description", ""),
                    "entrypoint": item.get("entrypoint", ""),
                    "working_dir": item.get("working_dir", ""),
                    "permissions": item.get("permissions", []),
                    "risk_level": item.get("risk_level", "low"),
                    "validated": bool(item.get("validated", False)),
                    "type": item.get("type", "python"),
                }
            )
        return normalized

    def list_generated_tools(self) -> list[dict[str, Any]]:
        if not self.generated_root.exists():
            return []

        registry_by_name: dict[str, dict[str, Any]] = {}
        for item in self.registry.list_registered_tools():
            if isinstance(item, dict) and item.get("name"):
                registry_by_name[str(item.get("name"))] = item

        rows: list[dict[str, Any]] = []
        for candidate in sorted(self.generated_root.iterdir()):
            if not candidate.is_dir() or candidate.name == "_outputs":
                continue

            slug = candidate.name
            spec_path = candidate / "toolforge.yaml"
            test_dir = candidate / "tests"
            plan_path = candidate / "plan.json"

            registry_item = registry_by_name.get(slug)
            rows.append(
                {
                    "name": slug,
                    "path": str(candidate.relative_to(self.workspace_root)),
                    "has_spec": spec_path.exists(),
                    "has_tests": test_dir.exists() and test_dir.is_dir(),
                    "has_plan": plan_path.exists(),
                    "registered": registry_item is not None,
                    "validated": bool(registry_item.get("validated", False)) if registry_item else False,
                    "risk_level": str(registry_item.get("risk_level", "unknown")) if registry_item else "unknown",
                    "description": str(registry_item.get("description", "")) if registry_item else "",
                }
            )

        return rows

    def validate_tool_request(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        tool = self.registry.get_registered_tool(tool_name)
        if not tool:
            return {
                "allowed": False,
                "errors": [f"Tool not found: {tool_name}"],
                "warnings": [],
                "preview": {},
            }

        permissions = list(tool.get("permissions") or [])
        errors: list[str] = []
        warnings: list[str] = []

        arg_schema = self._parameter_schema_for_tool(tool)
        if arg_schema:
            errors.extend(self._validate_args_against_schema(args, arg_schema))

        touched_paths = self._extract_paths(args)
        for p in touched_paths:
            if self._is_blocked_path(p):
                errors.append(f"Blocked path access: {p}")
            elif not self._is_within_workspace(p):
                warnings.append(f"Path is outside workspace: {p}")

        if "read_secrets" in permissions:
            errors.append("Tool requests read_secrets permission, blocked in local_safe mode.")
        if "shell_commands" in permissions:
            errors.append("shell_commands permission is blocked for this demo.")

        command_preview = self._command_preview(tool)
        preview = {
            "tool": tool_name,
            "arguments": args,
            "arg_schema": arg_schema,
            "permissions": permissions,
            "touched_paths": touched_paths,
            "network_required": any(p in permissions for p in ("network_access", "external_api")),
            "command_preview": command_preview,
        }

        return {
            "allowed": not errors,
            "errors": errors,
            "warnings": warnings,
            "preview": preview,
        }

    def run_tool(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        validation = self.validate_tool_request(tool_name, args)
        if not validation["allowed"]:
            raise AdapterError("; ".join(validation["errors"]))

        tool = self.registry.get_registered_tool(tool_name)
        if not tool:
            raise AdapterError(f"Tool not found: {tool_name}")

        spec, tool_dir = self._build_toolspec_for_registered_tool(tool)
        started = time.monotonic()
        output_dir = self.outputs_root / tool_name
        output_dir.mkdir(parents=True, exist_ok=True)
        result = run_tool(
            spec=spec,
            tool_dir=tool_dir,
            inputs=args,
            timeout_s=60.0,
            env={"TOOLFORGE_DEMO_OUTPUT_DIR": str(output_dir.resolve())},
        )
        duration = time.monotonic() - started

        artifacts = self._collect_artifacts(tool_name)

        return {
            "tool": tool_name,
            "stdout": result.output,
            "stderr": result.error,
            "exit_code": result.exit_code,
            "duration_seconds": round(duration, 3),
            "artifacts": artifacts,
        }

    def plan_tool_creation(self, prompt: str) -> dict[str, Any]:
        planner = SkillPlanner()
        plan = planner.build_plan(prompt)
        slug = self._slugify(plan.skill_name)
        safe_path = self.generated_root / slug
        return {
            "tool_name": slug,
            "purpose": prompt.strip(),
            "inputs": ["request", "context"],
            "outputs": ["result", "artifacts"],
            "file_paths": [
                str((safe_path / "tool.py").relative_to(self.workspace_root)),
                str((safe_path / "toolforge.yaml").relative_to(self.workspace_root)),
                str((safe_path / "README.md").relative_to(self.workspace_root)),
                str((safe_path / "tests" / f"test_{slug}.py").relative_to(self.workspace_root)),
            ],
            "safety_risks": [
                "Path traversal attempts",
                "Writes outside generated_tools",
                "Sensitive file access",
                "Network or shell permissions without declaration",
            ],
            "validation_plan": plan.validation_plan,
            "mode": plan.mode,
            "risk_level": plan.risk_level,
        }

    def create_tool_from_plan(
        self,
        plan: dict[str, Any],
        allow_overwrite: bool = False,
    ) -> dict[str, Any]:
        requested_name = str(plan.get("tool_name") or "generated-tool")
        slug = self._slugify(requested_name)
        tool_root = (self.generated_root / slug).resolve()
        if not is_under(tool_root, self.generated_root):
            raise AdapterError("Refusing to write outside ToolForge/generated_tools.")
        if tool_root.exists() and not allow_overwrite:
            raise AdapterError(
                f"Tool already exists: {tool_root}. "
                "Set allow_overwrite=true to replace."
            )

        tool_root.mkdir(parents=True, exist_ok=True)
        (tool_root / "tests").mkdir(parents=True, exist_ok=True)

        purpose = str(plan.get("purpose") or "Generated from ToolForge local demo")

        tool_py = tool_root / "tool.py"
        tool_yaml = tool_root / "toolforge.yaml"
        readme = tool_root / "README.md"
        test_file = tool_root / "tests" / f"test_{slug}.py"
        plan_file = tool_root / "plan.json"

        tool_py.write_text(
            "from __future__ import annotations\n\n"
            "import json\n"
            "import os\n"
            "from pathlib import Path\n\n"
            "def run(inputs: dict) -> dict:\n"
            "    output_dir = Path(\n"
            "        os.environ.get(\n"
            "            'TOOLFORGE_DEMO_OUTPUT_DIR',\n"
            "            str(Path(__file__).resolve().parents[1] / '_outputs' / '"
            + slug
            + "'),\n"
            "        )\n"
            "    )\n"
            "    output_dir.mkdir(parents=True, exist_ok=True)\n"
            "    payload = {'echo': inputs, 'status': 'ok'}\n"
            "    out_file = output_dir / 'result.json'\n"
            "    out_file.write_text(json.dumps(payload, indent=2) + '\\n', encoding='utf-8')\n"
            "    return {'message': 'Tool executed', 'output_file': str(out_file)}\n\n"
            "def main() -> int:\n"
            "    raw = os.environ.get('TOOLFORGE_INPUTS', '{}')\n"
            "    try:\n"
            "        inputs = json.loads(raw)\n"
            "    except json.JSONDecodeError:\n"
            "        inputs = {}\n"
            "    result = run(inputs)\n"
            "    print(json.dumps(result))\n"
            "    return 0\n\n"
            "if __name__ == '__main__':\n"
            "    raise SystemExit(main())\n",
            encoding="utf-8",
        )

        tool_yaml.write_text(
            "name: " + slug + "\n"
            "slug: " + slug + "\n"
            "description: " + purpose.replace("\n", " ") + "\n"
            "language: python\n"
            "entry_point: tool.py\n"
            "parameters:\n"
            "  - name: request\n"
            "    type: string\n"
            "    description: User request\n"
            "    required: false\n"
            "output:\n"
            "  type: object\n"
            "  description: Result payload\n"
            "security:\n"
            "  required_capabilities: [read_files, write_files]\n"
            "  requires_network: false\n"
            "  requires_shell: false\n"
            "  requires_filesystem: true\n"
            "  allowed_read_paths: ['./generated_tools/**']\n"
            "  allowed_write_paths: ['./generated_tools/_outputs/**']\n"
            "sandbox_level: 2\n",
            encoding="utf-8",
        )

        readme.write_text(
            f"# {slug}\n\n{purpose}\n\nGenerated by Local DeepSeek Tool UI Demo.\n",
            encoding="utf-8",
        )

        test_file.write_text(
            "from __future__ import annotations\n\n"
            "import importlib.util\n"
            "import json\n"
            "from pathlib import Path\n\n"
            "\n"
            "def _load_run(tool_path: Path):\n"
            "    spec = importlib.util.spec_from_file_location('generated_tool_module', tool_path)\n"
            "    if spec is None or spec.loader is None:\n"
            "        raise RuntimeError('Unable to load generated tool module')\n"
            "    module = importlib.util.module_from_spec(spec)\n"
            "    spec.loader.exec_module(module)\n"
            "    return module.run\n\n"
            "def test_run_writes_result(tmp_path: Path, monkeypatch) -> None:\n"
            "    tool_path = Path(__file__).resolve().parents[1] / 'tool.py'\n"
            "    run = _load_run(tool_path)\n"
            "    monkeypatch.setenv('TOOLFORGE_DEMO_OUTPUT_DIR', str(tmp_path))\n"
            "    result = run({'request': 'hello'})\n"
            "    output_file = Path(result['output_file'])\n"
            "    assert output_file.exists()\n"
            "    payload = json.loads(output_file.read_text(encoding='utf-8'))\n"
            "    assert payload['status'] == 'ok'\n",
            encoding="utf-8",
        )

        plan_file.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")

        self.registry.register_tool(
            {
                "name": slug,
                "type": "python",
                "entrypoint": str(tool_py.relative_to(self.workspace_root)),
                "working_dir": str(tool_root.relative_to(self.workspace_root)),
                "description": purpose,
                "permissions": ["read_files", "write_files", "run_tests"],
                "risk_level": "low",
                "validated": False,
                "mcp_server": None,
            }
        )

        created_files = [
            str(tool_py.relative_to(self.workspace_root)),
            str(tool_yaml.relative_to(self.workspace_root)),
            str(readme.relative_to(self.workspace_root)),
            str(test_file.relative_to(self.workspace_root)),
            str(plan_file.relative_to(self.workspace_root)),
        ]

        validation = self.validate_generated_tool(str(tool_root.relative_to(self.workspace_root)))

        return {
            "tool_name": slug,
            "tool_path": str(tool_root.relative_to(self.workspace_root)),
            "created_files": created_files,
            "validation": validation,
        }

    def validate_generated_tool(self, path: str) -> dict[str, Any]:
        candidate = (self.workspace_root / path).resolve()
        if not is_under(candidate, self.generated_root):
            raise AdapterError("Validation is limited to ToolForge/generated_tools/ paths.")
        if not candidate.exists() or not candidate.is_dir():
            raise AdapterError(f"Generated tool path not found: {candidate}")

        required = ["tool.py", "toolforge.yaml", "README.md"]
        missing = [name for name in required if not (candidate / name).exists()]

        errors: list[str] = []
        warnings: list[str] = []

        spec_path = candidate / "toolforge.yaml"
        if spec_path.exists():
            try:
                validate_yaml_file(spec_path)
            except Exception as exc:
                errors.append(f"toolforge.yaml validation failed: {exc}")
        else:
            errors.append("toolforge.yaml is missing")

        tool_py = candidate / "tool.py"
        if tool_py.exists():
            try:
                ast.parse(tool_py.read_text(encoding="utf-8"))
            except SyntaxError as exc:
                errors.append(f"tool.py has syntax error: {exc}")
        else:
            errors.append("tool.py is missing")

        if missing:
            warnings.append(f"Missing expected files: {', '.join(missing)}")

        return {
            "path": str(candidate.relative_to(self.workspace_root)),
            "passed": not errors,
            "errors": errors,
            "warnings": warnings,
        }

    def _build_toolspec_for_registered_tool(self, tool: dict[str, Any]) -> tuple[ToolSpec, Path]:
        working_dir = self._resolve_workspace_path(str(tool.get("working_dir") or ""))
        entrypoint = str(tool.get("entrypoint") or "")
        entry_path = self._resolve_workspace_path(entrypoint)

        if not working_dir.exists():
            raise AdapterError(f"Tool working_dir does not exist: {working_dir}")
        if not entry_path.exists():
            raise AdapterError(f"Tool entrypoint does not exist: {entry_path}")

        entry_point_for_spec = str(entry_path.relative_to(working_dir))
        lang = (
            ToolLanguage.TYPESCRIPT
            if str(tool.get("type")) in {"typescript", "mcp"}
            else ToolLanguage.PYTHON
        )

        permissions = set(tool.get("permissions") or [])
        required_caps: list[ToolCapability] = []
        if "read_files" in permissions:
            required_caps.append(ToolCapability.READ_FILES)
        if "write_files" in permissions:
            required_caps.append(ToolCapability.WRITE_FILES)
        if "network_access" in permissions or "external_api" in permissions:
            required_caps.append(ToolCapability.CALL_HTTP)

        security = SecuritySpec(
            required_capabilities=required_caps,
            requires_network=("network_access" in permissions or "external_api" in permissions),
            requires_shell=("shell_commands" in permissions),
            requires_filesystem=True,
            allowed_read_paths=["./**"],
            allowed_write_paths=[
                str(self.outputs_root.resolve()) + "/**",
                "./generated_tools/_outputs/**",
            ],
            blocked_paths=[
                "~/.ssh/**",
                "~/.aws/**",
                "~/.config/**",
                "/etc/**",
                "/var/**",
                "/root/**",
                "./.git/**",
            ],
        )

        spec = ToolSpec(
            name=str(tool.get("name") or "demo-tool"),
            slug=str(tool.get("name") or "demo-tool"),
            description=str(tool.get("description") or "Registered tool"),
            language=lang,
            entry_point=entry_point_for_spec,
            output=OutputSpec(type="string", description="Tool output"),
            security=security,
        )

        return spec, working_dir

    def _command_preview(self, tool: dict[str, Any]) -> str:
        tool_type = str(tool.get("type") or "python")
        entry = str(tool.get("entrypoint") or "")
        if tool_type == "typescript":
            return f"node {entry}".strip()
        return f"python {entry}".strip()

    def _extract_paths(self, args: dict[str, Any]) -> list[str]:
        out: list[str] = []

        def walk(value: Any) -> None:
            if isinstance(value, dict):
                for nested in value.values():
                    walk(nested)
            elif isinstance(value, list):
                for nested in value:
                    walk(nested)
            elif isinstance(value, str):
                if "/" in value or "\\" in value or value.endswith(
                    (".py", ".json", ".txt", ".md", ".yaml", ".yml")
                ):
                    out.append(value)

        walk(args)
        return out

    def _is_blocked_path(self, value: str) -> bool:
        normalized = value.replace("\\", "/")
        if any(fragment in normalized for fragment in BLOCKED_PATH_FRAGMENTS):
            return True

        candidate = Path(value).expanduser()
        if not candidate.is_absolute():
            candidate = self.workspace_root / candidate
        candidate = candidate.resolve()

        for prefix in BLOCKED_PREFIXES:
            if is_under(candidate, Path(prefix).expanduser().resolve()):
                return True
        return False

    def _is_within_workspace(self, value: str) -> bool:
        candidate = self._resolve_workspace_path(value)
        return is_under(candidate, self.workspace_root)

    def _resolve_workspace_path(self, maybe_path: str) -> Path:
        p = Path(maybe_path).expanduser()
        if p.is_absolute():
            return p.resolve()
        return (self.workspace_root / p).resolve()

    def _collect_artifacts(self, tool_name: str) -> list[str]:
        artifacts: list[str] = []
        if not self.outputs_root.exists():
            return artifacts
        for file in sorted(self.outputs_root.rglob("*")):
            if file.is_file():
                artifacts.append(str(file.relative_to(self.workspace_root)))
        tool_specific = self.generated_root / tool_name / "_outputs"
        if tool_specific.exists():
            for file in sorted(tool_specific.rglob("*")):
                if file.is_file():
                    rel = str(file.relative_to(self.workspace_root))
                    if rel not in artifacts:
                        artifacts.append(rel)
        return artifacts

    def _parameter_schema_for_tool(self, tool: dict[str, Any]) -> dict[str, dict[str, Any]]:
        spec_path = self._resolve_tool_spec_path(tool)
        if not spec_path or not spec_path.exists():
            return {}

        try:
            spec = validate_yaml_file(spec_path)
        except Exception:
            return {}

        schema: dict[str, dict[str, Any]] = {}
        for param in spec.parameters:
            schema[param.name] = {
                "type": param.type,
                "required": param.required,
                "enum": param.enum,
                "min_length": param.min_length,
                "max_length": param.max_length,
                "minimum": param.minimum,
                "maximum": param.maximum,
            }

        # Optional extended constraints can be present in raw YAML parameter metadata.
        # We support them here without requiring ToolSpec schema expansion.
        raw_constraints = self._raw_parameter_constraints_for_tool(spec_path)
        for name, extras in raw_constraints.items():
            schema.setdefault(name, {}).update(extras)

        return schema

    def _raw_parameter_constraints_for_tool(
        self,
        spec_path: Path,
    ) -> dict[str, dict[str, Any]]:
        try:
            payload = load_yaml(spec_path)
        except Exception:
            return {}
        if not isinstance(payload, dict):
            return {}

        params = payload.get("parameters")
        if not isinstance(params, list):
            return {}

        out: dict[str, dict[str, Any]] = {}
        for item in params:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if not isinstance(name, str) or not name.strip():
                continue

            extras: dict[str, Any] = {}
            if isinstance(item.get("min_items"), int):
                extras["min_items"] = item["min_items"]
            if isinstance(item.get("max_items"), int):
                extras["max_items"] = item["max_items"]

            required_keys = item.get("required_keys")
            if isinstance(required_keys, list) and all(
                isinstance(k, str) for k in required_keys
            ):
                extras["required_keys"] = required_keys

            if extras:
                out[name] = extras

        return out

    def _resolve_tool_spec_path(self, tool: dict[str, Any]) -> Path | None:
        working_dir = str(tool.get("working_dir") or "").strip()
        if working_dir:
            candidate = self._resolve_workspace_path(working_dir) / "toolforge.yaml"
            if candidate.exists():
                return candidate

        entrypoint = str(tool.get("entrypoint") or "").strip()
        if entrypoint:
            entry_path = self._resolve_workspace_path(entrypoint)
            candidate = entry_path.parent / "toolforge.yaml"
            if candidate.exists():
                return candidate
        return None

    def _validate_args_against_schema(
        self,
        args: dict[str, Any],
        arg_schema: dict[str, dict[str, Any]],
    ) -> list[str]:
        errors: list[str] = []
        allowed_keys = set(arg_schema.keys())
        provided_keys = set(args.keys())

        unknown = sorted(provided_keys - allowed_keys)
        if unknown:
            errors.append(
                "Unknown argument keys: "
                + ", ".join(unknown)
                + ". Only declared tool parameters are allowed."
            )

        for key, meta in arg_schema.items():
            required = bool(meta.get("required"))
            expected_type = str(meta.get("type") or "")

            if required and key not in args:
                errors.append(f"Missing required argument: {key}")
                continue
            if key not in args:
                continue

            if not self._arg_matches_type(args[key], expected_type):
                errors.append(
                    f"Argument {key!r} expected type {expected_type!r}, "
                    f"got {type(args[key]).__name__!r}."
                )
                continue

            value = args[key]
            enum_values = meta.get("enum")
            if isinstance(enum_values, list) and enum_values and value not in enum_values:
                errors.append(
                    f"Argument {key!r} must be one of {enum_values!r}, got {value!r}."
                )

            min_length = meta.get("min_length")
            max_length = meta.get("max_length")
            if isinstance(value, str):
                if isinstance(min_length, int) and len(value) < min_length:
                    errors.append(
                        f"Argument {key!r} length must be >= {min_length}, got {len(value)}."
                    )
                if isinstance(max_length, int) and len(value) > max_length:
                    errors.append(
                        f"Argument {key!r} length must be <= {max_length}, got {len(value)}."
                    )

            minimum = meta.get("minimum")
            maximum = meta.get("maximum")
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                if isinstance(minimum, (int, float)) and value < minimum:
                    errors.append(
                        f"Argument {key!r} must be >= {minimum}, got {value}."
                    )
                if isinstance(maximum, (int, float)) and value > maximum:
                    errors.append(
                        f"Argument {key!r} must be <= {maximum}, got {value}."
                    )

            min_items = meta.get("min_items")
            max_items = meta.get("max_items")
            if isinstance(value, list):
                if isinstance(min_items, int) and len(value) < min_items:
                    errors.append(
                        f"Argument {key!r} item count must be >= {min_items}, "
                        f"got {len(value)}."
                    )
                if isinstance(max_items, int) and len(value) > max_items:
                    errors.append(
                        f"Argument {key!r} item count must be <= {max_items}, "
                        f"got {len(value)}."
                    )

            required_keys = meta.get("required_keys")
            if isinstance(value, dict) and isinstance(required_keys, list):
                missing_keys = [k for k in required_keys if k not in value]
                if missing_keys:
                    errors.append(
                        f"Argument {key!r} missing required keys: {missing_keys!r}."
                    )

        return errors

    @staticmethod
    def _arg_matches_type(value: Any, expected_type: str) -> bool:
        if expected_type == "string":
            return isinstance(value, str)
        if expected_type == "number":
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        if expected_type == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        if expected_type == "boolean":
            return isinstance(value, bool)
        if expected_type == "array":
            return isinstance(value, list)
        if expected_type == "object":
            return isinstance(value, dict)
        return True

    @staticmethod
    def _slugify(value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return slug or "generated-tool"
