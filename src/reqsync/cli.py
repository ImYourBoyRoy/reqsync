# ./src/reqsync/cli.py
"""Command-line entrypoints for reqsync and built-in MCP serving.

Primary usage is `reqsync run ...` for synchronization workflows and
`reqsync mcp` for local AI model integrations. CLI arguments override optional
project config files and can emit either human summaries or JSON payloads.
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import typer
from click.core import ParameterSource

from . import __version__
from ._logging import setup_logging
from ._types import ExitCode, JsonResult, Options
from .config import load_project_config, merge_options
from .core import sync
from .errors import ReqsyncError
from .report import result_to_json, write_json_report


class PolicyEnum(str, Enum):
    LOWER_BOUND = "lower-bound"
    FLOOR_ONLY = "floor-only"
    FLOOR_AND_CAP = "floor-and-cap"
    UPDATE_IN_PLACE = "update-in-place"


class TransportEnum(str, Enum):
    STDIO = "stdio"
    SSE = "sse"
    STREAMABLE_HTTP = "streamable-http"


class OutputModeEnum(str, Enum):
    HUMAN = "human"
    JSON = "json"
    BOTH = "both"


class HelpTopicEnum(str, Enum):
    ALL = "all"
    RUN = "run"
    VERSION = "version"
    MCP = "mcp"


_ROOT_HELP_EPILOG = """Help tips:
  reqsync run --help
  reqsync mcp --help
  reqsync help all
"""

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Keep requirements files synced to installed versions with safety checks and atomic writes.",
    epilog=_ROOT_HELP_EPILOG,
)

_SUBCOMMAND_HELP_FOOTER = """Other reqsync commands:
  reqsync run [OPTIONS]
  reqsync help [all|run|version|mcp]
  reqsync version
  reqsync mcp [--transport stdio|sse|streamable-http]
"""

_HELP_TEXTS: dict[HelpTopicEnum, str] = {
    HelpTopicEnum.ALL: """reqsync help overview

Top-level commands:
  reqsync run [OPTIONS]
  reqsync help [all|run|version|mcp]
  reqsync version
  reqsync mcp [--transport stdio|sse|streamable-http]

Command-specific help:
  reqsync run --help
  reqsync mcp --help
  reqsync version --help

Common quick starts:
  reqsync run --no-upgrade --dry-run --show-diff
  reqsync run --show-diff
  reqsync run --check --no-upgrade
""",
    HelpTopicEnum.RUN: """reqsync run help

Use:
  reqsync run --help

Common run patterns:
  reqsync run --show-diff
  reqsync run --no-upgrade --dry-run --show-diff
  reqsync run --check --no-upgrade
  reqsync run --output json --no-upgrade --dry-run
""",
    HelpTopicEnum.VERSION: """reqsync version help

Use:
  reqsync version
""",
    HelpTopicEnum.MCP: """reqsync mcp help

Use:
  reqsync mcp --help
  reqsync mcp --transport stdio
  reqsync mcp --transport sse
""",
}


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"reqsync {__version__}")
        raise typer.Exit()


@app.callback()
def app_callback(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        is_eager=True,
        callback=_version_callback,
        help="Show reqsync version and exit.",
    ),
) -> None:
    """Global CLI options for reqsync."""


def _build_options(ctx: typer.Context, use_config: bool) -> Options:
    options = Options(path=Path("requirements.txt"))
    if use_config:
        options = merge_options(options, load_project_config(Path(".").resolve()))

    non_option_keys = {
        "ctx",
        "output",
        "stdout_json",
        "use_config",
    }
    overrides: dict[str, Any] = {}
    for key, value in ctx.params.items():
        if key in non_option_keys:
            continue
        if ctx.get_parameter_source(key) is not ParameterSource.DEFAULT:
            overrides[key] = value

    return merge_options(options, overrides)


def _print_human_summary(payload: JsonResult, options: Options, report_path: Optional[Path]) -> None:
    mode = "apply"
    if options.check:
        mode = "check"
    elif options.dry_run:
        mode = "dry-run"

    files_total = len(payload["files"])
    files_changed = sum(1 for file_row in payload["files"] if file_row["changed"])
    changes_total = len(payload["changes"])

    if payload["changed"]:
        typer.secho(f"reqsync [{mode}] -> changes detected", fg=typer.colors.YELLOW)
    else:
        typer.secho(f"reqsync [{mode}] -> already in sync", fg=typer.colors.GREEN)

    typer.echo(f"files scanned: {files_total} | files changed: {files_changed} | package updates: {changes_total}")

    if changes_total:
        typer.echo("top package updates:")
        preview_limit = 8
        for change in payload["changes"][:preview_limit]:
            file_name = Path(change["file"]).name
            typer.echo(f"  - {change['package']} -> {change['installed_version']} ({file_name})")

        if changes_total > preview_limit:
            typer.echo(f"  ... and {changes_total - preview_limit} more")

    if report_path:
        typer.echo(f"json report written: {report_path}")


def _resolve_output_mode(output: OutputModeEnum, stdout_json: bool) -> OutputModeEnum:
    if stdout_json and output == OutputModeEnum.HUMAN:
        return OutputModeEnum.JSON
    return output


def _emit_result(
    payload: JsonResult,
    result_diff: Optional[str],
    options: Options,
    output_mode: OutputModeEnum,
) -> None:
    report_path: Optional[Path] = None
    if options.json_report:
        report_path = write_json_report(payload, str(options.json_report))

    if output_mode in {OutputModeEnum.HUMAN, OutputModeEnum.BOTH}:
        _print_human_summary(payload=payload, options=options, report_path=report_path)
        if result_diff and (options.show_diff or options.dry_run):
            typer.echo(result_diff)

    if output_mode in {OutputModeEnum.JSON, OutputModeEnum.BOTH}:
        typer.echo(json.dumps(payload, indent=2))


@app.command("run", epilog=_SUBCOMMAND_HELP_FOOTER)
def run_command(
    ctx: typer.Context,
    path: Path = typer.Option(
        Path("requirements.txt"),
        "--path",
        help="Path to requirements file.",
        dir_okay=False,
        rich_help_panel="Target",
    ),
    follow_includes: bool = typer.Option(
        True,
        help="Follow -r includes recursively.",
        rich_help_panel="Target",
    ),
    update_constraints: bool = typer.Option(
        False,
        help="Allow updating files reached through -c/--constraint.",
        rich_help_panel="Target",
    ),
    policy: PolicyEnum = typer.Option(
        PolicyEnum.LOWER_BOUND,
        help="Version rewrite policy.",
        rich_help_panel="Policy",
    ),
    allow_prerelease: bool = typer.Option(
        False,
        help="Adopt pre/dev installed versions.",
        rich_help_panel="Policy",
    ),
    keep_local: bool = typer.Option(
        False,
        help="Keep local version suffixes like +cpu.",
        rich_help_panel="Policy",
    ),
    no_upgrade: bool = typer.Option(
        False,
        help="Skip pip upgrade and rewrite from current env only.",
        rich_help_panel="Execution",
    ),
    pip_timeout_sec: int = typer.Option(
        900,
        help="Timeout for pip upgrade in seconds.",
        rich_help_panel="Execution",
    ),
    pip_args: str = typer.Option(
        "",
        help="Allowlisted pip args passed to upgrade command.",
        rich_help_panel="Execution",
    ),
    only: Optional[str] = typer.Option(
        None,
        help="Comma-separated package globs to include.",
        rich_help_panel="Filtering",
    ),
    exclude: Optional[str] = typer.Option(
        None,
        help="Comma-separated package globs to exclude.",
        rich_help_panel="Filtering",
    ),
    check: bool = typer.Option(
        False,
        help="Exit nonzero when changes would be made.",
        rich_help_panel="Execution",
    ),
    dry_run: bool = typer.Option(
        False,
        help="Preview changes without writing files.",
        rich_help_panel="Execution",
    ),
    show_diff: bool = typer.Option(
        False,
        help="Show unified diff for changed files.",
        rich_help_panel="Output",
    ),
    output: OutputModeEnum = typer.Option(
        OutputModeEnum.HUMAN,
        "--output",
        "-o",
        help="Stdout output mode.",
        rich_help_panel="Output",
    ),
    json_report: Optional[Path] = typer.Option(
        None,
        help="Write machine-readable JSON report to file.",
        rich_help_panel="Output",
    ),
    stdout_json: bool = typer.Option(
        False,
        "--stdout-json",
        help="Deprecated alias for `--output json`.",
        hidden=True,
    ),
    backup_suffix: str = typer.Option(
        ".bak",
        help="Backup file suffix.",
        rich_help_panel="Write Safety",
    ),
    timestamped_backups: bool = typer.Option(
        True,
        help="Use timestamped backup filenames.",
        rich_help_panel="Write Safety",
    ),
    backup_keep_last: int = typer.Option(
        5,
        help="Keep only the newest N timestamped backups per file (0 disables pruning).",
        min=0,
        rich_help_panel="Write Safety",
    ),
    lock_timeout_sec: int = typer.Option(
        15,
        help="Lock acquisition timeout in seconds.",
        rich_help_panel="Write Safety",
    ),
    system_ok: bool = typer.Option(
        False,
        help="Allow running outside a virtualenv.",
        rich_help_panel="Safety",
    ),
    allow_hashes: bool = typer.Option(
        False,
        help="Skip hashed stanzas instead of refusing.",
        rich_help_panel="Safety",
    ),
    allow_dirty: bool = typer.Option(
        True,
        help="Allow running in a dirty git repository.",
        rich_help_panel="Safety",
    ),
    last_wins: bool = typer.Option(
        False,
        help="For duplicate packages, rewrite only final occurrence.",
        rich_help_panel="Safety",
    ),
    log_file: Optional[Path] = typer.Option(
        None,
        help="Optional log file path.",
        rich_help_panel="Logging",
    ),
    verbosity: int = typer.Option(
        0,
        "--verbose",
        "-v",
        count=True,
        help="Increase logging verbosity (-vv for debug).",
        rich_help_panel="Logging",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Reduce logging output.",
        rich_help_panel="Logging",
    ),
    use_config: bool = typer.Option(
        True,
        help="Load reqsync.toml / [tool.reqsync] / reqsync.json.",
        rich_help_panel="Config",
    ),
) -> None:
    """Run synchronization with explicit, script-friendly options."""

    options = _build_options(ctx, use_config=use_config)
    setup_logging(verbosity=options.verbosity, quiet=options.quiet, log_file=options.log_file)

    try:
        result = sync(options)
    except ReqsyncError as error:
        typer.secho(str(error), fg=typer.colors.RED, err=True)
        raise typer.Exit(int(error.exit_code)) from error
    except Exception as error:
        typer.secho(str(error), fg=typer.colors.RED, err=True)
        raise typer.Exit(int(ExitCode.GENERIC_ERROR)) from error

    payload = result_to_json(result)
    output_mode = _resolve_output_mode(output, stdout_json)
    _emit_result(payload=payload, result_diff=result.diff, options=options, output_mode=output_mode)

    if options.check and result.changed:
        raise typer.Exit(int(ExitCode.CHANGES_WOULD_BE_MADE)) from None

    raise typer.Exit(int(ExitCode.OK)) from None


@app.command("help", epilog=_SUBCOMMAND_HELP_FOOTER)
def help_command(
    topic: HelpTopicEnum = typer.Argument(
        HelpTopicEnum.ALL,
        help="Help topic: all, run, version, or mcp.",
    ),
) -> None:
    """Show concise command guidance and discoverability tips."""

    typer.echo(_HELP_TEXTS[topic].strip())


@app.command("version", epilog=_SUBCOMMAND_HELP_FOOTER)
def version_command() -> None:
    """Print installed reqsync version."""

    typer.echo(f"reqsync {__version__}")


@app.command("mcp", epilog=_SUBCOMMAND_HELP_FOOTER)
def mcp_server(
    transport: TransportEnum = typer.Option(TransportEnum.STDIO, help="MCP transport to serve"),
) -> None:
    """Start reqsync MCP server for local AI model clients."""

    from .mcp_server import serve_mcp

    serve_mcp(transport=transport.value)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
