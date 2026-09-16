"""Command line for the Laboratory 01 governed-proposal workflow.

Three commands map one to one onto the governed-proposal protocol, and one
command verifies the workstation:

* ``validate`` — check a candidate proposal; it changes nothing.
* ``decide``   — record the explicit human approval or rejection.
* ``apply``    — turn an approved proposal into the accepted contract.
* ``doctor``   — write a normalized workstation capability report.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from .doctor import collect_environment_report
from .lab02 import (
    Lab02InputError,
    apply_candidate,
    compare_live_runs,
    import_response,
    prepare_request,
    record_decision as record_lab02_decision,
    record_run_metadata,
    register_source,
    revise_candidate,
    validate_candidate,
    verify_lab02,
)
from .workflow import (
    ACCEPTED_FILENAME,
    DECISION_FILENAME,
    WorkflowError,
    apply_proposal,
    create_decision,
    ensure_decision_matches,
    record_approval,
    record_rejection,
    validate_proposal,
)


def _sibling(proposal_path: Path, explicit: Path | None, filename: str) -> Path:
    return explicit if explicit is not None else proposal_path.parent / filename


def _discover_course_root() -> Path | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        return None


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="learning-project",
        description="Govern an AI proposal with an explicit human decision.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser("validate", help="Validate a candidate proposal.")
    validate.add_argument("proposal", type=Path)

    decide = commands.add_parser("decide", help="Record the human decision on a proposal.")
    decide.add_argument("proposal", type=Path)
    outcome = decide.add_mutually_exclusive_group(required=True)
    outcome.add_argument("--approve", action="store_true", help="Approve the proposal.")
    outcome.add_argument("--reject", action="store_true", help="Reject the proposal.")
    decide.add_argument("--by", required=True, help="Name of the human who decides.")
    decide.add_argument("--reason", help="Why the proposal was rejected.")
    decide.add_argument("--decision", type=Path, help=f"Decision file (default: {DECISION_FILENAME}).")

    apply_command = commands.add_parser("apply", help="Apply an approved proposal.")
    apply_command.add_argument("proposal", type=Path)
    apply_command.add_argument("--decision", type=Path, help=f"Decision file (default: {DECISION_FILENAME}).")
    apply_command.add_argument("--output", type=Path, help=f"Accepted contract (default: {ACCEPTED_FILENAME}).")

    doctor = commands.add_parser("doctor", help="Verify Laboratory 01 workstation capabilities.")
    doctor.add_argument(
        "--output",
        type=Path,
        default=Path("environment-report.json"),
        help="Machine-readable capability report (default: environment-report.json).",
    )

    lab02 = commands.add_parser("lab02", help="Run the Laboratory 02 governed workflow.")
    lab02_commands = lab02.add_subparsers(dest="lab02_command", required=True)

    register = lab02_commands.add_parser("register-source", help="Register the Module 02 source.")
    register.add_argument("--vault", type=Path, required=True)
    register.add_argument("--course-root", type=Path, required=True)
    register.add_argument("--theory", type=Path, required=True)
    register.add_argument("--course-repository", required=True)
    register.add_argument("--course-commit", required=True)
    register.add_argument("--by", required=True)

    prepare = lab02_commands.add_parser("prepare", help="Write one deterministic model request.")
    prepare.add_argument("--vault", type=Path, required=True)
    prepare.add_argument("--report-dir", type=Path, required=True)
    prepare.add_argument("--run-id", required=True)

    import_command = lab02_commands.add_parser("import", help="Import one raw JSON response.")
    import_command.add_argument("--vault", type=Path, required=True)
    import_command.add_argument("--report-dir", type=Path, required=True)
    import_command.add_argument("--run-id", required=True)
    import_command.add_argument("--evidence-kind", choices=("live", "fixture"), required=True)

    record_run = lab02_commands.add_parser("record-run", help="Record run attribution metadata.")
    record_run.add_argument("--report-dir", type=Path, required=True)
    record_run.add_argument("--run-id", required=True)
    record_run.add_argument("--evidence-kind", choices=("live", "fixture"), required=True)
    record_run.add_argument(
        "--adapter", choices=("agy", "openai-compatible", "offline-fixture"), required=True
    )
    record_run.add_argument("--model-id", required=True)
    record_run.add_argument("--by", required=True)

    validate_lab02 = lab02_commands.add_parser("validate", help="Validate one candidate proposal.")
    validate_lab02.add_argument("--vault", type=Path, required=True)
    validate_lab02.add_argument("--report-dir", type=Path, required=True)
    validate_lab02.add_argument("--proposal-id", required=True)
    validate_lab02.add_argument("--output", type=Path, required=True)

    revise = lab02_commands.add_parser("revise", help="Create a human-revised successor proposal.")
    revise.add_argument("--vault", type=Path, required=True)
    revise.add_argument("--revision", type=Path, required=True)

    compare = lab02_commands.add_parser("compare-live", help="Compare two live runs.")
    compare.add_argument("--vault", type=Path, required=True)
    compare.add_argument("--report-dir", type=Path, required=True)
    compare.add_argument("--run-id", nargs=2, required=True)
    compare.add_argument("--output", type=Path)

    decide_lab02 = lab02_commands.add_parser("decide", help="Record a Laboratory 02 decision.")
    decide_lab02.add_argument("--vault", type=Path, required=True)
    decide_lab02.add_argument("--proposal-id", required=True)
    decide_lab02.add_argument("--validation", type=Path, required=True)
    decide_lab02.add_argument("--review", type=Path, required=True)
    lab02_outcome = decide_lab02.add_mutually_exclusive_group(required=True)
    lab02_outcome.add_argument("--approve", action="store_true")
    lab02_outcome.add_argument("--reject", action="store_true")
    decide_lab02.add_argument("--by", required=True)
    decide_lab02.add_argument("--reason")

    apply_lab02 = lab02_commands.add_parser("apply", help="Apply an approved Laboratory 02 proposal.")
    apply_lab02.add_argument("--vault", type=Path, required=True)
    apply_lab02.add_argument("--proposal-id", required=True)
    apply_lab02.add_argument("--validation", type=Path, required=True)
    apply_lab02.add_argument("--review", type=Path, required=True)

    verify = lab02_commands.add_parser("verify", help="Verify Laboratory 02 evidence read-only.")
    verify.add_argument("--vault", type=Path, required=True)
    verify.add_argument("--report-dir", type=Path, required=True)

    return parser


def _run_validate(args: argparse.Namespace) -> int:
    validation = validate_proposal(args.proposal)
    if not validation.valid:
        print(f"Proposal {args.proposal} is not valid:", file=sys.stderr)
        for error in validation.errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print(f"Proposal {validation.proposal_id} is valid.")
    return 0


def _run_decide(args: argparse.Namespace) -> int:
    validation = validate_proposal(args.proposal)
    if not validation.valid:
        raise WorkflowError(
            "Proposal is invalid and cannot be decided: " + "; ".join(validation.errors)
        )

    decision_path = _sibling(args.proposal, args.decision, DECISION_FILENAME)
    if not decision_path.exists():
        create_decision(validation, decision_path)
    else:
        ensure_decision_matches(validation, decision_path)

    if args.approve:
        record_approval(decision_path, recorded_by=args.by)
        print(f"Approved {validation.proposal_id} as {args.by}.")
    else:
        record_rejection(decision_path, recorded_by=args.by, reason=args.reason)
        print(f"Rejected {validation.proposal_id} as {args.by}.")
    return 0


def _run_apply(args: argparse.Namespace) -> int:
    decision_path = _sibling(args.proposal, args.decision, DECISION_FILENAME)
    accepted_path = _sibling(args.proposal, args.output, ACCEPTED_FILENAME)
    apply_proposal(args.proposal, decision_path, accepted_path)
    print(f"Wrote the accepted contract to {accepted_path}.")
    return 0


def _run_doctor(args: argparse.Namespace) -> int:
    report = collect_environment_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote the environment report to {args.output}.")
    return 0 if report["preflight"] == "green" else 1


def _run_lab02(args: argparse.Namespace) -> int:
    command = args.lab02_command
    course_root = _discover_course_root()
    if command == "register-source":
        path = register_source(
            course_root=args.course_root,
            theory_path=args.theory,
            vault=args.vault,
            course_repository=args.course_repository,
            course_commit=args.course_commit,
            registered_by=args.by,
        )
        print(f"Registered the Module 02 source at {path}.")
        return 0
    if command == "prepare":
        path = prepare_request(
            vault=args.vault,
            report_dir=args.report_dir,
            run_id=args.run_id,
            course_root=course_root,
        )
        print(f"Wrote the model request to {path}.")
        return 0
    if command == "import":
        path = import_response(
            vault=args.vault,
            report_dir=args.report_dir,
            run_id=args.run_id,
            evidence_kind=args.evidence_kind,
            course_root=course_root,
        )
        print(f"Wrote the candidate proposal to {path}.")
        return 0
    if command == "record-run":
        path = record_run_metadata(
            report_dir=args.report_dir,
            run_id=args.run_id,
            evidence_kind=args.evidence_kind,
            adapter=args.adapter,
            model_id=args.model_id,
            recorded_by=args.by,
        )
        print(f"Wrote run metadata to {path}.")
        return 0
    if command == "validate":
        result = validate_candidate(
            vault=args.vault,
            report_dir=args.report_dir,
            proposal_id=args.proposal_id,
            output_path=args.output,
            course_root=course_root,
        )
        print(f"Validation {'passed' if result['valid'] else 'failed'} for {args.proposal_id}.")
        return 0 if result["valid"] else 1
    if command == "revise":
        path = revise_candidate(
            vault=args.vault, revision_path=args.revision, course_root=course_root
        )
        print(f"Wrote the revised candidate to {path}.")
        return 0
    if command == "compare-live":
        output = args.output or args.report_dir / "live-comparison.json"
        comparison = compare_live_runs(
            vault=args.vault,
            report_dir=args.report_dir,
            run_ids=tuple(args.run_id),
            output_path=output,
            course_root=course_root,
        )
        print(f"Wrote {comparison['comparison_kind']} evidence to {output}.")
        return 0
    if command == "decide":
        status = "approved" if args.approve else "rejected"
        path = record_lab02_decision(
            vault=args.vault,
            proposal_id=args.proposal_id,
            validation_path=args.validation,
            review_path=args.review,
            status=status,
            recorded_by=args.by,
            reason=args.reason,
            course_root=course_root,
        )
        print(f"Recorded {status} decision at {path}.")
        return 0
    if command == "apply":
        concept, operation = apply_candidate(
            vault=args.vault,
            proposal_id=args.proposal_id,
            validation_path=args.validation,
            review_path=args.review,
            course_root=course_root,
        )
        print(f"Wrote accepted concept {concept} and operation {operation}.")
        return 0
    if command == "verify":
        report = verify_lab02(
            vault=args.vault,
            report_dir=args.report_dir,
            course_root=course_root,
        )
        print(f"Laboratory 02 verification {report['status']}.")
        return 0 if report["status"] == "passed" else 1
    raise WorkflowError(f"Unknown Laboratory 02 command: {command}")


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    handlers = {
        "validate": _run_validate,
        "decide": _run_decide,
        "apply": _run_apply,
        "doctor": _run_doctor,
        "lab02": _run_lab02,
    }
    try:
        return handlers[args.command](args)
    except Lab02InputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except WorkflowError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
