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
    build_positions,
    close_unstarted_positions,
    freeze_protocol,
    load_family,
    load_frozen_instructions,
    record_assessment,
    record_completion_status,
    record_interrupted_position,
    record_premature_exposure,
    record_recommendation,
    record_regression,
    record_selected_comparison,
    record_variant_b,
    run_position,
    lab03_status,
    select_family,
    start_calibration,
    structural_check,
    submit_calibration,
    validate_completion_detail,
    verify_lab03,
)
from .lab04 import (
    DEFAULT_STAGE_B_FIXTURE,
    prepare_boundary_comparison,
    record_boundary_decision,
    validate_lab04_report,
    verify_lab04,
    verify_stage_b,
)
from .lab04_retrieval import execute_retrieval, verify_stage_c2
from . import lab04_evaluation
from .lab04_index import (
    DEFAULT_STAGE_C1_FIXTURE,
    check_index_bindings,
    fetch_embedding_model,
    prepare_retrieval_unit_embeddings,
    prepare_vector_index,
    verify_stage_c1,
)
from .lab05 import (
    DEFAULT_CONTEXT_CONSTRUCTION_FIXTURE as DEFAULT_LAB05_CONTEXT_FIXTURE,
    DEFAULT_ACCEPTANCE_CONDITIONS_FIXTURE as DEFAULT_LAB05_ACCEPTANCE_FIXTURE,
    DEFAULT_GENERATION_FIXTURE as DEFAULT_LAB05_GENERATION_FIXTURE,
    DEFAULT_GENERATION_SCHEMA as DEFAULT_LAB05_GENERATION_SCHEMA,
    DEFAULT_RETRIEVAL_UNIT_SELECTION_FIXTURE as DEFAULT_LAB05_SELECTION_FIXTURE,
    DEFAULT_STAGE_B_FIXTURE as DEFAULT_LAB05_STAGE_B_FIXTURE,
    apply_context_construction,
    apply_query_rewriting,
    apply_retrieval_unit_selection,
    calculate_rubric_pass_rate,
    evaluate_acceptance_conditions,
    prepare_acceptance_conditions,
    prepare_generation_cases,
    record_configuration_decision,
    record_generation_judgment,
    run_generation_agy,
    verify_context_construction,
    verify_evaluation_outputs,
    verify_generation_outputs,
    verify_retrieval_unit_selection,
    verify_stage_b as verify_lab05_stage_b,
    validate_lab05_report,
    verify_lab05,
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


    variant_b = lab03_commands.add_parser("record-variant-b", help="Record Variant B and its change declaration.")
    variant_b.add_argument("--report-dir", type=Path, required=True)
    variant_b.add_argument("--text", type=Path, required=True)
    variant_b.add_argument("--change", type=Path, required=True)

    dev_run = lab03_commands.add_parser("dev-run", help="Run one development position (4 scheduled).")
    dev_run.add_argument("--report-dir", type=Path, required=True)
    dev_run.add_argument("--position-id", required=True)
    dev_run.add_argument("--adapter", choices=("offline-fixture", "openrouter"), required=True)
    dev_run.add_argument("--model-id", default="offline-fixture",
                         help="Model id; defaults to 'offline-fixture' for the offline adapter.")
    dev_run.add_argument("--by", required=True)

    dev_struct_check = lab03_commands.add_parser(
        "dev-structural-check",
        help="Validate one returned development response against the envelope contract.",
    )
    dev_struct_check.add_argument("--report-dir", type=Path, required=True)
    dev_struct_check.add_argument("--position-id", required=True)

    dev_interrupted = lab03_commands.add_parser(
        "dev-record-interrupted",
        help="Close a dispatched development position whose process ended before terminal evidence.",
    )
    dev_interrupted.add_argument("--report-dir", type=Path, required=True)
    dev_interrupted.add_argument("--position-id", required=True)
    dev_interrupted.add_argument("--reason", required=True)
    dev_interrupted.add_argument("--by", required=True)

    freeze = lab03_commands.add_parser("freeze", help="Freeze the comparison protocol.")
    freeze.add_argument("--report-dir", type=Path, required=True)
    freeze.add_argument("--protocol", type=Path, required=True)
    freeze.add_argument("--by", required=True)

    select = lab03_commands.add_parser("select-family", help="Select one reserve family after freeze.")
    select.add_argument("--report-dir", type=Path, required=True)
    select.add_argument("--freeze-id", required=True)
    select.add_argument("--by", required=True)

    premature = lab03_commands.add_parser(
        "record-premature-exposure",
        help="Record honest premature family exposure before freeze.",
    )
    premature.add_argument("--report-dir", type=Path, required=True)
    premature.add_argument("--family-id", required=True)
    premature.add_argument("--by", required=True)


    run_cmd = lab03_commands.add_parser("run", help="Run one held-out position through an adapter.")
    run_cmd.add_argument("--report-dir", type=Path, required=True)
    run_cmd.add_argument("--freeze-id", required=True)
    run_cmd.add_argument("--position-id", required=True)
    run_cmd.add_argument("--adapter", choices=("offline-fixture", "openrouter"), required=True)
    run_cmd.add_argument("--model-id", default="offline-fixture",
                         help="Model id; defaults to 'offline-fixture' for the offline adapter.")
    run_cmd.add_argument("--by", required=True)
    run_cmd.add_argument(
        "--resume-probe",
        action="store_true",
        help="Exactly one explicit resume after a route-wide stop, before the frozen deadline.",
    )

    list_pos = lab03_commands.add_parser("list-positions", help="List the scheduled position ids for a comparison.")
    list_pos.add_argument("--report-dir", type=Path, required=True)
    list_pos.add_argument("--freeze-id", required=True)

    struct_check = lab03_commands.add_parser("structural-check", help="Validate one returned response against the envelope contract.")
    struct_check.add_argument("--report-dir", type=Path, required=True)
    struct_check.add_argument("--freeze-id", required=True)
    struct_check.add_argument("--position-id", required=True)

    interrupted = lab03_commands.add_parser(
        "record-interrupted",
        help="Close a dispatched position whose process ended before terminal evidence was recorded.",
    )
    interrupted.add_argument("--report-dir", type=Path, required=True)
    interrupted.add_argument("--freeze-id", required=True)
    interrupted.add_argument("--position-id", required=True)
    interrupted.add_argument("--reason", required=True)
    interrupted.add_argument("--by", required=True)

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
    assess.add_argument("--by", required=True)


    status_cmd = lab03_commands.add_parser(
        "status",
        help="Read-only resume bootstrap: comparison ids, routes, and position states.",
    )
    status_cmd.add_argument("--report-dir", type=Path, required=True)

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
    completion.add_argument("--by", required=True)

    verify_lab03_cmd = lab03_commands.add_parser("verify", help="Commit-first verification of Laboratory 03.")
    verify_lab03_cmd.add_argument("--report-dir", type=Path, required=True)
    verify_lab03_cmd.add_argument("--final-commit", required=True)

    lab04 = commands.add_parser("lab04", help="Run the Laboratory 04 retrieval workflow.")
    lab04_commands = lab04.add_subparsers(dest="lab04_command", required=True)

    prepare_boundaries = lab04_commands.add_parser(
        "prepare-boundaries",
        help="Apply both supplied chunking configurations and preserve every provenance link.",
    )
    prepare_boundaries.add_argument("--report-dir", type=Path, required=True)

    record_boundary = lab04_commands.add_parser(
        "record-boundary-decision",
        help="Record the engineering team's selected chunking configuration.",
    )
    record_boundary.add_argument("--report-dir", type=Path, required=True)
    record_boundary.add_argument("--chunking-configuration-id", required=True)
    record_boundary.add_argument("--rationale", required=True)
    record_boundary.add_argument("--by", required=True)

    verify_stage_b_command = lab04_commands.add_parser(
        "verify-stage-b",
        help="Verify the Laboratory 04 Stage B evidence without making the human decision.",
    )
    verify_stage_b_command.add_argument("--report-dir", type=Path, required=True)

    fetch_model = lab04_commands.add_parser(
        "fetch-embedding-model",
        help="Acquire the pinned local embedding model once and record its provenance.",
    )
    fetch_model.add_argument("--model-dir", type=Path, required=True)
    fetch_model.add_argument("--fixture", type=Path, default=DEFAULT_STAGE_C1_FIXTURE)

    prepare_embeddings = lab04_commands.add_parser(
        "prepare-embeddings",
        help="Produce one compatible retrieval-unit embedding for every included retrieval unit.",
    )
    prepare_embeddings.add_argument("--report-dir", type=Path, required=True)
    prepare_embeddings.add_argument("--model-dir", type=Path)
    prepare_embeddings.add_argument("--fixture", type=Path, default=DEFAULT_STAGE_C1_FIXTURE)

    prepare_index = lab04_commands.add_parser(
        "prepare-index",
        help="Bind the compatible embeddings and their associations into one vector index.",
    )
    prepare_index.add_argument("--report-dir", type=Path, required=True)
    prepare_index.add_argument("--fixture", type=Path, default=DEFAULT_STAGE_C1_FIXTURE)

    check_bindings = lab04_commands.add_parser(
        "check-index-bindings",
        help="Compare the required bindings with the recorded index manifest before use.",
    )
    check_bindings.add_argument("--report-dir", type=Path, required=True)
    check_bindings.add_argument("--required-retrieval-configuration-id", required=True)
    check_bindings.add_argument("--fixture", type=Path, default=DEFAULT_STAGE_C1_FIXTURE)

    verify_stage_c1_command = lab04_commands.add_parser(
        "verify-stage-c1",
        help="Verify the Laboratory 04 Stage C1 evidence without executing retrieval.",
    )
    verify_stage_c1_command.add_argument("--report-dir", type=Path, required=True)
    verify_stage_c1_command.add_argument("--fixture", type=Path, default=DEFAULT_STAGE_C1_FIXTURE)

    execute = lab04_commands.add_parser("execute-retrieval", help="Produce one ranked candidate output.")
    execute.add_argument("--report-dir", type=Path, required=True)
    execute.add_argument("--case-id", required=True, choices=["Evaluation Case A", "Evaluation Case B"])
    execute.add_argument("--configuration-id", required=True, choices=[
        "lexical retrieval", "embedding-based retrieval", "hybrid retrieval",
        "lexical retrieval followed by embedding-based reranking"])
    execute.add_argument("--fixture", type=Path, default=DEFAULT_STAGE_C1_FIXTURE)
    execute.add_argument("--model-dir", type=Path)
    verify_c2 = lab04_commands.add_parser("verify-stage-c2", help="Independently recompute the eight retrieval outputs.")
    verify_c2.add_argument("--report-dir", type=Path, required=True)
    verify_c2.add_argument("--fixture", type=Path, default=DEFAULT_STAGE_C1_FIXTURE)
    verify_c2.add_argument("--model-dir", type=Path)

    record_judgments = lab04_commands.add_parser("record-relevance-judgments", help="Record the designated human evaluator's relevance judgments.")
    record_judgments.add_argument("--report-dir", type=Path, required=True)
    record_judgments.add_argument("--judgments", type=Path, required=True)
    record_judgments.add_argument("--evaluator", required=True)
    compute_metrics = lab04_commands.add_parser("compute-retrieval-metrics", help="Compute precision@k and recall@k with explicit numerators and denominators.")
    compute_metrics.add_argument("--report-dir", type=Path, required=True)
    compute_metrics.add_argument("--fixture", type=Path, default=DEFAULT_STAGE_C1_FIXTURE)
    compute_metrics.add_argument("--model-dir", type=Path)
    verify_c3 = lab04_commands.add_parser("verify-stage-c3", help="Independently recompute the Stage C3 metric arithmetic.")
    verify_c3.add_argument("--report-dir", type=Path, required=True)
    verify_c3.add_argument("--fixture", type=Path, default=DEFAULT_STAGE_C1_FIXTURE)
    verify_c3.add_argument("--model-dir", type=Path)
    measure_op = lab04_commands.add_parser("measure-operational-evidence", help="Measure the declared operational-evidence items per configuration.")
    measure_op.add_argument("--report-dir", type=Path, required=True)
    measure_op.add_argument("--fixture", type=Path, default=DEFAULT_STAGE_C1_FIXTURE)
    measure_op.add_argument("--model-dir", type=Path)
    measure_op.add_argument("--runs", type=int, default=3)
    decision = lab04_commands.add_parser("record-configuration-decision", help="Record one bounded configuration decision.")
    decision.add_argument("--report-dir", type=Path, required=True)
    decision.add_argument("--selected-configuration", required=True, choices=[
        "lexical retrieval", "embedding-based retrieval", "hybrid retrieval",
        "lexical retrieval followed by embedding-based reranking"])
    decision.add_argument("--rationale", required=True)
    decision.add_argument("--decided-by", required=True)
    validate_report_cmd = lab04_commands.add_parser(
        "validate-report",
        help="Validate the Laboratory 04 source report, screenshots, and evidence inventory.",
    )
    validate_report_cmd.add_argument("--report-dir", type=Path, required=True)
    verify_lab04_cmd = lab04_commands.add_parser(
        "verify",
        help="Commit-first verification of Laboratory 04.",
    )
    verify_lab04_cmd.add_argument("--report-dir", type=Path, required=True)
    verify_lab04_cmd.add_argument("--final-commit", required=True)

    lab05 = commands.add_parser("lab05", help="Run the Laboratory 05 RAG workflow.")
    lab05_commands = lab05.add_subparsers(dest="lab05_command", required=True)
    apply_rewriting = lab05_commands.add_parser(
        "apply-query-rewriting",
        help="Apply QR-05-v1 to the supplied information needs.",
    )
    apply_rewriting.add_argument("--report-dir", type=Path, required=True)
    apply_rewriting.add_argument("--fixture", type=Path, default=DEFAULT_LAB05_STAGE_B_FIXTURE)
    verify_lab05_b = lab05_commands.add_parser(
        "verify-query-rewriting",
        help="Recompute the Laboratory 05 query-rewriting outcomes.",
    )
    verify_lab05_b.add_argument("--report-dir", type=Path, required=True)
    verify_lab05_b.add_argument("--fixture", type=Path, default=DEFAULT_LAB05_STAGE_B_FIXTURE)
    apply_selection = lab05_commands.add_parser(
        "apply-retrieval-unit-selection",
        help="Apply RUS-05-v1 to one stipulated ranked candidate output.",
    )
    apply_selection.add_argument("--report-dir", type=Path, required=True)
    apply_selection.add_argument("--fixture", type=Path, default=DEFAULT_LAB05_SELECTION_FIXTURE)
    verify_selection = lab05_commands.add_parser(
        "verify-retrieval-unit-selection",
        help="Recompute the Laboratory 05 retrieval-unit selection record.",
    )
    verify_selection.add_argument("--report-dir", type=Path, required=True)
    verify_selection.add_argument("--fixture", type=Path, default=DEFAULT_LAB05_SELECTION_FIXTURE)

    apply_context = lab05_commands.add_parser(
        "apply-context-construction",
        help="Assemble one bounded model request from the selection record.",
    )
    apply_context.add_argument("--report-dir", type=Path, required=True)
    apply_context.add_argument("--fixture", type=Path, default=DEFAULT_LAB05_CONTEXT_FIXTURE)
    verify_context = lab05_commands.add_parser(
        "verify-context-construction",
        help="Recompute the Laboratory 05 bounded model request.",
    )
    verify_context.add_argument("--report-dir", type=Path, required=True)
    verify_context.add_argument("--fixture", type=Path, default=DEFAULT_LAB05_CONTEXT_FIXTURE)

    prepare_generation = lab05_commands.add_parser(
        "prepare-generation-cases",
        help="Freeze two generation configuration roles and prepare three evaluation cases.",
    )
    prepare_generation.add_argument("--report-dir", type=Path, required=True)
    prepare_generation.add_argument("--fixture", type=Path, default=DEFAULT_LAB05_GENERATION_FIXTURE)
    prepare_generation.add_argument("--baseline-model-id", required=True)
    prepare_generation.add_argument("--candidate-model-id", required=True)
    prepare_generation.add_argument("--by", required=True)
    run_generation = lab05_commands.add_parser(
        "run-generation-agy",
        help="Execute one frozen generation case through AGY.",
    )
    run_generation.add_argument("--report-dir", type=Path, required=True)
    run_generation.add_argument(
        "--role", choices=("experiment baseline", "candidate configuration"), required=True
    )
    run_generation.add_argument(
        "--evaluation-case-id", choices=("EC-05-1", "EC-05-2", "EC-05-3"), required=True
    )
    run_generation.add_argument("--schema", type=Path, default=DEFAULT_LAB05_GENERATION_SCHEMA)
    run_generation.add_argument("--by", required=True)
    verify_generation = lab05_commands.add_parser(
        "verify-generation-outputs",
        help="Verify claim citations and required refusal outcomes without judging support.",
    )
    verify_generation.add_argument("--report-dir", type=Path, required=True)
    prepare_conditions = lab05_commands.add_parser(
        "prepare-acceptance-conditions",
        help="Freeze the declared acceptance conditions under SEP-05-1.",
    )
    prepare_conditions.add_argument("--report-dir", type=Path, required=True)
    prepare_conditions.add_argument("--fixture", type=Path, default=DEFAULT_LAB05_ACCEPTANCE_FIXTURE)
    record_judgment = lab05_commands.add_parser(
        "record-generation-judgment",
        help="Record one human-evaluator rubric judgment for one observed outcome.",
    )
    record_judgment.add_argument("--report-dir", type=Path, required=True)
    record_judgment.add_argument(
        "--role", choices=("experiment baseline", "candidate configuration"), required=True
    )
    record_judgment.add_argument(
        "--evaluation-case-id", choices=("EC-05-1", "EC-05-2", "EC-05-3"), required=True
    )
    record_judgment.add_argument("--judgment", choices=("pass", "fail"), required=True)
    record_judgment.add_argument("--rationale", required=True)
    record_judgment.add_argument("--review-minutes", type=float, required=True)
    record_judgment.add_argument("--by", required=True)
    calculate_rate = lab05_commands.add_parser(
        "calculate-rubric-pass-rate",
        help="Calculate the rubric pass rate separately for each configuration role.",
    )
    calculate_rate.add_argument("--report-dir", type=Path, required=True)
    evaluate_conditions = lab05_commands.add_parser(
        "evaluate-acceptance-conditions",
        help="Evaluate every declared acceptance condition for each configuration role.",
    )
    evaluate_conditions.add_argument("--report-dir", type=Path, required=True)
    record_decision = lab05_commands.add_parser(
        "record-configuration-decision",
        help="Record the bounded configuration decision for the concept-proposal operation.",
    )
    record_decision.add_argument("--report-dir", type=Path, required=True)
    record_decision.add_argument(
        "--decision",
        choices=(
            "adopt the candidate configuration",
            "do not adopt the candidate configuration",
        ),
        required=True,
    )
    record_decision.add_argument("--rationale", required=True)
    record_decision.add_argument("--by", required=True)
    verify_evaluation = lab05_commands.add_parser(
        "verify-evaluation-outputs",
        help="Verify judgments, rates, conditions, and the decision without judging support.",
    )
    verify_evaluation.add_argument("--report-dir", type=Path, required=True)
    lab05_validate_report = lab05_commands.add_parser(
        "validate-report",
        help="Validate the Laboratory 05 source report, screenshots, and evidence inventory.",
    )
    lab05_validate_report.add_argument("--report-dir", type=Path, required=True)
    lab05_verify = lab05_commands.add_parser(
        "verify",
        help="Commit-first verification of Laboratory 05.",
    )
    lab05_verify.add_argument("--report-dir", type=Path, required=True)
    lab05_verify.add_argument("--final-commit", required=True)

    lab06 = commands.add_parser("lab06", help="Prepare a reviewed prerequisite graph.")
    lab06_commands = lab06.add_subparsers(dest="lab06_command", required=True)
    prepare_graph_review = lab06_commands.add_parser("prepare-graph-review")
    prepare_graph_review.add_argument("--output", type=Path, required=True)
    apply_graph_review = lab06_commands.add_parser("apply-graph-review")
    apply_graph_review.add_argument("--review", type=Path, required=True)
    apply_graph_review.add_argument("--collection", type=Path, required=True)
    compile_graph = lab06_commands.add_parser("compile-graph")
    compile_graph.add_argument("--collection", type=Path, required=True)
    compile_graph.add_argument("--output", type=Path, required=True)
    verify_graph = lab06_commands.add_parser("verify-graph")
    verify_graph.add_argument("--collection", type=Path, required=True)
    verify_graph.add_argument("--graph", type=Path, required=True)
    query_paths = lab06_commands.add_parser("query-paths")
    query_paths.add_argument("--collection", type=Path, required=True)
    query_paths.add_argument("--graph", type=Path, required=True)
    query_paths.add_argument("--start", required=True)
    query_paths.add_argument("--max-edges", type=int, choices=(1, 2), required=True)
    query_paths.add_argument("--output", type=Path, required=True)
    direct_edge = lab06_commands.add_parser("inspect-direct-edge")
    direct_edge.add_argument("--collection", type=Path, required=True)
    direct_edge.add_argument("--graph", type=Path, required=True)
    direct_edge.add_argument("--start", required=True)
    direct_edge.add_argument("--target", required=True)
    direct_edge.add_argument("--output", type=Path, required=True)

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
                training_project / "cases" / "lab03" / "development" / "dev-common-inputs.json",
                expected_cases=2,
            )
            dev_cases = dev_family["cases"]
            build_positions(
                comparison_dir=dev_dir,
                family={"family_id": "dev-common", "cases": dev_cases},
                kind="development",
                cases=dev_cases,
            )
        schedule = json.loads(dev_schedule_path.read_text(encoding="utf-8"))
        position = next(
            (item for item in schedule["positions"] if item["position_id"] == args.position_id),
            None,
        )
        if position is None:
            raise WorkflowError(f"Unknown position {args.position_id}.")
        instructions = instructions_for(
            report_dir,
            training_project,
            required_variants={position["variant"]},
        )
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
    if command == "dev-structural-check":
        result = structural_check(
            comparison_dir=report_dir / "development",
            position_id=args.position_id,
        )
        print(
            f"Development structural check for {args.position_id}: "
            f"{'valid' if result['valid'] else 'invalid'}."
        )
        for error in result["errors"]:
            print(f"  - {error}")
        return 0 if result["valid"] else 1
    if command == "dev-record-interrupted":
        record_interrupted_position(
            comparison_dir=report_dir / "development",
            position_id=args.position_id,
            reason=args.reason,
            student=args.by,
        )
        print(f"Recorded interrupted development position {args.position_id} as failed.")
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
        print(
            f"Froze comparison {manifest['freeze_id']}; "
            f"eligible reserve families: {manifest['eligible_reserve_count_at_freeze']}."
        )
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
    if command == "record-premature-exposure":
        ledger = ExposureLedger(report_dir / "exposure-ledger.json")
        record_premature_exposure(ledger=ledger, family_id=args.family_id, student=args.by)
        print(f"Recorded premature exposure of family {args.family_id}.")
        return 0

    if command == "run":
        cmp_dir = comparison_dir(args.freeze_id)
        schedule = json.loads((cmp_dir / "schedule.json").read_text(encoding="utf-8"))
        revealed = json.loads((cmp_dir / "revealed-family.json").read_text(encoding="utf-8"))
        cases_by_id = {c["case_id"]: c for c in revealed["family"]["cases"]}
        instructions = load_frozen_instructions(cmp_dir)
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
            resume_probe=args.resume_probe,
        )
        print(f"Position {args.position_id}: {result['outcome']}"
              + (f" ({result['failure_class']})" if "failure_class" in result else "") + ".")
        metadata_path = cmp_dir / "attempts" / args.position_id / "run-metadata.json"
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            if metadata.get("observed_model"):
                print(f"Observed provider-resolved model: {metadata['observed_model']} "
                      "(reported evidence; the requested route identifier remains frozen).")
        return 0
    if command == "list-positions":
        cmp_dir = comparison_dir(args.freeze_id)
        schedule = json.loads((cmp_dir / "schedule.json").read_text(encoding="utf-8"))
        by_id = {position["position_id"]: position for position in schedule["positions"]}
        for position_id in schedule["order"]:
            print(f"{position_id}\t{by_id[position_id]['state']}")
        return 0
    if command == "structural-check":
        result = structural_check(
            comparison_dir=comparison_dir(args.freeze_id), position_id=args.position_id
        )
        print(f"Structural check for {args.position_id}: {'valid' if result['valid'] else 'invalid'}.")
        for error in result["errors"]:
            print(f"  - {error}")
        return 0 if result["valid"] else 1
    if command == "record-interrupted":
        record_interrupted_position(
            comparison_dir=comparison_dir(args.freeze_id),
            position_id=args.position_id,
            reason=args.reason,
            student=args.by,
        )
        print(f"Recorded interrupted position {args.position_id} as failed.")
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
            "assessed_by": args.by,
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

    if command == "status":
        summary = lab03_status(report_dir=report_dir)
        print(json.dumps(summary, indent=2, ensure_ascii=False))
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
        detail = validate_completion_detail(detail)
        detail = {**detail, "recorded_by": args.by}
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


def _run_lab04(args: argparse.Namespace) -> int:
    command = args.lab04_command
    if command == "prepare-boundaries":
        path = prepare_boundary_comparison(fixture_path=DEFAULT_STAGE_B_FIXTURE, report_dir=args.report_dir)
        print(f"Prepared the boundary comparison at {path}.")
        return 0
    if command == "record-boundary-decision":
        path = record_boundary_decision(
            report_dir=args.report_dir,
            selected_chunking_configuration_id=args.chunking_configuration_id,
            rationale=args.rationale,
            student=args.by,
        )
        print(f"Recorded the boundary decision at {path}.")
        return 0
    if command == "verify-stage-b":
        verification = verify_stage_b(report_dir=args.report_dir)
        print(
            "Laboratory 04 Stage B verification "
            f"{verification['outcome']} for {verification['selected chunking configuration']}."
        )
        return 0
    if command == "fetch-embedding-model":
        provenance = fetch_embedding_model(model_dir=args.model_dir, fixture_path=args.fixture)
        print(
            f"Acquired the declared local embedding model {provenance['embedding model']} "
            f"at revision {provenance['model revision']} in {args.model_dir}."
        )
        return 0
    if command == "prepare-embeddings":
        path = prepare_retrieval_unit_embeddings(
            report_dir=args.report_dir,
            fixture_path=args.fixture,
            model_dir=args.model_dir,
        )
        print(f"Prepared the retrieval-unit embeddings at {path}.")
        return 0
    if command == "prepare-index":
        path = prepare_vector_index(report_dir=args.report_dir, fixture_path=args.fixture)
        print(f"Prepared the vector index at {path}.")
        return 0
    if command == "check-index-bindings":
        record = check_index_bindings(
            report_dir=args.report_dir,
            fixture_path=args.fixture,
            required_retrieval_configuration_id=args.required_retrieval_configuration_id,
        )
        if record["outcome"] == "admissible":
            print(
                f"The vector index identified by index version {record['index version']} is admissible for "
                f"{record['required retrieval configuration id']}."
            )
        else:
            print(
                f"The vector index identified by index version {record['index version']} is stale for "
                f"{record['required retrieval configuration id']}; failed binding: "
                f"{record['failed binding']}. Rebuild condition: {record['rebuild condition']}."
            )
        return 0
    if command == "verify-stage-c1":
        verification = verify_stage_c1(report_dir=args.report_dir, fixture_path=args.fixture)
        print(f"Laboratory 04 Stage C1 verification {verification['outcome']} for {verification['index version']}.")
        return 0
    if command == "execute-retrieval":
        path = execute_retrieval(report_dir=args.report_dir, c1_fixture_path=args.fixture,
                                 case_id=args.case_id, configuration_id=args.configuration_id, model_dir=args.model_dir)
        print(f"Ranked candidate output at {path}.")
        return 0
    if command == "verify-stage-c2":
        verification = verify_stage_c2(report_dir=args.report_dir, c1_fixture_path=args.fixture, model_dir=args.model_dir)
        print(f"Laboratory 04 Stage C2 verification {verification['outcome']} for {verification['verified outputs']} outputs.")
        return 0
    if command == "record-relevance-judgments":
        path = lab04_evaluation.record_relevance_judgments(report_dir=args.report_dir,
            judgments_path=args.judgments, evaluator=args.evaluator)
        print(f"Relevance judgments recorded at {path}.")
        return 0
    if command == "compute-retrieval-metrics":
        path = lab04_evaluation.compute_retrieval_metrics(report_dir=args.report_dir,
            c1_fixture_path=args.fixture, model_dir=args.model_dir)
        print(f"Retrieval metrics recorded at {path}.")
        return 0
    if command == "verify-stage-c3":
        verification = lab04_evaluation.verify_stage_c3(report_dir=args.report_dir,
            c1_fixture_path=args.fixture, model_dir=args.model_dir)
        print(f"Laboratory 04 Stage C3 verification {verification['outcome']} for {verification['verified metric entries']} metric entries.")
        return 0
    if command == "measure-operational-evidence":
        path = lab04_evaluation.measure_operational_evidence(report_dir=args.report_dir,
            c1_fixture_path=args.fixture, model_dir=args.model_dir, runs=args.runs)
        print(f"Operational evidence recorded at {path}.")
        return 0
    if command == "record-configuration-decision":
        path = lab04_evaluation.record_configuration_decision(report_dir=args.report_dir,
            selected_configuration_id=args.selected_configuration, rationale=args.rationale,
            decided_by=args.decided_by)
        print(f"Configuration decision recorded at {path}.")
        return 0
    if command == "validate-report":
        validation = validate_lab04_report(report_dir=args.report_dir)
        for item in validation["checks"]:
            if item["status"] != "passed":
                print(f"{item['check_id']}: {item['message']}", file=sys.stderr)
        print(f"Laboratory 04 report validation {validation['status']}.")
        return 0 if validation["status"] == "passed" else 1
    if command == "verify":
        report = verify_lab04(report_dir=args.report_dir, final_commit=args.final_commit)
        for item in report["checks"]:
            if item["status"] != "passed":
                print(f"{item['check_id']}: {item['message']}", file=sys.stderr)
        print(f"Laboratory 04 verification {report['outcome']} for final commit {report['final_commit']}.")
        return 0 if report["outcome"] == "passed" else 1
    raise WorkflowError(f"Unknown Laboratory 04 command: {command}")


def _run_lab05(args: argparse.Namespace) -> int:
    command = args.lab05_command
    if command == "apply-query-rewriting":
        path = apply_query_rewriting(fixture_path=args.fixture, report_dir=args.report_dir)
        print(f"Prepared the query-rewriting result at {path}.")
        return 0
    if command == "verify-query-rewriting":
        verification = verify_lab05_stage_b(fixture_path=args.fixture, report_dir=args.report_dir)
        print(f"Query-rewriting verification passed for {verification['verified cases']} cases.")
        return 0
    if command == "apply-retrieval-unit-selection":
        path = apply_retrieval_unit_selection(fixture_path=args.fixture, report_dir=args.report_dir)
        print(f"Prepared the selection record at {path}.")
        return 0
    if command == "verify-retrieval-unit-selection":
        verification = verify_retrieval_unit_selection(fixture_path=args.fixture, report_dir=args.report_dir)
        print(
            "Retrieval-unit selection verification passed for "
            f"{verification['selected retrieval units']} selected and "
            f"{verification['excluded retrieval units']} excluded retrieval units."
        )
        return 0
    if command == "apply-context-construction":
        path = apply_context_construction(fixture_path=args.fixture, report_dir=args.report_dir)
        print(f"Prepared the bounded model request at {path}.")
        return 0
    if command == "verify-context-construction":
        verification = verify_context_construction(fixture_path=args.fixture, report_dir=args.report_dir)
        print(
            "Context-construction verification passed for "
            f"{verification['required fields']} required and "
            f"{verification['excluded request fields']} excluded request fields."
        )
        return 0
    if command == "prepare-generation-cases":
        result = prepare_generation_cases(
            fixture_path=args.fixture,
            report_dir=args.report_dir,
            baseline_model_id=args.baseline_model_id,
            candidate_model_id=args.candidate_model_id,
            recorded_by=args.by,
        )
        print(f"Prepared {len(result['requests'])} generation cases at {args.report_dir / 'generation'}.")
        return 0
    if command == "run-generation-agy":
        result = run_generation_agy(
            report_dir=args.report_dir,
            role=args.role,
            evaluation_case_id=args.evaluation_case_id,
            schema_path=args.schema,
            recorded_by=args.by,
        )
        print(
            f"Recorded {args.role} outcome for {args.evaluation_case_id} "
            f"at {result['raw outcome']}."
        )
        return 0
    if command == "verify-generation-outputs":
        result = verify_generation_outputs(report_dir=args.report_dir)
        print(
            "Generation verification passed for "
            f"{result['verified outcomes']} observed outcomes: "
            f"{result['candidate concept definitions']} candidate concept definitions, "
            f"{result['refusals']} refusals, and "
            f"{result['indirect prompt injection refusals']} indirect prompt injection refusals."
        )
        return 0
    if command == "prepare-acceptance-conditions":
        path = prepare_acceptance_conditions(
            fixture_path=args.fixture,
            report_dir=args.report_dir,
        )
        print(f"Prepared the acceptance conditions at {path}.")
        return 0
    if command == "record-generation-judgment":
        path = record_generation_judgment(
            report_dir=args.report_dir,
            role=args.role,
            evaluation_case_id=args.evaluation_case_id,
            judgment=args.judgment,
            rationale=args.rationale,
            review_minutes=args.review_minutes,
            recorded_by=args.by,
        )
        print(
            f"Recorded {args.role} judgment for {args.evaluation_case_id} at {path}."
        )
        return 0
    if command == "calculate-rubric-pass-rate":
        rates = calculate_rubric_pass_rate(report_dir=args.report_dir)
        print(
            "Calculated rubric pass rates: "
            f"experiment baseline {rates['experiment baseline']['rubric pass rate']:.2f}, "
            f"candidate configuration {rates['candidate configuration']['rubric pass rate']:.2f}."
        )
        return 0
    if command == "evaluate-acceptance-conditions":
        record = evaluate_acceptance_conditions(report_dir=args.report_dir)
        evaluation = record["acceptance condition evaluation"]
        print(
            "Evaluated acceptance conditions: "
            f"candidate configuration {evaluation['candidate configuration']['role outcome']}, "
            f"experiment baseline {evaluation['experiment baseline']['role outcome']}."
        )
        return 0
    if command == "record-configuration-decision":
        path = record_configuration_decision(
            report_dir=args.report_dir,
            decision=args.decision,
            rationale=args.rationale,
            recorded_by=args.by,
        )
        print(f"Recorded the bounded configuration decision at {path}.")
        return 0
    if command == "verify-evaluation-outputs":
        result = verify_evaluation_outputs(report_dir=args.report_dir)
        print(
            "Evaluation verification passed for "
            f"{result['judged outputs']} judged outputs: "
            f"{result['candidate concept definition passes']} candidate concept definition passes, "
            f"{result['refusal passes']} refusal passes, and "
            f"{result['bounded configuration decisions']} bounded configuration decision."
        )
        return 0
    if command == "validate-report":
        validation = validate_lab05_report(report_dir=args.report_dir)
        for item in validation["checks"]:
            if item["status"] != "passed":
                print(f"{item['check_id']}: {item['message']}", file=sys.stderr)
        print(f"Laboratory 05 report validation {validation['status']}.")
        return 0 if validation["status"] == "passed" else 1
    if command == "verify":
        report = verify_lab05(report_dir=args.report_dir, final_commit=args.final_commit)
        for item in report["checks"]:
            if item["status"] != "passed":
                print(f"{item['check_id']}: {item['message']}", file=sys.stderr)
        print(f"Laboratory 05 verification {report['outcome']} for final commit {report['final_commit']}.")
        return 0 if report["outcome"] == "passed" else 1
    raise WorkflowError(f"Unknown Laboratory 05 command: {command}")


def _run_lab06(args: argparse.Namespace) -> int:
    from . import lab06

    if args.lab06_command == "prepare-graph-review":
        path = lab06.prepare_graph_review(output=args.output)
        print(f"Prepared graph review at {path}.")
        return 0
    if args.lab06_command == "apply-graph-review":
        path = lab06.apply_graph_review(review_path=args.review, collection=args.collection)
        print(f"Stored accepted graph records at {path}.")
        return 0
    if args.lab06_command == "compile-graph":
        path = lab06.compile_graph(collection=args.collection, output=args.output)
        print(f"Compiled prerequisite graph at {path}.")
        return 0
    if args.lab06_command == "verify-graph":
        result = lab06.verify_graph(collection=args.collection, graph_path=args.graph)
        print(f"Graph verification passed for {result['nodes']} nodes and {result['edges']} edges; source support remains a human judgment.")
        return 0
    if args.lab06_command == "query-paths":
        path = lab06.query_paths(collection=args.collection, graph_path=args.graph, start=args.start,
                                 max_edges=args.max_edges, output=args.output)
        print(f"Wrote bounded graph paths at {path}; graph and collection unchanged.")
        return 0
    if args.lab06_command == "inspect-direct-edge":
        path = lab06.inspect_direct_edge(collection=args.collection, graph_path=args.graph, start=args.start,
                                         target=args.target, output=args.output)
        print(f"Wrote complete outgoing-edge inspection at {path}; no domain-level absence inferred.")
        return 0
    raise WorkflowError(f"Unknown Laboratory 06 command: {args.lab06_command}")


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
        "lab04": _run_lab04,
        "lab05": _run_lab05,
        "lab06": _run_lab06,
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
