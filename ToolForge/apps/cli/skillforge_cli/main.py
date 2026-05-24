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
    from skillforge_ai.commands.chat import run_chat

    run_chat(workspace_root=ws_root, provider=provider)


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

    request = " ".join(prompt)

    from skillforge_ai.commands.create import run_create

    with console.status(f"[bold green]Generating skill from: {request!r}…[/]"):
        try:
            tool_dir, manifest = run_create(
                workspace_root=ws_root,
                prompt=request,
                provider=provider,
                name=name,
                generate_mcp=not no_mcp,
                generate_eval_harness=not no_eval,
            )
        except Exception as exc:
            err_console.print(f"[red]Error: {exc}[/]")
            sys.exit(1)

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

    from skillforge_ai.commands.validate import run_validate

    with console.status(f"[bold]Validating '{slug}'…[/]"):
        report = run_validate(
            workspace_root=ws_root,
            slug=slug,
            repair=repair,
            provider=provider,
        )

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

    from skillforge_ai.commands.repair import run_repair

    with console.status(f"[bold]Repairing '{slug}'…[/]"):
        report = run_repair(
            workspace_root=ws_root,
            slug=slug,
            provider=provider,
            max_attempts=max_attempts,
        )

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

    try:
        from skillforge_ai.commands.run import run_skill

        with console.status(f"[bold]Running '{slug}'…[/]"):
            result = run_skill(ws_root, slug, params)

        if result.exit_code == 0:
            console.print(f"[green]✓ Tool '{slug}' completed[/]")
            if result.output:
                console.print(result.output)
        else:
            err_console.print(f"[red]Tool exited with code {result.exit_code}[/]")
            if result.error:
                err_console.print(result.error)
            sys.exit(result.exit_code)
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

    from skillforge_ai.commands.package import run_package

    output = run_package(
        workspace_root=ws_root,
        slug=slug,
        output=output,
    )

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
    from skillforge_ai.commands.install import run_install

    if not zipfile.is_zipfile(skill_path):
        err_console.print(f"[red]Not a valid zip file: {skill_path}[/]")
        sys.exit(1)

    with console.status(f"[bold]Installing '{skill_path.stem}'…[/]"):
        slug, dest = run_install(workspace_root=ws_root, archive_path=skill_path)

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

    from skillforge_ai.commands.list import run_list

    skills = run_list(workspace_root=ws_root)

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

    from skillforge_ai.commands.inspect import run_inspect

    skill = run_inspect(workspace_root=ws_root, skill_name=slug)

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
@click.argument("slug", required=False)
@click.option(
    "--server-path",
    default=None,
    type=click.Path(path_type=Path),
    help="Path to MCP server file (auto-detected if omitted).",
)
@click.pass_context
def tools_list(ctx: click.Context, slug: Optional[str], server_path: Optional[Path]) -> None:
    """List tools exposed by MCP or list registered tools when SLUG is omitted."""
    ws_root: Path = ctx.obj["workspace"]

    if slug is None and server_path is None:
        from skillforge_ai.commands.tools import list_registry_tools

        reg_tools = list_registry_tools(ws_root)
        if not reg_tools:
            console.print("[yellow]No registered tools found.[/]")
            return

        table = Table(title="Registered Tools")
        table.add_column("Name", style="cyan")
        table.add_column("Type")
        table.add_column("Entrypoint")
        table.add_column("Validated")

        for item in reg_tools:
            table.add_row(
                str(item.get("name", "")),
                str(item.get("type", "python")),
                str(item.get("entrypoint", "")),
                "✓" if item.get("validated") else "✗",
            )
        console.print(table)
        return

    if slug is None:
        err_console.print("[red]Provide a SLUG or omit --server-path to list registry tools.[/]")
        sys.exit(1)

    if server_path is None:
        server_path = ws_root / "tools" / "generated" / slug / "mcp" / "server.py"

    if not server_path.exists():
        err_console.print(f"[red]MCP server not found: {server_path}[/]")
        sys.exit(1)

    from skillforge_ai.commands.tools import list_mcp_tools

    try:
        mcp_tools = list_mcp_tools(server_path)
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

    from skillforge_ai.commands.tools import call_mcp_tool

    try:
        result = call_mcp_tool(server_path, tool_name, arguments)
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
@click.argument("slug", required=False)
@click.option(
    "--server-path",
    default=None,
    type=click.Path(path_type=Path),
    help="Path to MCP server file (auto-detected if omitted).",
)
@click.option(
    "--profile",
    default=None,
    help="Run Toolathlon profile smoke (e.g. smoke) instead of skill-local MCP smoke.",
)
@click.pass_context
def mcp_smoke(
    ctx: click.Context,
    slug: Optional[str],
    server_path: Optional[Path],
    profile: Optional[str],
) -> None:
    """Run smoke against skill MCP or Toolathlon profile."""
    ws_root: Path = ctx.obj["workspace"]

    if profile:
        from skillforge_ai.commands.mcp import smoke_toolathlon_profile

        with console.status(f"[bold]Running Toolathlon MCP smoke profile '{profile}'…[/]"):
            try:
                exit_code, _stdout, stderr, summary_path = smoke_toolathlon_profile(
                    ws_root,
                    profile,
                )
            except FileNotFoundError as exc:
                err_console.print(f"[red]{exc}[/]")
                sys.exit(1)

        if exit_code == 0:
            console.print(f"[green]✓ Toolathlon MCP smoke passed for profile '{profile}'[/]")
            console.print(f"Summary: {summary_path}")
            return

        err_console.print(f"[red]✗ Toolathlon MCP smoke failed for profile '{profile}'[/]")
        if stderr:
            err_console.print(stderr.strip())
        sys.exit(exit_code)

    if slug is None:
        err_console.print("[red]Provide a SLUG for skill-local MCP smoke or use --profile.[/]")
        sys.exit(1)

    if server_path is None:
        server_path = ws_root / "tools" / "generated" / slug / "mcp" / "server.py"

    if not server_path.exists():
        err_console.print(f"[red]MCP server not found: {server_path}[/]")
        sys.exit(1)

    from skillforge_ai.commands.mcp import smoke_skill_server

    with console.status("[bold]Running MCP smoke test…[/]"):
        ok = smoke_skill_server(server_path)

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
