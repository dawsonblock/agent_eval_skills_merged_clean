"""
Safety analyzer — static analysis of a generated tool directory.

Checks:
  - Denied import patterns from security_policy.yaml
  - Shell command patterns in source files
  - Path traversal patterns
  - Hardcoded secrets / tokens
  - Capability / sandbox level consistency
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

from packages.core.tool_spec import ToolSpec


@dataclass
class SafetyIssue:
    severity: str  # "error" | "warning" | "info"
    code: str
    message: str
    file: str | None = None
    line: int | None = None


@dataclass
class SafetyReport:
    tool_slug: str
    issues: list[SafetyIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(i.severity == "error" for i in self.issues)

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    @property
    def has_warnings(self) -> bool:
        return any(i.severity == "warning" for i in self.issues)

    def summary(self) -> str:
        errors = sum(1 for i in self.issues if i.severity == "error")
        warnings = sum(1 for i in self.issues if i.severity == "warning")
        return f"{errors} error(s), {warnings} warning(s)"


# Patterns that are always suspicious in generated code
_SECRET_PATTERNS = [
    (re.compile(r'(?i)(password|passwd|secret|api_key|token)\s*=\s*["\'][^"\']{6,}["\']'), "HARDCODED_SECRET"),
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "OPENAI_KEY_LITERAL"),
    (re.compile(r'(?i)aws_secret_access_key\s*=\s*["\'][^"\']+["\']'), "AWS_SECRET_LITERAL"),
]

_DANGEROUS_SHELL_MODULES = {
    "subprocess",
    "pty",
    "ctypes",
    "cffi",
}

_NETWORK_GATED_MODULES = {
    "socket",
}

_DANGEROUS_CALLS = {
    "subprocess.run",
    "subprocess.call",
    "subprocess.check_output",
    "subprocess.Popen",
    "subprocess.getoutput",
    "os.system",
    "os.popen",
    "asyncio.create_subprocess_exec",
    "asyncio.create_subprocess_shell",
}

_DANGEROUS_FROM_IMPORTS = {
    "subprocess": {"run", "call", "check_output", "Popen", "getoutput"},
    "os": {"system", "popen"},
    "asyncio": {"create_subprocess_exec", "create_subprocess_shell"},
}

_OS_DANGEROUS_PREFIXES = (
    "os.exec",
    "os.spawn",
)

_DANGEROUS_BUILTINS = {
    "eval",
    "exec",
    "compile",
    "__import__",
}

_TRAVERSAL_PATTERN = re.compile(r"\.\.[/\\]")


def _qualname(expr: ast.expr) -> str | None:
    if isinstance(expr, ast.Name):
        return expr.id
    if isinstance(expr, ast.Attribute):
        base = _qualname(expr.value)
        if base:
            return f"{base}.{expr.attr}"
    return None


def _analyze_ast(
    src: str,
    rel: str,
    *,
    requires_shell: bool,
    requires_network: bool,
) -> list[SafetyIssue]:
    issues: list[SafetyIssue] = []

    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        issues.append(
            SafetyIssue(
                severity="warning",
                code="AST_PARSE_FAILED",
                message=f"Could not parse {rel}: {exc.msg}",
                file=rel,
                line=exc.lineno,
            )
        )
        return issues

    module_aliases: dict[str, str] = {}
    imported_symbols: dict[str, str] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                local = alias.asname or root
                module_aliases[local] = root

                if root in _DANGEROUS_SHELL_MODULES:
                    issues.append(
                        SafetyIssue(
                            severity="error" if not requires_shell else "warning",
                            code="DENIED_IMPORT",
                            message=f"Dangerous module import '{root}' in {rel}:{node.lineno}",
                            file=rel,
                            line=node.lineno,
                        )
                    )
                elif root in _NETWORK_GATED_MODULES and not (requires_network or requires_shell):
                    issues.append(
                        SafetyIssue(
                            severity="error",
                            code="DENIED_IMPORT",
                            message=f"Network module import '{root}' in {rel}:{node.lineno}",
                            file=rel,
                            line=node.lineno,
                        )
                    )

        if isinstance(node, ast.ImportFrom):
            module = (node.module or "").split(".")[0]
            if not module:
                continue

            for alias in node.names:
                if alias.name == "*":
                    continue

                imported_symbols[alias.asname or alias.name] = f"{module}.{alias.name}"

                if module in _DANGEROUS_SHELL_MODULES:
                    issues.append(
                        SafetyIssue(
                            severity="error" if not requires_shell else "warning",
                            code="DENIED_IMPORT",
                            message=f"Dangerous import '{module}.{alias.name}' in {rel}:{node.lineno}",
                            file=rel,
                            line=node.lineno,
                        )
                    )
                elif module in _NETWORK_GATED_MODULES and not (requires_network or requires_shell):
                    issues.append(
                        SafetyIssue(
                            severity="error",
                            code="DENIED_IMPORT",
                            message=f"Network import '{module}.{alias.name}' in {rel}:{node.lineno}",
                            file=rel,
                            line=node.lineno,
                        )
                    )
                elif alias.name in _DANGEROUS_FROM_IMPORTS.get(module, set()):
                    issues.append(
                        SafetyIssue(
                            severity="error" if not requires_shell else "warning",
                            code="DENIED_IMPORT",
                            message=f"Dangerous import '{module}.{alias.name}' in {rel}:{node.lineno}",
                            file=rel,
                            line=node.lineno,
                        )
                    )

        if not isinstance(node, ast.Call):
            continue

        target = _qualname(node.func)
        if not target:
            continue

        resolved = target
        if isinstance(node.func, ast.Name):
            name = node.func.id
            if name in _DANGEROUS_BUILTINS:
                issues.append(
                    SafetyIssue(
                        severity="error",
                        code="UNSAFE_BUILTIN",
                        message=f"Dangerous builtin '{name}' in {rel}:{node.lineno}",
                        file=rel,
                        line=node.lineno,
                    )
                )
                continue
            resolved = imported_symbols.get(name, name)
        elif isinstance(node.func, ast.Attribute):
            parts = target.split(".")
            if parts and parts[0] in module_aliases:
                resolved = ".".join([module_aliases[parts[0]], *parts[1:]])

        shell_call = (
            resolved in _DANGEROUS_CALLS
            or any(resolved.startswith(prefix) for prefix in _OS_DANGEROUS_PREFIXES)
        )

        if shell_call:
            issues.append(
                SafetyIssue(
                    severity="error" if not requires_shell else "warning",
                    code="UNEXPECTED_SHELL" if not requires_shell else "RISKY_SHELL",
                    message=f"Dangerous call '{resolved}' in {rel}:{node.lineno}",
                    file=rel,
                    line=node.lineno,
                )
            )

    return issues


def analyze_safety(spec: ToolSpec, tool_dir: Path) -> SafetyReport:
    """
    Run static safety checks against all Python source files in *tool_dir*.
    """
    report = SafetyReport(tool_slug=spec.slug)

    # 1. Capability / sandbox level check
    if spec.security.requires_shell and spec.sandbox_level < 2:
        report.issues.append(
            SafetyIssue(
                severity="error",
                code="SANDBOX_TOO_LOW",
                message=f"requires_shell=True but sandbox_level={spec.sandbox_level}; minimum is 2",
            )
        )

    if spec.security.requires_network and spec.sandbox_level < 1:
        report.issues.append(
            SafetyIssue(
                severity="error",
                code="SANDBOX_TOO_LOW",
                message=f"requires_network=True but sandbox_level={spec.sandbox_level}; minimum is 1",
            )
        )

    # 2. Static file analysis
    py_files = list(tool_dir.rglob("*.py"))
    for py_file in py_files:
        rel = str(py_file.relative_to(tool_dir))
        try:
            src = py_file.read_text(encoding="utf-8")
            lines = src.splitlines()
        except OSError:
            report.issues.append(
                SafetyIssue(
                    severity="warning",
                    code="UNREADABLE_FILE",
                    message=f"Could not read {rel}: skipped from safety analysis",
                    file=rel,
                )
            )
            continue

        for lineno, line in enumerate(lines, start=1):
            for pattern, code in _SECRET_PATTERNS:
                if pattern.search(line):
                    report.issues.append(
                        SafetyIssue(
                            severity="error",
                            code=code,
                            message=f"Possible hardcoded secret: {line.strip()[:80]}",
                            file=rel,
                            line=lineno,
                        )
                    )

            if _TRAVERSAL_PATTERN.search(line):
                report.issues.append(
                    SafetyIssue(
                        severity="warning",
                        code="PATH_TRAVERSAL",
                        message=f"Possible path traversal: {line.strip()[:80]}",
                        file=rel,
                        line=lineno,
                    )
                )

        report.issues.extend(
            _analyze_ast(
                src,
                rel,
                requires_shell=spec.security.requires_shell,
                requires_network=spec.security.requires_network,
            )
        )

    return report
