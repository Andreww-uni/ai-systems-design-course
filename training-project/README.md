# AI Engineering training project

Status: Laboratory 01 workstation doctor and governed-proposal workflow implemented. Laboratory 02
structured-output governed workflow, AGY profile, and OpenRouter contingency implemented and
reference-sliced.

This directory holds the neutral cumulative AI system built across the eight laboratories. It runs
without access to the instructor's private repositories or personal data: every artefact you produce
here is your own.

Every student builds the same learning knowledge system. Read the supplied
[`requirements/SYSTEM_BRIEF.md`](requirements/SYSTEM_BRIEF.md) and
[`requirements/REQUIREMENTS_BASELINE.md`](requirements/REQUIREMENTS_BASELINE.md) and
[`requirements/VAULT_STRUCTURE.md`](requirements/VAULT_STRUCTURE.md) before treating a laboratory task
as a change to the system. These draft files define the fixed project and its testable obligations
for instructor review; they are project input, not requirements for the student to elicit or replace.

The clone that contains this directory is one Git repository. `origin` is the student's GitHub fork.
`upstream` is https://github.com/sobol-mo/ai-systems-design-course. Folders are not remotes.
Upstream-owned paths may be overwritten by a later instructor publication. Student work is committed
only under `student/` and `reports/` and is pushed only to `origin`.

```text
training-project/
  README.md, pyproject.toml, uv.lock, .gitignore   upstream
  boundary-proposal.yaml                           upstream starter — copy into reports/lab01/
  requirements/                                    upstream system brief, requirements baseline, vault contract
  fixtures/                                        upstream
  platform/                                        upstream
  tests/public/                                    upstream
  student/                                         student-owned — create, commit, push to origin
  reports/                                         student-owned — create, commit, push to origin
  .venv/                                           derived — never commit
```

## What is being built

The complete project helps a student preserve sources and provenance, develop accepted technical
concepts, identify missing prerequisites and unresolved questions, inspect typed relations, and answer
questions from retained evidence. AI may propose interpretations and changes. Deterministic project
rules validate available structures and workflow invariants. The student retains authority over
meaning and every accepted change. Canonical knowledge remains in an external Markdown vault;
embeddings, indexes, and graph views are rebuildable derived state.

Laboratory 01 initializes this working contour and verifies its authority boundary. It does not yet
materialize structured concepts or implement the complete knowledge-processing system.

## What exists now

Laboratory 01 contributes the governed-proposal workflow. It encodes one rule of the course: an AI
model may propose, but only a recorded human decision may accept. The workflow refuses to apply a
proposal that no human explicitly approved, and it refuses to overwrite a decision that was already
recorded. The decision contains a SHA-256 digest of the reviewed proposal, so changing proposal
content after the decision invalidates approval. Reapplying unchanged approved content is idempotent.
The `recorded_by` field is student-supplied attribution, not authenticated actor identity. On the
normal agent path, Laboratory 01 therefore also requires evidence that the AI proposer did not invoke
`decide` or `apply`. If no existing agent path can complete the local proposal operation within available
access and quota without a new purchase, the documented manual fallback requires the student to author
the same candidate, preserve the justification and any available sanitized failure evidence for
instructor acceptance, and make no AI-authorship claim. The fallback does not demonstrate live
AI/student actor separation.

The `doctor` command writes a normalized machine-readable report for a supported Windows or Linux host
and the Git, GitHub CLI, `uv`, and Obsidian capabilities. Authenticated Antigravity CLI is recorded when
present; it is not required for a green report when another agent subscription is used.

Three files carry the protocol. Their authorized writers depend on the documented proposal path:

| File | Written by | Meaning |
|---|---|---|
| `reports/lab01/boundary-proposal.yaml` | the AI, corrected by the student; or the student on the no-agent fallback | a candidate system boundary, with no authority |
| `reports/lab01/boundary-decision.json` | the `decide` command | the recorded human decision, the only authority |
| `student/design/learning-system-boundary.yaml` | the `apply` command | the accepted contract, never edited by hand |

## Running it

```bash
uv sync
uv run learning-project doctor --output reports/lab01/environment-report.json
uv run learning-project validate reports/lab01/boundary-proposal.yaml
uv run learning-project decide reports/lab01/boundary-proposal.yaml --approve --by "your-name" --decision reports/lab01/boundary-decision.json
uv run learning-project apply reports/lab01/boundary-proposal.yaml --decision reports/lab01/boundary-decision.json --output student/design/learning-system-boundary.yaml
```

`validate` changes nothing and reports every problem it finds. `decide` records your approval or
rejection, with `--reject --reason "..."` for a rejection. `apply` writes the accepted contract, and
fails if the decision is missing, pending, rejected, or points at a different proposal.
Laboratory 01 creates the report and student-design directories and copies the starter proposal into
the report directory before these commands are used. The
command-line defaults place all three files beside the proposal; the explicit paths above preserve
the course ownership boundary instead.

## Running the tests

```bash
uv run python -m unittest discover -s tests/public -v
```

The tests under `tests/public/` are the specification of the workflow. Read them before you change
the code: they state what the protocol must guarantee, not how it is implemented.

## Laboratory 02 governed structured-output workflow

Laboratory 02 registers the Module 02 theory as a source and governs the creation of one accepted
concept, `Structured Output`, from a fixed source fragment. The source record, proposals, decisions,
operations, and the accepted concept live in the external Markdown vault; run evidence, the live
comparison, the semantic review, screenshots, and the verification report live under `reports/lab02/`.

The `lab02` subcommands, in the approved order, are:

```bash
vault="/absolute/path/to/your/vault"   # set once per terminal session

uv run learning-project lab02 register-source --vault "$vault" --course-root .. \
  --theory ../modules/02_Foundation_Models_and_AI_Application_Architecture/02_Foundation_Models_and_AI_Application_Architecture_Theory.md \
  --course-repository "$(git remote get-url origin)" --course-commit "$(git rev-parse HEAD)" --by "your-name"

uv run learning-project lab02 check-fixtures --vault "$vault"

uv run learning-project lab02 prepare      --vault "$vault" --report-dir reports/lab02 --run-id live-primary-01
uv run learning-project lab02 run-agy      --report-dir reports/lab02 --run-id live-primary-01 \
  --model-id "<model-from-agy-models>" --by "your-name"
uv run learning-project lab02 import       --vault "$vault" --report-dir reports/lab02 --run-id live-primary-01 --evidence-kind live
uv run learning-project lab02 validate     --vault "$vault" --report-dir reports/lab02 \
  --proposal-id lab02-structured-output-live-primary-01 \
  --output reports/lab02/runs/live-primary-01/validation-result.json

# ... repeat prepare/run/record-run/import/validate for live-primary-02, then ...
uv run learning-project lab02 compare-live --vault "$vault" --report-dir reports/lab02 \
  --run-id live-primary-01 live-primary-02

# ... the student writes reports/lab02/semantic-review.yaml and then ...
uv run learning-project lab02 decide       --vault "$vault" --proposal-id lab02-structured-output-live-primary-01 \
  --validation reports/lab02/runs/live-primary-01/validation-result.json \
  --review reports/lab02/semantic-review.yaml --approve --by "your-name"
uv run learning-project lab02 apply        --vault "$vault" --proposal-id lab02-structured-output-live-primary-01 \
  --validation reports/lab02/runs/live-primary-01/validation-result.json \
  --review reports/lab02/semantic-review.yaml
uv run learning-project lab02 verify       --vault "$vault" --report-dir reports/lab02
```

`verify` is read-only with respect to the vault and writes only
`reports/lab02/verification-report.json`. It exits `0` when every check passes, `1` when verification
completes with failures, and `2` when required inputs cannot be read. `revise` (`--revision
reports/lab02/revisions/<id>.yaml`) creates a new human-revised proposal rather than editing a model
candidate in place; the revised candidate repeats the full validate, review, decide, and apply cycle.

`run-agy` is the primary live path and records the selected AGY model in run metadata. The tested
contingency is `run-openrouter`, which reads `OPENROUTER_API_KEY` from the process environment and uses
the pinned free profile `nex-agi/nex-n2.5-mini:free`. The adapter enforces a 120-second overall deadline
and writes no partial run evidence after a timeout. Free model availability is external and may change.
`record-run` remains available when another permitted harness writes the exact raw response itself.

Every record is write-once and every derived record binds the SHA-256 digest of its inputs. A file
never contains its own digest. The mandatory path requires two live responses; offline fixtures are
deterministic test substitutes and never satisfy the live-response requirement.

## Later laboratories

The system brief and requirements baseline define supplied project obligations and remain Work in
Progress until instructor approval. The current executable workflow contract is specified by
`tests/public/`. Sample data and model options, together with interfaces not yet defined by the
requirements or current tests, are introduced by the laboratories that need them.
