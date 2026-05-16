"""
ToolForge CLI — main entry point.

Commands:
  toolforge init                          — initialise a ToolForge workspace
  toolforge new tool --from-prompt TEXT   — create a tool from a prompt
  toolforge generate mcp SLUG             — generate MCP server for a tool
  toolforge generate skill SLUG           — generate SKILL.md for a tool
  toolforge generate eval SLUG            — generate eval harness for a tool
  toolforge validate SLUG                 — run all validators
  toolforge run SLUG --input KEY=VAL      — run a tool with inputs
  toolforge eval SLUG                     — run eval suite
  toolforge package SLUG                  — build distributable zip
  toolforge registry list|search|info     — manage tool registry
  toolforge install SKILL_PATH            — install a legacy skill
"""
from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

console = Console()
err_console = Console(stderr=True)

# ---------------------------------------------------------------------------
# Workspace helpers
# ---------------------------------------------------------------------------

_WORKSPACE_MARKER = ".toolforge"


def _find_workspace_root(start: Path | None = None) -> Path:
    """Walk up from *start* (or cwd) to find the nearest .toolforge marker."""
    cwd = start or Path.cwd()
    for candidate in [cwd, *cwd.parents]:
        if (candidate / _WORKSPACE_MARKER).exists():
            return candidate
    return cwd  # fallback to cwd


def _tool_dir(workspace_root: Path, slug: str) -> Path:
    return workspace_root / "tools" / "generated" / slug


def _registry_path(workspace_root: Path) -> Path:
    return workspace_root / "toolforge_registry.json"


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------


@click.group()
@click.version_option(package_name="toolforge")
def cli() -> None:
    """ToolForge — CLI-first Tool Creator Platform."""


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("directory", default=".", type=click.Path())
def init(directory: str) -> None:
    """Initialise a ToolForge workspace in DIRECTORY (default: current dir)."""
    root = Path(directory).resolve()
    marker = root / _WORKSPACE_MARKER
    if marker.exists():
        console.print(f"[yellow]Already a ToolForge workspace: {root}[/]")
        return

    marker.mkdir(parents=True, exist_ok=True)
    for subdir in ("tools/generated", "skills/generated", "evals/generated", "dist"):
        (root / subdir).mkdir(parents=True, exist_ok=True)

    (root / "toolforge_registry.json").write_text("{}", encoding="utf-8")
    console.print(f"[green]✓ Initialised ToolForge workspace at {root}[/]")


# ---------------------------------------------------------------------------
# new
# ---------------------------------------------------------------------------


@cli.group()
def new() -> None:
    """Create new ToolForge artefacts."""


@new.command("tool")
@click.option("--from-prompt", "prompt", required=True, help="Natural-language tool description.")
@click.option("--slug", default=None, help="Override the generated slug.")
@click.option("--provider", default="rule_based", type=click.Choice(["rule_based", "llm"]))
@click.option("--llm-backend", default="openai", type=click.Choice(["openai", "anthropic"]))
@click.option("--model", default=None, help="Override default LLM model.")
@click.option("--overwrite", is_flag=True, help="Overwrite existing files.")
def new_tool(
    prompt: str,
    slug: str | None,
    provider: str,
    llm_backend: str,
    model: str | None,
    overwrite: bool,
) -> None:
    """Generate a tool spec and scaffold from a natural-language PROMPT."""
    from packages.core.spec_from_prompt import generate_spec_from_prompt
    from packages.core.tool_generator import scaffold_tool

    workspace_root = _find_workspace_root()

    console.print("[bold]Generating spec...[/]")
    spec = generate_spec_from_prompt(prompt, provider=provider, backend=llm_backend, model=model)
    if slug:
        spec = spec.model_copy(update={"slug": slug})

    output_root = workspace_root / "tools" / "generated"
    created = scaffold_tool(spec, output_root, overwrite=overwrite)

    for p in created:
        console.print(f"  [green]+[/] {p.relative_to(workspace_root)}")

    # Register the tool
    from packages.core.registry import ToolRegistry

    registry = ToolRegistry(_registry_path(workspace_root))
    registry.register(spec)
    console.print(f"\n[bold green]✓ Tool '{spec.slug}' created and registered.[/]")


# ---------------------------------------------------------------------------
# generate
# ---------------------------------------------------------------------------


@cli.group()
def generate() -> None:
    """Generate artefacts for an existing tool."""


@generate.command("mcp")
@click.argument("slug")
@click.option("--overwrite", is_flag=True)
def generate_mcp(slug: str, overwrite: bool) -> None:
    """Generate an MCP server for tool SLUG."""
    from packages.core.mcp_generator import generate_mcp_server
    from packages.core.tool_spec import ToolSpec

    workspace_root = _find_workspace_root()
    td = _tool_dir(workspace_root, slug)
    spec = ToolSpec.from_yaml(td / "toolforge.yaml")

    created = generate_mcp_server(spec, td, overwrite=overwrite)
    for p in created:
        console.print(f"  [green]+[/] {p.relative_to(workspace_root)}")

    from packages.core.registry import ToolRegistry
    registry = ToolRegistry(_registry_path(workspace_root))
    registry.set_mcp_path(slug, td / "mcp")

    console.print(f"[bold green]✓ MCP server generated for '{slug}'.[/]")


@generate.command("skill")
@click.argument("slug")
@click.option("--overwrite", is_flag=True)
def generate_skill(slug: str, overwrite: bool) -> None:
    """Generate a SKILL.md for tool SLUG."""
    from packages.core.skill_generator import generate_skill as _gen
    from packages.core.tool_spec import ToolSpec

    workspace_root = _find_workspace_root()
    td = _tool_dir(workspace_root, slug)
    spec = ToolSpec.from_yaml(td / "toolforge.yaml")

    skill_root = td / "skill"
    created = _gen(spec, skill_root, overwrite=overwrite)
    for p in created:
        console.print(f"  [green]+[/] {p.relative_to(workspace_root)}")

    from packages.core.registry import ToolRegistry
    registry = ToolRegistry(_registry_path(workspace_root))
    registry.set_skill_path(slug, td / "skill")

    console.print(f"[bold green]✓ Skill generated for '{slug}'.[/]")


@generate.command("eval")
@click.argument("slug")
@click.option("--overwrite", is_flag=True)
def generate_eval(slug: str, overwrite: bool) -> None:
    """Generate eval harness for tool SLUG."""
    from packages.core.eval_generator import generate_eval as _gen
    from packages.core.tool_spec import ToolSpec

    workspace_root = _find_workspace_root()
    td = _tool_dir(workspace_root, slug)
    spec = ToolSpec.from_yaml(td / "toolforge.yaml")

    evals_root = td / "evals"
    created = _gen(spec, evals_root, overwrite=overwrite)
    for p in created:
        console.print(f"  [green]+[/] {p.relative_to(workspace_root)}")

    from packages.core.registry import ToolRegistry
    registry = ToolRegistry(_registry_path(workspace_root))
    registry.set_eval_path(slug, td / "evals")

    console.print(f"[bold green]✓ Eval harness generated for '{slug}'.[/]")


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("slug")
def validate(slug: str) -> None:
    """Run all validators against tool SLUG."""
    from packages.validators.mcp_validator import validate_mcp_server
    from packages.validators.schema_validator import SchemaValidationError, validate_yaml_file
    from packages.validators.security_validator import validate_security
    from packages.validators.skill_validator import validate_skill_file
    from packages.validators.test_validator import run_safety_checks, run_tests

    workspace_root = _find_workspace_root()
    td = _tool_dir(workspace_root, slug)
    yaml_path = td / "toolforge.yaml"

    all_ok = True

    # Schema
    console.print("[bold]Schema validation...[/]", end=" ")
    try:
        spec = validate_yaml_file(yaml_path)
        console.print("[green]✓[/]")
    except SchemaValidationError as e:
        console.print("[red]✗[/]")
        for err in e.errors:
            console.print(f"  [red]{err}[/]")
        sys.exit(1)

    # Security
    console.print("[bold]Security validation...[/]", end=" ")
    sec_errors = validate_security(spec)
    if sec_errors:
        console.print("[red]✗[/]")
        for err in sec_errors:
            console.print(f"  [red]{err}[/]")
        all_ok = False
    else:
        console.print("[green]✓[/]")

    # MCP
    mcp_dir = td / "mcp"
    if mcp_dir.exists():
        console.print("[bold]MCP validation...[/]", end=" ")
        mcp_errors = validate_mcp_server(spec, mcp_dir)
        if mcp_errors:
            console.print("[red]✗[/]")
            for err in mcp_errors:
                console.print(f"  [red]{err}[/]")
            all_ok = False
        else:
            console.print("[green]✓[/]")

    # Skill
    skill_path = td / "skill" / "SKILL.md"
    if skill_path.exists():
        console.print("[bold]Skill validation...[/]", end=" ")
        skill_errors = validate_skill_file(skill_path)
        if skill_errors:
            console.print("[red]✗[/]")
            for err in skill_errors:
                console.print(f"  [red]{err}[/]")
            all_ok = False
        else:
            console.print("[green]✓[/]")
    elif (td / "skill").exists():
        console.print("[bold]Skill validation...[/]", end=" ")
        console.print("[red]✗[/]")
        console.print("  [red]Missing skill/SKILL.md[/]")
        all_ok = False

    # Eval artifacts
    evals_dir = td / "evals"
    if evals_dir.exists():
        console.print("[bold]Eval artifact validation...[/]", end=" ")
        cases_dir = evals_dir / "cases"
        if not (evals_dir / "task_config.json").exists() or not cases_dir.exists() or not list(cases_dir.glob("*.json")):
            console.print("[red]✗[/]")
            console.print("  [red]Eval artifacts are incomplete (task_config.json and case files required)[/]")
            all_ok = False
        else:
            console.print("[green]✓[/]")

    # Tests
    tests_dir = td / "tests"
    if tests_dir.exists():
        console.print("[bold]Running tests...[/]", end=" ")
        report = run_tests(td)
        if report.all_passed and report.passed > 0:
            console.print(f"[green]✓ {report.passed} passed[/]")
        else:
            console.print(f"[red]✗ {report.failed} failed, {report.errors} errors[/]")
            all_ok = False

    # Static safety analysis
    console.print("[bold]Static safety analysis...[/]", end=" ")
    safety_report = run_safety_checks(spec, td)
    if safety_report.all_passed:
        console.print("[green]✓[/]")
    else:
        console.print("[red]✗[/]")
        for failure in safety_report.failures:
            code = failure.get("code", "SAFETY")
            msg = failure.get("message", "")
            file_path = failure.get("file")
            line = failure.get("line")
            location = f" ({file_path}:{line})" if file_path and line else ""
            console.print(f"  [red]{code}: {msg}{location}[/]")
        all_ok = False

    from packages.core.registry import ToolRegistry
    registry = ToolRegistry(_registry_path(workspace_root))
    registry.set_validation_result(slug, all_ok)
    registry.set_status(slug, "validated" if all_ok else "failed")

    if not all_ok:
        sys.exit(1)
    console.print("\n[bold green]All validations passed.[/]")


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("slug")
@click.option("--input", "inputs", multiple=True, metavar="KEY=VALUE", help="Input key=value pairs.")
@click.option("--timeout", default=30.0, help="Timeout in seconds.")
def run(slug: str, inputs: tuple[str, ...], timeout: float) -> None:
    """Run tool SLUG with the given inputs."""
    from packages.core.tool_spec import ToolSpec
    from packages.runners.tool_runner import run_tool

    workspace_root = _find_workspace_root()
    td = _tool_dir(workspace_root, slug)
    spec = ToolSpec.from_yaml(td / "toolforge.yaml")

    parsed: dict[str, str] = {}
    for pair in inputs:
        if "=" not in pair:
            console.print(f"[red]Invalid input format: {pair!r} (expected KEY=VALUE)[/]")
            sys.exit(1)
        k, _, v = pair.partition("=")
        parsed[k.strip()] = v.strip()

    result = run_tool(spec, td, parsed, timeout_s=timeout)

    from packages.core.registry import ToolRegistry
    registry = ToolRegistry(_registry_path(workspace_root))
    registry.set_last_run(slug, success=result.success)

    if result.success:
        console.print(result.output)
    else:
        err_console.print(f"[red]Error (exit {result.exit_code}):[/] {result.error}")
        sys.exit(result.exit_code)


# ---------------------------------------------------------------------------
# eval
# ---------------------------------------------------------------------------


@cli.command("eval")
@click.argument("slug")
@click.option("--timeout", default=30.0)
def eval_cmd(slug: str, timeout: float) -> None:
    """Run the eval suite for tool SLUG."""
    from packages.core.tool_spec import ToolSpec
    from packages.runners.eval_runner import run_evals

    workspace_root = _find_workspace_root()
    td = _tool_dir(workspace_root, slug)
    spec = ToolSpec.from_yaml(td / "toolforge.yaml")

    report = run_evals(spec, td, timeout_s=timeout)

    from packages.core.registry import ToolRegistry
    registry = ToolRegistry(_registry_path(workspace_root))
    registry.set_eval_score(slug, report.pass_rate)
    registry.set_status(slug, "eval_passed" if report.overall_pass else "failed")

    table = Table(title=f"Eval: {slug}", show_header=True)
    table.add_column("Case ID")
    table.add_column("Pass")
    table.add_column("Score")
    table.add_column("Details")

    for r in report.results:
        status = "[green]✓[/]" if r.passed else "[red]✗[/]"
        table.add_row(r.case_id, status, f"{r.score:.2f}", r.details or r.error)

    console.print(table)
    console.print(f"\nPass rate: [bold]{report.pass_rate * 100:.1f}%[/]")

    if not report.overall_pass:
        sys.exit(1)


# ---------------------------------------------------------------------------
# package
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("slug")
@click.option("--dist-dir", default=None, help="Output directory for the package.")
def package(slug: str, dist_dir: str | None) -> None:
    """Build a distributable zip package for tool SLUG."""
    from packages.core.package_builder import build_package
    from packages.core.tool_spec import ToolSpec

    workspace_root = _find_workspace_root()
    td = _tool_dir(workspace_root, slug)
    spec = ToolSpec.from_yaml(td / "toolforge.yaml")

    dist = Path(dist_dir) if dist_dir else workspace_root / "dist"
    archive = build_package(spec, td, dist)

    from packages.core.registry import ToolRegistry
    registry = ToolRegistry(_registry_path(workspace_root))
    registry.set_package_path(slug, archive)
    registry.set_status(slug, "packaged")

    console.print(f"[green]✓[/] Package built: {archive}")


# ---------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------


@cli.group()
def registry() -> None:
    """Manage the ToolForge tool registry."""


@registry.command("list")
def registry_list() -> None:
    """List all registered tools."""
    from packages.core.registry import ToolRegistry

    workspace_root = _find_workspace_root()
    reg = ToolRegistry(_registry_path(workspace_root))
    tools = reg.list_all()

    if not tools:
        console.print("[yellow]No tools registered.[/]")
        return

    table = Table(title="Registered Tools", show_header=True)
    table.add_column("Slug")
    table.add_column("Name")
    table.add_column("Version")
    table.add_column("Tags")

    for s in tools:
        table.add_row(s.slug, s.name, s.version, ", ".join(s.tags))
    console.print(table)


@registry.command("search")
@click.argument("tag")
def registry_search(tag: str) -> None:
    """Search registered tools by TAG."""
    from packages.core.registry import ToolRegistry

    workspace_root = _find_workspace_root()
    reg = ToolRegistry(_registry_path(workspace_root))
    tools = reg.search_by_tag(tag)

    if not tools:
        console.print(f"[yellow]No tools tagged '{tag}'.[/]")
        return

    for s in tools:
        console.print(f"  [cyan]{s.slug}[/]  {s.description}")


@registry.command("info")
@click.argument("slug")
def registry_info(slug: str) -> None:
    """Show detailed info for tool SLUG."""
    from packages.core.registry import ToolRegistry

    workspace_root = _find_workspace_root()
    reg = ToolRegistry(_registry_path(workspace_root))
    spec = reg.find(slug)

    if spec is None:
        console.print(f"[red]Tool '{slug}' not found in registry.[/]")
        sys.exit(1)

    console.print(f"[bold]{spec.name}[/] ({spec.slug}) v{spec.version}")
    console.print(f"  [dim]{spec.description}[/]")
    console.print(f"  Language: {spec.language.value}")
    console.print(f"  Tags:     {', '.join(spec.tags) or '—'}")
    if spec.author:
        console.print(f"  Author:   {spec.author}")
    meta = reg.get_metadata(slug) or {}
    console.print(f"  Status:   {meta.get('status', 'unknown')}")
    console.print(f"  Last validation: {meta.get('last_validation') or '—'}")
    console.print(f"  Last run: {meta.get('last_run') or '—'}")
    console.print(f"  Last eval: {meta.get('last_eval') or '—'}")
    console.print(f"  Eval score: {meta.get('eval_score')}")
    console.print(f"  MCP path: {meta.get('mcp_path') or '—'}")
    console.print(f"  Skill path: {meta.get('skill_path') or '—'}")
    console.print(f"  Eval path: {meta.get('eval_path') or '—'}")
    console.print(f"  Package path: {meta.get('package_path') or '—'}")


# ---------------------------------------------------------------------------
# install (legacy skill importer)
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("skill_path", type=click.Path(exists=True))
def install(skill_path: str) -> None:
    """Install a legacy skill from SKILL_PATH into the ToolForge workspace."""
    from packages.integrations.agent_skills.importer import import_skill

    workspace_root = _find_workspace_root()
    skills_root = workspace_root / "skills" / "generated"
    created = import_skill(Path(skill_path), skills_root)
    for p in created:
        console.print(f"  [green]+[/] {p}")
    console.print("[bold green]✓ Skill installed.[/]")


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------


@cli.command()
def doctor() -> None:
    """Check ToolForge environment and dependencies."""
    import importlib

    checks: list[tuple[str, str]] = [
        ("Python ≥ 3.9", ""),
        ("pydantic", "pydantic"),
        ("click", "click"),
        ("jinja2", "jinja2"),
        ("ruamel.yaml", "ruamel.yaml"),
        ("rich", "rich"),
        ("jsonschema", "jsonschema"),
        ("pytest", "pytest"),
    ]
    all_ok = True
    for label, module in checks:
        if not module:
            ok = sys.version_info >= (3, 9)
        else:
            try:
                importlib.import_module(module)
                ok = True
            except ImportError:
                ok = False
        status = "[green]✓[/]" if ok else "[red]✗[/]"
        console.print(f"  {status} {label}")
        if not ok:
            all_ok = False
    if all_ok:
        console.print("\n[bold green]ToolForge environment OK.[/]")
    else:
        console.print("\n[bold red]Some checks failed.[/]")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
