"""Command line for the Laboratory 01 governed-proposal workflow.

Three commands map one to one onto the governed-proposal protocol, one
command verifies the workstation, and one command writes a Teams submission
copy of a Markdown report:

* ``validate`` — check a candidate proposal; it changes nothing.
* ``decide``   — record the explicit human approval or rejection.
* ``apply``    — turn an approved proposal into the accepted contract.
* ``doctor``   — write a normalized workstation capability report.
* ``prepare-report`` — write ``submission/REPORT.md`` with images embedded.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from .agy_adapter import run_agy
from .doctor import collect_environment_report
from .lab02 import (
    Lab02InputError,
    apply_candidate,
    check_approved_fixtures,
    compare_live_runs,
    course_tree_drift,
    import_response,
    prepare_request,
    record_decision as record_lab02_decision,
    record_run_metadata,
    register_source,
    revise_candidate,
    validate_candidate,
    verify_lab02,
)
from .lab03 import (
    aggregate as aggregate_lab03,
    build_blinded_index,
    build_curator_input,
    build_positions,
    close_unstarted_positions,
    freeze_protocol,
    ingest_curator_candidate,
    load_family,
    record_assessment,
    record_completion_status,
    record_human_case_review,
    record_premature_exposure,
    record_recommendation,
    record_regression,
    record_selected_comparison,
    record_transfer_case,
    record_variant_b,
    run_position,
    select_family,
    start_calibration,
    structural_check,
    submit_calibration,
    verify_lab03,
)
from .openai_compatible import run_openrouter
from .report_submission import prepare_report
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

    prepare_report_command = commands.add_parser(
        "prepare-report",
        help="Write a Teams submission copy of a Markdown report with images embedded.",
    )
    prepare_report_command.add_argument("report", type=Path, help="Source Markdown report.")
    prepare_report_command.add_argument(
        "--output",
        type=Path,
        help="Submission copy (default: <report-dir>/submission/REPORT.md).",
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

    check_fixtures = lab02_commands.add_parser(
        "check-fixtures", help="Exercise approved offline fixtures without changing the vault."
    )
    check_fixtures.add_argument("--vault", type=Path, required=True)

    prepare = lab02_commands.add_parser("prepare", help="Write one deterministic model request.")
    prepare.add_argument("--vault", type=Path, required=True)
    prepare.add_argument("--report-dir", type=Path, required=True)
    prepare.add_argument("--run-id", required=True)

    run_agy_command = lab02_commands.add_parser(
        "run-agy", help="Run the verified Antigravity CLI live profile."
    )
    run_agy_command.add_argument("--report-dir", type=Path, required=True)
    run_agy_command.add_argument("--run-id", required=True)
    run_agy_command.add_argument("--model-id", required=True)
    run_agy_command.add_argument("--by", required=True)

    run_openrouter_command = lab02_commands.add_parser(
        "run-openrouter", help="Run the verified OpenRouter Free contingency profile."
    )
    run_openrouter_command.add_argument("--report-dir", type=Path, required=True)
    run_openrouter_command.add_argument("--run-id", required=True)
    run_openrouter_command.add_argument("--by", required=True)

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

    lab03 = commands.add_parser("lab03", help="Run the Laboratory 03 evaluation workflow.")
    lab03_commands = lab03.add_subparsers(dest="lab03_command", required=True)

    calibrate = lab03_commands.add_parser("calibrate", help="Start rubric calibration on a packet.")
    calibrate.add_argument("--report-dir", type=Path, required=True)
    calibrate.add_argument("--packet", required=True, choices=("calibration-a", "calibration-b"))
    calibrate.add_argument("--by", required=True)

    calibrate_submit = lab03_commands.add_parser("calibrate-submit", help="Freeze labels and compare with reviewed ones.")
    calibrate_submit.add_argument("--report-dir", type=Path, required=True)
    calibrate_submit.add_argument("--packet", required=True, choices=("calibration-a", "calibration-b"))
    calibrate_submit.add_argument("--by", required=True)

    transfer = lab03_commands.add_parser("record-transfer", help="Record the transfer case and perturbation.")
    transfer.add_argument("--report-dir", type=Path, required=True)
    transfer.add_argument("--transfer", type=Path, required=True)
    transfer.add_argument("--perturbation", type=Path, required=True)

    variant_b = lab03_commands.add_parser("record-variant-b", help="Record Variant B and its change declaration.")
    variant_b.add_argument("--report-dir", type=Path, required=True)
    variant_b.add_argument("--text", type=Path, required=True)
    variant_b.add_argument("--change", type=Path, required=True)

    dev_run = lab03_commands.add_parser("dev-run", help="Run one development position (8 scheduled).")
    dev_run.add_argument("--report-dir", type=Path, required=True)
    dev_run.add_argument("--position-id", required=True)
    dev_run.add_argument("--adapter", choices=("offline-fixture", "openrouter"), required=True)
    dev_run.add_argument("--model-id", required=True)
    dev_run.add_argument("--by", required=True)

    freeze = lab03_commands.add_parser("freeze", help="Freeze the comparison protocol.")
    freeze.add_argument("--report-dir", type=Path, required=True)
    freeze.add_argument("--protocol", type=Path, required=True)
    freeze.add_argument("--by", required=True)

    select = lab03_commands.add_parser("select-family", help="Select one reserve family after freeze.")
    select.add_argument("--report-dir", type=Path, required=True)
    select.add_argument("--freeze-id", required=True)
    select.add_argument("--by", required=True)

    run_cmd = lab03_commands.add_parser("run", help="Run one held-out position through an adapter.")
    run_cmd.add_argument("--report-dir", type=Path, required=True)
    run_cmd.add_argument("--freeze-id", required=True)
    run_cmd.add_argument("--position-id", required=True)
    run_cmd.add_argument("--adapter", choices=("offline-fixture", "openrouter"), required=True)
    run_cmd.add_argument("--model-id", required=True)
    run_cmd.add_argument("--by", required=True)

    close_cmd = lab03_commands.add_parser("close-unstarted", help="Close remaining unstarted positions honestly.")
    close_cmd.add_argument("--report-dir", type=Path, required=True)
    close_cmd.add_argument("--freeze-id", required=True)
    close_cmd.add_argument("--reason", required=True)
    close_cmd.add_argument("--by", required=True)

    blind = lab03_commands.add_parser("build-scoring", help="Build the blinded scoring view.")
    blind.add_argument("--report-dir", type=Path, required=True)
    blind.add_argument("--freeze-id", required=True)

    assess = lab03_commands.add_parser("assess", help="Record one blinded rubric judgment.")
    assess.add_argument("--report-dir", type=Path, required=True)
    assess.add_argument("--freeze-id", required=True)
    assess.add_argument("--blind-id", required=True)
    assess.add_argument("--category", required=True)
    assess.add_argument("--source-pointer", required=True)
    assess.add_argument("--rationale", required=True)
    assess.add_argument("--shares-rationale-with")

    agg = lab03_commands.add_parser("aggregate", help="Join identities and compute nested counts.")
    agg.add_argument("--report-dir", type=Path, required=True)
    agg.add_argument("--freeze-id", required=True)

    select_cmp = lab03_commands.add_parser("select-comparison", help="Select the comparison to submit.")
    select_cmp.add_argument("--report-dir", type=Path, required=True)
    select_cmp.add_argument("--comparison-id", required=True)
    select_cmp.add_argument("--by", required=True)

    recommend = lab03_commands.add_parser("recommend", help="Record the bounded recommendation.")
    recommend.add_argument("--report-dir", type=Path, required=True)
    recommend.add_argument("--freeze-id", required=True)
    recommend.add_argument("--outcome", required=True, choices=("recommend-b", "retain-a", "reject-both", "seek-more-evidence"))
    recommend.add_argument("--rationale", required=True)
    recommend.add_argument("--limitations", required=True, help="Semicolon-separated limitations.")
    recommend.add_argument("--by", required=True)

    regression = lab03_commands.add_parser("record-regression", help="Record the regression case.")
    regression.add_argument("--report-dir", type=Path, required=True)
    regression.add_argument("--record", type=Path, required=True)

    completion = lab03_commands.add_parser("record-completion", help="Record complete or honest-partial completion.")
    completion.add_argument("--report-dir", type=Path, required=True)
    completion.add_argument("--status", required=True, choices=("complete", "honest-partial"))
    completion.add_argument("--detail", type=Path, required=True)

    verify_lab03_cmd = lab03_commands.add_parser("verify", help="Commit-first verification of Laboratory 03.")
    verify_lab03_cmd.add_argument("--report-dir", type=Path, required=True)
    verify_lab03_cmd.add_argument("--final-commit", required=True)

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


def _run_prepare_report(args: argparse.Namespace) -> int:
    output_path, image_count = prepare_report(args.report, output_path=args.output)
    print(f"Wrote the submission report to {output_path}.")
    print(f"Embedded images: {image_count}")
    return 0


def _run_lab02(args: argparse.Namespace) -> int:
    command = args.lab02_command
    course_root = _discover_course_root()
    if command == "check-fixtures":
        results = check_approved_fixtures(vault=args.vault, course_root=course_root)
        for name, result in results.items():
            print(f"{name}: {result}")
        return 0
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
    if command == "run-agy":
        result = run_agy(
            report_dir=args.report_dir,
            run_id=args.run_id,
            schema_path=(
                Path(__file__).resolve().parent.parent.parent
                / "schemas/lab02-candidate.schema.json"
            ),
            model_id=args.model_id,
            recorded_by=args.by,
        )
        print(
            "Recorded an AGY live response using model "
            f"{result['model_id']} for run {args.run_id}."
        )
        return 0
    if command == "run-openrouter":
        result = run_openrouter(
            report_dir=args.report_dir,
            run_id=args.run_id,
            schema_path=(
                Path(__file__).resolve().parent.parent.parent
                / "schemas/lab02-candidate.schema.json"
            ),
            api_key=os.environ.get("OPENROUTER_API_KEY", ""),
            recorded_by=args.by,
        )
        print(
            "Recorded an OpenRouter live response using model "
            f"{result['model_id']} for run {args.run_id}."
        )
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


def _run_lab03(args: argparse.Namespace) -> int:
    import yaml

    from .lab03 import ExposureLedger, _now
    from .lab03_adapters import cases_for, instructions_for, runner_for

    course_root = _discover_course_root()
    if course_root is None:
        raise WorkflowError("The Laboratory 03 workflow must run inside the course git repository.")
    report_dir = args.report_dir.resolve()
    training_project = Path(__file__).resolve().parent.parent.parent
    command = args.lab03_command

    def comparison_dir(freeze_id: str) -> Path:
        matches = sorted(report_dir.glob(f"comparisons/{freeze_id}*"))
        if not matches:
            raise WorkflowError(f"No comparison found for freeze id {freeze_id}.")
        return matches[0]

    if command == "calibrate":
        path = start_calibration(
            report_dir=report_dir,
            packet_id=args.packet,
            packets_dir=training_project / "cases" / "lab03" / "calibration",
            student=args.by,
        )
        print(f"Wrote the calibration scaffold to {path}.")
        return 0
    if command == "calibrate-submit":
        result = submit_calibration(
            report_dir=report_dir,
            packet_id=args.packet,
            packets_dir=training_project / "cases" / "lab03" / "calibration",
            student=args.by,
        )
        print(f"Calibration complete: {result['agreement']}/{result['total']} labels agree with reviewed labels.")
        return 0
    if command == "record-transfer":
        transfer = yaml.safe_load(args.transfer.read_text(encoding="utf-8"))
        perturbation = yaml.safe_load(args.perturbation.read_text(encoding="utf-8"))
        path = record_transfer_case(
            report_dir=report_dir, transfer_case=transfer, perturbation=perturbation
        )
        print(f"Wrote the transfer case to {path}.")
        return 0
    if command == "record-variant-b":
        variant_b_text = args.text.read_text(encoding="utf-8")
        change = yaml.safe_load(args.change.read_text(encoding="utf-8"))
        path = record_variant_b(
            report_dir=report_dir, variant_b_text=variant_b_text, change_declaration=change
        )
        print(f"Wrote Variant B declaration to {path}.")
        return 0
    if command == "dev-run":
        dev_dir = report_dir / "development"
        dev_schedule_path = dev_dir / "schedule.json"
        if not dev_schedule_path.exists():
            dev_family = load_family(
                training_project / "cases" / "lab03" / "development" / "dev-common-family.json",
                expected_cases=2,
            )
            transfer = yaml.safe_load((dev_dir / "transfer-case.yaml").read_text(encoding="utf-8"))
            perturbation = yaml.safe_load((dev_dir / "transfer-perturbation.yaml").read_text(encoding="utf-8"))
            dev_cases = [
                *dev_family["cases"],
                {
                    "case_id": transfer["case_id"],
                    "task": transfer["task"],
                    "supplied_source": transfer["supplied_source"],
                },
                {
                    "case_id": perturbation["case_id"],
                    "task": perturbation["task"],
                    "supplied_source": perturbation["supplied_source"],
                },
            ]
            build_positions(
                comparison_dir=dev_dir,
                family={"family_id": "dev-common", "cases": dev_cases},
                kind="development",
                cases=dev_cases,
            )
        schedule = json.loads(dev_schedule_path.read_text(encoding="utf-8"))
        instructions = instructions_for(report_dir, training_project)
        cases = cases_for(dev_dir, training_project, report_dir)
        result = run_position(
            comparison_dir=dev_dir,
            schedule=schedule,
            position_id=args.position_id,
            cases_by_id=cases,
            instructions=instructions,
            runner=lambda request: runner_for(args.adapter, args.model_id)(request),
            adapter=args.adapter,
            model_id=args.model_id,
            recorded_by=args.by,
        )
        print(f"Development position {args.position_id}: {result['outcome']}.")
        return 0
    if command == "freeze":
        protocol = yaml.safe_load(args.protocol.read_text(encoding="utf-8"))
        ledger = ExposureLedger(report_dir / "exposure-ledger.json")
        manifest = freeze_protocol(
            report_dir=report_dir,
            protocol=protocol,
            reserves_dir=training_project / "cases" / "lab03" / "reserves",
            ledger=ledger,
            student=args.by,
        )
        print(f"Froze comparison {manifest['freeze_id']}.")
        return 0
    if command == "select-family":
        manifest = json.loads(
            (comparison_dir(args.freeze_id) / "freeze-manifest.json").read_text(encoding="utf-8")
        )
        ledger = ExposureLedger(report_dir / "exposure-ledger.json")
        family = select_family(
            reserves_dir=training_project / "cases" / "lab03" / "reserves",
            ledger=ledger,
            freeze_manifest=manifest,
            student=args.by,
        )
        positions = build_positions(
            comparison_dir=comparison_dir(args.freeze_id),
            family=family,
            kind="held-out",
        )
        ledger.append({
            "event": "used-in-comparison",
            "family_id": family["family_id"],
            "freeze_id": manifest["freeze_id"],
            "actor": args.by,
            "recorded_at": _now(),
        })
        print(f"Selected family {family['family_id']} and scheduled {len(positions)} positions.")
        return 0
    if command == "run":
        cmp_dir = comparison_dir(args.freeze_id)
        schedule = json.loads((cmp_dir / "schedule.json").read_text(encoding="utf-8"))
        revealed = json.loads((cmp_dir / "revealed-family.json").read_text(encoding="utf-8"))
        cases_by_id = {c["case_id"]: c for c in revealed["family"]["cases"]}
        instructions = instructions_for(report_dir, training_project)
        result = run_position(
            comparison_dir=cmp_dir,
            schedule=schedule,
            position_id=args.position_id,
            cases_by_id=cases_by_id,
            instructions=instructions,
            runner=lambda request: runner_for(args.adapter, args.model_id)(request),
            adapter=args.adapter,
            model_id=args.model_id,
            recorded_by=args.by,
        )
        print(f"Position {args.position_id}: {result['outcome']}"
              + (f" ({result['failure_class']})" if "failure_class" in result else "") + ".")
        return 0
    if command == "close-unstarted":
        closure = close_unstarted_positions(
            comparison_dir=comparison_dir(args.freeze_id),
            reason=args.reason,
            student=args.by,
        )
        print(f"Closed {len(closure['closed_positions'])} unstarted positions.")
        return 0
    if command == "build-scoring":
        cmp_dir = comparison_dir(args.freeze_id)
        revealed = json.loads((cmp_dir / "revealed-family.json").read_text(encoding="utf-8"))
        index = build_blinded_index(comparison_dir=cmp_dir, family=revealed["family"])
        print(f"Built the blinded index with {len(index['entries'])} entries.")
        return 0
    if command == "assess":
        assessment = {
            "category": args.category,
            "source_pointer": args.source_pointer,
            "rationale": args.rationale,
        }
        if args.shares_rationale_with:
            assessment["shares_rationale_with"] = args.shares_rationale_with
        path = record_assessment(
            comparison_dir=comparison_dir(args.freeze_id),
            blind_id=args.blind_id,
            assessment=assessment,
        )
        print(f"Recorded the assessment to {path}.")
        return 0
    if command == "aggregate":
        result = aggregate_lab03(comparison_dir=comparison_dir(args.freeze_id))
        a, b = result["nested_counts"]["a"], result["nested_counts"]["b"]
        print(f"Nested counts — A: {a['returned']} returned / {a['rubric_acceptable']} acceptable; "
              f"B: {b['returned']} returned / {b['rubric_acceptable']} acceptable.")
        return 0
    if command == "select-comparison":
        path = record_selected_comparison(
            report_dir=report_dir, comparison_id=args.comparison_id, student=args.by
        )
        print(f"Recorded the selected comparison to {path}.")
        return 0
    if command == "recommend":
        path = record_recommendation(
            comparison_dir=comparison_dir(args.freeze_id),
            outcome=args.outcome,
            rationale=args.rationale,
            limitations=[item.strip() for item in args.limitations.split(";") if item.strip()],
            student=args.by,
        )
        print(f"Recorded the recommendation to {path}.")
        return 0
    if command == "record-regression":
        record = yaml.safe_load(args.record.read_text(encoding="utf-8"))
        path = record_regression(report_dir=report_dir, regression=record)
        print(f"Recorded the regression case to {path}.")
        return 0
    if command == "record-completion":
        detail = yaml.safe_load(args.detail.read_text(encoding="utf-8"))
        path = record_completion_status(
            report_dir=report_dir, status=args.status, detail=detail
        )
        print(f"Recorded completion status {args.status} to {path}.")
        return 0
    if command == "verify":
        report = verify_lab03(report_dir=report_dir, final_commit=args.final_commit)
        print(f"Laboratory 03 verification {report['outcome']}.")
        return 0 if report["outcome"] in {"passed-complete", "passed-partial"} else 1
    raise WorkflowError(f"Unknown Laboratory 03 command: {command}")


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    handlers = {
        "validate": _run_validate,
        "decide": _run_decide,
        "apply": _run_apply,
        "doctor": _run_doctor,
        "prepare-report": _run_prepare_report,
        "lab02": _run_lab02,
        "lab03": _run_lab03,
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
