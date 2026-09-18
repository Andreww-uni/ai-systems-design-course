"""Normalized workstation capability report for Laboratory 01."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path

REPORT_SCHEMA_VERSION = "1.0"


def _first_output_line(completed: subprocess.CompletedProcess[str]) -> str:
    output = completed.stdout or completed.stderr
    return next((line.strip() for line in output.splitlines() if line.strip()), "available")[:200]


def _probe_command(
    command: list[str],
    *,
    success_status: str = "available",
    disclose_output: bool = True,
) -> tuple[str, str]:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return "unavailable", "command unavailable"
    if completed.returncode != 0:
        return "authentication-required" if success_status == "authenticated" else "unavailable", "command failed"
    detail = _first_output_line(completed) if disclose_output else "models available"
    return success_status, detail


def _windows_build() -> int | None:
    parts = platform.version().split(".")
    for part in reversed(parts):
        if part.isdigit():
            return int(part)
    return None


def _obsidian_available() -> bool:
    if shutil.which("obsidian"):
        return True
    app_candidates = [
        Path("/Applications/Obsidian.app"),
    ]
    home = os.environ.get("HOME")
    if home:
        app_candidates.append(Path(home) / "Applications" / "Obsidian.app")
    if any(path.is_dir() for path in app_candidates):
        return True
    candidates = []
    for variable in ("LOCALAPPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)"):
        root = os.environ.get(variable)
        if root:
            candidates.extend(
                (
                    Path(root) / "Obsidian" / "Obsidian.exe",
                    Path(root) / "Programs" / "Obsidian" / "Obsidian.exe",
                )
            )
    return any(path.is_file() for path in candidates)


def collect_environment_report() -> dict:
    system = platform.system()
    build = _windows_build() if system == "Windows" else None
    capabilities: dict[str, dict[str, str]] = {}

    for name, command in (
        ("git", ["git", "--version"]),
        ("github_cli", ["gh", "--version"]),
        ("uv", ["uv", "--version"]),
    ):
        status, detail = _probe_command(command)
        capabilities[name] = {"status": status, "detail": detail}

    agy_status, agy_detail = _probe_command(
        ["agy", "models"],
        success_status="authenticated",
        disclose_output=False,
    )
    capabilities["agy"] = {"status": agy_status, "detail": agy_detail}
    obsidian_available = _obsidian_available()
    capabilities["obsidian"] = {
        "status": "available" if obsidian_available else "unavailable",
        "detail": "application detected" if obsidian_available else "application unavailable",
    }

    required_statuses = {
        "git": "available",
        "github_cli": "available",
        "uv": "available",
        "obsidian": "available",
    }
    capabilities_ready = all(
        capabilities[name]["status"] == expected
        for name, expected in required_statuses.items()
    )

    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "host": {
            "system": system.lower(),
            "release": platform.release(),
            "build": build,
        },
        "preflight": "green" if capabilities_ready else "red",
        "capabilities": capabilities,
    }
