"""Verified Antigravity CLI live-model adapter for Laboratory 02."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .lab02 import REQUEST_ID, SLUG_RE, record_run_metadata
from .workflow import WorkflowError


DEFAULT_AGY_MODEL = "gemini-3.8-flash-low"


def run_agy(
    *,
    report_dir: Path,
    run_id: str,
    schema_path: Path,
    model_id: str,
    recorded_by: str,
    runner=subprocess.run,
    deadline_seconds: float = 330,
) -> dict:
    """Run the verified AGY profile and bind its structured response."""
    if not isinstance(recorded_by, str) or not recorded_by.strip():
        raise WorkflowError("recorded_by is required before a live AGY request.")
    if not isinstance(model_id, str) or not model_id.strip():
        raise WorkflowError("model_id is required before a live AGY request.")
    if not isinstance(run_id, str) or not SLUG_RE.fullmatch(run_id):
        raise WorkflowError("run_id must be a lowercase slug without spaces.")

    run_dir = report_dir / "runs" / run_id
    request_path = run_dir / "model-request.json"
    raw_path = run_dir / "raw-response.txt"
    metadata_path = run_dir / "run-metadata.json"
    if raw_path.exists() or metadata_path.exists():
        raise WorkflowError("AGY run evidence is write-once and already exists.")

    try:
        model_request = json.loads(request_path.read_text(encoding="utf-8"))
        json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WorkflowError(f"AGY profile input cannot be read: {exc}") from exc
    if not isinstance(model_request, dict) or model_request.get("request_id") != REQUEST_ID:
        raise WorkflowError("Model request does not match the Laboratory 02 request contract.")

    prompt = (
        "Return only one JSON object matching the enforced schema. Use only the exact source text "
        "embedded in this request. The three source_support entries must use claim_kind values "
        "definition, syntax-vs-semantics, authority-boundary in that exact order. Use one distinct "
        "exact source quotation for each entry. Do not add external knowledge.\n\n"
        + json.dumps(model_request, ensure_ascii=False, sort_keys=True)
    )
    command = [
        "agy",
        "--print",
        prompt,
        "--model",
        model_id.strip(),
        "--json-schema",
        str(schema_path),
        "--output-format",
        "json",
        "--sandbox",
        "--print-timeout",
        "5m",
    ]
    try:
        completed = runner(
            command,
            capture_output=True,
            text=True,
            timeout=deadline_seconds,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise WorkflowError("AGY request did not complete within the supported profile.") from exc
    if completed.returncode != 0:
        raise WorkflowError("AGY request failed without writing run evidence.")

    try:
        envelope = json.loads(completed.stdout)
        content = envelope["response"]
        if envelope.get("status") != "SUCCESS" or not isinstance(content, str) or not content.strip():
            raise WorkflowError("AGY response did not contain a successful structured result.")
    except WorkflowError:
        raise
    except (TypeError, KeyError, json.JSONDecodeError) as exc:
        raise WorkflowError("AGY response envelope could not be read.") from exc

    try:
        candidate = json.loads(content)
    except json.JSONDecodeError as exc:
        raise WorkflowError("AGY structured response must contain exactly one JSON object.") from exc
    if not isinstance(candidate, dict):
        raise WorkflowError("AGY structured response must contain exactly one JSON object.")

    raw_path.write_bytes(content.encode("utf-8"))
    metadata = record_run_metadata(
        report_dir=report_dir,
        run_id=run_id,
        evidence_kind="live",
        adapter="agy",
        model_id=model_id,
        recorded_by=recorded_by,
    )
    return {"raw_response": raw_path, "run_metadata": metadata, "model_id": model_id.strip()}
