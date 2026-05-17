#!/usr/bin/env python3
"""VulnScout CLI — AI-powered code vulnerability scanner."""

from __future__ import annotations

import json
import sys
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
    """VulnScout: AI-Powered Vulnerability Code Audit Assistant.

    Scan local code, GitHub repositories, or ZIP files for security vulnerabilities
    using locally deployed DeepSeek-Coder. Get detailed reports and auto-generated fixes.
    """
    pass


# ── Scan Command ───────────────────────────────────────────────────────

@cli.command()
@click.argument("path", required=True)
@click.option("--format", "-f", "output_format", type=click.Choice(["json", "sarif", "markdown"]), default="json",
              help="Report format (default: json). Choices: json (machine), sarif (CodeQL), markdown (human).")
@click.option("--output", "-o", type=click.Path(),
              help="Save report to file (e.g. --format sarif --output results.sarif).")
@click.option("--auto-fix", is_flag=True, help="Automatically generate fix patches for all vulnerabilities.")
@click.option("--lang", multiple=True, type=click.Choice(["python", "javascript", "typescript", "java", "c", "cpp"]), help="Target languages to scan. Default: all supported.")
@click.option("--severity", type=click.Choice(["critical", "high", "medium", "low"]), help="Minimum severity to report.")
def scan(path, output_format, output, auto_fix, lang, severity):
    """Scan code for vulnerabilities.

    PATH can be a local directory, a GitHub repository URL, or a ZIP file path.
    """
    from vulnscout.models.db import init_db, SessionLocal
    from vulnscout.models.schemas import Scan, ScanStatus, SourceType, Vulnerability
    from vulnscout.scanner.code_fetcher import CodeFetcher
    from vulnscout.scanner.pipeline import ScanPipeline
    from vulnscout.utils.report_formatter import format_report

    init_db()
    db = SessionLocal()

    # Detect source type
    path_lower = path.lower()
    if path_lower.startswith("http://") or path_lower.startswith("https://"):
        source_type = SourceType.URL
        source_path = path
    elif path.endswith(".zip"):
        source_type = SourceType.LOCAL
        source_path = path
    else:
        source_type = SourceType.LOCAL
        source_path = path

    click.echo(f"VulnScout v{__version__}")
    click.echo(f"   Scanning: {path}")

    # Create scan record
    scan = Scan(source_type=source_type, source_path=source_path)
    db.add(scan)
    db.commit()
    db.refresh(scan)

    # Fetch code
    fetcher = CodeFetcher()
    try:
        if source_type == SourceType.URL:
            click.echo("   Cloning repository...")
            source_dir = str(fetcher.fetch_github(source_path))
        elif path.endswith(".zip"):
            click.echo("   Extracting ZIP file...")
            zip_data = Path(path).read_bytes()
            source_dir = str(fetcher.fetch_zip(zip_data))
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

    # Run pipeline with progress
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Scanning code...", total=None)

        class CliProgress:
            def on_progress(self, percent, current_file=None):
                progress.update(task, description=f"Scanning: {current_file or '...'} ({percent:.0f}%)")
            def on_vuln_found(self, file, severity, title):
                pass
            def on_file_done(self, file, vuln_count):
                pass
            def on_scan_done(self, total_vulns, duration):
                progress.update(task, description=f"Done! Found {total_vulns} vulnerabilities in {duration:.1f}s")

        pipeline = ScanPipeline(db, CliProgress())

        try:
            pipeline.run(scan, source_dir)
        except Exception as e:
            import traceback
            click.echo(f"\nError during scan: {e}", err=True)
            traceback.print_exc()
            scan.status = ScanStatus.FAILED
            db.commit()
            sys.exit(1)
        finally:
            fetcher.cleanup()

    # Fetch results
    vulns = db.query(Vulnerability).filter(Vulnerability.scan_id == scan.id).all()

    if vulns:
        table = Table(title=f"Found {len(vulns)} Vulnerabilities")
        table.add_column("Severity", style="bold")
        table.add_column("File", style="cyan")
        table.add_column("Line", style="yellow")
        table.add_column("Title", style="white")

        for v in vulns:
            sev_style = {"critical": "red", "high": "orange1", "medium": "yellow", "low": "white"}
            table.add_row(
                f"[{sev_style.get(v.severity, 'white')}]{v.severity.upper()}[/]",
                v.file_path,
                str(v.line_start or ""),
                v.title or "",
            )
        console.print(table)

    # Output
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


# ── Config Command ─────────────────────────────────────────────────────

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


# ── Patch Commands ─────────────────────────────────────────────────────

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
    click.echo(f"Patch applied.")
    click.echo(f"\nDiff:\n{patch.diff_content}")

    db.close()


@patch.command("apply-all")
@click.argument("scan_id")
def patch_apply_all(scan_id):
    """Apply all patches for a scan."""
    from vulnscout.models.db import init_db, SessionLocal
    from vulnscout.models.schemas import Patch, PatchStatus, Vulnerability

    init_db()
    db = SessionLocal()

    patches = (
        db.query(Patch)
        .join(Vulnerability)
        .filter(Vulnerability.scan_id == scan_id)
        .all()
    )

    if not patches:
        click.echo("No patches found.")
        return

    count = 0
    for p in patches:
        p.status = PatchStatus.APPLIED
        count += 1

    db.commit()
    click.echo(f"Applied {count} patches.")
    db.close()


# ── Doctor Command ─────────────────────────────────────────────────────

@cli.command()
def doctor():
    """Diagnose the environment."""
    click.echo(f"VulnScout v{__version__}")
    click.echo("")

    hw = detect_hardware()
    click.echo("Hardware:")
    click.echo(f"  GPU: {hw.gpu_name if hw.has_gpu else 'Not detected (CPU mode)'}")
    click.echo(f"  VRAM: {hw.total_vram_mb}MB ({hw.gpu_count} GPU(s))")
    click.echo(f"  Recommended model: {hw.recommended_model}")
    click.echo(f"  Recommended backend: {hw.recommended_backend}")

    if hw.warnings:
        click.echo("")
        click.echo("Warnings:")
        for w in hw.warnings:
            click.echo(f"  [!] {w}")

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
                    click.echo(f"    [x] {m}")
            else:
                click.echo("  No models pulled. Run `vulnscout model download`.")

    click.echo("")
    deps = [
        ("fastapi", "fastapi"),
        ("sqlalchemy", "sqlalchemy"),
        ("click", "click"),
        ("gitpython", "git"),
        ("openai", "openai"),
    ]
    click.echo("Dependencies:")
    for name, mod in deps:
        try:
            __import__(mod)
            click.echo(f"  [x] {name}")
        except ImportError:
            click.echo(f"  [ ] {name} (missing)")


# ── Model Commands ─────────────────────────────────────────────────────

@cli.group()
def model():
    """Manage AI models."""
    pass


@model.command("list")
def model_list():
    """List available and downloaded models."""
    mm = ModelManager()

    click.echo("Available models:")
    for m in mm.list_available_models():
        status = "x" if mm.is_downloaded(m["name"]) else " "
        click.echo(f"  [{status}] {m['name']} ({m['size_gb']}GB)")

    click.echo("")
    click.echo("Pull a model: vulnscout model download <model-name>")


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
    click.echo(f"Current model: {settings.model_name}")
    click.echo(f"Backend: {settings.model_backend}")

    mm = ModelManager()
    hw = detect_hardware()
    click.echo(f"Recommended: {hw.recommended_model} ({hw.recommended_backend})")


# ── GitHub Commands ────────────────────────────────────────────────────

@cli.group()
def github():
    """Manage GitHub issues and pull requests."""
    pass


@github.command("issue")
@click.argument("scan_id")
@click.option("--repo", "-r", help="GitHub repo (owner/repo). Defaults to scan source.")
@click.option("--severity", type=click.Choice(["critical", "high", "medium", "low"]), help="Minimum severity.")
def github_issue(scan_id, repo, severity):
    """Create GitHub issues for vulnerabilities found in a scan."""
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
        body = (
            f"## {v.title}\n\n"
            f"- **Severity:** {v.severity}\n"
            f"- **CWE:** {v.cwe_id or 'N/A'}\n"
            f"- **File:** `{v.file_path}:{v.line_start or ''}`\n\n"
            f"### Description\n{v.description or 'No description.'}\n\n"
        )
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
@click.option("--repo", "-r", help="GitHub repo (owner/repo). Defaults to scan source.")
@click.option("--branch", "-b", default="vulnscout-fix", help="Branch name for the PR.")
@click.option("--base", default="main", help="Base branch for the PR.")
def github_pr(scan_id, repo, branch, base):
    """Create a GitHub PR with auto-generated fix patches."""
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
    patches = (
        db.query(Patch)
        .join(Vulnerability)
        .filter(Vulnerability.scan_id == scan_id, Patch.status == "draft")
        .all()
    )

    if not patches:
        click.echo("No fix patches found for this scan.")
        return

    click.echo(f"Creating PR with {len(patches)} fix(es) in {repo}...")

    # Aggregate all diffs into one
    all_diffs = "\n".join(p.diff_content or "" for p in patches if p.diff_content)
    vuln_summary = "\n".join(f"- {p.vulnerability.title} ({p.vulnerability.severity})" for p in patches[:10])

    try:
        result = create_pr(
            repo_path=repo,
            branch_name=branch,
            diff_content=all_diffs,
            commit_message="fix: apply VulnScout security fixes",
            pr_title=f"[VulnScout] Security fixes ({len(patches)} vulnerabilities)",
            pr_body=f"## Automated Security Fixes\n\nThis PR was automatically generated by VulnScout.\n\n{vuln_summary}",
            base_branch=base,
        )
        click.echo(f"  PR created: {result.get('html_url', '')}")
    except Exception as e:
        click.echo(f"  Failed: {e}", err=True)

    db.close()


# ── Uninstall Command ──────────────────────────────────────────────────

@cli.command()
def uninstall():
    """Completely remove VulnScout (package + config + models + database)."""
    import shutil
    from pathlib import Path

    click.confirm("This will delete ALL VulnScout data:\n"
                  "  - Python package\n"
                  "  - Database file\n"
                  "  - Config file (.env)\n"
                  "  - Downloaded AI models\n"
                  "  - Scan cache\n"
                  "Continue?", abort=True)

    removed = []

    # 1. Uninstall Python package
    try:
        import subprocess
        subprocess.run(["pip", "uninstall", "vulnscout", "-y"],
                       capture_output=True)
        removed.append("Python package")
    except Exception:
        pass

    # 2. Remove database
    db_path = Path.cwd() / "vulnscout.db"
    if db_path.exists():
        db_path.unlink()
        removed.append("Database (vulnscout.db)")

    # 3. Remove .env
    env_path = Path.cwd() / ".env"
    if env_path.exists():
        env_path.unlink()
        removed.append("Config file (.env)")

    # 4. Remove model cache
    model_dir = Path.home() / ".vulnscout"
    if model_dir.exists():
        shutil.rmtree(model_dir)
        removed.append("AI models (~/.vulnscout)")

    # 5. Remove SQLite DB in home
    home_db = Path.home() / ".vulnscout" / "vulnscout.db"
    if home_db.exists():
        home_db.unlink()

    if removed:
        click.echo("Removed:")
        for item in removed:
            click.echo(f"  - {item}")
        click.echo("VulnScout has been completely uninstalled.")
    else:
        click.echo("Nothing to remove. VulnScout is not installed.")


if __name__ == "__main__":
    cli()
