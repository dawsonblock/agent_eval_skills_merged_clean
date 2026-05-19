"""
ToolForge CLI — main entry point.

Commands:
  toolforge init                          — initialise a ToolForge workspace
  toolforge ai spec                       — generate tool spec via AI
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


def _validate_azure_openai_params(azure_deployment: str | None, azure_endpoint: str | None) -> None:
    """Validate Azure OpenAI provider parameters."""
    if not azure_deployment:
        console.print("[red]Error: --azure-deployment is required for azure_openai provider[/]")
        sys.exit(1)
    if not azure_endpoint:
        console.print("[red]Error: --azure-endpoint is required for azure_openai provider[/]")
        sys.exit(1)


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
# ai
# ---------------------------------------------------------------------------


@cli.group()
def ai() -> None:
    """AI-powered tool generation commands."""


@ai.command("spec")
@click.option("--prompt", "-p", required=True, help="Natural-language tool description.")
@click.option(
    "--provider",
    default="rule_based",
    type=click.Choice(["rule_based", "mock", "openai", "anthropic", "ollama", "azure_openai", "deepseek"]),
    help="AI provider to use for spec generation.",
)
@click.option("--backend", default="openai", type=click.Choice(["openai", "anthropic"]), help="LLM backend for llm provider.")
@click.option("--model", default=None, help="Override default model for the provider.")
@click.option("--azure-deployment", default=None, help="Azure OpenAI deployment name (required for azure_openai provider).")
@click.option("--azure-endpoint", default=None, help="Azure OpenAI endpoint URL (required for azure_openai provider).")
@click.option("--output", "-o", default=None, type=click.Path(), help="Output file path (default: stdout).")
@click.option("--stdout", is_flag=True, help="Print spec to stdout instead of writing file.")
@click.option("--interactive", is_flag=True, help="Interactive mode: review spec before writing.")
@click.option("--dry-run", is_flag=True, help="Generate spec without writing any files.")
@click.option("--max-retries", default=3, type=int, help="Number of retry attempts for transient errors.")
@click.option("--timeout", default=30, type=int, help="Timeout in seconds for API calls.")
@click.option("--fallback-to-rule-based", is_flag=True, help="Fallback to rule-based on AI failure.")
def ai_spec(
    prompt: str,
    provider: str,
    backend: str,
    model: str | None,
    azure_deployment: str | None,
    azure_endpoint: str | None,
    output: str | None,
    stdout: bool,
    interactive: bool,
    dry_run: bool,
    max_retries: int,
    timeout: int,
    fallback_to_rule_based: bool,
) -> None:
    """
    Generate a tool spec from a natural-language prompt using AI.

    IMPORTANT: AI ROLE BOUNDARIES
    - AI returns structured data (ToolSpec objects), NOT file writes
    - User approval is required before using AI-generated specs
    - Fallback to rule-based generation is mandatory on AI failure
    - No autonomous file writes or command execution
    - See ToolForge/docs/AI_ROLE_BOUNDARIES.md for full boundaries
    """
    from packages.ai.spec_generator import AISpecGenerator

    console.print("[bold]Generating tool spec...[/]")

    # Validate required parameters for azure_openai provider
    if provider == "azure_openai":
        _validate_azure_openai_params(azure_deployment, azure_endpoint)

    gen = AISpecGenerator(
        provider=provider,
        backend=backend,
        model=model,
        max_retries=max_retries,
        timeout_seconds=timeout,
        fallback_to_rule_based=fallback_to_rule_based,
        azure_openai_deployment=azure_deployment,
        azure_openai_endpoint=azure_endpoint,
    )

    spec = gen.generate(prompt)

    import yaml

    yaml_output = yaml.dump(spec.model_dump(mode="python", exclude_none=True), sort_keys=False)

    if stdout:
        console.print(yaml_output)
        return

    if interactive:
        console.print("\n[bold]Generated spec:[/]")
        console.print(yaml_output)
        if not click.confirm("\nAccept this spec?"):
            console.print("[yellow]Spec rejected.[/]")
            sys.exit(0)

    if dry_run:
        console.print("[yellow]Dry run: spec not written.[/]")
        console.print(yaml_output)
        return

    output_path = Path(output) if output else Path(f"{spec.slug}.yaml")
    output_path.write_text(yaml_output, encoding="utf-8")
    console.print(f"[green]✓[/] Spec written to {output_path}")


# ---------------------------------------------------------------------------
# new
# ---------------------------------------------------------------------------


@cli.group()
def new() -> None:
    """Create new ToolForge artefacts."""


@new.command("tool")
@click.option("--from-prompt", "prompt", required=True, help="Natural-language tool description.")
@click.option("--slug", default=None, help="Override the generated slug.")
@click.option("--provider", default="rule_based", type=click.Choice(["rule_based", "llm", "openai", "anthropic", "ollama", "azure_openai"]))
@click.option("--llm-backend", default="openai", type=click.Choice(["openai", "anthropic"]), help="LLM backend for llm provider.")
@click.option("--model", default=None, help="Override default model for the provider.")
@click.option("--azure-deployment", default=None, help="Azure OpenAI deployment name (required for azure_openai provider).")
@click.option("--azure-endpoint", default=None, help="Azure OpenAI endpoint URL (required for azure_openai provider).")
@click.option("--overwrite", is_flag=True, help="Overwrite existing files.")
@click.option("--review", is_flag=True, help="Review spec before scaffolding.")
@click.option("--fallback-to-rule-based", is_flag=True, help="Fallback to rule-based on AI failure.")
@click.option("--max-retries", default=3, type=int, help="Number of retry attempts for transient errors.")
@click.option("--timeout", default=30, type=int, help="Timeout in seconds for API calls.")
def new_tool(
    prompt: str,
    slug: str | None,
    provider: str,
    llm_backend: str,
    model: str | None,
    azure_deployment: str | None,
    azure_endpoint: str | None,
    overwrite: bool,
    review: bool,
    fallback_to_rule_based: bool,
    max_retries: int,
    timeout: int,
) -> None:
    """Generate a tool spec and scaffold from a natural-language PROMPT."""
    from packages.core.spec_from_prompt import generate_spec_from_prompt
    from packages.core.tool_generator import scaffold_tool

    workspace_root = _find_workspace_root()

    console.print("[bold]Generating spec...[/]")

    # Validate required parameters for azure_openai provider
    if provider == "azure_openai":
        _validate_azure_openai_params(azure_deployment, azure_endpoint)

    # Use new AI integration for AI providers
    if provider in ("openai", "anthropic", "ollama", "azure_openai"):
        from packages.ai.spec_generator import AISpecGenerator

        gen = AISpecGenerator(
            provider=provider,
            backend=llm_backend,
            model=model,
            max_retries=max_retries,
            timeout_seconds=timeout,
            fallback_to_rule_based=fallback_to_rule_based,
            azure_openai_deployment=azure_deployment,
            azure_openai_endpoint=azure_endpoint,
        )
        spec = gen.generate(prompt)
    elif provider == "llm":
        spec = generate_spec_from_prompt(
            prompt,
            provider="llm",
            backend=llm_backend,
            model=model,
            max_retries=max_retries,
            timeout_seconds=timeout,
        )
    else:
        spec = generate_spec_from_prompt(prompt, provider="rule_based")

    if slug:
        spec = spec.model_copy(update={"slug": slug})

    # Review mode
    if review:
        import yaml

        console.print("\n[bold]Generated spec:[/]")
        console.print(yaml.dump(spec.model_dump(mode="python", exclude_none=True), sort_keys=False))
        if not click.confirm("\nProceed with scaffolding?"):
            console.print("[yellow]Scaffolding cancelled.[/]")
            sys.exit(0)

    output_root = workspace_root / "tools" / "generated"
    try:
        created = scaffold_tool(spec, output_root, overwrite=overwrite)
    except FileExistsError:
        err_console.print(
            "[red]Tool scaffold already exists.[/] "
            "Use [bold]--overwrite[/] to replace files or [bold]--slug[/] "
            "to generate a new tool."
        )
        sys.exit(1)

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
    if spec.mcp.enabled:
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
    if spec.skill.enabled:
        console.print("[bold]Skill validation...[/]", end=" ")
        if skill_path.exists():
            skill_errors = validate_skill_file(skill_path)
            if skill_errors:
                console.print("[red]✗[/]")
                for err in skill_errors:
                    console.print(f"  [red]{err}[/]")
                all_ok = False
            else:
                console.print("[green]✓[/]")
        else:
            console.print("[red]✗[/]")
            console.print("  [red]Missing skill/SKILL.md[/]")
            all_ok = False

    # Eval artifacts
    evals_dir = td / "evals"
    if spec.eval.enabled:
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
    else:
        console.print("[bold]Running tests...[/]", end=" ")
        console.print("[red]✗[/]")
        console.print("  [red]Missing tests/ directory[/]")
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
    run_type = "normal"
    operational_success = result.success
    # Only treat a path failure as a confirmed safety probe when the error
    # message indicates the guardrail itself fired (traversal blocked, symlink
    # blocked, or blocked_paths policy matched).  User misconfigurations such
    # as wrong extension, missing file, or unconfigured roots are NOT safety
    # probes and should remain operational failures.
    _GUARDRAIL_PHRASES = (
        "resolved outside allowed_read_paths",
        "resolved outside allowed_write_paths",
        "matches blocked_paths policy",
        "Symlink inputs are not allowed",
    )
    if (not result.success) and any(
        phrase in result.error for phrase in _GUARDRAIL_PHRASES
    ):
        run_type = "safety_test"
        operational_success = True
    registry.set_last_run(
        slug,
        success=result.success,
        run_type=run_type,
        operational_success=operational_success,
    )

    if result.success:
        console.print(result.output)
    else:
        err_console.print(f"[red]Error (exit {result.exit_code}):[/] {result.error}")
        # Clamp to a positive exit code — sandbox_runner uses -1 for timeout/
        # docker failures, which maps to 255 on Unix and confuses callers.
        sys.exit(result.exit_code if result.exit_code > 0 else 1)


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
        sys.stdout.flush()
        sys.stderr.flush()
        return

    table = Table(title="Registered Tools", show_header=True)
    table.add_column("Slug")
    table.add_column("Name")
    table.add_column("Version")
    table.add_column("Tags")

    for s in tools:
        table.add_row(s.slug, s.name, s.version, ", ".join(s.tags))
    console.print(table)
    sys.stdout.flush()
    sys.stderr.flush()


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
        sys.stdout.flush()
        sys.stderr.flush()
        return

    for s in tools:
        console.print(f"  [cyan]{s.slug}[/]  {s.description}")
    sys.stdout.flush()
    sys.stderr.flush()


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
        sys.stdout.flush()
        sys.stderr.flush()
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
    sys.stdout.flush()
    sys.stderr.flush()
    # Explicit exit ensures the subprocess terminates cleanly regardless of
    # any Python atexit / Rich console cleanup that might stall on a pipe.
    sys.exit(0)


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

    from packages.core.repo_hygiene import scan_repo_hygiene

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

    workspace_root = _find_workspace_root()
    hygiene_root = workspace_root / "ToolForge" if (workspace_root / "ToolForge").exists() else workspace_root
    hygiene_report = scan_repo_hygiene(hygiene_root)
    if hygiene_report.has_issues:
        all_ok = False
        console.print("  [red]✗[/] repository hygiene")
        for issue in hygiene_report.issues:
            location = f" {issue.path}"
            if issue.line is not None:
                location += f":{issue.line}"
            console.print(f"    [red]{issue.kind}:{location}[/] {issue.message}")
    else:
        console.print("  [green]✓[/] repository hygiene")
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
