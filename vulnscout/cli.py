#!/usr/bin/env python3
"""VulnScout CLI — AI-powered code vulnerability scanner."""
from __future__ import annotations
import json, sys, traceback
from pathlib import Path
import click
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from vulnscout import __version__
from vulnscout.core.config import settings
from vulnscout.core.detector import detect_hardware
from vulnscout.core.model_manager import ModelManager

console = Console()

@click.group()
@click.version_option(version=__version__, prog_name="vulnscout")
def cli():
    """VulnScout: AI-Powered Vulnerability Code Audit Assistant."""
    pass

# ── Scan ──
@cli.command()
@click.argument("path", required=True)
@click.option("--format", "-f", "output_format", type=click.Choice(["json", "sarif", "markdown"]), default="json", help="Report format (default: json). Choices: json (machine), sarif (CodeQL), markdown (human).")
@click.option("--output", "-o", type=click.Path(), help="Save report to file (e.g. --format sarif --output results.sarif).")
@click.option("--auto-fix", is_flag=True, help="Automatically generate fix patches.")
@click.option("--lang", multiple=True, type=click.Choice(["python", "javascript", "typescript", "java", "c", "cpp"]), help="Target languages.")
@click.option("--severity", type=click.Choice(["critical", "high", "medium", "low"]), help="Minimum severity.")
def scan(path, output_format, output, auto_fix, lang, severity):
    """Scan code for vulnerabilities. PATH can be a directory, GitHub URL, or ZIP."""
    from vulnscout.models.db import init_db, SessionLocal
    from vulnscout.models.schemas import Scan, ScanStatus, SourceType, Vulnerability
    from vulnscout.scanner.code_fetcher import CodeFetcher
    from vulnscout.scanner.pipeline import ScanPipeline
    from vulnscout.utils.report_formatter import format_report
    init_db()
    db = SessionLocal()
    path_lower = path.lower()
    source_type = SourceType.URL if (path_lower.startswith("http://") or path_lower.startswith("https://")) else SourceType.LOCAL
    source_path = path
    click.echo(f"VulnScout v{__version__}")
    click.echo(f"   Scanning: {path}")
    scan = Scan(source_type=source_type, source_path=source_path)
    db.add(scan)
    db.commit()
    db.refresh(scan)
    fetcher = CodeFetcher()
    try:
        if source_type == SourceType.URL:
            click.echo("   Cloning repository...")
            source_dir = str(fetcher.fetch_github(source_path))
        elif path.endswith(".zip"):
            click.echo("   Extracting ZIP file...")
            source_dir = str(fetcher.fetch_zip(Path(path).read_bytes()))
        else:
            if not Path(path).exists():
                click.echo(f"Error: Path not found: {path}", err=True)
                sys.exit(1)
            source_dir = path
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        scan.status = ScanStatus.FAILED
        db.commit()
        sys.exit(1)
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task("Scanning code...", total=None)
        class CliProgress:
            def on_progress(self, percent, current_file=None):
                progress.update(task, description=f"Scanning: {current_file or '...'} ({percent:.0f}%)")
            def on_vuln_found(self, file, severity, title): pass
            def on_file_done(self, file, vuln_count): pass
            def on_scan_done(self, total_vulns, duration):
                progress.update(task, description=f"Done! Found {total_vulns} vulnerabilities in {duration:.1f}s")
        pipeline = ScanPipeline(db, CliProgress())
        try:
            pipeline.run(scan, source_dir)
        except Exception as e:
            click.echo(f"\nError during scan: {e}", err=True)
            traceback.print_exc()
            scan.status = ScanStatus.FAILED
            db.commit()
            sys.exit(1)
        finally:
            fetcher.cleanup()
    vulns = db.query(Vulnerability).filter(Vulnerability.scan_id == scan.id).all()
    if vulns:
        table = Table(title=f"Found {len(vulns)} Vulnerabilities")
        table.add_column("Severity", style="bold")
        table.add_column("File", style="cyan")
        table.add_column("Line", style="yellow")
        table.add_column("Title", style="white")
        for v in vulns:
            sev_style = {"critical": "red", "high": "orange1", "medium": "yellow", "low": "white"}
            table.add_row(f"[{sev_style.get(v.severity, 'white')}]{v.severity.upper()}[/]", v.file_path, str(v.line_start or ""), v.title or "")
        console.print(table)
    content, media_type = format_report(scan, vulns, output_format)
    if output:
        Path(output).write_text(content)
        click.echo(f"Report saved to: {output}")
    else:
        if output_format == "markdown":
            console.print(Markdown(content))
        else:
            click.echo(content)
    db.close()

# ── Config ──
@cli.group()
def config():
    """Manage VulnScout configuration."""
    pass

@config.command("init")
def config_init():
    """Create default configuration file."""
    from shutil import copyfile
    env_example = Path(__file__).parent.parent / ".env.example"
    env_path = Path(".env")
    if env_path.exists():
        click.echo(".env already exists.")
        return
    if env_example.exists():
        copyfile(str(env_example), str(env_path))
        click.echo("Created .env with default configuration.")
    else:
        click.echo("Example config not found.", err=True)
        sys.exit(1)

@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key, value):
    """Set a configuration value."""
    env_path = Path(".env")
    if not env_path.exists():
        click.echo("No .env file found. Run `vulnscout config init` first.", err=True)
        sys.exit(1)
    content = env_path.read_text()
    lines = content.split("\n")
    found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            found = True
            break
    if not found:
        lines.append(f"{key}={value}")
        click.echo(f"Added new config key: {key}")
    env_path.write_text("\n".join(lines))
    click.echo(f"Set {key}={value}")

@config.command("show")
def config_show():
    """Show all current configuration values."""
    env_path = Path(".env")
    env_vars = {}
    if env_path.exists():
        for line in env_path.read_text().split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env_vars[k.strip()] = v.strip()
    table = Table(title="VulnScout Configuration")
    table.add_column("Key", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")
    table.add_column("Source", style="yellow")
    config_map = {
        "MODEL_PROVIDER": settings.model_provider.value,
        "MODEL_NAME": settings.model_name,
        "OPENAI_BASE_URL": settings.openai_base_url,
        "OPENAI_API_KEY": "[set]" if settings.openai_api_key else "[not set]",
        "OLLAMA_API_URL": settings.ollama_api_url,
        "DATABASE_URL": settings.database_url,
        "GITHUB_TOKEN": "[set]" if settings.github_token else "[not set]",
        "LANGUAGE": settings.language,
    }
    for key, val in config_map.items():
        source = ".env" if key in env_vars else "default"
        display = val
        if key == "OPENAI_API_KEY" and val not in ("[set]", "[not set]") and len(val) > 8:
            display = val[:8] + "..."
        elif key == "GITHUB_TOKEN" and val not in ("[set]", "[not set]") and len(val) > 8:
            display = val[:8] + "..."
        table.add_row(key, display, source)
    console.print(table)

# ── Patch ──
@cli.group()
def patch():
    """Manage fix patches."""
    pass

@patch.command("apply")
@click.argument("vuln_id")
def patch_apply(vuln_id):
    """Apply a fix patch for a vulnerability."""
    from vulnscout.models.db import init_db, SessionLocal
    from vulnscout.models.schemas import Patch, PatchStatus
    init_db()
    db = SessionLocal()
    patch = db.query(Patch).filter(Patch.vuln_id == vuln_id).first()
    if not patch:
        click.echo(f"No patch found for vulnerability: {vuln_id}.", err=True)
        sys.exit(1)
    patch.status = PatchStatus.APPLIED
    db.commit()
    click.echo(f"Patch applied.\n\nDiff:\n{patch.diff_content}")
    db.close()

@patch.command("apply-all")
@click.argument("scan_id")
def patch_apply_all(scan_id):
    """Apply all patches for a scan."""
    from vulnscout.models.db import init_db, SessionLocal
    from vulnscout.models.schemas import Patch, PatchStatus, Vulnerability
    init_db()
    db = SessionLocal()
    patches = db.query(Patch).join(Vulnerability).filter(Vulnerability.scan_id == scan_id).all()
    if not patches:
        click.echo("No patches found.")
        return
    for p in patches:
        p.status = PatchStatus.APPLIED
    db.commit()
    click.echo(f"Applied {len(patches)} patches.")
    db.close()

# ── Doctor ──
@cli.command()
def doctor():
    """Diagnose the environment."""
    click.echo(f"VulnScout v{__version__}\n")
    hw = detect_hardware()
    click.echo("Hardware:")
    click.echo(f"  GPU: {hw.gpu_name if hw.has_gpu else 'Not detected (CPU mode)'}")
    click.echo(f"  VRAM: {hw.total_vram_mb}MB ({hw.gpu_count} GPU(s))")
    click.echo(f"  Recommended model: {hw.recommended_model}")
    if hw.warnings:
        click.echo("")
        click.echo("Warnings:")
        for w in hw.warnings:
            click.echo(f"  [!] {w}")
    click.echo("")
    click.echo("Model Provider:")
    click.echo(f"  Provider: {settings.model_provider.value}")
    click.echo(f"  Model: {settings.model_name}")
    if settings.is_cloud:
        click.echo(f"  API: {settings.openai_base_url}")
        click.echo(f"  API Key: {'[set]' if settings.openai_api_key else '[not set]'}")
    if settings.is_ollama:
        click.echo("")
        mm = ModelManager()
        click.echo("Ollama:")
        click.echo(f"  Installed: {'Yes' if mm.is_ollama_installed() else 'No'}")
        if mm.is_ollama_installed():
            click.echo(f"  Running: {'Yes' if mm.is_ollama_running() else 'No'}")
            if mm.is_ollama_running():
                pulled = mm.list_downloaded_models()
                if pulled:
                    click.echo("  Models pulled:")
                    for m in pulled:
                        click.echo(f"    [downloaded] {m}")
                else:
                    click.echo("  No models pulled. Run `vulnscout model download`.")
    click.echo("")
    deps = [("fastapi", "fastapi"), ("sqlalchemy", "sqlalchemy"), ("click", "click"), ("gitpython", "git"), ("openai", "openai")]
    click.echo("Dependencies:")
    for name, mod in deps:
        try:
            __import__(mod)
            click.echo(f"  [x] {name}")
        except ImportError:
            click.echo(f"  [ ] {name} (missing)")

# ── Model ──
@cli.group()
def model():
    """Manage AI models."""
    pass

@model.command("list")
def model_list():
    """List all available models with setup instructions."""
    mm = ModelManager()
    available = mm.get_actually_available_models()

    # Local / downloaded models
    table = Table(title="Local Models (Ollama)")
    table.add_column("Status", style="bold")
    table.add_column("Model", style="cyan")
    table.add_column("Size")
    table.add_column("Description", style="white")
    for m in available["local"]:
        table.add_row("[green]downloaded[/]", m["name"], f"{m['size_gb']}GB" if m["size_gb"] else "?", m["description"])
    for m in available["downloadable"]:
        status = "[yellow]available[/]"
        table.add_row(status, m["name"], f"{m['size_gb']}GB" if m["size_gb"] else "?", m["description"])
    if not available["local"] and not available["downloadable"]:
        table.add_row("[dim]—[/]", "[dim]No models found[/]", "", "")
    console.print(table)

    # Cloud models
    if available["cloud"]:
        table2 = Table(title="Cloud Models (configured)")
        table2.add_column("Model", style="cyan")
        table2.add_column("Provider", style="green")
        table2.add_column("Description", style="white")
        for m in available["cloud"]:
            table2.add_row(m["name"], m["provider"], m["description"])
        console.print(table2)

    click.echo("")
    click.echo(f"Active model: {settings.model_name} ({settings.model_provider.value})")
    if settings.is_cloud:
        click.echo(f"  API: {settings.openai_base_url}")
    if available["cloud_configured"]:
        click.echo("  [green]Cloud API: connected[/]")
    elif settings.openai_api_key:
        click.echo("  [yellow]Cloud API key set but unreachable[/]")
    else:
        click.echo("  [dim]Cloud API: not configured[/]")
    click.echo("")
    click.echo("Quick switch:  vulnscout model use <model-name>")

@model.command("download")
@click.argument("model_name", required=False)
@click.option("--mirror", is_flag=True, help="Use ModelScope mirror (China).")
def model_download(model_name, mirror):
    """Download an AI model."""
    mm = ModelManager()
    model_name = mm.resolve_model(model_name)
    if mm.is_downloaded(model_name):
        click.echo(f"Model already downloaded: {model_name}")
        return
    click.echo(f"Pulling {model_name} via Ollama...")
    try:
        tag = mm.download_model(model_name, use_mirror=mirror)
        click.echo(f"Model ready: {tag}")
    except Exception as e:
        click.echo(f"Download failed: {e}", err=True)
        sys.exit(1)

@model.command("status")
def model_status():
    """Show current model status."""
    click.echo(f"Provider: {settings.model_provider.value}")
    click.echo(f"Model: {settings.model_name}")
    if settings.is_cloud:
        click.echo(f"API: {settings.openai_base_url}")
    click.echo("")
    mm = ModelManager()
    hw = detect_hardware()
    click.echo(f"Recommended (local): {hw.recommended_model}")

@model.command("use")
@click.argument("model_name")
def model_use(model_name):
    """Switch to a different model."""
    env_path = Path(".env")
    if not env_path.exists():
        click.echo("No .env file found. Run `vulnscout config init` first.", err=True)
        sys.exit(1)

    # Dynamically determine provider
    mm = ModelManager()
    available = mm.get_actually_available_models()

    is_ollama_model = any(
        m["name"] == model_name for m in available["local"] + available["downloadable"]
    )
    is_cloud_model = any(m["name"] == model_name for m in available["cloud"])

    if is_ollama_model:
        provider = "ollama"
    elif is_cloud_model:
        provider = "openai"
    else:
        provider = "custom"

    content = env_path.read_text()
    lines = content.split("\n")
    found_name = found_prov = False
    for i, line in enumerate(lines):
        if line.startswith("MODEL_NAME="):
            lines[i] = f"MODEL_NAME={model_name}"
            found_name = True
        elif line.startswith("MODEL_PROVIDER="):
            lines[i] = f"MODEL_PROVIDER={provider}"
            found_prov = True
    if not found_name:
        lines.append(f"MODEL_NAME={model_name}")
    if not found_prov:
        lines.append(f"MODEL_PROVIDER={provider}")
    env_path.write_text("\n".join(lines))
    click.echo(f"Switched to: {model_name} ({provider})")
    click.echo("Run `vulnscout config show` to verify.")

# ── GitHub ──
@cli.group()
def github():
    """Manage GitHub issues and pull requests."""
    pass

@github.command("issue")
@click.argument("scan_id")
@click.option("--repo", "-r", help="GitHub repo.")
@click.option("--severity", type=click.Choice(["critical", "high", "medium", "low"]), help="Minimum severity.")
def github_issue(scan_id, repo, severity):
    """Create GitHub issues for vulnerabilities."""
    from vulnscout.models.db import init_db, SessionLocal
    from vulnscout.models.schemas import Scan, Vulnerability
    from vulnscout.utils.github_integration import create_issue
    init_db()
    db = SessionLocal()
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        click.echo(f"Scan not found: {scan_id}", err=True)
        sys.exit(1)
    repo = repo or scan.source_path
    query = db.query(Vulnerability).filter(Vulnerability.scan_id == scan_id)
    if severity:
        order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        query = query.filter(Vulnerability.severity.in_([s for s in order if order[s] <= order[severity]]))
    vulns = query.all()
    if not vulns:
        click.echo("No vulnerabilities to report.")
        return
    click.echo(f"Creating {len(vulns)} issue(s) in {repo}...")
    for v in vulns:
        body = f"## {v.title}\n\n- **Severity:** {v.severity}\n- **CWE:** {v.cwe_id or 'N/A'}\n- **File:** `{v.file_path}:{v.line_start or ''}`\n\n### Description\n{v.description or 'No description.'}\n"
        if v.vulnerable_code:
            body += f"### Vulnerable Code\n```\n{v.vulnerable_code[:1000]}\n```\n"
        patches = v.patches
        if patches:
            body += "### Fix\n```diff\n" + patches[0].diff_content[:1000] + "\n```\n"
        try:
            result = create_issue(repo, f"[VulnScout] {v.title}", body, labels=["security"])
            click.echo(f"  Created issue #{result['number']}: {result['html_url']}")
        except Exception as e:
            click.echo(f"  Failed: {e}", err=True)
    db.close()

@github.command("pr")
@click.argument("scan_id")
@click.option("--repo", "-r", help="GitHub repo.")
@click.option("--branch", "-b", default="vulnscout-fix", help="Branch name.")
@click.option("--base", default="main", help="Base branch.")
def github_pr(scan_id, repo, branch, base):
    """Create a GitHub PR with fix patches."""
    from vulnscout.models.db import init_db, SessionLocal
    from vulnscout.models.schemas import Scan, Patch, Vulnerability
    from vulnscout.utils.github_integration import create_pr
    init_db()
    db = SessionLocal()
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        click.echo(f"Scan not found: {scan_id}", err=True)
        sys.exit(1)
    repo = repo or scan.source_path
    patches = db.query(Patch).join(Vulnerability).filter(Vulnerability.scan_id == scan_id, Patch.status == "draft").all()
    if not patches:
        click.echo("No fix patches found.")
        return
    click.echo(f"Creating PR with {len(patches)} fix(es) in {repo}...")
    all_diffs = "\n".join(p.diff_content or "" for p in patches if p.diff_content)
    summary = "\n".join(f"- {p.vulnerability.title} ({p.vulnerability.severity})" for p in patches[:10])
    try:
        result = create_pr(repo_path=repo, branch_name=branch, diff_content=all_diffs,
            commit_message="fix: apply VulnScout security fixes",
            pr_title=f"[VulnScout] Security fixes ({len(patches)} vulnerabilities)",
            pr_body=f"## Automated Security Fixes\n\nThis PR was automatically generated by VulnScout.\n\n{summary}", base_branch=base)
        click.echo(f"  PR created: {result.get('html_url', '')}")
    except Exception as e:
        click.echo(f"  Failed: {e}", err=True)
    db.close()

# ── Uninstall ──
@cli.command()
def uninstall():
    """Completely remove VulnScout."""
    import shutil
    from pathlib import Path
    found = []
    try:
        import subprocess as sp
        r = sp.run(["pip", "show", "vulnscout"], capture_output=True, text=True)
        found.append("Python package") if r.returncode == 0 else None
    except Exception:
        pass
    config_locations = [Path.cwd(), Path.home()]
    dotenv_paths = list(dict.fromkeys(p / ".env" for p in config_locations if (p / ".env").exists()))
    db_paths = list(dict.fromkeys(p / "vulnscout.db" for p in config_locations if (p / "vulnscout.db").exists()))
    model_dir = Path.home() / ".vulnscout"
    try:
        import vulnscout as v
        src = Path(v.__file__).resolve().parent.parent
        if (src / "pyproject.toml").exists():
            found.append(f"Source ({src.name})")
    except Exception:
        pass
    click.echo("Found the following VulnScout files:")
    if "Python package" in found:
        click.echo("  - Python package (vulnscout)")
    for p in dotenv_paths:
        click.echo(f"  - Config file ({p})")
    for p in db_paths:
        click.echo(f"  - Database ({p})")
    if model_dir.exists():
        click.echo(f"  - AI models ({model_dir})")
    click.confirm("\nDelete all of the above?", abort=True)
    removed = []
    try:
        sp.run(["pip", "uninstall", "vulnscout", "-y"], capture_output=True)
        removed.append("Python package")
    except Exception:
        pass
    for p in dotenv_paths:
        try:
            p.unlink()
            removed.append(f"Config ({p.name})")
        except Exception:
            pass
    for p in db_paths:
        try:
            p.unlink()
            removed.append(f"Database ({p.name})")
        except Exception:
            pass
    if model_dir.exists():
        try:
            shutil.rmtree(model_dir)
            removed.append("AI models (~/.vulnscout)")
        except Exception:
            pass
    if removed:
        click.echo("\nRemoved:")
        for item in removed:
            click.echo(f"  - {item}")
        click.echo("\nVulnScout has been completely uninstalled.")
    else:
        click.echo("\nNothing to remove.")

if __name__ == "__main__":
    cli()
