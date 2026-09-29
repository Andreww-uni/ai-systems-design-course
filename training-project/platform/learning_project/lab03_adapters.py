"""Provider-neutral runners for Laboratory 03 positions.

Each runner receives the provider-neutral request payload written by
``lab03.run_position`` and returns the raw assistant content string. Any
exception is recorded as position evidence; messages containing route-wide
markers (authentication, quota, rate limit, unavailability) classify the
failure as route-wide rather than position-specific.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_TIMEOUT = 120


def offline_fixture_runner(request: dict) -> str:
    """Deterministic no-purchase runner for workflow exercises and tests.

    Produces a structurally valid envelope that answers from the supplied
    source only when the task is answerable from it; used with the
    ``offline-fixture`` adapter label so runs are never confused with live
    model evidence.
    """
    envelope = {
        "case_id": request["case_id"],
        "proposed_text": (
            f"Offline fixture response for task '{request['task']}' "
            f" grounded only in the supplied source."
        ),
    }
    return json.dumps(envelope, ensure_ascii=False)


def openrouter_runner_factory(model_id: str, api_key: str | None = None) -> Callable[[dict], str]:
    """Build a live OpenRouter runner for one model."""
    key = api_key if api_key is not None else os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        raise RuntimeError("openrouter authentication failed: OPENROUTER_API_KEY is not set")

    def runner(request: dict) -> str:
        payload = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": request["instruction"]},
                {
                    "role": "user",
                    "content": (
                        f"Task: {request['task']}\n\n"
                        f"Supplied source:\n{request['supplied_source']}\n\n"
                        "Return one JSON object with exactly the fields "
                        f'"case_id" (value "{request["case_id"]}") and "proposed_text".'
                    ),
                },
            ],
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            OPENROUTER_URL,
            data=data,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=OPENROUTER_TIMEOUT) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"openrouter request failed with HTTP {exc.code}: {exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"openrouter route unavailable: {exc.reason}") from exc
        choices = body.get("choices") or []
        if not choices or not isinstance(choices[0].get("message", {}).get("content"), str):
            raise RuntimeError("openrouter returned no assistant content")
        return choices[0]["message"]["content"]

    return runner


ADAPTERS = {
    "offline-fixture": lambda model_id: offline_fixture_runner,
    "openrouter": openrouter_runner_factory,
}


def runner_for(adapter: str, model_id: str) -> Callable[[dict], str]:
    try:
        factory = ADAPTERS[adapter]
    except KeyError:
        raise ValueError(f"Unknown Laboratory 03 adapter: {adapter}") from None
    return factory(model_id)


def instructions_for(report_dir: Path, course_root: Path) -> dict[str, str]:
    """Load Variant A from course material and Variant B from the student report."""
    variant_a_path = course_root / "instructions" / "lab03" / "variant-a.txt"
    variant_b_path = report_dir / "development" / "variant-b.txt"
    try:
        variant_a = variant_a_path.read_text(encoding="utf-8")
        variant_b = variant_b_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Instruction variant cannot be read: {exc}") from exc
    return {"a": variant_a, "b": variant_b}


def cases_for(comparison_dir: Path, training_project: Path, report_dir: Path) -> dict[str, dict]:
    """Resolve the case catalog for a comparison from its schedule kind."""
    schedule = json.loads((comparison_dir / "schedule.json").read_text(encoding="utf-8"))
    if schedule["kind"] == "held-out":
        revealed = json.loads((comparison_dir / "revealed-family.json").read_text(encoding="utf-8"))
        return {c["case_id"]: c for c in revealed["family"]["cases"]}
    dev_family_path = (
        training_project / "cases" / "lab03" / "development" / "dev-common-inputs.json"
    )
    dev_family = json.loads(dev_family_path.read_text(encoding="utf-8"))
    cases = {c["case_id"]: c for c in dev_family["cases"]}
    dev_dir = report_dir / "development"
    transfer_path = dev_dir / "transfer-case.yaml"
    perturbation_path = dev_dir / "transfer-perturbation.yaml"
    import yaml

    transfer = yaml.safe_load(transfer_path.read_text(encoding="utf-8"))
    perturbation = yaml.safe_load(perturbation_path.read_text(encoding="utf-8"))
    for record in (transfer, perturbation):
        cases[record["case_id"]] = {
            "case_id": record["case_id"],
            "task": record["task"],
            "supplied_source": record["supplied_source"],
            "evidence_situation": record.get("evidence_situation", "sufficient-evidence"),
        }
    return cases
