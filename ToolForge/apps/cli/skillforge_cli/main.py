"""
SkillForge CLI — AI-powered skill lifecycle management.

Commands:
  skillforge init                   — initialise a SkillForge workspace
  skillforge chat                   — launch the AI REPL
  skillforge create TEXT            — create a skill from a prompt
  skillforge validate SLUG          — validate a skill
  skillforge repair SLUG            — AI-driven repair loop
  skillforge run SLUG               — run a skill tool
  skillforge package SLUG           — package a skill as distributable zip
  skillforge install PATH           — install a packaged skill zip
  skillforge list                   — list all registered skills
  skillforge inspect SLUG           — show detailed skill info
  skillforge tools list             — list tools via MCP server
  skillforge tools call SLUG NAME   — call an MCP tool
  skillforge mcp smoke SLUG         — MCP smoke test
  skillforge doctor                 — workspace health check
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

console = Console()
err_console = Console(stderr=True)

# ---------------------------------------------------------------------------
# Workspace helpers (analogous to toolforge_cli/main.py)
# ---------------------------------------------------------------------------

_WORKSPACE_MARKER = ".skillforge"
_TOOLFORGE_MARKER = ".toolforge"


def _find_workspace_root(start: Optional[Path] = None) -> Path:
    """
    Walk up from *start* (or cwd) looking for .skillforge or .toolforge markers.
    Falls back to cwd if neither is found.
    """
    cwd = (start or Path.cwd()).resolve()
    for candidate in [cwd, *cwd.parents]:
        if (candidate / _WORKSPACE_MARKER).exists():
            return candidate
        if (candidate / _TOOLFORGE_MARKER).exists():
            return candidate
    return cwd


def _add_packages_to_path(workspace_root: Path) -> None:
    """Add workspace root to sys.path so ToolForge packages are importable."""
    pkg_root = str(workspace_root)
    if pkg_root not in sys.path:
        sys.path.insert(0, pkg_root)


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------


@click.group()
@click.version_option(package_name="toolforge", prog_name="skillforge")
@click.option(
    "--provider",
    default="rule_based",
    envvar="SKILLFORGE_PROVIDER",
    type=click.Choice(
        ["rule_based", "openai", "anthropic", "ollama", "azure_openai", "deepseek"],
        case_sensitive=False,
    ),
    help="AI provider for skill generation (default: rule_based).",
    show_default=True,
)
@click.option(
    "--workspace",
    default=None,
    type=click.Path(file_okay=False, path_type=Path),
    help="Override workspace root directory.",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    default=False,
    help="Auto-approve all approval-required actions.",
)
@click.pass_context
def main(ctx: click.Context, provider: str, workspace: Optional[Path], yes: bool) -> None:
    """SkillForge — AI-powered skill lifecycle management."""
    ctx.ensure_object(dict)
    ws_root = workspace or _find_workspace_root()
    ctx.obj["workspace"] = ws_root
    ctx.obj["provider"] = provider
    ctx.obj["yes"] = yes
    _add_packages_to_path(ws_root)


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


@main.command()
@click.argument("directory", default=".", type=click.Path(path_type=Path))
@click.pass_context
def init(ctx: click.Context, directory: Path) -> None:
    """Initialise a SkillForge workspace in DIRECTORY (default: current dir)."""
    # If DIRECTORY is omitted, prefer the already-resolved workspace root
    # (which honors --workspace) instead of always using cwd.
    if ctx.get_parameter_source("directory") == click.core.ParameterSource.DEFAULT:
        root = Path(ctx.obj["workspace"]).resolve()
    else:
        root = directory.resolve()
    sf_dir = root / ".skillforge"
    if sf_dir.exists():
        console.print(f"[yellow]Already a SkillForge workspace: {root}[/]")
        return

    _add_packages_to_path(root)
    from skillforge_ai.orchestrator import AIOrchestrator

    orch = AIOrchestrator(workspace_root=root, interactive=False)
    msg = orch._cmd_init()
    console.print(f"[green]{msg}[/]")

    # Also initialise ToolForge markers so existing generators work
    tf_dir = root / ".toolforge"
    tf_dir.mkdir(exist_ok=True)
    for subdir in ("tools/generated", "skills/generated", "evals/generated", "dist"):
        (root / subdir).mkdir(parents=True, exist_ok=True)
    if not (root / "toolforge_registry.json").exists():
        (root / "toolforge_registry.json").write_text("{}", encoding="utf-8")

    console.print(f"[green]✓ SkillForge workspace ready at {root}[/]")


# ---------------------------------------------------------------------------
# chat
# ---------------------------------------------------------------------------


@main.command()
@click.pass_context
def chat(ctx: click.Context) -> None:
    """Launch the interactive AI REPL."""
    ws_root: Path = ctx.obj["workspace"]
    provider: str = ctx.obj["provider"]
    yes: bool = ctx.obj["yes"]

    from skillforge_ai.orchestrator import AIOrchestrator

    orch = AIOrchestrator(
        workspace_root=ws_root,
        provider=provider,
        interactive=not yes,
        auto_approve=yes,
    )
    orch.run_chat_loop()


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


@main.command()
@click.argument("prompt", nargs=-1, required=True)
@click.option("--name", "-n", default=None, help="Explicit skill slug/name.")
@click.option("--no-mcp", is_flag=True, default=False, help="Skip MCP server generation.")
@click.option("--no-eval", is_flag=True, default=False, help="Skip eval harness generation.")
@click.pass_context
def create(
    ctx: click.Context,
    prompt: tuple[str, ...],
    name: Optional[str],
    no_mcp: bool,
    no_eval: bool,
) -> None:
    """Create a new skill from a natural-language PROMPT."""
    ws_root: Path = ctx.obj["workspace"]
    provider: str = ctx.obj["provider"]
    yes: bool = ctx.obj["yes"]

    request = " ".join(prompt)

    from skillforge_ai.skill_builder import SkillBuilder
    from skillforge_ai.tool_registry import SkillForgeRegistry

    builder = SkillBuilder(
        workspace_root=ws_root,
        provider=provider,
        generate_mcp=not no_mcp,
        generate_eval_harness=not no_eval,
    )

    with console.status(f"[bold green]Generating skill from: {request!r}…[/]"):
        try:
            tool_dir, manifest = builder.build(request, skill_name=name)
        except Exception as exc:
            err_console.print(f"[red]Error: {exc}[/]")
            sys.exit(1)

    reg = SkillForgeRegistry(ws_root)
    try:
        reg.register_skill(manifest, tool_dir)
    except Exception:
        pass

    console.print(f"[green]✓ Skill '{manifest.name}' created[/]")
    console.print(f"  Location : {tool_dir}")
    console.print(f"  Category : {manifest.category}")
    console.print(f"  Risk     : {manifest.risk_level}")
    console.print(f"\nNext: [cyan]skillforge validate {manifest.name}[/]")


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


@main.command()
@click.argument("slug")
@click.option("--repair", is_flag=True, default=False, help="Attempt AI-driven repair on failure.")
@click.pass_context
def validate(ctx: click.Context, slug: str, repair: bool) -> None:
    """Validate SLUG — run schema, security, MCP, skill, test, and safety checks."""
    ws_root: Path = ctx.obj["workspace"]
    provider: str = ctx.obj["provider"]

    from skillforge_ai.validation_runner import ValidationRunner

    runner = ValidationRunner(workspace_root=ws_root)

    with console.status(f"[bold]Validating '{slug}'…[/]"):
        if repair:
            report = runner.repair_loop(slug, provider=provider)
        else:
            report = runner.validate(slug)

    _print_validation_report(report)
    if not report.passed:
        sys.exit(1)


# ---------------------------------------------------------------------------
# repair
# ---------------------------------------------------------------------------


@main.command()
@click.argument("slug")
@click.option("--max-attempts", default=3, show_default=True, help="Maximum repair iterations.")
@click.pass_context
def repair(ctx: click.Context, slug: str, max_attempts: int) -> None:
    """Run AI-driven repair loop for SLUG."""
    ws_root: Path = ctx.obj["workspace"]
    provider: str = ctx.obj["provider"]

    from skillforge_ai.validation_runner import ValidationRunner

    runner = ValidationRunner(
        workspace_root=ws_root,
        max_repair_attempts=max_attempts,
    )

    with console.status(f"[bold]Repairing '{slug}'…[/]"):
        report = runner.repair_loop(slug, provider=provider)

    _print_validation_report(report)
    if not report.passed:
        sys.exit(1)


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------


@main.command()
@click.argument("slug")
@click.option(
    "--input",
    "-i",
    "inputs",
    multiple=True,
    help="Input as KEY=VALUE (may be repeated).",
)
@click.pass_context
def run(ctx: click.Context, slug: str, inputs: tuple[str, ...]) -> None:
    """Run the tool identified by SLUG."""
    ws_root: Path = ctx.obj["workspace"]

    params: dict[str, str] = {}
    for item in inputs:
        if "=" in item:
            k, v = item.split("=", 1)
            params[k.strip()] = v.strip()
        else:
            err_console.print(f"[yellow]Ignoring malformed input (expected KEY=VALUE): {item}[/]")

    tool_dir = ws_root / "tools" / "generated" / slug
    if not tool_dir.exists():
        err_console.print(f"[red]Tool '{slug}' not found at {tool_dir}[/]")
        sys.exit(1)

    try:
        from packages.runners.tool_runner import run_tool

        with console.status(f"[bold]Running '{slug}'…[/]"):
            result = run_tool(tool_dir, params)

        if result.returncode == 0:
            console.print(f"[green]✓ Tool '{slug}' completed[/]")
            if result.output:
                console.print(result.output)
        else:
            err_console.print(f"[red]Tool exited with code {result.returncode}[/]")
            if result.stderr:
                err_console.print(result.stderr)
            sys.exit(result.returncode)
    except Exception as exc:
        err_console.print(f"[red]Run failed: {exc}[/]")
        sys.exit(1)


# ---------------------------------------------------------------------------
# package
# ---------------------------------------------------------------------------


@main.command()
@click.argument("slug")
@click.option(
    "--output",
    "-o",
    default=None,
    type=click.Path(path_type=Path),
    help="Output zip path (default: dist/<slug>-<timestamp>.zip).",
)
@click.pass_context
def package(ctx: click.Context, slug: str, output: Optional[Path]) -> None:
    """Package SLUG as a distributable zip archive."""
    ws_root: Path = ctx.obj["workspace"]
    yes: bool = ctx.obj["yes"]

    tool_dir = ws_root / "tools" / "generated" / slug
    if not tool_dir.exists():
        err_console.print(f"[red]Tool directory not found for '{slug}'[/]")
        sys.exit(1)

    import zipfile
    import datetime

    out_dir = ws_root / "dist"
    out_dir.mkdir(exist_ok=True)

    if output is None:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output = out_dir / f"{slug}-{ts}.zip"

    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in tool_dir.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(tool_dir))

    from skillforge_ai.tool_registry import SkillForgeRegistry

    SkillForgeRegistry(ws_root).mark_packaged(slug)

    console.print(f"[green]✓ Packaged '{slug}' → {output}[/]")


# ---------------------------------------------------------------------------
# install
# ---------------------------------------------------------------------------


@main.command()
@click.argument("skill_path", type=click.Path(exists=True, path_type=Path))
@click.pass_context
def install(ctx: click.Context, skill_path: Path) -> None:
    """Install a packaged skill zip into the workspace."""
    ws_root: Path = ctx.obj["workspace"]

    import zipfile

    if not zipfile.is_zipfile(skill_path):
        err_console.print(f"[red]Not a valid zip file: {skill_path}[/]")
        sys.exit(1)

    slug = skill_path.stem.split("-")[0]
    dest = ws_root / "tools" / "generated" / slug

    with console.status(f"[bold]Installing '{slug}'…[/]"):
        with zipfile.ZipFile(skill_path) as zf:
            zf.extractall(dest)

    console.print(f"[green]✓ Installed '{slug}' → {dest}[/]")


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


@main.command(name="list")
@click.option("--json", "output_json", is_flag=True, default=False, help="Output as JSON.")
@click.pass_context
def list_skills(ctx: click.Context, output_json: bool) -> None:
    """List all registered skills."""
    ws_root: Path = ctx.obj["workspace"]

    from skillforge_ai.tool_registry import SkillForgeRegistry

    reg = SkillForgeRegistry(ws_root)
    skills = reg.list_skills()

    if output_json:
        import json

        console.print(json.dumps(skills, indent=2))
        return

    if not skills:
        console.print("[yellow]No skills registered. Use 'create' to build one.[/]")
        return

    table = Table(title="Registered Skills", show_lines=False)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Status", style="magenta")
    table.add_column("Validated", style="green")
    table.add_column("Risk", style="yellow")
    table.add_column("Category")

    for s in skills:
        table.add_row(
            s["name"],
            s["status"],
            "✓" if s["validated"] else "✗",
            s["risk_level"],
            s["category"],
        )

    console.print(table)


# ---------------------------------------------------------------------------
# inspect
# ---------------------------------------------------------------------------


@main.command()
@click.argument("slug")
@click.pass_context
def inspect(ctx: click.Context, slug: str) -> None:
    """Show detailed information about SLUG."""
    ws_root: Path = ctx.obj["workspace"]

    from skillforge_ai.tool_registry import SkillForgeRegistry

    reg = SkillForgeRegistry(ws_root)
    skill = reg.get_skill(slug)

    if skill is None:
        err_console.print(f"[red]Skill '{slug}' not found.[/]")
        sys.exit(1)

    table = Table(title=f"Skill: {slug}", show_header=False)
    table.add_column("Key", style="bold cyan")
    table.add_column("Value")

    for k, v in skill.items():
        table.add_row(str(k), str(v))

    console.print(table)


# ---------------------------------------------------------------------------
# tools (sub-group)
# ---------------------------------------------------------------------------


@main.group(name="tools")
def tools_group() -> None:
    """Interact with MCP tool servers."""


@tools_group.command(name="list")
@click.argument("slug")
@click.option(
    "--server-path",
    default=None,
    type=click.Path(path_type=Path),
    help="Path to MCP server file (auto-detected if omitted).",
)
@click.pass_context
def tools_list(ctx: click.Context, slug: str, server_path: Optional[Path]) -> None:
    """List tools exposed by the MCP server for SLUG."""
    ws_root: Path = ctx.obj["workspace"]

    if server_path is None:
        server_path = ws_root / "tools" / "generated" / slug / "mcp" / "server.py"

    if not server_path.exists():
        err_console.print(f"[red]MCP server not found: {server_path}[/]")
        sys.exit(1)

    from skillforge_ai.mcp_controller import MCPController

    ctrl = MCPController()
    try:
        ctrl.start(server_path)
        mcp_tools = ctrl.list_tools()
        ctrl.stop()
    except Exception as exc:
        err_console.print(f"[red]MCP error: {exc}[/]")
        sys.exit(1)

    if not mcp_tools:
        console.print("[yellow]No tools found.[/]")
        return

    table = Table(title=f"MCP Tools — {slug}")
    table.add_column("Name", style="cyan")
    table.add_column("Description")

    for t in mcp_tools:
        table.add_row(t.get("name", "?"), t.get("description", ""))

    console.print(table)


@tools_group.command(name="call")
@click.argument("slug")
@click.argument("tool_name")
@click.option("--arg", "-a", "args", multiple=True, help="Argument as KEY=VALUE.")
@click.option(
    "--server-path",
    default=None,
    type=click.Path(path_type=Path),
    help="Path to MCP server file (auto-detected if omitted).",
)
@click.pass_context
def tools_call(
    ctx: click.Context,
    slug: str,
    tool_name: str,
    args: tuple[str, ...],
    server_path: Optional[Path],
) -> None:
    """Call TOOL_NAME on the MCP server for SLUG."""
    ws_root: Path = ctx.obj["workspace"]

    if server_path is None:
        server_path = ws_root / "tools" / "generated" / slug / "mcp" / "server.py"

    if not server_path.exists():
        err_console.print(f"[red]MCP server not found: {server_path}[/]")
        sys.exit(1)

    arguments: dict[str, str] = {}
    for item in args:
        if "=" in item:
            k, v = item.split("=", 1)
            arguments[k.strip()] = v.strip()

    from skillforge_ai.mcp_controller import MCPController

    ctrl = MCPController()
    try:
        ctrl.start(server_path)
        result = ctrl.call_tool(tool_name, arguments)
        ctrl.stop()
    except Exception as exc:
        err_console.print(f"[red]MCP call failed: {exc}[/]")
        sys.exit(1)

    import json

    console.print(json.dumps(result, indent=2))


# ---------------------------------------------------------------------------
# mcp smoke
# ---------------------------------------------------------------------------


@main.group(name="mcp")
def mcp_group() -> None:
    """MCP server management commands."""


@mcp_group.command(name="smoke")
@click.argument("slug")
@click.option(
    "--server-path",
    default=None,
    type=click.Path(path_type=Path),
    help="Path to MCP server file (auto-detected if omitted).",
)
@click.pass_context
def mcp_smoke(ctx: click.Context, slug: str, server_path: Optional[Path]) -> None:
    """Run a smoke test against the MCP server for SLUG."""
    ws_root: Path = ctx.obj["workspace"]

    if server_path is None:
        server_path = ws_root / "tools" / "generated" / slug / "mcp" / "server.py"

    if not server_path.exists():
        err_console.print(f"[red]MCP server not found: {server_path}[/]")
        sys.exit(1)

    from skillforge_ai.mcp_controller import MCPController

    ctrl = MCPController()
    with console.status("[bold]Running MCP smoke test…[/]"):
        ok = ctrl.smoke_test(server_path)

    if ok:
        console.print(f"[green]✓ MCP smoke test passed for '{slug}'[/]")
    else:
        err_console.print(f"[red]✗ MCP smoke test failed for '{slug}'[/]")
        sys.exit(1)


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------


@main.command()
@click.pass_context
def doctor(ctx: click.Context) -> None:
    """Check workspace health."""
    ws_root: Path = ctx.obj["workspace"]

    from skillforge_ai.orchestrator import AIOrchestrator

    orch = AIOrchestrator(workspace_root=ws_root, interactive=False)
    msg = orch._cmd_doctor()
    console.print(msg)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _print_validation_report(report: Any) -> None:
    """Print a ValidationReport to the console."""
    from skillforge_ai.models import ValidationReport

    status = "[green]PASSED[/]" if report.passed else "[red]FAILED[/]"
    console.print(f"\nValidation: {status} (attempt {report.attempt})")
    console.print(f"  Schema   : {'✓' if report.schema_ok else '✗'}")
    console.print(f"  Security : {'✓' if report.security_ok else '✗'}")
    console.print(f"  MCP      : {'✓' if report.mcp_ok else '–' if report.mcp_ok is None else '✗'}")
    console.print(f"  Skill    : {'✓' if report.skill_ok else '✗'}")
    console.print(f"  Tests    : {'✓' if report.tests_ok else '✗'}")
    console.print(f"  Safety   : {'✓' if report.safety_ok else '✗'}")

    if report.errors:
        console.print("\n[red]Errors:[/]")
        for e in report.errors:
            console.print(f"  • {e}")

    if report.warnings:
        console.print("\n[yellow]Warnings:[/]")
        for w in report.warnings:
            console.print(f"  • {w}")


# This is referenced in the type hint on _print_validation_report above
from typing import Any  # noqa: E402 (needed after function def)
