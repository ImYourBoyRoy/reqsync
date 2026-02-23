# ./src/reqsync/mcp_server.py
"""Built-in MCP server for reqsync automation.

Run as `reqsync mcp` or `reqsync-mcp` to expose reqsync as MCP tools over stdio
(or alternate FastMCP transports). Inputs are plain tool parameters and outputs
are structured JSON payloads suitable for local AI model clients.
"""

from __future__ import annotations

import importlib
from typing import Any, TypedDict

from ._types import ExitCode, JsonResult
from .api import run_sync_payload
from .errors import ReqsyncError

FastMCP: Any
_MCP_IMPORT_ERROR: Exception | None
try:
    _fastmcp_module = importlib.import_module("mcp.server.fastmcp")
except Exception as exc:  # pragma: no cover - import guarded at runtime
    FastMCP = None
    _MCP_IMPORT_ERROR = exc
else:
    FastMCP = _fastmcp_module.FastMCP
    _MCP_IMPORT_ERROR = None


class McpToolResult(TypedDict):
    ok: bool
    exit_code: int
    error: str | None
    result: JsonResult | None


def _server() -> Any:
    if FastMCP is None:
        raise RuntimeError(
            "MCP support requires the `mcp` package. Install optional extras: `pip install reqsync[mcp]`."
        ) from _MCP_IMPORT_ERROR

    mcp = FastMCP("reqsync")

    @mcp.tool(name="reqsync_sync", description="Sync requirement files to installed versions.")
    def reqsync_sync(
        path: str = "requirements.txt",
        dry_run: bool = True,
        check: bool = False,
        show_diff: bool = True,
        no_upgrade: bool = True,
        policy: str = "lower-bound",
        follow_includes: bool = True,
        update_constraints: bool = False,
        allow_prerelease: bool = False,
        keep_local: bool = False,
        allow_hashes: bool = False,
        system_ok: bool = False,
        allow_dirty: bool = True,
        pip_args: str = "",
        pip_timeout_sec: int = 900,
    ) -> McpToolResult:
        payload: dict[str, Any] = {
            "path": path,
            "dry_run": dry_run,
            "check": check,
            "show_diff": show_diff,
            "no_upgrade": no_upgrade,
            "policy": policy,
            "follow_includes": follow_includes,
            "update_constraints": update_constraints,
            "allow_prerelease": allow_prerelease,
            "keep_local": keep_local,
            "allow_hashes": allow_hashes,
            "system_ok": system_ok,
            "allow_dirty": allow_dirty,
            "pip_args": pip_args,
            "pip_timeout_sec": pip_timeout_sec,
        }

        try:
            result = run_sync_payload(payload)
            return {"ok": True, "exit_code": int(ExitCode.OK), "error": None, "result": result}
        except ReqsyncError as error:
            return {"ok": False, "exit_code": int(error.exit_code), "error": str(error), "result": None}
        except Exception as error:
            return {
                "ok": False,
                "exit_code": int(ExitCode.GENERIC_ERROR),
                "error": str(error),
                "result": None,
            }

    return mcp


def serve_mcp(transport: str = "stdio") -> None:
    """Start reqsync MCP server using the requested FastMCP transport."""

    server = _server()
    server.run(transport=transport)


def main() -> None:
    serve_mcp("stdio")


__all__ = ["main", "serve_mcp"]
