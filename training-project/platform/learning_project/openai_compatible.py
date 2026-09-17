"""OpenAI-compatible live-model adapter for Laboratory 02."""

from __future__ import annotations

import json
from pathlib import Path
from queue import Queue
from threading import Thread
from urllib.request import Request, urlopen

from .lab02 import REQUEST_ID, SLUG_RE, record_run_metadata
from .workflow import WorkflowError

OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_FREE_MODEL = "nex-agi/nex-n2.5-mini:free"


def run_openrouter(
    *,
    report_dir: Path,
    run_id: str,
    schema_path: Path,
    api_key: str,
    recorded_by: str,
    opener=urlopen,
    deadline_seconds: float = 120,
) -> dict:
    """Run the verified OpenRouter Free profile and bind its raw response."""
    if not isinstance(api_key, str) or not api_key.strip():
        raise WorkflowError("OPENROUTER_API_KEY is required for the OpenRouter live profile.")
    if not isinstance(recorded_by, str) or not recorded_by.strip():
        raise WorkflowError("recorded_by is required before a live OpenRouter request.")
    if not isinstance(run_id, str) or not SLUG_RE.fullmatch(run_id):
        raise WorkflowError("run_id must be a lowercase slug without spaces.")
    run_dir = report_dir / "runs" / run_id
    request_path = run_dir / "model-request.json"
    raw_path = run_dir / "raw-response.txt"
    metadata_path = run_dir / "run-metadata.json"
    if raw_path.exists() or metadata_path.exists():
        raise WorkflowError("OpenRouter run evidence is write-once and already exists.")

    try:
        model_request = json.loads(request_path.read_text(encoding="utf-8"))
        output_schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WorkflowError(f"OpenRouter profile input cannot be read: {exc}") from exc
    if not isinstance(model_request, dict) or model_request.get("request_id") != REQUEST_ID:
        raise WorkflowError("Model request does not match the Laboratory 02 request contract.")
    if not isinstance(output_schema, dict):
        raise WorkflowError("Candidate schema must contain a JSON object.")

    body = {
        "model": OPENROUTER_FREE_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Return only one JSON object matching the supplied schema. Use only the source "
                    "text in the request and do not add external knowledge. The three source_support "
                    "entries must use claim_kind values definition, syntax-vs-semantics, "
                    "authority-boundary in that exact order. Use one distinct exact source quotation "
                    "for each entry."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(model_request, ensure_ascii=False, sort_keys=True),
            },
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "lab02_structured_output_candidate",
                "strict": True,
                "schema": output_schema,
            },
        },
        "provider": {"require_parameters": True},
        "temperature": 0,
        "stream": False,
    }
    request = Request(
        OPENROUTER_ENDPOINT,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-OpenRouter-Title": "AI Systems Design Laboratory 02",
        },
        method="POST",
    )
    response_queue: Queue[tuple[str, object]] = Queue(maxsize=1)

    def fetch_response() -> None:
        try:
            with opener(request, timeout=120) as response:
                response_queue.put(("ok", response.read()))
        except Exception as exc:
            response_queue.put(("error", exc))

    worker = Thread(target=fetch_response, daemon=True)
    worker.start()
    worker.join(deadline_seconds)
    if worker.is_alive():
        raise WorkflowError(
            f"OpenRouter request timed out after {deadline_seconds:g} seconds without writing evidence."
        )
    result_kind, result_value = response_queue.get_nowait()
    if result_kind == "error":
        raise WorkflowError("OpenRouter response could not be read.") from None

    try:
        envelope = json.loads(result_value)
        model_id = envelope["model"]
        choice = envelope["choices"][0]
        if choice.get("finish_reason") != "stop":
            raise WorkflowError("OpenRouter response did not finish normally.")
        content = choice["message"]["content"]
        if not isinstance(model_id, str) or not model_id.strip():
            raise WorkflowError("OpenRouter response did not identify the selected model.")
        if not isinstance(content, str) or not content.strip():
            raise WorkflowError("OpenRouter response did not contain assistant message content.")
    except WorkflowError:
        raise
    except Exception as exc:
        raise WorkflowError("OpenRouter response could not be read.") from exc

    raw_path.write_bytes(content.encode("utf-8"))
    metadata = record_run_metadata(
        report_dir=report_dir,
        run_id=run_id,
        evidence_kind="live",
        adapter="openai-compatible",
        model_id=model_id,
        recorded_by=recorded_by,
    )
    return {"raw_response": raw_path, "run_metadata": metadata, "model_id": model_id}
